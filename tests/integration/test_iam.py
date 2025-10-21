from typing import Any

from mcp_servers.security.server import list_iam_users


def test_iam_list_users_minimal(tenancy_ocid, oci_profile, oci_region):
    out: dict[str, Any] = list_iam_users(
        compartment_id=tenancy_ocid
    )
    assert isinstance(out, dict)
    assert "ok" in out
    # If successful, should have "data" key; if error, should have "error" key
    if out["ok"]:
        assert "data" in out
        assert isinstance(out["data"], list)
    else:
        assert "error" in out
