from typing import Dict, Any

from mcp_oci_iam.server import list_users


def test_iam_list_users_minimal(tenancy_ocid, oci_profile, oci_region):
    out: Dict[str, Any] = list_users(
        compartment_id=tenancy_ocid, limit=1, profile=oci_profile, region=oci_region
    )
    assert "items" in out
    assert isinstance(out["items"], list)

