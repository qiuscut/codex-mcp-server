# VS Code MCP Extension

If you use the official [Model Context Protocol](https://marketplace.visualstudio.com/items?itemName=modelcontextprotocol.modelcontextprotocol-vscode) extension, add the server under the `modelContextProtocol.mcpServers` setting.

Either edit global settings (`~/Library/Application Support/Code/User/settings.json`) or workspace `.vscode/settings.json`:

```json
{
  "modelContextProtocol.mcpServers": {
    "codex-mcp-server": {
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

Reload VS Code (or run the “Model Context Protocol: Reload MCP Servers” command). Once connected, the extension exposes the `codex` and `codex-reply` tools exactly as if Codex were running locally.
