#!/usr/bin/env python3
"""File-based daemon that spawns `codex mcp-server` sessions on demand.

The daemon watches a queue directory for session request files. Each request should
contain a JSON payload with the following fields:
  - id: unique session identifier
  - stdin: absolute path to the FIFO the client will write into
  - stdout: absolute path to the FIFO the client will read from
  - session_dir: absolute path to the session directory (used for cleanup)
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE_DIR = ROOT_DIR / "tmp" / "queue"
DEFAULT_SESSIONS_DIR = ROOT_DIR / "tmp" / "sessions"
DEFAULT_LOG = ROOT_DIR / "logs" / "codex_mcp_daemon.log"
DEFAULT_ENTRYPOINT = ROOT_DIR / "bin" / "codex_mcp_server"
DEFAULT_PID_FILE = ROOT_DIR / ".codex_mcp_server.pid"
DEFAULT_STATUS_FILE = ROOT_DIR / "tmp" / "codex_mcp_server.status"
DEFAULT_STOP_FILE = ROOT_DIR / "tmp" / "codex_mcp_server.stop"


def log(message: str, log_handle) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_handle.write(f"[{timestamp}] {message}\n")
    log_handle.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="File watcher daemon for codex_mcp_server")
    parser.add_argument("--queue-dir", default=str(DEFAULT_QUEUE_DIR), help="Directory containing session request files")
    parser.add_argument("--sessions-dir", default=str(DEFAULT_SESSIONS_DIR), help="Directory where session FIFOs live")
    parser.add_argument("--codex-entrypoint", default=str(DEFAULT_ENTRYPOINT), help="Executable that launches `codex mcp-server`")
    parser.add_argument("--codex-arg", dest="codex_args", action="append", default=[], help="Extra argument passed to Codex (repeatable)")
    parser.add_argument("--log-file", default=str(DEFAULT_LOG), help="Daemon + child stderr log file")
    parser.add_argument("--poll-interval", type=float, default=0.2, help="Seconds between queue scans (default: 0.2)")
    parser.add_argument("--session-timeout", type=float, default=5.0, help="Seconds to wait for FIFOs before failing a session")
    parser.add_argument("--max-concurrent", type=int, default=1, help="Maximum concurrent Codex sessions (default: 1)")
    parser.add_argument("--pid-file", default=str(DEFAULT_PID_FILE), help="Path to write the daemon PID")
    parser.add_argument("--status-file", default=str(DEFAULT_STATUS_FILE), help="Heartbeat file written by the daemon")
    parser.add_argument("--stop-file", default=str(DEFAULT_STOP_FILE), help="When this file exists, the daemon shuts down")
    return parser.parse_args()


def validate_path(path: Path, base: Path) -> None:
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"{path} is outside of allowed directory {base}") from exc


def handle_session(payload: Dict[str, str], args: argparse.Namespace, log_handle, semaphore: threading.Semaphore) -> None:
    session_id = payload["id"]
    stdin_path = Path(payload["stdin"]).resolve()
    stdout_path = Path(payload["stdout"]).resolve()
    session_dir = Path(payload["session_dir"]).resolve()

    sessions_dir = Path(args.sessions_dir).resolve()
    validate_path(session_dir, sessions_dir)
    validate_path(stdin_path, sessions_dir)
    validate_path(stdout_path, sessions_dir)

    log(f"Session {session_id}: waiting for FIFOs", log_handle)
    deadline = time.time() + args.session_timeout
    while time.time() < deadline:
        if stdin_path.exists() and stdout_path.exists():
            break
        time.sleep(0.05)
    else:
        log(f"Session {session_id}: FIFOs were not created in time", log_handle)
        semaphore.release()
        return

    ready_flag = session_dir / "ready"

    try:
        ready_flag.touch(exist_ok=True)
        with open(stdin_path, "rb", buffering=0) as stdin_fifo, open(stdout_path, "wb", buffering=0) as stdout_fifo:
            cmd = [args.codex_entrypoint, *args.codex_args]
            log(f"Session {session_id}: launching {' '.join(cmd)}", log_handle)
            child = subprocess.Popen(cmd, stdin=stdin_fifo, stdout=stdout_fifo, stderr=log_handle)
            child.wait()
            log(f"Session {session_id}: codex exited with {child.returncode}", log_handle)
    except Exception as exc:
        log(f"Session {session_id}: error {exc}", log_handle)
    finally:
        semaphore.release()
        try:
            for path in (stdin_path, stdout_path, ready_flag):
                if path.exists():
                    path.unlink()
            if session_dir.exists():
                session_dir.rmdir()
        except OSError:
            # Directory may still contain client temp files; leave it.
            pass


def main() -> int:
    args = parse_args()
    queue_dir = Path(args.queue_dir).resolve()
    sessions_dir = Path(args.sessions_dir).resolve()
    queue_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    Path(args.log_file).parent.mkdir(parents=True, exist_ok=True)

    log_handle = open(args.log_file, "a", buffering=1)
    running = True
    semaphore = threading.Semaphore(args.max_concurrent)

    def handle_signal(signum, _frame):
        nonlocal running
        log(f"Received signal {signum}; shutting down after current sessions", log_handle)
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    pid_path = Path(args.pid_file).resolve()
    status_path = Path(args.status_file).resolve()
    stop_path = Path(args.stop_file).resolve()
    status_path.parent.mkdir(parents=True, exist_ok=True)
    stop_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(str(os.getpid()))

    log("codex_mcp_fifo_daemon started", log_handle)
    try:
        while running:
            request_files = sorted(queue_dir.glob("*.json"))
            if not request_files:
                time.sleep(args.poll_interval)
                tmp_status = status_path.with_suffix(".tmp")
                tmp_status.write_text(json.dumps({"pid": os.getpid(), "timestamp": time.time(), "queue_depth": 0}))
                tmp_status.replace(status_path)
                if stop_path.exists():
                    stop_path.unlink(missing_ok=True)
                    running = False
                continue
            for request_path in request_files:
                log(f"Found request {request_path.name}", log_handle)
                if not running:
                    break
                processing_path = request_path.with_suffix(".processing")
                try:
                    request_path.rename(processing_path)
                except FileNotFoundError:
                    log(f"Request {request_path.name} disappeared before processing", log_handle)
                    continue
                try:
                    payload = json.loads(processing_path.read_text())
                except json.JSONDecodeError as exc:
                    log(f"Failed to parse {processing_path.name}: {exc}", log_handle)
                    processing_path.unlink(missing_ok=True)
                    continue

                processing_path.unlink(missing_ok=True)

                semaphore.acquire()
                worker = threading.Thread(
                    target=handle_session,
                    args=(payload, args, log_handle, semaphore),
                    daemon=True,
                )
                worker.start()
            tmp_status = status_path.with_suffix(".tmp")
            tmp_status.write_text(
                json.dumps({"pid": os.getpid(), "timestamp": time.time(), "queue_depth": len(request_files)})
            )
            tmp_status.replace(status_path)
            if stop_path.exists():
                stop_path.unlink(missing_ok=True)
                running = False
    finally:
        log("Daemon stopping", log_handle)
        log_handle.close()
        pid_path.unlink(missing_ok=True)
        status_path.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
