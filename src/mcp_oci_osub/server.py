"""MCP Server: OCI Subscriptions (OSUB)

Expose basic subscription listing via `oci:osub:<action>`.
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
    return make_client(oci.osub_subscription.SubscriptionClient, profile=profile, region=region)


def register_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "oci:osub:list-subscriptions",
            "description": "List subscriptions for a tenancy.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tenancy_id": {"type": "string"},
                    "limit": {"type": "integer"},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["tenancy_id"],
            },
            "handler": list_subscriptions,
        }
    ]


def list_subscriptions(tenancy_id: str, limit: int | None = None, page: str | None = None,
                       profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {"tenancy_id": tenancy_id}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    method = getattr(client, "list_subscriptions", None)
    if method is None:
        raise RuntimeError("list_subscriptions not available in this SDK version")
    resp = method(**kwargs)
    items = [i.__dict__ for i in getattr(resp, "data", [])]
    return with_meta(resp, {"items": items})
