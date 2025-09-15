# Claude Desktop Integration

Claude Desktop supports MCP servers via a config file with a `mcpServers` map.

Config file locations
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Example config (Standard MCP servers)
```
{
  "mcpServers": {
    "oci-iam": {
      "command": "mcp-oci-serve-iam",
      "args": ["--profile", "DEFAULT", "--region", "eu-frankfurt-1", "--log-level", "INFO"]
    },
    "oci-compute": {
      "command": "mcp-oci-serve-compute",
      "args": ["--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
    },
    "oci-usageapi": {
      "command": "mcp-oci-serve-usageapi",
      "args": ["--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
    },
    "oci-monitoring": {
      "command": "mcp-oci-serve-monitoring",
      "args": ["--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
    },
    "oci-loganalytics": {
      "command": "mcp-oci-serve-loganalytics",
      "args": ["--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
    },
    "oci-introspect": {
      "command": "mcp-oci-serve-introspect",
      "args": []
    }
  }
}
```

Example config (FastMCP servers - recommended for better performance)
```
{
  "mcpServers": {
    "oci-iam-fast": {
      "command": "mcp-oci-serve-fast",
      "args": ["iam", "--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
    },
    "oci-compute-fast": {
      "command": "mcp-oci-serve-fast",
      "args": ["compute", "--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
    },
    "oci-usageapi-fast": {
      "command": "mcp-oci-serve-fast",
      "args": ["usageapi", "--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
    }
  }
}
```

Docker-based servers
Replace the command with a Docker invocation, for example:
```
"command": "docker",
"args": ["run", "--rm", "-i", "-v", "${HOME}/.oci:/root/.oci", "mcp-oci", "mcp-oci-serve-iam", "--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
```

Troubleshooting
- spawn ENOENT (could not find command): Claude Desktop cannot find the server binary on PATH.
  - Fix 1 (absolute path): point `command` to your venv binary, e.g. `/Users/abirzu/dev/mcp-oci/.venv/bin/mcp-oci-serve-iam`.
  - Fix 2 (PATH): install the package and ensure the venv/bin is on PATH for Claude. For macOS, launch Claude from a shell after `source .venv/bin/activate`, or add the venv bin to your login shell PATH.
  - Fix 3 (Docker): use the Docker command form shown above so `docker` is the command and the image contains the server.
  - Log location: macOS logs are under `~/Library/Logs/Claude/`. Look for files like `mcp-server-oci-iam.log`, `mcp.log`. Errors will show `spawn mcp-oci-serve-<service> ENOENT` when PATH is the issue.
- Validate installation with `mcp-oci doctor` and re-run servers with `--log-level DEBUG` to increase verbosity.
