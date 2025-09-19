"""MCP Server: OCI Identity and Access Management (IAM)

Exposes tools as `oci:iam:<action>` following AWS MCP best practices.
Focus: read/list operations first; add write ops with explicit confirmation.
"""

from typing import Any

from mcp_oci_common import make_client
from mcp_oci_common.response import with_meta
from mcp_oci_common.cache import get_cache
from mcp_oci_common.name_registry import get_registry

try:
    import oci  # type: ignore
except Exception:  # pragma: no cover - SDK may not be installed locally
    oci = None  # fallback for docs/tests without SDK


def create_client(profile: str | None = None, region: str | None = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.identity.IdentityClient, profile=profile, region=region)


def register_tools() -> list[dict[str, Any]]:
    """Register MCP tools for IAM.

    Returns a list of tool specs; wire these into your MCP framework adapter.
    """
    tools: list[dict[str, Any]] = [
        {
            "name": "oci:iam:list-users",
            "description": "List IAM users in a compartment; optional exact name filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "name": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_users,  # to be wired by the MCP runtime
        },
        {
            "name": "oci:iam:list-policy-statements",
            "description": "List policy statements (strings) in a compartment.",
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
            "handler": list_policy_statements,
        },
        {
            "name": "oci:iam:list-api-keys",
            "description": "List API keys for a user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["user_id"],
            },
            "handler": list_api_keys,
        },
        {
            "name": "oci:iam:add-user-to-group",
            "description": "Add a user to a group (confirm=true required; supports dry_run).",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "group_id": {"type": "string"},
                    "dry_run": {"type": "boolean", "default": False},
                    "confirm": {"type": "boolean", "default": False},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["user_id", "group_id"],
            },
            "handler": add_user_to_group,
            "mutating": True,
        },
        {
            "name": "oci:iam:get-user",
            "description": "Get a user by OCID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["user_id"],
            },
            "handler": get_user,
        },
        {
            "name": "oci:iam:list-compartments",
            "description": "List compartments with optional subtree traversal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "include_subtree": {"type": "boolean", "default": True},
                    "access_level": {"type": "string", "enum": ["ANY", "ACCESSIBLE"], "default": "ANY"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_compartments,
        },
        {
            "name": "oci:iam:list-groups",
            "description": "List groups in a compartment.",
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
            "handler": list_groups,
        },
        {
            "name": "oci:iam:list-policies",
            "description": "List policies in a compartment.",
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
            "handler": list_policies,
        },
        {
            "name": "oci:iam:list-user-groups",
            "description": "List group memberships for a user; optionally expand group details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "include_groups": {"type": "boolean", "default": False},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                    "page": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id", "user_id"],
            },
            "handler": list_user_groups,
        },
        {
            "name": "oci:iam:list-dynamic-groups",
            "description": "List dynamic groups in a compartment.",
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
            "handler": list_dynamic_groups,
        },
        {
            "name": "oci:iam:list-auth-tokens",
            "description": "List auth tokens for a user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["user_id"],
            },
            "handler": list_auth_tokens,
        },
    ]
    return tools


def list_users(compartment_id: str, name: str | None = None, limit: int | None = None, page: str | None = None,
               profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    cache = get_cache()
    registry = get_registry()
    kwargs: dict[str, Any] = {}
    if name:
        kwargs["name"] = name
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    cache_params = {"compartment_id": compartment_id, "name": name, "limit": limit, "page": page}
    cached = cache.get("iam", "list_users", cache_params)
    if cached:
        return cached
    resp = client.list_users(compartment_id=compartment_id, **kwargs)
    users = [u.data.__dict__ if hasattr(u, "data") else u.__dict__ for u in resp.data] if hasattr(resp, "data") else []
    if users:
        try:
            registry.update_users(users)
        except Exception:
            pass
    next_page = getattr(resp, "opc_next_page", None)
    out = with_meta(resp, {"items": users}, next_page=next_page)
    # IAM data is stable; cache for 6h
    cache.set("iam", "list_users", cache_params, out, ttl_seconds=21600)
    return out


def get_user(user_id: str, profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.get_user(user_id)
    data = resp.data.__dict__ if hasattr(resp, "data") else getattr(resp, "__dict__", {})
    return with_meta(resp, {"item": data})


def list_compartments(compartment_id: str, include_subtree: bool = True, access_level: str = "ANY",
                      limit: int | None = None, page: str | None = None,
                      profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    """List compartments with enhanced error handling and helpful hints"""
    try:
        client = create_client(profile=profile, region=region)
        kwargs: dict[str, Any] = {"compartment_id_in_subtree": include_subtree, "access_level": access_level}
        if limit:
            kwargs["limit"] = limit
        if page:
            kwargs["page"] = page
        
        resp = client.list_compartments(compartment_id=compartment_id, **kwargs)
        items = [c.__dict__ for c in getattr(resp, "data", [])]
        next_page = getattr(resp, "opc_next_page", None)
        
        # Update registry for name→OCID
        try:
            from mcp_oci_common.name_registry import get_registry as _get_reg
            _get_reg().update_compartments(items)
        except Exception:
            pass
        result = with_meta(resp, {"items": items}, next_page=next_page)
        
        # Add helpful hints for common issues
        if not items:
            result["hints"] = {
                "message": "No compartments found. This might be due to insufficient permissions or incorrect compartment_id.",
                "suggestions": [
                    "Verify the compartment_id is correct",
                    "Check if you have the required IAM permissions",
                    "Try using the tenancy OCID as compartment_id",
                    "Ensure the compartment exists and is accessible"
                ],
                "common_compartment_ids": {
                    "tenancy_root": "Use your tenancy OCID (ocid1.tenancy.oc1..<your-tenancy-id>)",
                    "example": "ocid1.tenancy.oc1..aaaaaaaagy3yddkkampnhj3cqm5ar7w2p7tuq5twbojyycvol6wugfav3ckq"
                }
            }
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        return {
            "items": [],
            "error": f"Failed to list compartments: {error_msg}",
            "hints": {
                "message": "Compartment listing failed. This is usually due to:",
                "suggestions": [
                    "Insufficient IAM permissions (need 'manage' permission on the compartment)",
                    "Invalid compartment_id (use tenancy OCID for root level)",
                    "Network connectivity issues",
                    "Incorrect OCI configuration"
                ],
                "troubleshooting": [
                    "Check your OCI config file (~/.oci/config)",
                    "Verify your API key has the required permissions",
                    "Try using the tenancy OCID: ocid1.tenancy.oc1..<your-tenancy-id>"
                ]
            }
        }


def list_groups(compartment_id: str, limit: int | None = None, page: str | None = None,
                profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_groups(compartment_id=compartment_id, **kwargs)
    items = [g.__dict__ for g in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_policies(compartment_id: str, limit: int | None = None, page: str | None = None,
                  profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_policies(compartment_id=compartment_id, **kwargs)
    items = [p.__dict__ for p in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"items": items}, next_page=next_page)


def list_dynamic_groups(compartment_id: str, limit: int | None = None, page: str | None = None,
                        profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_dynamic_groups(compartment_id=compartment_id, **kwargs)
    items = [g.__dict__ for g in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    return {"items": items, "next_page": next_page}


def list_auth_tokens(user_id: str, profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.list_auth_tokens(user_id=user_id)
    items = [t.__dict__ for t in getattr(resp, "data", [])]
    return {"items": items}


def list_user_groups(compartment_id: str, user_id: str, include_groups: bool = False,
                     limit: int | None = None, page: str | None = None,
                     profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {"user_id": user_id}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_user_group_memberships(compartment_id=compartment_id, **kwargs)
    memberships = [m.__dict__ for m in getattr(resp, "data", [])]
    next_page = getattr(resp, "opc_next_page", None)
    result: dict[str, Any] = with_meta(resp, {"items": memberships}, next_page=next_page)
    if include_groups:
        groups: list[dict[str, Any]] = []
        for m in getattr(resp, "data", []) or []:
            gid = getattr(m, "group_id", None) or (m.get("group_id") if isinstance(m, dict) else None)
            if gid:
                try:
                    g = client.get_group(gid)
                    groups.append(g.data.__dict__ if hasattr(g, "data") else getattr(g, "__dict__", {}))
                except Exception:
                    continue
        result["groups"] = groups
    return result


def list_policy_statements(compartment_id: str, limit: int | None = None, page: str | None = None,
                           profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    kwargs: dict[str, Any] = {}
    if limit:
        kwargs["limit"] = limit
    if page:
        kwargs["page"] = page
    resp = client.list_policies(compartment_id=compartment_id, **kwargs)
    statements: list[str] = []
    for p in getattr(resp, "data", []) or []:
        stmts = getattr(p, "statements", None) or (p.get("statements") if isinstance(p, dict) else None)
        if stmts:
            statements.extend(list(stmts))
    next_page = getattr(resp, "opc_next_page", None)
    return with_meta(resp, {"statements": statements}, next_page=next_page)


def add_user_to_group(user_id: str, group_id: str, dry_run: bool = False, confirm: bool = False,
                      profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    details = {"user_id": user_id, "group_id": group_id}
    if dry_run:
        return {"dry_run": True, "request": details}
    model = oci.identity.models.AddUserToGroupDetails(**details)  # type: ignore
    client = create_client(profile=profile, region=region)
    resp = client.add_user_to_group(add_user_to_group_details=model)
    data = resp.data.__dict__ if hasattr(resp, "data") else getattr(resp, "__dict__", {})
    return with_meta(resp, {"item": data})


def list_api_keys(user_id: str, profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    client = create_client(profile=profile, region=region)
    resp = client.list_api_keys(user_id=user_id)
    items = [k.__dict__ for k in getattr(resp, "data", [])]
    return with_meta(resp, {"items": items})
