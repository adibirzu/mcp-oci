import os
import threading
from typing import Any, TypeVar

import oci

# =============================================================================
# Configuration & Authentication
# =============================================================================

def get_oci_config(profile_name: str | None = None) -> dict[str, Any]:
    """
    Get OCI configuration with robust fallback:
    1. Resource Principals (OKE/Functions)
    2. Config File (~/.oci/config)
    3. Instance Principals
    """

    # 1. Resource Principals Check
    auth_mode = os.getenv("OCI_CLI_AUTH", "").lower()
    rp_version = os.getenv("OCI_RESOURCE_PRINCIPAL_VERSION")
    is_resource_principal = auth_mode in ("resource_principal", "resource_principals", "resource")
    if is_resource_principal or rp_version:
        try:
            from oci.auth.signers import get_resource_principals_signer
            signer = get_resource_principals_signer()
            region = os.getenv("OCI_REGION") or getattr(signer, "region", None)
            if not region:
                raise RuntimeError("Resource Principals detected but OCI_REGION not set.")
            return {"region": region, "signer": signer}
        except Exception as e:
            if auth_mode:
                 # Explicitly requested RP but failed
                 raise RuntimeError(f"Failed to initialize Resource Principals: {e}") from e

    # 2. Config File
    profile = profile_name or os.getenv("OCI_PROFILE") or os.getenv("OCI_CLI_PROFILE", "DEFAULT")
    config_path = os.getenv("OCI_CONFIG_FILE", os.path.expanduser("~/.oci/config"))

    try:
        config = oci.config.from_file(file_location=config_path, profile_name=profile)
    except oci.exceptions.ConfigFileNotFound:
        # 3. Fallback: Resource Principals (Implicit)
        try:
            from oci.auth.signers import get_resource_principals_signer
            rp_signer = get_resource_principals_signer()
            rp_region = os.getenv("OCI_REGION") or getattr(rp_signer, "region", None)
            if not rp_region:
                raise RuntimeError("Resource Principals available but OCI_REGION not set")
            return {"region": rp_region, "signer": rp_signer}
        except Exception:
             # 4. Fallback: Instance Principals
            try:
                from oci.auth.signers import InstancePrincipalsSecurityTokenSigner
                signer = InstancePrincipalsSecurityTokenSigner()
                return {"region": signer.region, "signer": signer}
            except Exception as e:
                msg = f"Failed to load OCI config from {config_path}"
                msg += " or authenticate via Principals."
                raise RuntimeError(f"{msg} Error: {e}") from e
    except Exception as e:
        msg = f"Failed to load OCI config from {config_path} with profile '{profile}'"
        raise RuntimeError(f"{msg}: {e}") from e

    # Override region from environment if provided
    env_region = os.getenv("OCI_REGION")
    if env_region:
        config["region"] = env_region

    return config

def get_compartment_id() -> str | None:
    """Get compartment OCID from environment."""
    return os.getenv("COMPARTMENT_OCID")

def allow_mutations() -> bool:
    """Check if mutations (create/update/delete) are allowed."""
    return os.getenv("ALLOW_MUTATIONS", "false").lower() == "true"

# =============================================================================
# Client Session Management
# =============================================================================

T = TypeVar("T")
_client_cache: dict[tuple[str, str | None, str | None], Any] = {}
_client_lock = threading.Lock()

def _fqcn(klass: type) -> str:
    return f"{klass.__module__}.{klass.__name__}"

def get_client(
    oci_client_class: type[T],
    profile: str | None = None,
    region: str | None = None
) -> T:
    """
    Return a cached OCI SDK client instance.
    """
    key = (_fqcn(oci_client_class), profile, region)
    with _client_lock:
        if key in _client_cache:
            return _client_cache[key]

        cfg = get_oci_config(profile_name=profile)
        if region:
            cfg["region"] = region

        # Build client kwargs
        client_kwargs = {}

        # Retry Strategy
        if os.getenv("OCI_ENABLE_RETRIES", "true").lower() == "true":
             client_kwargs["retry_strategy"] = oci.retry.DEFAULT_RETRY_STRATEGY

        # Timeout
        timeout = os.getenv("OCI_REQUEST_TIMEOUT")
        if timeout:
            client_kwargs["timeout"] = float(timeout)

        # Create Client
        signer = cfg.get("signer")
        if signer is not None:
            client = oci_client_class(cfg, signer=signer, **client_kwargs)
        else:
            client = oci_client_class(cfg, **client_kwargs)

        _client_cache[key] = client
        return client
