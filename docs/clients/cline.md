# Cline (VS Code) Integration

Cline supports MCP servers via the `cline.mcpServers` setting in VS Code’s settings.json.

Edit settings.json
- Open Command Palette → Preferences: Open Settings (JSON)
- Add or merge the following:

Standard MCP servers:
```
{
  "cline.mcpServers": {
    "oci-iam": {
      "command": "mcp-oci-serve-iam",
      "args": ["--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
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

FastMCP servers (recommended for better performance):
```
{
  "cline.mcpServers": {
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

Docker-based Option
```
"oci-iam": {
  "command": "docker",
  "args": ["run", "--rm", "-i", "-v", "${env:HOME}/.oci:/root/.oci", "mcp-oci", "mcp-oci-serve-iam", "--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
}
```

Tips
- Ensure VS Code can find `mcp-oci` in PATH (set in your shell or VS Code terminal).
- Use `--log-level INFO` to monitor requests; `DEBUG` for more details.
