# FastMCP Runtime (Optional)

This repo includes an optional FastMCP-based runtime alongside the minimal stdio runtime. Use it if your host prefers FastMCP’s conventions or you want a quick health/tooling scaffold.

What’s included
- Entrypoint: `mcp-oci-serve-fast`
- Service: `compute` (initial)
  - Tools: `oci_compute_list_instances`, `oci_compute_search_instances`, `oci_compute_list_stopped_instances`, and `get_server_info`.
  - These wrap the existing SDK handlers in `mcp_oci_compute.server` and accept the same parameters, with `profile/region` defaulting from CLI args.

Why different names?
- FastMCP’s decorator uses the function name as the tool identifier. To keep things simple, the FastMCP tools use snake_case names.
- The stdio runtime continues to expose canonical names like `oci:compute:list-instances`.

Install
```
pip install fastmcp
```

Run (compute)
```
mcp-oci-serve-fast compute --profile DEFAULT --region eu-frankfurt-1
```

Claude Desktop
- Use a separate entry under `mcpServers`:
```
"oci-compute-fast": {
  "command": "/path/to/venv/bin/mcp-oci-serve-fast",
  "args": ["compute", "--profile", "DEFAULT", "--region", "eu-frankfurt-1"]
}
```

Notes
- The canonical stdio runtime remains the default for production. FastMCP is provided as an alternative where helpful and can be extended to other services.
- You can add more FastMCP-wrapped services by following `src/mcp_oci_fastmcp/compute.py` as a template.
