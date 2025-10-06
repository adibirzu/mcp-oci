#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import json

def main() -> None:
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
    from mcp_oci_introspect.server import warm_services, warm_compartment, registry_report
    comp = os.getenv("COMPARTMENT_OCID")
    print(json.dumps(warm_services(compartment_id=comp, limit=50), indent=2))
    if comp:
        print(json.dumps(warm_compartment(compartment_id=comp, limit=1000), indent=2))
    print(json.dumps(registry_report(), indent=2))

if __name__ == '__main__':
    main()

