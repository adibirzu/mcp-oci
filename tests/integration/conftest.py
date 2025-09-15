import os
import pytest
from typing import Optional


def pytest_collection_modifyitems(config, items):
    # Skip entire integration suite unless explicitly enabled
    if os.environ.get("OCI_INTEGRATION") != "1":
        skip = pytest.mark.skip(reason="Set OCI_INTEGRATION=1 to run direct OCI integration tests")
        for item in items:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def oci_profile() -> str:
    return os.environ.get("TEST_OCI_PROFILE", "DEFAULT")


@pytest.fixture(scope="session")
def oci_region(oci_profile: str) -> str:
    val = os.environ.get("TEST_OCI_REGION")
    if val:
        return val
    try:
        import oci  # type: ignore
    except Exception:
        raise pytest.skip("OCI SDK not installed and TEST_OCI_REGION not set")
    cfg = oci.config.from_file(profile_name=oci_profile)
    return cfg.get("region")


@pytest.fixture(scope="session")
def tenancy_ocid(oci_profile: str) -> str:
    val = os.environ.get("TEST_OCI_TENANCY_OCID")
    if val:
        return val
    try:
        import oci  # type: ignore
    except Exception:
        raise pytest.skip("OCI SDK not installed and TEST_OCI_TENANCY_OCID not set")
    cfg = oci.config.from_file(profile_name=oci_profile)
    tid = cfg.get("tenancy")
    if not tid:
        raise pytest.skip("Could not determine tenancy OCID from OCI config; set TEST_OCI_TENANCY_OCID")
    return tid


def _discover_log_analytics_namespace(oci_profile: str, oci_region: str, tenancy_ocid: str) -> Optional[str]:
    try:
        import oci  # type: ignore
    except Exception:
        return None
    try:
        cfg = oci.config.from_file(profile_name=oci_profile)
        if oci_region:
            cfg["region"] = oci_region
        client = oci.log_analytics.LogAnalyticsClient(cfg)
    except Exception:
        return None
    # Try common method names and parameter shapes
    candidates = ["list_namespaces", "list_log_analytics_namespaces", "list_namespaces_details"]
    for name in candidates:
        method = getattr(client, name, None)
        if method is None:
            continue
        for kwargs in ({"compartment_id": tenancy_ocid}, {}):
            try:
                resp = method(**kwargs)
                data = getattr(resp, "data", [])
                if not data:
                    continue
                if isinstance(data[0], str):
                    return str(data[0])
                # Try attributes
                for x in data:
                    for attr in ("namespace", "name", "namespace_name"):
                        val = getattr(x, attr, None)
                        if val:
                            return str(val)
            except Exception:
                continue
    return None


@pytest.fixture(scope="session")
def log_analytics_namespace(oci_profile: str, oci_region: str, tenancy_ocid: str) -> Optional[str]:
    val = os.environ.get("TEST_LOGANALYTICS_NAMESPACE")
    if val:
        return val
    return _discover_log_analytics_namespace(oci_profile, oci_region, tenancy_ocid)
