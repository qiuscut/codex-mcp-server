# Troubleshooting Codex MCP Server

## Common symptoms

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `status` shows "Not running" right after `start` | Codex CLI crashed on boot (bad config, missing login) | Check `logs/codex_mcp_server.log` for stderr, rerun `codex login` if token expired. |
| Client shim times out waiting for daemon | Daemon not watching queue, or wrong queue path | Ensure `scripts/codex-mcp-serverctl.sh status` is healthy, confirm `CODEX_MCP_QUEUE_DIR` matches both daemon + client environment. |
| Stale FIFO directories under `tmp/sessions` | Interrupted client or crash | Safe to remove the directory manually; daemon cleans up on stop/start. |
| Codex prompts fail due to sandbox restrictions | Adjust `-c sandbox=workspace-write` etc. when starting daemon (`codex_mcp_server_client` just forwards args). |

## Log locations

- `logs/codex_mcp_server.log` – control script and `nohup` output.
- `logs/codex_mcp_daemon.log` – daemon lifecycle + per-session logs.
- `tmp/codex_mcp_server.status` – JSON heartbeat (pid/timestamp/queue depth).

Rotate/trim logs with standard tools (e.g., add `logrotate` entry or `cp /dev/null`).
