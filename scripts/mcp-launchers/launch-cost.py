#!/usr/bin/env python3
import os
import sys
import runpy

# Ensure consistent service name for tracing
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-cost")

# Ensure src/ and repo root are on PYTHONPATH (for shared modules)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Ensure working directory is project root for relative paths (e.g., third_party/*)
os.chdir(ROOT)

# Launch the canonical MCP Cost server entrypoint
runpy.run_module("mcp_servers.cost.server", run_name="__main__")
