#!/usr/bin/env python3
import importlib
import inspect
import json
import pkgutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


def iter_servers():
    for pkg in pkgutil.iter_modules([str(SRC) + "/"]):
        name = pkg.name
        if name.startswith("mcp_oci_") and name not in (
            "mcp_oci_runtime", "mcp_oci_common", "mcp_oci_cli", 
            "mcp_oci_serve", "mcp_oci_fastmcp_optimized", 
            "mcp_oci_fastmcp_rest", "mcp_oci_rest"
        ):
            yield name


def validate_tool(tool, module_name):
    errors = []
    name = tool.get("name")
    if not name or not isinstance(name, str) or not name.startswith("oci:"):
        errors.append("invalid or missing name")
    if not tool.get("description"):
        errors.append("missing description")
    params = tool.get("parameters")
    if not params or not isinstance(params, dict) or params.get("type") != "object":
        errors.append("parameters must be a JSON Schema object")
    else:
        props = params.get("properties")
        if props is None or not isinstance(props, dict):
            errors.append("parameters.properties must be a dict")
    handler = tool.get("handler")
    if handler is None or not callable(handler):
        errors.append("handler must be callable")
    if tool.get("mutating"):
        # ensure confirm or dry_run present in schema
        props = (params or {}).get("properties", {})
        if "confirm" not in props and "dry_run" not in props:
            errors.append("mutating tool should define confirm and/or dry_run parameters")
        # and that handler accepts confirm
        try:
            sig = inspect.signature(handler)
            if "confirm" not in sig.parameters and "dry_run" not in sig.parameters:
                errors.append("mutating handler should accept confirm and/or dry_run")
        except Exception:
            pass
    return errors


def main():
    failed = False
    report = {}
    for server_pkg in iter_servers():
        try:
            mod = importlib.import_module(f"{server_pkg}.server")
        except Exception as e:
            print(f"ERROR: cannot import {server_pkg}.server: {e}")
            failed = True
            continue
        if not hasattr(mod, "register_tools"):
            print(f"ERROR: {server_pkg}.server missing register_tools()")
            failed = True
            continue
        try:
            tools = mod.register_tools()
        except Exception as e:
            print(f"ERROR: {server_pkg}.server.register_tools() failed: {e}")
            failed = True
            continue
        tool_errors = {}
        for t in tools:
            errs = validate_tool(t, server_pkg)
            if errs:
                tool_errors[t.get("name", "<unnamed>")] = errs
        # Light docs check
        docs_file = ROOT / "docs" / "servers" / f"{server_pkg.split('mcp_oci_')[-1]}.md"
        if docs_file.exists():
            text = docs_file.read_text(encoding="utf-8")
            for t in tools:
                nm = t.get("name", "")
                if nm and nm.split(":")[-1] not in text and nm not in text:
                    tool_errors.setdefault(nm or "<unnamed>", []).append("tool name not found in docs page")
                params = (t.get("parameters") or {}).get("properties", {})
                for p in params.keys():
                    if p not in text:
                        tool_errors.setdefault(nm or "<unnamed>", []).append(f"param '{p}' not mentioned in docs (heuristic)")
        # Check docs for mutating confirm/dry_run mention
        if docs_file.exists():
            text = docs_file.read_text(encoding="utf-8")
            for t in tools:
                if t.get("mutating"):
                    if ("confirm" not in text) and ("dry_run" not in text):
                        tool_errors.setdefault(t.get("name", "<unnamed>"), []).append("mutating tool docs should mention confirm/dry_run")
        report[server_pkg] = {"count": len(tools), "errors": tool_errors}
        if tool_errors:
            failed = True
    print(json.dumps(report, indent=2))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
