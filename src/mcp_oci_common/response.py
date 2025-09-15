from typing import Any, Dict, Optional


def with_meta(resp: Any, payload: Dict[str, Any], *, next_page: Optional[str] = None) -> Dict[str, Any]:
    """Attach opc_request_id and next_page to payload if available."""
    try:
        headers = getattr(resp, "headers", None)
        if headers and isinstance(headers, dict):
            rid = headers.get("opc-request-id") or headers.get("opc_request_id")
            if rid:
                payload.setdefault("opc_request_id", rid)
    except Exception:
        pass
    if next_page is not None:
        payload.setdefault("next_page", next_page)
    return payload

