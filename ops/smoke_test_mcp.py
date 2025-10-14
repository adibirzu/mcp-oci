#!/usr/bin/env python3
import json
import sys
from datetime import datetime, timezone

# Ensure repo paths
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

def main():
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ok": False,
        "servers": {},
        "note": "This smoke test imports each MCP server module and invokes its doctor/healthcheck via observability.doctor_all()"
    }
    try:
        # doctor_all aggregates doctor/healthcheck across all MCP servers without starting them
        from mcp_servers.observability.server import doctor_all
        agg = doctor_all()
        result["ok"] = bool(agg.get("ok"))
        result["servers"] = agg.get("servers", {})
    except Exception as e:
        result["error"] = f"smoke test failed: {e}"

    out_path = os.path.join(ROOT, "ops", "MCP_HEALTH.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
