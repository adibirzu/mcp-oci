import os
from typing import Dict, Any, Optional


class OCISDKImportError(ImportError):
    """Custom exception for OCI SDK import failures with actionable guidance."""

    def __init__(self, operation: str, original_error: Exception):
        self.operation = operation
        self.original_error = original_error

        message = f"""
Failed to import OCI SDK for {operation}.

This likely means the OCI SDK is not installed. To fix this:

1. Install the OCI SDK:
   pip install oci

2. Or install with optional dependencies:
   pip install "mcp-oci[oci]"

3. For development with all dependencies:
   pip install "mcp-oci[dev]"

Original error: {original_error}

Note: Some utilities in mcp_oci_common can be used without the OCI SDK,
but operations requiring OCI services need the SDK installed.
"""
        super().__init__(message)


def _lazy_import_oci():
    """Lazy import of OCI SDK with informative error handling."""
    try:
        import oci
        return oci
    except ImportError as e:
        raise OCISDKImportError("OCI configuration", e)


def _lazy_import_instance_principals():
    """Lazy import of OCI instance principals with informative error handling."""
    try:
        from oci.auth.signers import InstancePrincipalsSecurityTokenSigner
        return InstancePrincipalsSecurityTokenSigner
    except ImportError as e:
        raise OCISDKImportError("instance principals authentication", e)

def _lazy_import_resource_principals():
    """Lazy import of OCI resource principals (OKE Workload Identity, Functions, etc.)."""
    try:
        from oci.auth.signers import get_resource_principals_signer
        return get_resource_principals_signer
    except ImportError as e:
        raise OCISDKImportError("resource principals authentication", e)

def get_oci_config(profile_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get OCI configuration with lazy SDK import and comprehensive error handling.

    Args:
        profile_name: Optional OCI config profile name. Defaults to OCI_PROFILE env var or 'DEFAULT'

    Returns:
        Dict containing OCI configuration

    Raises:
        OCISDKImportError: If OCI SDK is not installed
        RuntimeError: If neither config file nor instance principals work
    """
    # Lazy import OCI SDK
    oci = _lazy_import_oci()

    # Honor explicit resource principal mode or detected OKE/Functions environment first
    auth_mode = os.getenv('OCI_CLI_AUTH', '').lower()
    if auth_mode in ('resource_principal', 'resource_principals', 'resource') or os.getenv('OCI_RESOURCE_PRINCIPAL_VERSION'):
        try:
            get_rp_signer = _lazy_import_resource_principals()
            signer = get_rp_signer()
            region = os.getenv('OCI_REGION') or getattr(signer, 'region', None)
            if not region:
                # Region is required by SDK base_client; require OCI_REGION via ConfigMap/Secret in k8s
                raise RuntimeError(
                    "Using Resource Principals requires OCI_REGION to be set in environment."
                )
            return {'region': region, 'signer': signer}
        except OCISDKImportError:
            # Fall through to other mechanisms if SDK missing
            pass
        except Exception as e:
            # If resource principal was explicitly requested, fail fast with guidance
            if auth_mode in ('resource_principal', 'resource_principals', 'resource'):
                raise RuntimeError(f"Failed to initialize Resource Principals signer: {e}") from e
            # Otherwise continue to next auth mechanisms

    profile = profile_name or os.getenv('OCI_PROFILE', 'DEFAULT')
    config_path = os.getenv('OCI_CONFIG_FILE', os.path.expanduser('~/.oci/config'))

    try:
        config = oci.config.from_file(file_location=config_path, profile_name=profile)
    except oci.exceptions.ConfigFileNotFound:
        try:
            # Try Resource Principals first (OKE Workload Identity, Functions)
            get_rp_signer = _lazy_import_resource_principals()
            rp_signer = get_rp_signer()
            rp_region = os.getenv('OCI_REGION') or getattr(rp_signer, 'region', None)
            if not rp_region:
                # If region still missing, attempt instance principals next
                raise RuntimeError("Resource Principals available but OCI_REGION not set")
            return {'region': rp_region, 'signer': rp_signer}
        except Exception:
            # Fallback to Instance Principals
            try:
                InstancePrincipalsSecurityTokenSigner = _lazy_import_instance_principals()
                signer = InstancePrincipalsSecurityTokenSigner()
                config = {'region': signer.region}
                config['signer'] = signer
            except OCISDKImportError:
                # Re-raise SDK import errors
                raise
            except Exception as e:
                raise RuntimeError(
                    f"""Failed to load OCI config, resource principals, and instance principals fallback: {str(e)}

Troubleshooting:
1. Ensure OCI config file exists at: {config_path}
2. Or run on OCI compute instance with instance principals enabled
3. Or enable OKE Workload Identity / Resource Principals for pods and set OCI_REGION
4. Check OCI_PROFILE environment variable if using non-default profile
5. Verify OCI SDK is properly installed: pip install oci
"""
                ) from e
    except Exception as e:
        raise RuntimeError(
            f"""Failed to load OCI config from {config_path} with profile '{profile}': {str(e)}

Troubleshooting:
1. Check if the config file exists and is readable
2. Verify the profile '{profile}' exists in the config file
3. Ensure the config file format is correct
4. Try with profile_name='DEFAULT' or set OCI_PROFILE environment variable
"""
        ) from e

    # Override region from environment if provided
    env_region = os.getenv('OCI_REGION')
    if env_region:
        config['region'] = env_region

    # Inject tenancy OCID if provided via environment (needed when using Resource Principals)
    env_tenancy = os.getenv('TENANCY_OCID') or os.getenv('OCI_TENANCY')
    if env_tenancy:
        config['tenancy'] = env_tenancy

    return config

def get_compartment_id() -> Optional[str]:
    """
    Get compartment OCID from environment.

    Returns:
        Optional[str]: Compartment OCID if set, None otherwise
    """
    return os.getenv('COMPARTMENT_OCID')


def allow_mutations() -> bool:
    """
    Check if mutations are allowed.

    Defaults to True for compute operations to avoid configuration issues.
    Can be explicitly disabled by setting ALLOW_MUTATIONS=false.

    Returns:
        bool: True if mutations are allowed, False otherwise
    """
    env_value = os.getenv('ALLOW_MUTATIONS', 'true').lower()
    return env_value == 'true'


def is_oci_sdk_available() -> bool:
    """
    Check if OCI SDK is available without raising exceptions.

    Returns:
        bool: True if OCI SDK can be imported, False otherwise
    """
    try:
        import oci
        return True
    except ImportError:
        return False


def get_oci_config_safe(profile_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Safely attempt to get OCI config, returning None if SDK is unavailable.

    This is useful for optional OCI functionality where the SDK may not be installed.

    Args:
        profile_name: Optional OCI config profile name

    Returns:
        Optional[Dict[str, Any]]: OCI config if successful, None if SDK unavailable

    Raises:
        RuntimeError: If SDK is available but config loading fails
    """
    if not is_oci_sdk_available():
        return None

    try:
        return get_oci_config(profile_name)
    except OCISDKImportError:
        return None
