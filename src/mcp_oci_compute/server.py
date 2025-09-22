"""MCP Server: OCI Compute

Exposes tools as `oci:compute:<action>`; read/list ops prioritized.
"""

from datetime import datetime
from typing import Any

from mcp_oci_common import make_client
from mcp_oci_common.response import with_meta
from mcp_oci_common.cache import get_cache
from mcp_oci_common.name_registry import get_registry

try:
    import oci  # type: ignore
except Exception:
    oci = None


def create_client(profile: str | None = None, region: str | None = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.core.ComputeClient, profile=profile, region=region)


def create_search_client(profile: str | None = None, region: str | None = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.resource_search.ResourceSearchClient, profile=profile, region=region)


def register_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "oci_compute_list_instances",
            "description": "List compute instances; defaults to tenancy root if compartment_id omitted; can include all subcompartments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "compartment_name": {"type": "string", "description": "Resolve to compartment_id by exact name (subtree search)"},
                    "availability_domain": {"type": "string"},
                    "lifecycle_state": {"type": "string", "enum": [
                        "PROVISIONING","RUNNING","STARTING","STOPPING","STOPPED","CREATING_IMAGE","TERMINATING","TERMINATED","MIGRATING"
                    ]},
                    "include_subtree": {"type": "boolean", "default": True},
                    "display_name": {"type": "string"},
                    "display_name_contains": {"type": "string"},
                    "shape": {"type": "string"},
                    "time_created_after": {"type": "string", "description": "ISO8601, e.g. 2025-01-01T00:00:00Z"},
                    "time_created_before": {"type": "string", "description": "ISO8601, e.g. 2025-01-31T23:59:59Z"},
                    "freeform_tags": {"type": "object", "additionalProperties": {"type": "string"}},
                    "defined_tags": {"type": "object", "additionalProperties": {"type": "string"}},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "max_items": {"type": "integer", "minimum": 1, "maximum": 5000, "description": "Cap total results aggregated across compartments. Default 500."},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": [],
            },
            "handler": list_instances,
        },
        {
            "name": "oci_compute_list_boot_volume_attachments",
            "description": "List boot volume attachments; filter by instance or compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "instance_id": {"type": "string"},
                    "availability_domain": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
            },
            "handler": list_boot_volume_attachments,
        },
        {
            "name": "oci_compute_list_images",
            "description": "List images in a compartment; filter by OS and version.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "operating_system": {"type": "string"},
                    "operating_system_version": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_images,
        },
        {
            "name": "oci_compute_list_vnics",
            "description": "List VNIC attachments for an instance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "instance_id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id", "instance_id"],
            },
            "handler": list_vnics,
        },
        {
            "name": "oci_compute_get_instance",
            "description": "Get instance details by OCID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instance_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["instance_id"],
            },
            "handler": get_instance,
        },
        {
            "name": "oci_compute_list_boot_volumes",
            "description": "List boot volumes in an availability domain (Blockstorage).",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "availability_domain": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id", "availability_domain"],
            },
            "handler": list_boot_volumes,
        },
        {
            "name": "oci_compute_list_instance_configurations",
            "description": "List instance configurations (Compute Management).",
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
            "handler": list_instance_configurations,
        },
        {
            "name": "oci_compute_list_shapes",
            "description": "List compute shapes in a compartment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "availability_domain": {"type": "string"},
                    "image_id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_shapes,
        },
        {
            "name": "oci_compute_instance_action",
            "description": "Perform an instance action (START, STOP, SOFTSTOP, RESET). Requires confirm=true; supports dry_run.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instance_id": {"type": "string"},
                    "action": {"type": "string", "enum": ["START", "STOP", "SOFTSTOP", "RESET"]},
                    "dry_run": {"type": "boolean", "default": False},
                    "confirm": {"type": "boolean", "default": False},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["instance_id", "action"],
            },
            "handler": instance_action,
            "mutating": True,
        },
        {
            "name": "oci_compute_search_instances",
            "description": "Search instances via OCI Resource Search (structured query).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Structured search query; if omitted, built from filters."},
                    "lifecycle_state": {"type": "string", "enum": [
                        "PROVISIONING","RUNNING","STARTING","STOPPING","STOPPED","CREATING_IMAGE","TERMINATING","TERMINATED","MIGRATING"
                    ]},
                    "display_name": {"type": "string"},
                    "compartment_id": {"type": "string"},
                    "include_subtree": {"type": "boolean", "default": True},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": [],
            },
            "handler": search_instances,
        },
        {
            "name": "oci_compute_list_stopped_instances",
            "description": "Convenience alias: list STOPPED instances. Prompts to narrow by compartment/time window if results are large or empty.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "compartment_name": {"type": "string"},
                    "include_subtree": {"type": "boolean", "default": True},
                    "display_name": {"type": "string"},
                    "display_name_contains": {"type": "string"},
                    "shape": {"type": "string"},
                    "time_created_after": {"type": "string"},
                    "time_created_before": {"type": "string"},
                    "freeform_tags": {"type": "object", "additionalProperties": {"type": "string"}},
                    "defined_tags": {"type": "object", "additionalProperties": {"type": "string"}},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "max_items": {"type": "integer", "minimum": 1, "maximum": 5000},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": [],
            },
            "handler": list_stopped_instances,
        },
    ]


def list_instances(compartment_id: str | None = None, compartment_name: str | None = None,
                   availability_domain: str | None = None,
                   lifecycle_state: str | None = None,
                   include_subtree: bool = True,
                   display_name: str | None = None,
                   display_name_contains: str | None = None,
                   shape: str | None = None,
                   time_created_after: str | None = None,
                   time_created_before: str | None = None,
                   freeform_tags: dict[str, str] | None = None,
                   defined_tags: dict[str, str] | None = None,
                   limit: int | None = None, page: str | None = None,
                   max_items: int | None = None,
                   profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    cache = get_cache()
    registry = get_registry()
    # Resolve root compartment (tenancy) if not provided
    root_compartment: str | None = compartment_id
    if root_compartment is None:
        try:
            from mcp_oci_common import get_oci_config  # type: ignore
            cfg = get_oci_config(profile_name=profile)
            if region:
                cfg["region"] = region
            root_compartment = cfg.get("tenancy")
        except Exception:
            root_compartment = None
    if not root_compartment:
        raise ValueError("compartment_id is required (no default tenancy found)")

    # Optional: resolve compartment by name using registry first; fall back to IAM only once
    if compartment_name and not compartment_id:
        resolved = registry.resolve_compartment(compartment_name)
        if not resolved:
            _build_compartment_registry(root_compartment, include_subtree, profile, region)
            resolved = registry.resolve_compartment(compartment_name)
        if resolved:
            root_compartment = resolved

    # Build list of compartments to search
    compartments: list[str] = [root_compartment]
    if include_subtree:
        try:
            if oci is None:
                raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
            from mcp_oci_common import make_client as _make
            iam = _make(oci.identity.IdentityClient, profile=profile, region=region)
            nextp: str | None = None
            while True:
                kwargs_comp: dict[str, Any] = {
                    "compartment_id": root_compartment,
                    "compartment_id_in_subtree": True,
                    "access_level": "ANY",
                }
                if nextp:
                    kwargs_comp["page"] = nextp
                respc = iam.list_compartments(**kwargs_comp)
                for c in getattr(respc, "data", []) or []:
                    cid = getattr(c, "id", None) or (c.get("id") if isinstance(c, dict) else None)
                    if cid:
                        compartments.append(cid)
                nextp = getattr(respc, "opc_next_page", None)
                if not nextp:
                    break
        except Exception:
            # Fallback silently to just root compartment
            pass

    # Check aggregated cache for this query to avoid backend calls
    _cache_params = {
        "root_compartment": root_compartment,
        "include_subtree": include_subtree,
        "availability_domain": availability_domain,
        "lifecycle_state": lifecycle_state,
        "display_name": display_name,
        "display_name_contains": display_name_contains,
        "shape": shape,
        "time_created_after": time_created_after,
        "time_created_before": time_created_before,
        "freeform_tags": freeform_tags or {},
        "defined_tags": defined_tags or {},
        "limit": limit,
        "page": page,
        "max_items": max_items,
    }
    _cached = cache.get("compute", "list_instances_v2", _cache_params)
    if _cached:
        return _cached

    # Collect instances across compartments
    all_items: list[dict[str, Any]] = []
    total_cap = max_items or 500
    for comp_id in compartments:
        kwargs_req: dict[str, Any] = {}
        if availability_domain:
            kwargs_req["availability_domain"] = availability_domain
        if lifecycle_state:
            # pass through; supported by SDK. If not, we will still filter client-side below.
            kwargs_req["lifecycle_state"] = lifecycle_state
        next_token: str | None = page
        while True:
            if next_token:
                kwargs_req["page"] = next_token
            resp = client.list_instances(compartment_id=comp_id, **kwargs_req)
            items = [i.data.__dict__ if hasattr(i, "data") else i.__dict__ for i in getattr(resp, "data", [])]
            if items:
                items = [i for i in items if _instance_matches_filters(
                    i,
                    lifecycle_state=lifecycle_state,
                    display_name=display_name,
                    display_name_contains=display_name_contains,
                    shape=shape,
                    time_created_after=time_created_after,
                    time_created_before=time_created_before,
                    freeform_tags=freeform_tags,
                    defined_tags=defined_tags,
                )]
            # Index instances for fast name->ocid resolution
            if items:
                try:
                    registry.update_instances(comp_id, items)
                except Exception:
                    pass
            all_items.extend(items)
            if len(all_items) >= total_cap:
                all_items = all_items[:total_cap]
                break
            next_token = getattr(resp, "opc_next_page", None)
            if not next_token:
                break
        # Do not propagate next_page when aggregating; return full aggregated list
    result: dict[str, Any] = {"items": all_items}
    if len(all_items) >= total_cap:
        result["truncated"] = True
        result["hints"] = {
            "message": "Result capped. Narrow scope with compartment_name/compartment_id, lifecycle_state, display_name_contains, or time_created_after/before.",
            "suggested_params": [
                "compartment_name",
                "lifecycle_state",
                "display_name_contains",
                "time_created_after",
                "time_created_before",
            ],
        }
    if not all_items:
        result["hints"] = {
            "message": "No instances matched. Check region/compartment; try removing lifecycle_state or use search-instances.",
            "suggested_params": [
                "region",
                "compartment_name",
                "include_subtree",
                "lifecycle_state",
            ],
        }
    # Save aggregated result to cache (TTL uses global default)
    try:
        import os
        ttl = int(os.getenv("MCP_CACHE_TTL_COMPUTE", os.getenv("MCP_CACHE_TTL", "3600")))
        cache.set("compute", "list_instances_v2", _cache_params, result, ttl_seconds=ttl)
    except Exception:
        pass
    return result


def _build_search_query(lifecycle_state: str | None, display_name: str | None, compartment_id: str | None, include_subtree: bool) -> str:
    """Build OCI Resource Search query with proper syntax"""
    clauses: list[str] = []
    
    # Resource type
    clauses.append("resourceType = 'Instance'")
    
    # Lifecycle state - handle multiple states with OR
    if lifecycle_state:
        if ' OR ' in lifecycle_state:
            # Handle OR conditions properly
            lifecycle_clause = f"({lifecycle_state})"
        else:
            lifecycle_clause = f"lifecycleState = '{lifecycle_state}'"
        clauses.append(lifecycle_clause)
    
    # Display name - use contains for partial matches
    if display_name:
        clauses.append(f"displayName contains '{display_name}'")
    
    # Compartment handling
    if compartment_id:
        if include_subtree:
            clauses.append(f"compartmentId = '{compartment_id}'")
            clauses.append("compartmentIdInSubtree = true")
        else:
            clauses.append(f"compartmentId = '{compartment_id}'")
    
    # Join with AND
    return f"query all resources where {' AND '.join(clauses)}"


def search_instances(query: str | None = None,
                     lifecycle_state: str | None = None,
                     display_name: str | None = None,
                     compartment_id: str | None = None,
                     include_subtree: bool = True,
                     limit: int | None = None, page: str | None = None,
                     profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    
    client = create_search_client(profile=profile, region=region)
    
    # Handle the specific query format that was failing
    if query and 'lifecycle_state:' in query:
        # Convert the failing query format to proper OCI syntax
        query = _convert_lifecycle_query(query)
    else:
        query = query or _build_search_query(lifecycle_state, display_name, compartment_id, include_subtree)
    
    details = oci.resource_search.models.StructuredSearchDetails(  # type: ignore
        query=query,
        matching_context_type="NONE",
    )
    kwargs: dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    
    try:
        resp = client.search_resources(details, **kwargs)
        data_items = []
        items = getattr(resp, "data", None)
        items = getattr(items, "items", items)
        for it in items or []:
            # Convert SDK model to dict when possible
            data_items.append(it.__dict__ if hasattr(it, "__dict__") else it)
        next_page = getattr(resp, "opc_next_page", None)
        return with_meta(resp, {"items": data_items, "query": query}, next_page=next_page)
    except Exception as e:
        # Fallback to regular list_instances if search fails
        return _fallback_to_list_instances(
            lifecycle_state, display_name, compartment_id, include_subtree,
            limit, page, profile, region, str(e)
        )


def _convert_lifecycle_query(query: str) -> str:
    """Convert lifecycle_state:STATE OR lifecycle_state:STATE format to OCI syntax"""
    # Handle the specific format: lifecycle_state:RUNNING OR lifecycle_state:STARTING OR lifecycle_state:PROVISIONING OR lifecycle_state:PENDING
    if 'lifecycle_state:' in query and ' OR ' in query:
        # Extract lifecycle states
        states = []
        for part in query.split(' OR '):
            if 'lifecycle_state:' in part:
                state = part.split('lifecycle_state:')[1].strip()
                states.append(f"lifecycleState = '{state}'")
        
        if states:
            lifecycle_clause = f"({' OR '.join(states)})"
            return f"query all resources where resourceType = 'Instance' AND {lifecycle_clause}"
    
    # Fallback to original query
    return query


def _fallback_to_list_instances(lifecycle_state: str | None, display_name: str | None, 
                               compartment_id: str | None, include_subtree: bool,
                               limit: int | None, page: str | None,
                               profile: str | None, region: str | None, error_msg: str) -> dict[str, Any]:
    """Fallback to regular list_instances when search fails"""
    try:
        # Parse lifecycle_state for multiple states
        if lifecycle_state and ' OR ' in lifecycle_state:
            # For multiple states, we'll need to make multiple calls and combine results
            states = [s.strip() for s in lifecycle_state.split(' OR ')]
            all_items = []
            
            for state in states:
                result = list_instances(
                    compartment_id=compartment_id,
                    lifecycle_state=state,
                    include_subtree=include_subtree,
                    display_name=display_name,
                    limit=limit,
                    page=page,
                    profile=profile,
                    region=region
                )
                all_items.extend(result.get("items", []))
            
            # Remove duplicates based on id
            seen_ids = set()
            unique_items = []
            for item in all_items:
                item_id = item.get("id")
                if item_id and item_id not in seen_ids:
                    seen_ids.add(item_id)
                    unique_items.append(item)
            
            return {
                "items": unique_items,
                "query": f"Fallback search for lifecycle_state: {lifecycle_state}",
                "fallback_reason": f"Search API failed: {error_msg}",
                "method": "list_instances_fallback"
            }
        else:
            # Single state, use regular list_instances
            result = list_instances(
                compartment_id=compartment_id,
                lifecycle_state=lifecycle_state,
                include_subtree=include_subtree,
                display_name=display_name,
                limit=limit,
                page=page,
                profile=profile,
                region=region
            )
            result["fallback_reason"] = f"Search API failed: {error_msg}"
            result["method"] = "list_instances_fallback"
            return result
    except Exception as fallback_error:
        return {
            "items": [],
            "error": f"Both search and list_instances failed. Search error: {error_msg}, Fallback error: {str(fallback_error)}",
            "query": f"Failed search for lifecycle_state: {lifecycle_state}"
        }


def list_stopped_instances(compartment_id: str | None = None, compartment_name: str | None = None,
                           include_subtree: bool = True,
                           display_name: str | None = None,
                           display_name_contains: str | None = None,
                           shape: str | None = None,
                           time_created_after: str | None = None,
                           time_created_before: str | None = None,
                           freeform_tags: dict[str, str] | None = None,
                           defined_tags: dict[str, str] | None = None,
                           limit: int | None = None, page: str | None = None,
                           max_items: int | None = None,
                           profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    # Force lifecycle_state STOPPED and reuse list_instances
    result = list_instances(
        compartment_id=compartment_id,
        compartment_name=compartment_name,
        include_subtree=include_subtree,
        lifecycle_state="STOPPED",
        display_name=display_name,
        display_name_contains=display_name_contains,
        shape=shape,
        time_created_after=time_created_after,
        time_created_before=time_created_before,
        freeform_tags=freeform_tags,
        defined_tags=defined_tags,
        limit=limit,
        page=page,
        max_items=max_items or 500,
        profile=profile,
        region=region,
    )
    items = result.get("items") or []
    # Proactive guidance when scope is ambiguous
    if (not items) or result.get("truncated"):
        hints = result.get("hints") or {}
        suggestions = set(hints.get("suggested_params", [])) if isinstance(hints, dict) else set()
        suggestions.update(["compartment_name", "time_created_after", "time_created_before", "display_name_contains"])  # steer refinement
        result["hints"] = {
            "message": "Use compartment_name (or compartment_id) and optionally a creation time window to narrow the STOPPED instances list.",
            "suggested_params": sorted(suggestions),
        }
    return result


def _resolve_compartment_by_name(name: str, root_compartment: str, include_subtree: bool,
                                 profile: str | None, region: str | None) -> str | None:
    try:
        if oci is None:
            return None
        from mcp_oci_common import make_client as _make
        iam = _make(oci.identity.IdentityClient, profile=profile, region=region)
        nextp: str | None = None
        while True:
            kwargs_comp: dict[str, Any] = {
                "compartment_id": root_compartment,
                "compartment_id_in_subtree": include_subtree,
                "access_level": "ANY",
            }
            if nextp:
                kwargs_comp["page"] = nextp
            respc = iam.list_compartments(**kwargs_comp)
            for c in getattr(respc, "data", []) or []:
                cname = getattr(c, "name", None) or (c.get("name") if isinstance(c, dict) else None)
                if cname == name:
                    cid = getattr(c, "id", None) or (c.get("id") if isinstance(c, dict) else None)
                    if cid:
                        return cid
            nextp = getattr(respc, "opc_next_page", None)
            if not nextp:
                break
    except Exception:
        return None
    return None


def _build_compartment_registry(root_compartment: str, include_subtree: bool,
                                profile: str | None, region: str | None) -> None:
    """Populate global compartment name->OCID mapping. Safe no-op if already populated."""
    from mcp_oci_common.name_registry import get_registry as _get_reg
    reg = _get_reg()
    if reg.compartments_by_name:
        return
    try:
        if oci is None:
            return
        from mcp_oci_common import make_client as _make
        iam = _make(oci.identity.IdentityClient, profile=profile, region=region)
        nextp: str | None = None
        items: list[dict] = []
        while True:
            kwargs_comp: dict[str, Any] = {
                "compartment_id": root_compartment,
                "compartment_id_in_subtree": include_subtree,
                "access_level": "ANY",
            }
            if nextp:
                kwargs_comp["page"] = nextp
            respc = iam.list_compartments(**kwargs_comp)
            for c in getattr(respc, "data", []) or []:
                items.append({
                    "id": getattr(c, "id", None),
                    "name": getattr(c, "name", None),
                })
            nextp = getattr(respc, "opc_next_page", None)
            if not nextp:
                break
        # Include root
        items.append({"id": root_compartment, "name": "tenancy"})
        reg.update_compartments(items)
    except Exception:
        return


def _parse_iso8601(ts: str | None) -> datetime | None:
    if not ts:
        return None
    # Basic parser for Z timestamps
    try:
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _instance_matches_filters(item: dict[str, Any], *, lifecycle_state: str | None, display_name: str | None,
                              display_name_contains: str | None, shape: str | None,
                              time_created_after: str | None, time_created_before: str | None,
                              freeform_tags: dict[str, str] | None, defined_tags: dict[str, str] | None) -> bool:
    # Handle both underscore-prefixed and non-prefixed attribute names
    def get_attr(item: dict[str, Any], key: str) -> Any:
        return item.get(key) or item.get(f"_{key}")
    
    if lifecycle_state and str(get_attr(item, "lifecycle_state")) != lifecycle_state:
        return False
    if display_name and str(get_attr(item, "display_name")) != display_name:
        return False
    if display_name_contains and display_name_contains.lower() not in str(get_attr(item, "display_name") or "").lower():
        return False
    if shape and str(get_attr(item, "shape")) != shape:
        return False
    # Time filters
    tca = _parse_iso8601(time_created_after)
    tcb = _parse_iso8601(time_created_before)
    if tca or tcb:
        created = get_attr(item, "time_created")
        try:
            created_dt = None
            if isinstance(created, datetime):
                created_dt = created
            elif isinstance(created, str):
                created_dt = _parse_iso8601(created)
            if created_dt:
                if tca and created_dt < tca:
                    return False
                if tcb and created_dt > tcb:
                    return False
        except Exception:
            pass
    # Tags
    if freeform_tags:
        ftags = get_attr(item, "freeform_tags") or {}
        for k, v in (freeform_tags or {}).items():
            if str(ftags.get(k)) != str(v):
                return False
    if defined_tags:
        dtags = get_attr(item, "defined_tags") or {}
        # defined tags map is nested: {"namespace": {"key": value}}
        for kval, v in (defined_tags or {}).items():
            # expect key as namespace.key
            if "." in kval:
                ns, key = kval.split(".", 1)
                if str((dtags.get(ns) or {}).get(key)) != str(v):
                    return False
            # fallback: top-level key lookup
            elif str(dtags.get(kval)) != str(v):
                return False
    return True


def list_images(compartment_id: str, operating_system: str | None = None, operating_system_version: str | None = None,
                limit: int | None = None, page: str | None = None,
                profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if operating_system:
        kwargs["operating_system"] = operating_system
    if operating_system_version:
        kwargs["operating_system_version"] = operating_system_version
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_images(compartment_id=compartment_id, **kwargs)
    items = [i.__dict__ for i in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_vnics(compartment_id: str, instance_id: str,
               limit: int | None = None, page: str | None = None,
               profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {"instance_id": instance_id}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_vnic_attachments(compartment_id=compartment_id, **kwargs)
    items = [a.__dict__ for a in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def get_instance(instance_id: str, profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.get_instance(instance_id)
    data = resp.data.__dict__ if hasattr(resp, "data") else getattr(resp, "__dict__", {})
    return with_meta(resp, {"item": data})


def instance_action(instance_id: str, action: str, dry_run: bool = False, confirm: bool = False,
                    profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    if dry_run:
        return {"dry_run": True, "request": {"instance_id": instance_id, "action": action}}
    client = create_client(profile=profile, region=region)
    resp = client.instance_action(instance_id=instance_id, action=action)
    data = resp.data.__dict__ if hasattr(resp, "data") else getattr(resp, "__dict__", {})
    return with_meta(resp, {"item": data})


def list_boot_volumes(compartment_id: str, availability_domain: str,
                      limit: int | None = None, page: str | None = None,
                      profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    from mcp_oci_common import make_client as _make

    blk = _make(oci.core.BlockstorageClient, profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = blk.list_boot_volumes(availability_domain=availability_domain, compartment_id=compartment_id, **kwargs)
    items = [b.__dict__ for b in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_instance_configurations(compartment_id: str, limit: int | None = None, page: str | None = None,
                                 profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    from mcp_oci_common import make_client as _make

    mgmt = _make(oci.core.ComputeManagementClient, profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = mgmt.list_instance_configurations(compartment_id=compartment_id, **kwargs)
    items = [c.__dict__ for c in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_boot_volume_attachments(compartment_id: str | None = None, instance_id: str | None = None,
                                 availability_domain: str | None = None,
                                 limit: int | None = None, page: str | None = None,
                                 profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if compartment_id:
        kwargs["compartment_id"] = compartment_id
    if instance_id:
        kwargs["instance_id"] = instance_id
    if availability_domain:
        kwargs["availability_domain"] = availability_domain
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_boot_volume_attachments(**kwargs)
    items = [a.__dict__ for a in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_shapes(compartment_id: str, availability_domain: str | None = None, image_id: str | None = None,
                limit: int | None = None, page: str | None = None,
                profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if availability_domain:
        kwargs["availability_domain"] = availability_domain
    if image_id:
        kwargs["image_id"] = image_id
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_shapes(compartment_id=compartment_id, **kwargs)
    items = [s.__dict__ for s in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return {"items": items, "next_page": next_page}
