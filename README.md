# Codex MCP Server (macOS daemon)

This repo turns the Codex CLI into a long-lived Model Context Protocol (MCP) server that runs locally on macOS and can be consumed by any MCP-capable client (Cline, Claude Code, Claude Desktop/Code, VS Code MCP extension, Agents SDK, etc.).

## Contents

```
bin/                    # Launchers for Codex MCP server + client shim
clients/                # Ready-to-copy client config snippets
  ├── cline/
  ├── claude-code/
  └── vscode/
docs/                   # Operational notes, troubleshooting
logs/                   # Runtime + daemon logs
scripts/                # Service management + daemon
```

## Prerequisites

- macOS with Codex CLI installed (`brew install openai/codex/codex`).
- Access tokens/config already on the machine (`codex login`).
- Python 3.11+ (ships with macOS) for the FIFO daemon + client shim.
- `bash`, `nohup`, `mkfifo` (standard on macOS).

## Quick start

```bash
# Create logs/tmp dirs the first time
mkdir -p logs tmp/queue tmp/sessions

# Start the background daemon
scripts/codex-mcp-serverctl.sh start

# Check status / stop / view logs
scripts/codex-mcp-serverctl.sh status
scripts/codex-mcp-serverctl.sh logs
scripts/codex-mcp-serverctl.sh stop
```

Under the hood `codex-mcp-serverctl.sh` bootstraps `scripts/codex_mcp_fifo_daemon.py`, which:

1. Watches `tmp/queue` for new session requests.
2. Creates FIFO pipes in `tmp/sessions/<session-id>`.
3. Spawns `bin/codex_mcp_server` (`codex mcp-server`) for each connection.
4. Streams stdin/stdout between the FIFOs and Codex.

The lightweight client shim (`bin/codex_mcp_server_client`) creates a queue entry and FIFOs, then bridges its STDIO to the daemon. MCP clients can point at the shim via `command`/`args`.

## Environment overrides

| Variable | Effect |
| --- | --- |
| `CODEX_BIN` | Path to `codex` binary (default: `codex`). |
| `CODEX_HOME` / `CODEX_CONFIG_FILE` | Use alternate Codex config directory/file. |
| `CODEX_MCP_QUEUE_DIR`, `CODEX_MCP_SESSIONS_DIR` | Override queue/session folders (defaults under repo `tmp/`). |
| `CODEX_MCP_LOG_DIR` | Relocate daemon + server logs. |
| `CODEX_MCP_STARTUP_DELAY`, `CODEX_MCP_STATUS_TTL` | Tune controller start/health thresholds. |

Set them before invoking the control script, e.g. `CODEX_BIN=/opt/homebrew/bin/codex scripts/codex-mcp-serverctl.sh start`.

## Health checks

- `scripts/codex-mcp-serverctl.sh status` → prints PID + heartbeat age.
- `bin/codex_mcp_server_client < /dev/null` → opens + immediately closes a Codex MCP session (verifies queue, FIFOs, spawn path). Exit code `0` means success.
- `tail -f logs/codex_mcp_daemon.log` → shows per-session lifecycle events.

## Client integrations

See `clients/` for copy/paste config files:

- `clients/cline/README.md` – VS Code Cline extension (`cline_mcp_settings.json`).
- `clients/claude-code/README.md` – Claude Code CLI (`claude mcp add` or `--mcp-config`).
- `clients/vscode/README.md` – official MCP VS Code extension.

Each snippet already uses absolute paths that assume the repo lives at `/Users/qm-mac/mcpserver/codex-mcp-server`. Adjust paths if you move the repo.

## Testing results (latest run)

- Daemon started via `scripts/codex-mcp-serverctl.sh start` (PID recorded in `logs/codex_mcp_server.log`).
- Handshake test: `bin/codex_mcp_server_client < /dev/null` exited 0 and daemon log shows the session (ID `3a5dc768643248719486bc59b5bbfee0`).
- Status command shows `Running (PID … heartbeat <1s)`.

If any step fails, consult `docs/troubleshooting.md` (or create it) and the log files.
