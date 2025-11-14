# Cline (VS Code) Integration

Cline stores MCP server definitions in `cline_mcp_settings.json`. On macOS with the default VS Code storage path the file lives at:

```
~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json
```

Add (or merge) the following block. It assumes this repo lives at `/Users/qm-mac/mcpserver/codex-mcp-server`.

```json
{
  "mcpServers": {
    "codex_mcp_server": {
      "command": "/Users/qm-mac/mcpserver/codex-mcp-server/bin/codex_mcp_server_client",
      "args": [],
      "env": {
        "CODEX_MCP_QUEUE_DIR": "/Users/qm-mac/mcpserver/codex-mcp-server/tmp/queue",
        "CODEX_MCP_SESSIONS_DIR": "/Users/qm-mac/mcpserver/codex-mcp-server/tmp/sessions"
      },
      "autoApprove": []
    }
  }
}
```

Notes:

- If you already have other servers defined, just append the `codex_mcp_server` entry inside the existing `mcpServers` object.
- Leave `autoApprove` empty so Cline keeps prompting before running Codex commands.
- Restart VS Code or run **Cline ➜ Reload MCP Servers** after editing the file.
