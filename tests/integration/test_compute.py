from typing import Any

from mcp_servers.compute.server import list_instances


def test_compute_list_instances(tenancy_ocid, oci_profile, oci_region):
    out: dict[str, Any] = list_instances(
        compartment_id=tenancy_ocid, limit=1, profile=oci_profile, region=oci_region
    )
    assert "items" in out
    assert isinstance(out["items"], list)

