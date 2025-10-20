from typing import Any

import pytest

# Object storage functions not yet implemented in mcp_servers
# from mcp_servers.inventory.server import get_namespace, list_buckets


def test_objectstorage_namespace_and_buckets(tenancy_ocid, oci_profile, oci_region):
    pytest.skip("Object storage functions not yet implemented in mcp_servers")
    # ns_out: dict[str, Any] = get_namespace(profile=oci_profile, region=oci_region)
    # namespace = ns_out.get("namespace")
    # assert namespace
    # buckets_out: dict[str, Any] = list_buckets(
    #     namespace_name=str(namespace), compartment_id=tenancy_ocid, limit=1, profile=oci_profile, region=oci_region
    # )
    # assert "items" in buckets_out

