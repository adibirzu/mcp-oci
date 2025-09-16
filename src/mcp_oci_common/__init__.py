from .auth import get_config, make_client

__all__ = [
    "get_config",
    "make_client",
    "get_oci_config",
    "get_compartment_id",
    "allow_mutations",
    "with_oci_errors",
]

def get_oci_config(profile_name=None):
    """
    Backwards-compatible alias used by MCP servers.
    Loads OCI config from ~/.oci/config, allows OCI_REGION override via env.
    """
    import os
    import oci
    profile = profile_name or os.getenv("OCI_PROFILE", "DEFAULT")
    config = oci.config.from_file(profile_name=profile)
    region = os.getenv("OCI_REGION", config.get("region"))
    if region:
        config["region"] = region
    return config

def get_compartment_id():
    """
    Returns COMPARTMENT_OCID from the environment.
    """
    import os
    return os.getenv("COMPARTMENT_OCID")

def allow_mutations():
    """
    Returns True if ALLOW_MUTATIONS=true in env (case-insensitive).
    """
    import os
    return os.getenv("ALLOW_MUTATIONS", "false").lower() == "true"

def with_oci_errors(func):
    """
    No-op decorator placeholder for compatibility.
    Can be extended to catch oci.exceptions.ServiceError and return structured errors.
    """
    return func
