import argparse
import importlib
import os
from typing import Any


def load_register_tools(service: str):
    mod = importlib.import_module(f"mcp_oci_{service}.server")
    return mod.register_tools


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

    defaults: dict[str, Any] = {}
    if args.profile:
        defaults["profile"] = args.profile
    if args.region:
        defaults["region"] = args.region
    tools = register_tools()

    # Add colon-form aliases for tools named like oci_<service>_<action>
    # This keeps backward-compatible snake_case names while exposing
    # guideline-compliant identifiers: oci:<service>:<action>
    def _alias_name(n: str) -> str | None:
        if ":" in n:
            return None
        if not n.startswith("oci_"):
            return None
        try:
            rest = n[len("oci_"):]
            svc, action = rest.split("_", 1)
            return f"oci:{svc}:{action.replace('_', '-')}"
        except Exception:
            return None

    existing = {t["name"] for t in tools}
    alias_entries: list[dict[str, Any]] = []
    for t in tools:
        alias = _alias_name(t.get("name", ""))
        if alias and alias not in existing:
            alias_entries.append({
                "name": alias,
                "description": t.get("description", ""),
                "parameters": t.get("parameters", {"type": "object"}),
                "handler": t.get("handler"),
                "mutating": t.get("mutating", False),
            })
            existing.add(alias)
    if alias_entries:
        tools.extend(alias_entries)
    # Add generic server info and ping tools to help hosts probe
    def _server_info() -> dict[str, Any]:  # type: ignore
        return {"service": args.service, "defaults": defaults, "runtime": "stdio"}

    def _ping() -> dict[str, Any]:  # type: ignore
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
