from __future__ import annotations

from typing import Any, Dict, List, Optional


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float safely; None/invalid → default.

    This avoids float(None) and similar crashes when parsing Usage API results.
    """
    try:
        if value is None:
            return default
        # Some SDK objects may already be numeric
        return float(value)
    except Exception:
        return default


def currency_from(data: Dict[str, Any]) -> Optional[str]:
    """Extract tenancy currency from a Usage API dict response."""
    cur = data.get("currency")
    if cur:
        return cur
    items = data.get("items") or []
    for it in items:
        c = it.get("currency")
        if c:
            return c
    return None


def map_compartment_rows(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize Usage API items → rows[{date, compartment, service, cost}]."""
    rows: List[Dict[str, Any]] = []
    for it in items or []:
        date = it.get("time_usage_started") or it.get("timeUsageStarted") or ""
        comp = it.get("compartmentName") or it.get("compartment_name") or "Unknown"
        svc = it.get("service") or "Unknown"
        cost = safe_float(it.get("computedAmount") or it.get("computed_amount"))
        rows.append({"date": date, "compartment": comp, "service": svc, "cost": cost})
    return rows


def resolve_tenancy(passed_tenancy: Optional[str], cfg: Dict[str, Any]) -> str:
    """Return a full tenancy OCID even if the caller passed a masked/invalid one."""
    if isinstance(passed_tenancy, str) and passed_tenancy.startswith("ocid1.tenancy.") and len(passed_tenancy) > 24 and "..." not in passed_tenancy:
        return passed_tenancy
    return cfg.get("tenancy")


def resolve_compartments(
    identity_client: Any,
    tenancy_id: str,
    value: Optional[str],
    include_children: bool,
) -> Optional[List[str]]:
    """Resolve a compartment scope from OCID or name → list of OCIDs.

    - If value starts with ocid1.compartment., treat as OCID and optionally expand children.
    - Otherwise treat as case-insensitive name and resolve to OCID (and optionally children).
    """
    if not value:
        return None
    val = str(value).strip()
    # OCID path
    if val.startswith("ocid1.compartment."):
        if include_children:
            comps = list_compartments_recursive(identity_client, tenancy_id, parent_compartment_id=val)
            return [c["id"] for c in comps]
        return [val]
    # Name path
    comps = list_compartments_recursive(identity_client, tenancy_id, parent_compartment_id=None)
    exact = [c for c in comps if str(c.get("name", "")).lower() == val.lower()]
    chosen = exact[0] if exact else (comps[0] if comps else None)
    if not chosen:
        return None
    if include_children:
        kids = list_compartments_recursive(identity_client, tenancy_id, parent_compartment_id=chosen["id"]) or []
        return [c["id"] for c in kids]
    return [chosen["id"]]


# Imported lazily to avoid circular imports
def list_compartments_recursive(identity_client: Any, tenancy_id: str, parent_compartment_id: Optional[str] = None) -> List[Dict[str, Any]]:
    from .oci_client_adapter import list_compartments_recursive as _list
    return _list(identity_client, tenancy_id, parent_compartment_id=parent_compartment_id)

