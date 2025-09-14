from typing import Dict, Any

from mcp_oci_compute.server import list_shapes


def test_compute_list_shapes(tenancy_ocid, oci_profile, oci_region):
    out: Dict[str, Any] = list_shapes(
        compartment_id=tenancy_ocid, limit=1, profile=oci_profile, region=oci_region
    )
    assert "items" in out
    assert isinstance(out["items"], list)

