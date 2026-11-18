---
title: MCP servers
order: 8
description: Add, toggle, and remove local or remote MCP servers.
---

# MCP servers

OpenCode MCP servers live under the `mcp` key of its configuration. OMO Manager supports both local command servers and remote HTTPS servers.

## Local server

```jsonc
{
  "mcp": {
    "filesystem": {
      "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    }
  }
}
```

Commands are entered space-separated and split safely — no shell interpretation is performed.

## Remote server

```jsonc
{
  "mcp": {
    "docs": { "type": "remote", "url": "https://example.com/mcp" }
  }
}
```

Only `https://` URLs are accepted by the menu.

## Enable or disable

Use **Enable / disable** on an existing entry. This toggles its `enabled` field without deleting the definition:

```jsonc
{ "mcp": { "docs": { "type": "remote", "url": "https://example.com/mcp", "enabled": false } } }
```

Slim can also disable servers globally through its `disabled_mcps` array; that setting is preserved.
