import os
import pytest
from typing import Dict, Any

from mcp_oci_objectstorage.server import get_namespace, list_buckets, list_objects


def _discover_first_bucket(namespace: str, compartment_id: str, oci_profile: str, oci_region: str) -> str:
    out: Dict[str, Any] = list_buckets(namespace_name=namespace, compartment_id=compartment_id, limit=1, profile=oci_profile, region=oci_region)
    items = out.get("items") or []
    if not items:
        return ""
    first = items[0]
    # Try field names typically present in bucket summary
    return str(first.get("name") or first.get("bucketName") or "")


def test_objectstorage_list_objects(oci_profile, oci_region, tenancy_ocid):
    bucket = os.environ.get("TEST_OCI_OS_BUCKET")
    ns: str
    ns_out: Dict[str, Any] = get_namespace(profile=oci_profile, region=oci_region)
    ns = str(ns_out.get("namespace"))
    if not bucket:
        bucket = _discover_first_bucket(ns, tenancy_ocid, oci_profile, oci_region)
        if not bucket:
            pytest.skip("No bucket available to list; set TEST_OCI_OS_BUCKET to force")
    out: Dict[str, Any] = list_objects(
        namespace_name=ns,
        bucket_name=bucket,
        limit=5,
        profile=oci_profile,
        region=oci_region,
    )
    assert "items" in out
