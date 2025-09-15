import argparse
import importlib
import os
from typing import Any, Dict

def load_register_tools(service: str):
    mod = importlib.import_module(f"mcp_oci_{service}.server")
    return getattr(mod, "register_tools")


def main() -> None:
    p = argparse.ArgumentParser(description="Serve an OCI MCP service over stdio")
    p.add_argument("service", help="Service name, e.g., iam")
    p.add_argument("--profile", default=os.environ.get("MCP_OCI_DEFAULT_PROFILE"))
    p.add_argument("--region", default=os.environ.get("MCP_OCI_DEFAULT_REGION"))
    p.add_argument("--log-level", default=os.environ.get("MCP_OCI_LOG_LEVEL", "WARN"))
    p.add_argument("--require-confirm", action="store_true", help="Require confirm=true for mutating tools")
    args = p.parse_args()

    register_tools = load_register_tools(args.service)
    from mcp_oci_runtime.stdio import run_with_tools

    defaults: Dict[str, Any] = {}
    if args.profile:
        defaults["profile"] = args.profile
    if args.region:
        defaults["region"] = args.region
    tools = register_tools()
    # Add generic server info and ping tools to help hosts probe
    def _server_info() -> Dict[str, Any]:  # type: ignore
        return {"service": args.service, "defaults": defaults, "runtime": "stdio"}

    def _ping() -> Dict[str, Any]:  # type: ignore
        return {"ok": True}

    tools.extend([
        {
            "name": "mcp:server:info",
            "description": "Return server information (service, defaults, runtime).",
            "parameters": {"type": "object", "properties": {}},
            "handler": _server_info,
        },
        {
            "name": "mcp:server:ping",
            "description": "Ping tool for connectivity checks.",
            "parameters": {"type": "object", "properties": {}},
            "handler": _ping,
        },
    ])
    run_with_tools(tools, defaults=defaults, require_confirm=args.require_confirm, log_level=args.log_level)


if __name__ == "__main__":
    main()
