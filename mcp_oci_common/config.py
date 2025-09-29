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

    profile = profile_name or os.getenv('OCI_PROFILE', 'DEFAULT')
    config_path = os.getenv('OCI_CONFIG_FILE', os.path.expanduser('~/.oci/config'))

    try:
        config = oci.config.from_file(file_location=config_path, profile_name=profile)
    except oci.exceptions.ConfigFileNotFound:
        try:
            # Fallback to instance principal
            InstancePrincipalsSecurityTokenSigner = _lazy_import_instance_principals()
            signer = InstancePrincipalsSecurityTokenSigner()
            config = {'region': signer.region}
            config['signer'] = signer
        except OCISDKImportError:
            # Re-raise SDK import errors
            raise
        except Exception as e:
            raise RuntimeError(
                f"""Failed to load OCI config and instance principal fallback: {str(e)}

Troubleshooting:
1. Ensure OCI config file exists at: {config_path}
2. Or run on OCI compute instance with instance principals enabled
3. Check OCI_PROFILE environment variable if using non-default profile
4. Verify OCI SDK is properly installed: pip install oci
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
