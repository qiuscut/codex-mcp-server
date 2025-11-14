#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENTRYPOINT="${ENTRYPOINT:-$ROOT_DIR/scripts/codex_mcp_fifo_daemon.py}"
PID_FILE="${PID_FILE:-$ROOT_DIR/.codex_mcp_server.pid}"
STATUS_FILE="${STATUS_FILE:-$ROOT_DIR/tmp/codex_mcp_server.status}"
STOP_FILE="${STOP_FILE:-$ROOT_DIR/tmp/codex_mcp_server.stop}"
LOG_DIR="${CODEX_MCP_LOG_DIR:-$ROOT_DIR/logs}"
LOG_FILE="$LOG_DIR/codex_mcp_server.log"
STARTUP_DELAY="${CODEX_MCP_STARTUP_DELAY:-2}"
STATUS_TTL="${CODEX_MCP_STATUS_TTL:-5}"

usage() {
  cat <<'USAGE'
Usage: scripts/codex-mcp-serverctl.sh <start|stop|restart|status|logs|run> [-- extra args]

Commands:
  start [-- <codex args>]     Start the Codex MCP server in the background (logs -> logs/codex_mcp_server.log)
  stop                        Stop the background server if running
  restart [-- <codex args>]   Restart the server (stop + start)
  status                      Print whether the background server is running
  logs                        Tail the background server log (Ctrl+C to exit)
  run [-- <codex args>]       Run the server in the foreground (no daemonization)
USAGE
}

ensure_log_dir() {
  mkdir -p "$LOG_DIR"
  mkdir -p "$(dirname "$STATUS_FILE")"
}

is_running() {
  local snapshot
  snapshot=$(python3 - "$STATUS_FILE" "$STATUS_TTL" <<'PY'
import json, sys, time, pathlib
path = pathlib.Path(sys.argv[1])
ttl = float(sys.argv[2])
if not path.exists():
    sys.exit(1)
try:
    data = json.loads(path.read_text())
except Exception:
    sys.exit(1)
ts = float(data.get("timestamp", 0))
pid = int(data.get("pid", 0))
age = time.time() - ts
if age > ttl or pid <= 0:
    sys.exit(1)
print(f"{pid} {age:.2f}")
PY
  ) || return 1
  RUNNING_PID="${snapshot%% *}"
  RUNNING_AGE="${snapshot#* }"
  return 0
}

start_server() {
  if is_running; then
    echo "[codex_mcp_server] Already running (PID $RUNNING_PID)"
    return 0
  fi

  ensure_log_dir
  rm -f "$STOP_FILE" "$PID_FILE"
  if (($#)); then
    echo "[codex_mcp_server] Starting via $ENTRYPOINT $*" | tee -a "$LOG_FILE"
    nohup "$ENTRYPOINT" "$@" >>"$LOG_FILE" 2>&1 &
  else
    echo "[codex_mcp_server] Starting via $ENTRYPOINT (no extra args)" | tee -a "$LOG_FILE"
    nohup "$ENTRYPOINT" >>"$LOG_FILE" 2>&1 &
  fi
  local pid=$!
  echo "$pid" >"$PID_FILE"
  disown "$pid" 2>/dev/null || true
  local timeout=${STARTUP_DELAY%.*}
  if [[ -z "$timeout" || ! "$timeout" =~ ^[0-9]+$ ]]; then
    timeout=2
  fi
  if (( timeout <= 0 )); then
    timeout=2
  fi
  local start_epoch=$(date +%s)
  while true; do
    if is_running; then
      echo "[codex_mcp_server] Started (PID $pid). Logs: $LOG_FILE"
      return 0
    fi
    local now=$(date +%s)
    if (( now - start_epoch >= timeout )); then
      break
    fi
    sleep 0.5
  done
  echo "[codex_mcp_server] Failed to start. Check $LOG_FILE for details." >&2
  return 1
}

stop_server() {
  if ! is_running; then
    echo "[codex_mcp_server] Not running"
    return 0
  fi
  touch "$STOP_FILE"
  echo "[codex_mcp_server] Stop signal written"
  for attempt in {1..30}; do
    if ! is_running; then
      break
    fi
    sleep 0.5
  done
  rm -f "$PID_FILE"
  rm -f "$STOP_FILE"
  echo "[codex_mcp_server] Stopped"
}

status_server() {
  if is_running; then
    echo "[codex_mcp_server] Running (PID $RUNNING_PID, heartbeat ${RUNNING_AGE}s ago)"
  else
    echo "[codex_mcp_server] Not running"
  fi
}

logs_server() {
  ensure_log_dir
  touch "$LOG_FILE"
  tail -F "$LOG_FILE"
}

run_foreground() {
  echo "[codex_mcp_server] Running in foreground via $ENTRYPOINT $*"
  exec "$ENTRYPOINT" "$@"
}

COMMAND=${1:-help}
shift || true

# Allow passing extra Codex arguments after `--`
declare -a EXTRA_ARGS=()
if [[ "$COMMAND" =~ ^(start|restart|run)$ ]]; then
  if [[ "${1:-}" == "--" ]]; then
    shift
  fi
  EXTRA_ARGS=("$@")
fi

case "$COMMAND" in
  start)
    if ((${#EXTRA_ARGS[@]})); then
      start_server "${EXTRA_ARGS[@]}"
    else
      start_server
    fi
    ;;
  stop)
    stop_server
    ;;
  restart)
    stop_server
    if ((${#EXTRA_ARGS[@]})); then
      start_server "${EXTRA_ARGS[@]}"
    else
      start_server
    fi
    ;;
  status)
    status_server
    ;;
  logs)
    logs_server
    ;;
  run)
    if ((${#EXTRA_ARGS[@]})); then
      run_foreground "${EXTRA_ARGS[@]}"
    else
      run_foreground
    fi
    ;;
  *)
    usage
    exit 1
    ;;
esac
