"""MCP Server: OCI Inventory (showoci integration)

Wraps Oracle's showoci example to provide inventory reports via MCP tools.
"""

from typing import Any


def register_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "oci:inventory:showoci-scan",
            "description": "Run showoci to gather inventory; returns stdout (requires local clone).",
            "parameters": {
                "type": "object",
                "properties": {
                    "regions": {"type": "string", "description": "Comma-separated regions"},
                    "profile": {"type": "string"},
                    "tenancy": {"type": "string"},
                    "path": {"type": "string", "description": "Path to showoci.py (optional)"},
                    "extra_args": {"type": "string", "description": "Additional CLI flags"},
                    "expect_json": {"type": "boolean", "default": False},
                },
            },
            "handler": showoci_scan,
        }
    ]


def showoci_scan(regions: str | None = None, profile: str | None = None, tenancy: str | None = None,
                 path: str | None = None, extra_args: str | None = None, expect_json: bool = False) -> dict[str, Any]:
    import os
    import shlex
    import subprocess

    from mcp_oci_common.parsing import parse_json_loose, parse_kv_lines

    script = path or os.environ.get("SHOWOCI_PATH") or "third_party/oci-python-sdk/examples/showoci/showoci.py"
    if not os.path.exists(script):
        raise RuntimeError("showoci.py not found; set SHOWOCI_PATH or place under third_party/.../showoci.py")
    cmd = ["python", script]
    if regions:
        cmd += ["-rg", regions]
    if profile:
        cmd += ["-p", profile]
    if tenancy:
        cmd += ["-t", tenancy]
    if extra_args:
        cmd += shlex.split(extra_args)
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"showoci failed: {proc.stderr.strip()}")
    out: dict[str, Any] = {"stdout": proc.stdout}
    if expect_json:
        parsed = parse_json_loose(proc.stdout)
        if parsed is None:
            parsed = parse_kv_lines(proc.stdout)
        out["parsed"] = parsed
    return out
