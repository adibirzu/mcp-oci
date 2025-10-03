import json
from datetime import datetime, timezone
from typing import Any, Dict

# Optional privacy masking for responses
try:
    from .privacy import privacy_enabled, redact_payload
except Exception:  # pragma: no cover - defensive import
    def privacy_enabled() -> bool:  # type: ignore
        return False

    def redact_payload(obj: Any) -> Any:  # type: ignore
        return obj


def _now_iso() -> str:
    try:
        return datetime.now(timezone.utc).isoformat()
    except Exception:
        # Fallback without tzinfo
        return datetime.utcnow().isoformat() + "Z"


def with_meta(payload: Dict[str, Any] | Any, *args, **kwargs) -> str:
    """
    Flexible response wrapper used across legacy src/* packages.

    Supported call patterns (for backward compatibility):
      1) with_meta(payload, extra_dict)
         - Merges extra_dict into payload (top-level), no _meta unless provided via kwargs
      2) with_meta(payload, success: bool, message: str | None = None)
         - Adds _meta.success and _meta.message
      3) with_meta(payload, extra_dict, success: bool, message: str | None = None)
         - Merges extra_dict and sets _meta fields
      4) with_meta(payload, success=..., message=..., meta={...})
         - Sets _meta from keyword args

    Always returns a JSON string; timestamp is added under _meta.timestamp.
    """
    extra = None
    success = None
    message = None

    if args:
        if isinstance(args[0], dict):
            extra = args[0]
            if len(args) > 1 and isinstance(args[1], bool):
                success = args[1]
            if len(args) > 2 and isinstance(args[2], (str, type(None))):
                message = args[2]
        elif isinstance(args[0], bool):
            success = args[0]
            if len(args) > 1 and isinstance(args[1], (str, type(None))):
                message = args[1]

    # Keyword overrides
    success = kwargs.get("success", success)
    message = kwargs.get("message", message)
    user_meta = kwargs.get("meta")

    # Start with a dict payload
    if isinstance(payload, dict):
        out: Dict[str, Any] = dict(payload)
    else:
        # If not a dict, wrap into a dict under 'data'
        out = {"data": payload}

    # Merge extra dict into top-level payload if provided
    if isinstance(extra, dict):
        try:
            out.update(extra)
        except Exception:
            # Be permissive: if update fails, include under a namespaced key
            out.setdefault("_extra", extra)

    # Build _meta
    meta: Dict[str, Any] = {"timestamp": _now_iso()}
    if success is not None:
        meta["success"] = bool(success)
    if message is not None:
        meta["message"] = message
    if isinstance(user_meta, dict):
        # User-provided meta wins on explicit keys
        meta.update(user_meta)

    if meta:
        out["_meta"] = meta

    # Apply privacy masking if enabled
    if privacy_enabled():
        out = redact_payload(out)

    # Serialize safely
    try:
        return json.dumps(out, default=str)
    except Exception:
        # Last resort: stringify payload
        return json.dumps({"data": str(out), "_meta": meta}, default=str)
