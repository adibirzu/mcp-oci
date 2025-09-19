import threading
from typing import Any, Dict, Optional, Tuple, Type

from .config import get_oci_config

# Simple in-process client cache keyed by (client fqcn, profile, region)
_client_cache: Dict[Tuple[str, Optional[str], Optional[str]], Any] = {}
_client_lock = threading.Lock()


def _fqcn(klass: Type) -> str:
    return f"{klass.__module__}.{klass.__name__}"


def get_client(oci_client_class: Type, profile: Optional[str] = None, region: Optional[str] = None) -> Any:
    """
    Return a cached OCI SDK client instance for (class, profile, region).
    Lazily creates a client if not present. Safe for concurrent access in a single process.

    Example:
        from mcp_oci_common.session import get_client
        compute = get_client(oci.core.ComputeClient, profile="DEFAULT", region="eu-frankfurt-1")
    """
    # Lazy import of oci to avoid hard dependency at import time for modules that don't use it
    try:
        import oci as _oci  # noqa: F401
    except Exception as _e:
        raise RuntimeError("OCI SDK not available. Please install 'oci' package.") from _e

    key = (_fqcn(oci_client_class), profile, region)
    with _client_lock:
        if key in _client_cache:
            return _client_cache[key]

        cfg = get_oci_config(profile_name=profile)
        if region:
            cfg["region"] = region

        signer = cfg.get("signer")
        if signer is not None:
            client = oci_client_class(cfg, signer=signer)
        else:
            client = oci_client_class(cfg)

        _client_cache[key] = client
        return client


def clear_client_cache() -> None:
    """
    Clear all cached clients. Useful for tests or when switching auth contexts.
    """
    with _client_lock:
        _client_cache.clear()
