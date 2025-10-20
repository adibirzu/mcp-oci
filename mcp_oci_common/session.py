import threading
import os
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

        # Build client kwargs with optional retries and timeouts (safe fallbacks)
        client_kwargs = {}
        try:
            enable_retries = os.getenv("OCI_ENABLE_RETRIES", "true").lower() in ("1", "true", "yes", "on")
            if enable_retries:
                try:
                    import oci as _oci_mod  # noqa: F401
                    from oci import retry as _oci_retry  # type: ignore
                    client_kwargs["retry_strategy"] = getattr(_oci_retry, "DEFAULT_RETRY_STRATEGY", None)
                except Exception:
                    # Retry strategy not available; proceed without
                    pass
        except Exception:
            pass

        # Timeout configuration: supports "OCI_REQUEST_TIMEOUT" (single seconds) or connect/read split
        try:
            to_connect = os.getenv("OCI_REQUEST_TIMEOUT_CONNECT")
            to_read = os.getenv("OCI_REQUEST_TIMEOUT_READ")
            to_both = os.getenv("OCI_REQUEST_TIMEOUT")
            if to_connect and to_read:
                client_kwargs["timeout"] = (float(to_connect), float(to_read))
            elif to_both:
                sec = float(to_both)
                client_kwargs["timeout"] = (sec, sec)
        except Exception:
            # If the SDK/client does not accept 'timeout', ignore silently
            pass

        signer = cfg.get("signer")
        try:
            if signer is not None:
                client = oci_client_class(cfg, signer=signer, **client_kwargs)
            else:
                client = oci_client_class(cfg, **client_kwargs)
        except TypeError:
            # Some clients may not accept retry_strategy/timeout kwargs; fall back gracefully
            if signer is not None:
                client = oci_client_class(cfg, signer=signer)
            else:
                client = oci_client_class(cfg)

        # Attach a sane default retry strategy to reduce transient failures and improve responsiveness
        try:
            from oci.retry import RetryStrategyBuilder  # type: ignore
            max_attempts = int(os.getenv("OCI_RETRY_MAX_ATTEMPTS", "4"))
            total_time_sec = int(os.getenv("OCI_RETRY_TOTAL_TIME_SEC", "30"))
            retry_strategy = RetryStrategyBuilder() \
                .add_max_attempts(max_attempts) \
                .add_total_time(total_time_sec) \
                .get_retry_strategy()
            # Set on base client so all operations inherit unless overridden
            try:
                client.base_client.retry_strategy = retry_strategy  # type: ignore[attr-defined]
            except Exception:
                pass
        except Exception:
            # Retry strategy attachment is best-effort
            pass

        _client_cache[key] = client
        return client


def clear_client_cache() -> None:
    """
    Clear all cached clients. Useful for tests or when switching auth contexts.
    """
    with _client_lock:
        _client_cache.clear()
