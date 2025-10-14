from typing import Any

from mcp_servers.compute.server import list_instances


def test_compute_list_instances(tenancy_ocid, oci_profile, oci_region):
    out: list[dict[str, Any]] = list_instances(
        compartment_id=tenancy_ocid, region=oci_region
    )
    assert isinstance(out, list)
