from .config import (
    get_oci_config,
    get_compartment_id as get_compartment_id,
    allow_mutations as allow_mutations,
)
from .observability import add_oci_call_attributes as add_oci_call_attributes
from .validation import validate_and_log_tools as validate_and_log_tools

# Placeholder for with_oci_errors if needed
def with_oci_errors(func):
    return func


def make_client(oci_client_class, profile: str | None = None, region: str | None = None):
    """
    Factory for OCI SDK clients that supports both config-file auth and instance principals.

    Usage:
        from mcp_oci_common import make_client
        client = make_client(oci.log_analytics.LogAnalyticsClient, profile="DEFAULT", region="eu-frankfurt-1")
    """
    # Lazy availability check to avoid hard dependency at import time
    import importlib.util as _importlib
    if _importlib.find_spec("oci") is None:
        raise RuntimeError("OCI SDK not available. Please install 'oci' package.")

    # Load config; supports instance principal fallback via get_oci_config()
    cfg = get_oci_config(profile_name=profile)
    if region:
        cfg["region"] = region

    signer = cfg.get("signer")
    if signer is not None:
        # Instance principals or other signer-based auth
        return oci_client_class(cfg, signer=signer)
    else:
        return oci_client_class(cfg)
