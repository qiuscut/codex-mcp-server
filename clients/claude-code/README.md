# Claude Code CLI Integration

Claude Code can register STDIO MCP servers via the built-in `claude mcp add` workflow. Run the following once (adjust the repo path if you moved it):

```bash
claude mcp add codex-mcp \
  --command /Users/qm-mac/mcpserver/codex-mcp-server/bin/codex_mcp_server_client \
  --env CODEX_MCP_QUEUE_DIR=/Users/qm-mac/mcpserver/codex-mcp-server/tmp/queue \
  --env CODEX_MCP_SESSIONS_DIR=/Users/qm-mac/mcpserver/codex-mcp-server/tmp/sessions
```

After registering you can manage it normally:

```bash
claude mcp list         # confirm codex-mcp is enabled
claude mcp enable codex-mcp
claude mcp disable codex-mcp
claude --mcp-config ~/.claude/mcp/config.json  # optional overrides per run
```

If you prefer to edit JSON directly, Claude Code accepts the same `mcpServers` structure described in the official docs. Drop in this snippet:

```json
{
  "mcpServers": {
    "codex-mcp": {
      "command": "/Users/qm-mac/mcpserver/codex-mcp-server/bin/codex_mcp_server_client",
      "args": [],
      "env": {
        "CODEX_MCP_QUEUE_DIR": "/Users/qm-mac/mcpserver/codex-mcp-server/tmp/queue",
        "CODEX_MCP_SESSIONS_DIR": "/Users/qm-mac/mcpserver/codex-mcp-server/tmp/sessions"
      }
    }
  }
}
```

Place the JSON in `~/.claude/mcp/config.json` (user scope) or alongside a repo-level `.mcp.json` (project scope). Restart the CLI or run `claude mcp reload` to apply the change.
