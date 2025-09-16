"""MCP Server: OCI Budgets (Cost Control)

Exposes tools as `oci:budgets:<action>`.
"""

from typing import Any

from mcp_oci_common import make_client
from mcp_oci_common.response import with_meta

try:
    import oci  # type: ignore
except Exception:
    oci = None


def create_client(profile: str | None = None, region: str | None = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.budget.BudgetClient, profile=profile, region=region)


def register_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "oci:budgets:list-budgets",
            "description": "List budgets for a compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_budgets,
        },
        {
            "name": "oci:budgets:get-budget",
            "description": "Get a budget by OCID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "budget_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["budget_id"],
            },
            "handler": get_budget,
        },
        {
            "name": "oci:budgets:list-alert-rules",
            "description": "List alert rules for a budget.",
            "parameters": {
                "type": "object",
                "properties": {
                    "budget_id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["budget_id"],
            },
            "handler": list_alert_rules,
        },
        {
            "name": "oci:budgets:create-budget",
            "description": "Create a budget (confirm=true required; dry_run supported).",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "amount": {"type": "number"},
                    "reset_period": {"type": "string", "enum": ["MONTHLY"], "default": "MONTHLY"},
                    "display_name": {"type": "string"},
                    "targets": {"type": "array", "items": {"type": "string"}},
                    "dry_run": {"type": "boolean", "default": False},
                    "confirm": {"type": "boolean", "default": False},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id", "amount"],
            },
            "handler": create_budget,
            "mutating": True,
        },
    ]


def list_budgets(compartment_id: str, limit: int | None = None, page: str | None = None,
                 profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_budgets(compartment_id=compartment_id, **kwargs)
    items = [b.__dict__ for b in getattr(resp, "items", getattr(resp, "data", []) or [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def get_budget(budget_id: str, profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.get_budget(budget_id)
    data = resp.data.__dict__ if hasattr(resp, "data") else getattr(resp, "__dict__", {})
    return with_meta(resp, {"item": data})


def list_alert_rules(budget_id: str, limit: int | None = None, page: str | None = None,
                     profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_alert_rules(budget_id=budget_id, **kwargs)
    items = [a.__dict__ for a in getattr(resp, "items", getattr(resp, "data", []) or [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def create_budget(compartment_id: str, amount: float, reset_period: str = "MONTHLY",
                  display_name: str | None = None, targets: list[str] | None = None,
                  dry_run: bool = False, confirm: bool = False,
                  profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    details = {
        "compartment_id": compartment_id,
        "amount": amount,
        "reset_period": reset_period,
    }
    if display_name:
        details["display_name"] = display_name
    if targets:
        details["targets"] = targets
    if dry_run:
        return {"dry_run": True, "request": details}
    model = oci.budget.models.CreateBudgetDetails(**details)  # type: ignore
    client = create_client(profile=profile, region=region)
    resp = client.create_budget(create_budget_details=model)
    data = resp.data.__dict__ if hasattr(resp, "data") else getattr(resp, "__dict__", {})
    return with_meta(resp, {"item": data})
