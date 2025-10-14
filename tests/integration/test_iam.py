from typing import Any

from mcp_servers.security.server import list_iam_users


def test_iam_list_users_minimal(tenancy_ocid, oci_profile, oci_region):
    out: dict[str, Any] = list_iam_users(
        compartment_id=tenancy_ocid, region=oci_region
    )
    assert isinstance(out, list)
