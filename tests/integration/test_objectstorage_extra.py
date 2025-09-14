import os
import pytest
from typing import Dict, Any

from mcp_oci_objectstorage.server import get_namespace, list_objects


@pytest.mark.skipif(
    not os.environ.get("TEST_OCI_OS_BUCKET"),
    reason="Set TEST_OCI_OS_BUCKET (and optionally TEST_OCI_OS_NAMESPACE) to enable Object Storage object listing test",
)
def test_objectstorage_list_objects(oci_profile, oci_region):
    bucket = os.environ["TEST_OCI_OS_BUCKET"]
    namespace = os.environ.get("TEST_OCI_OS_NAMESPACE")
    if not namespace:
        ns_out: Dict[str, Any] = get_namespace(profile=oci_profile, region=oci_region)
        namespace = str(ns_out.get("namespace"))
    out: Dict[str, Any] = list_objects(
        namespace_name=namespace,
        bucket_name=bucket,
        limit=5,
        profile=oci_profile,
        region=oci_region,
    )
    assert "items" in out

