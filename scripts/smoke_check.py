#!/usr/bin/env python3
"""
Lightweight MCP-OCI smoke check.

Imports each server module directly and invokes its `doctor` tool/function
if present (fallback to `healthcheck`). Summarizes status in JSON.

This avoids launching over MCP, so it can run in CI or locally without
depending on a specific client. It will not make network calls except
reading OCI config, which some doctor functions may attempt. Exceptions are
captured and reported per server.
"""
from __future__ import annotations

import importlib
import json
import os
from typing import Any, Dict
from pathlib import Path
import sys

SERVERS = [
    ("compute", "mcp_servers.compute.server"),
    ("db", "mcp_servers.db.server"),
    ("network", "mcp_servers.network.server"),
    ("security", "mcp_servers.security.server"),
    ("observability", "mcp_servers.observability.server"),
    ("cost", "mcp_servers.cost.server"),
    ("inventory", "mcp_servers.inventory.server"),
    ("blockstorage", "mcp_servers.blockstorage.server"),
    ("loadbalancer", "mcp_servers.loadbalancer.server"),
    ("agents", "mcp_servers.agents.server"),
]


def call_tool(mod: Any, preferred: str = "doctor") -> Dict[str, Any]:
    # 1) direct function or FunctionTool wrapper with .fn
    attr = getattr(mod, preferred, None)
    if callable(attr):
        try:
            res = attr()
            return {"ok": True, "result": res}
        except Exception as e:
            return {"ok": False, "error": f"{preferred}() failed: {e}"}
    # FunctionTool case
    if attr is not None:
        h = getattr(attr, "fn", None) or getattr(attr, "func", None) or getattr(attr, "handler", None)
        if callable(h):
            try:
                return {"ok": True, "result": h()}
            except Exception as e:
                return {"ok": False, "error": f"{preferred}.fn failed: {e}"}

    # 2) tools list -> pick by name
    tools = getattr(mod, "tools", None)
    if isinstance(tools, (list, tuple)):
        # Find preferred tool
        for t in tools:
            name = getattr(t, "name", getattr(t, "__name__", None))
            handler = getattr(t, "func", None) or getattr(t, "handler", None) or getattr(t, "fn", None)
            if name == preferred and callable(handler):
                try:
                    res = handler()  # type: ignore[misc]
                    return {"ok": True, "result": res}
                except Exception as e:
                    return {"ok": False, "error": f"tools[{preferred}] failed: {e}"}
        # Fallback to healthcheck if present
        for t in tools:
            name = getattr(t, "name", getattr(t, "__name__", None))
            handler = getattr(t, "func", None) or getattr(t, "handler", None) or getattr(t, "fn", None)
            if name == "healthcheck" and callable(handler):
                try:
                    res = handler()  # type: ignore[misc]
                    return {"ok": True, "result": res}
                except Exception as e:
                    return {"ok": False, "error": f"tools[healthcheck] failed: {e}"}
    # 3) FastMCP app registry (e.g., cost server)
    app = getattr(mod, "app", None)
    if app and hasattr(app, "list_tools"):
        try:
            for t in app.list_tools():
                if getattr(t, "name", None) == preferred:
                    h = getattr(t, "func", None) or getattr(t, "handler", None) or getattr(t, "fn", None)
                    if callable(h):
                        return {"ok": True, "result": h()}
        except Exception as e:
            return {"ok": False, "error": f"app[{preferred}] failed: {e}"}
    return {"ok": False, "error": f"No {preferred} or healthcheck tool found"}


def main() -> None:
    os.environ.setdefault("MCP_OCI_PRIVACY", "true")
    # Ensure src/ and project root are importable
    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "src"
    for p in (str(repo_root), str(src_dir)):
        if p not in sys.path:
            sys.path.insert(0, p)
    summary: Dict[str, Any] = {"privacy": os.getenv("MCP_OCI_PRIVACY")}
    results: Dict[str, Any] = {}
    for name, modpath in SERVERS:
        try:
            mod = importlib.import_module(modpath)
        except Exception as e:
            results[name] = {"ok": False, "error": f"import failed: {e}"}
            continue
        results[name] = call_tool(mod, preferred="doctor")
    summary["servers"] = results
    summary["ok"] = all(bool(v.get("ok")) for v in results.values())
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
