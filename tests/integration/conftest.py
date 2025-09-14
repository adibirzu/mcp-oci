import os
import pytest


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
