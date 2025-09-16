"""Minimal MCP stdio JSON-RPC server.

Implements a subset of MCP compatible with AWS MCP hosts:
- initialize
- tools/list
- tools/call

Framing: supports Content-Length headers (LSP-style) and newline-delimited JSON for dev.
"""
from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any

Json = dict[str, Any]


class StdioServer:
    def __init__(self, tools: list[dict[str, Any]], *, defaults: dict[str, Any] | None = None, require_confirm: bool = False, log_level: str = "WARN"):
        # Normalize tool entries
        self.tools = tools
        self.tool_by_name: dict[str, dict[str, Any]] = {t["name"]: t for t in tools}
        self.defaults = defaults or {}
        self.require_confirm = require_confirm
        self.log_level = (log_level or "WARN").upper()

    # ---------------- IO helpers -----------------
    def _read_message(self) -> Json | None:
        # Try LSP-style framing first
        header = ""
        length = 0
        while True:
            line = sys.stdin.readline()
            if not line:
                return None
            if line.strip() == "":
                break
            header += line
            if line.lower().startswith("content-length:"):
                try:
                    length = int(line.split(":", 1)[1].strip())
                except Exception:
                    length = 0
        if header:
            body = sys.stdin.read(length) if length else ""
            return json.loads(body) if body else None
        # Fallback: newline-delimited JSON
        line = sys.stdin.readline()
        if not line:
            return None
        return json.loads(line)

    def _write(self, obj: Json) -> None:
        data = json.dumps(obj, separators=(",", ":"))
        out = f"Content-Length: {len(data)}\r\n\r\n{data}"
        sys.stdout.write(out)
        sys.stdout.flush()

    def _log(self, level: str, msg: str) -> None:
        levels = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}
        if levels.get(level, 30) >= levels.get(self.log_level, 30):
            sys.stderr.write(f"[{level}] {msg}\n")
            sys.stderr.flush()

    # ---------------- Handlers -----------------
    def _handle_initialize(self, req: Json) -> Json:
        params = req.get("params", {}) if isinstance(req, dict) else {}
        client_version = None
        try:
            client_version = params.get("protocolVersion")
        except Exception:
            client_version = None
        # Log handshake for host compatibility diagnostics
        self._log("INFO", f"initialize received (client protocol={client_version})")
        return {
            "protocolVersion": client_version or "2024-05-01",
            "capabilities": {
                "tools": {},
            },
            "serverInfo": {
                "name": "mcp-oci",
                "version": "0.1.0",
            },
        }

    def _handle_tools_list(self, req: Json) -> Json:
        self._log("INFO", f"tools/list requested; returning {len(self.tools)} tools")
        items = []
        for t in self.tools:
            items.append(
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "inputSchema": t.get("parameters", {"type": "object"}),
                }
            )
        return {"tools": items}

    def _handle_tools_call(self, req: Json) -> Json:
        params = req.get("params") or req.get("params") or {}
        name = (params.get("name") if isinstance(params, dict) else None) or (
            req.get("name")
        )
        arguments = (params.get("arguments") if isinstance(params, dict) else None) or req.get(
            "arguments", {}
        )
        if not name:
            raise ValueError("Missing tool name")
        tool = self.tool_by_name.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        handler: Callable[..., Any] | None = tool.get("handler")
        if not handler:
            raise ValueError("Tool has no handler bound")
        # Merge defaults for profile/region if handler supports them and args omit
        args = dict(arguments or {})
        for k in ("profile", "region"):
            if k not in args and k in self.defaults:
                args[k] = self.defaults[k]
        # Confirmation for mutating operations if enabled
        if self.require_confirm and tool.get("mutating"):
            if not args.get("confirm"):
                raise ValueError("Confirmation required: pass `confirm=true` for mutating action")
        self._log("INFO", f"tools/call {name} args={list(args.keys())}")
        result = handler(**args)
        # MCP expects an array of outputs; we return a single json block
        return {"content": [{"type": "json", "json": result}]}

    # ---------------- Main loop -----------------
    def serve_forever(self) -> None:
        while True:
            req = self._read_message()
            if req is None:
                break
            rid = req.get("id")
            method = req.get("method", "")
            try:
                if method == "initialize":
                    result = self._handle_initialize(req)
                elif method == "tools/list":
                    result = self._handle_tools_list(req)
                elif method == "tools/call":
                    result = self._handle_tools_call(req)
                elif method in ("shutdown", "exit"):
                    result = {}
                    self._write({"jsonrpc": "2.0", "id": rid, "result": result})
                    break
                else:
                    raise ValueError(f"Unsupported method: {method}")
                self._write({"jsonrpc": "2.0", "id": rid, "result": result})
            except Exception as e:
                # Enrich error with OCI request id if present
                data = {}
                try:
                    import oci  # type: ignore
                    if isinstance(e, oci.exceptions.ServiceError):  # type: ignore
                        headers = getattr(e, "headers", {}) or {}
                        rid = headers.get("opc-request-id") or headers.get("opc_request_id")
                        if rid:
                            data["opc_request_id"] = rid
                        data["service_code"] = getattr(e, "code", None)
                except Exception:
                    pass
                self._log("ERROR", f"{type(e).__name__}: {e}")
                err_obj = {"jsonrpc": "2.0", "id": rid, "error": {"code": -32000, "message": str(e)}}
                if data:
                    err_obj["error"]["data"] = data
                self._write(err_obj)


def run_with_tools(tools: list[dict[str, Any]], *, defaults: dict[str, Any] | None = None, require_confirm: bool = False, log_level: str = "WARN") -> None:
    StdioServer(tools, defaults=defaults, require_confirm=require_confirm, log_level=log_level).serve_forever()
