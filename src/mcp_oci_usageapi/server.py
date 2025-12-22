from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

# Load repo-local .env.local so OCI config is applied consistently.
try:
    from pathlib import Path
    from dotenv import load_dotenv

    _repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(_repo_root / ".env.local")
except Exception:
    pass

import oci

from mcp_oci_common import get_oci_config

logging.basicConfig(level=logging.INFO if os.getenv("DEBUG") else logging.WARNING)


def _client_from_config(client_class, profile: str | None = None, region: str | None = None):
    config = get_oci_config(profile_name=profile)
    if region:
        config["region"] = region
    signer = config.get("signer")
    if signer is not None:
        return client_class(config, signer=signer)
    return client_class(config)


def create_client(profile: str | None = None, region: str | None = None):
    return _client_from_config(oci.usage_api.UsageapiClient, profile=profile, region=region)


def make_client(profile: str | None = None, region: str | None = None):
    return _client_from_config(
        oci.resource_search.ResourceSearchClient, profile=profile, region=region
    )


def _build_filter(dimensions: Dict[str, Any] | None = None, tags: Any | None = None):
    dimensions = dimensions or {}
    kwargs: Dict[str, Any] = {}
    if dimensions:
        kwargs["dimensions"] = dimensions
    if tags:
        kwargs["tags"] = tags
    return oci.usage_api.models.Filter(**kwargs)


def _resolve_compartment_name_to_id(
    name: str, profile: str | None = None, region: str | None = None
) -> Optional[str]:
    name = name.strip()
    if not name:
        return None
    config = get_oci_config(profile_name=profile)
    tenancy_id = config.get("tenancy")
    if not tenancy_id:
        return None
    identity = _client_from_config(oci.identity.IdentityClient, profile=profile, region=region)
    try:
        resp = identity.list_compartments(
            tenancy_id,
            compartment_id_in_subtree=True,
            access_level="ANY",
        )
    except Exception:
        return None
    for comp in getattr(resp, "data", []) or []:
        if getattr(comp, "name", None) == name:
            return getattr(comp, "id", None)
    return None


def request_summarized_usages(
    tenant_id: str,
    time_usage_started: str,
    time_usage_ended: str,
    granularity: str,
    query_type: str,
    group_by: Optional[List[str]] = None,
    group_by_tag: Optional[List[str]] = None,
    compartment_id: Optional[str] = None,
    compartment_name: Optional[str] = None,
    tags: Any | None = None,
    profile: str | None = None,
    region: str | None = None,
) -> Dict[str, Any]:
    client = create_client(profile=profile, region=region)

    dimensions: Dict[str, Any] = {}
    if compartment_id:
        dimensions["compartmentId"] = compartment_id
    elif compartment_name:
        resolved = _resolve_compartment_name_to_id(
            compartment_name, profile=profile, region=region
        )
        if resolved:
            dimensions["compartmentId"] = resolved

    filter_obj = _build_filter(dimensions=dimensions if dimensions else None, tags=tags)

    details = oci.usage_api.models.RequestSummarizedUsagesDetails(
        tenant_id=tenant_id,
        time_usage_started=time_usage_started,
        time_usage_ended=time_usage_ended,
        granularity=granularity,
        query_type=query_type,
        group_by=group_by,
        group_by_tag=group_by_tag,
        filter=filter_obj,
    )
    resp = client.request_summarized_usages(request_summarized_usages_details=details)
    return {"items": getattr(resp.data, "items", [])}


def cost_by_service(
    tenant_id: str,
    days: int = 7,
    granularity: str = "DAILY",
    profile: str | None = None,
    region: str | None = None,
) -> Dict[str, Any]:
    from datetime import datetime, timedelta, timezone

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days)
    end = end_dt.isoformat().replace("+00:00", "Z")
    start = start_dt.isoformat().replace("+00:00", "Z")
    return request_summarized_usages(
        tenant_id=tenant_id,
        time_usage_started=start,
        time_usage_ended=end,
        granularity=granularity,
        query_type="COST",
        group_by=["service"],
        profile=profile,
        region=region,
    )


def _resource_query(resource_type: str, compartment_id: str) -> str:
    return f"query {resource_type} resources where compartmentId = '{compartment_id}'"


def _paginate_resource_search(client, search_details):
    items: List[Any] = []
    page = None
    while True:
        resp = client.search_resources(search_details=search_details, limit=1000, page=page)
        items.extend(getattr(resp.data, "items", []) or [])
        page = getattr(resp, "opc_next_page", None)
        if not page:
            break
    return items


def count_instances(
    compartment_id: str,
    include_subtree: bool = True,
    profile: str | None = None,
    region: str | None = None,
) -> Dict[str, Any]:
    client = make_client(profile=profile, region=region)
    details = oci.resource_search.models.StructuredSearchDetails(
        query=_resource_query("instance", compartment_id),
        matching_context_type="NONE" if include_subtree else "NONE",
    )
    items = _paginate_resource_search(client, details)
    count = len([item for item in items if getattr(item, "resource_type", None) == "instance"])
    return {"resource": "instance", "count": count}


def correlate_costs_and_resources(
    tenant_id: str,
    days: int,
    compartment_id: str,
    include_subtree: bool = True,
    profile: str | None = None,
    region: str | None = None,
) -> Dict[str, Any]:
    cost_result = cost_by_service(
        tenant_id=tenant_id,
        days=days,
        granularity="DAILY",
        profile=profile,
        region=region,
    )
    cost_items = cost_result.get("items") if isinstance(cost_result, dict) else cost_result

    client = make_client(profile=profile, region=region)
    details = oci.resource_search.models.StructuredSearchDetails(
        query=_resource_query("all", compartment_id),
        matching_context_type="NONE" if include_subtree else "NONE",
    )
    items = _paginate_resource_search(client, details)

    counts: Dict[str, int] = {}
    for item in items:
        rtype = getattr(item, "resource_type", "unknown")
        counts[rtype] = counts.get(rtype, 0) + 1

    return {
        "cost_by_service": list(cost_items or []),
        "resource_counts": counts,
    }
