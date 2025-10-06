from __future__ import annotations

import os
import re
from typing import Any, Dict


_OCID_RE = re.compile(r"ocid1\.[A-Za-z0-9_.-]+")
_SENSITIVE_KEYS = {
    "tenancy",
    "compartment",
    "compartment_id",
    "parent_compartment_id",
    "user",
    "user_id",
    "id",
    "resource_id",
    "work_request_id",
    "namespace",
    "namespace_name",
}


def privacy_enabled() -> bool:
    """Return True if response privacy masking is enabled.

    Controlled via env var `MCP_OCI_PRIVACY` (true/1/on) or
    `MCP_OCI_PRIVACY_MASK` (back-compat).
    """
    val = os.getenv("MCP_OCI_PRIVACY", os.getenv("MCP_OCI_PRIVACY_MASK", "")).strip().lower()
    return val in {"1", "true", "yes", "on", "enabled"}


def _mask_string(value: str) -> str:
    """Mask OCID-like substrings and long opaque identifiers.

    - OCIDs: keep a small prefix and suffix; replace middle with ellipsis.
    - Namespaces/other identifiers: if > 8 chars and key-tagged, callers can
      decide to pass through here, but we primarily rely on key-based masking.
    """
    def _mask_match(m: re.Match[str]) -> str:
        s = m.group(0)
        # Keep the first 14 chars (e.g., "ocid1.compartment") when available
        # and the last 6 chars for quick identification.
        if len(s) <= 12:
            return s
        return f"{s[:14]}…{s[-6:]}"

    masked = _OCID_RE.sub(_mask_match, value)
    return masked


def _mask_value_by_key(key: str, value: Any) -> Any:
    if isinstance(value, str):
        # If the key is sensitive, mask the entire value string conservatively
        if key.lower() in _SENSITIVE_KEYS:
            if value.startswith("ocid1."):
                return _mask_string(value)
            # Non-OCID but sensitive identifier (e.g., namespace)
            if len(value) > 8:
                return f"{value[:3]}***{value[-2:]}"
        # Otherwise, mask any OCID substrings that may appear inline
        return _mask_string(value)
    return value


def redact_payload(obj: Any) -> Any:
    """Recursively redact sensitive identifiers in dict/list structures.

    - Masks OCIDs in any strings
    - Masks values for known sensitive keys (tenancy, compartment_id, namespace, etc.)
    """
    try:
        if isinstance(obj, dict):
            red: Dict[str, Any] = {}
            for k, v in obj.items():
                red[k] = _mask_value_by_key(k, redact_payload(v))
            return red
        if isinstance(obj, list):
            return [redact_payload(x) for x in obj]
        if isinstance(obj, str):
            return _mask_string(obj)
        return obj
    except Exception:
        # Never fail masking – return original object on error
        return obj

