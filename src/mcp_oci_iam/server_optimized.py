"""
Optimized MCP Server: OCI Identity and Access Management (IAM)
Provides clear, Claude-friendly responses
"""

from typing import Any

from mcp_oci_common import make_client

try:
    import oci  # type: ignore
except Exception:
    oci = None


def create_client(profile: str | None = None, region: str | None = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.identity.IdentityClient, profile=profile, region=region)


def list_users(compartment_id: str, name: str | None = None, limit: int | None = None, 
               page: str | None = None, profile: str | None = None, 
               region: str | None = None) -> dict[str, Any]:
    """List IAM users with clear, Claude-friendly response"""
    try:
        client = create_client(profile=profile, region=region)
        kwargs: dict[str, Any] = {}
        if name:
            kwargs["name"] = name
        if limit:
            kwargs["limit"] = limit
        if page:
            kwargs["page"] = page

        resp = client.list_users(compartment_id=compartment_id, **kwargs)
        
        # Extract users with proper formatting
        users = []
        if hasattr(resp, 'data') and resp.data:
            for user in resp.data:
                if hasattr(user, 'data'):
                    user_data = user.data.__dict__
                else:
                    user_data = user.__dict__
                
                users.append({
                    "id": user_data.get("id"),
                    "name": user_data.get("name"),
                    "description": user_data.get("description"),
                    "lifecycle_state": user_data.get("lifecycle_state"),
                    "time_created": user_data.get("time_created"),
                    "email": user_data.get("email"),
                    "email_verified": user_data.get("email_verified"),
                    "is_mfa_activated": user_data.get("is_mfa_activated")
                })

        return {
            "success": True,
            "compartment_id": compartment_id,
            "count": len(users),
            "users": users,
            "message": f"Found {len(users)} users in compartment {compartment_id}",
            "next_page": getattr(resp, "opc_next_page", None)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to list users: {str(e)}"
        }


def list_compartments(compartment_id: str, include_subtree: bool = True, access_level: str = "ANY",
                      limit: int | None = None, page: str | None = None,
                      profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    """List compartments with clear, Claude-friendly response"""
    try:
        client = create_client(profile=profile, region=region)
        
        # If listing all compartments, use the tenancy ID
        if include_subtree and access_level == "ANY":
            # Get the tenancy ID
            current_user = client.get_user(client.get_user().data.id)
            tenancy_id = current_user.data.compartment_id
            actual_compartment_id = tenancy_id
        else:
            actual_compartment_id = compartment_id
            
        kwargs: dict[str, Any] = {
            "compartment_id_in_subtree": include_subtree, 
            "access_level": access_level
        }
        if limit:
            kwargs["limit"] = limit
        if page:
            kwargs["page"] = page

        resp = client.list_compartments(compartment_id=actual_compartment_id, **kwargs)
        
        # Extract compartments with proper formatting
        compartments = []
        if hasattr(resp, 'data') and resp.data:
            for comp in resp.data:
                if hasattr(comp, 'data'):
                    comp_data = comp.data.__dict__
                else:
                    comp_data = comp.__dict__
                
                compartments.append({
                    "id": comp_data.get("id"),
                    "name": comp_data.get("name"),
                    "description": comp_data.get("description"),
                    "lifecycle_state": comp_data.get("lifecycle_state"),
                    "time_created": comp_data.get("time_created"),
                    "is_accessible": comp_data.get("is_accessible"),
                    "freeform_tags": comp_data.get("freeform_tags", {}),
                    "defined_tags": comp_data.get("defined_tags", {})
                })

        return {
            "success": True,
            "compartment_id": compartment_id,
            "actual_compartment_id": actual_compartment_id,
            "include_subtree": include_subtree,
            "access_level": access_level,
            "count": len(compartments),
            "compartments": compartments,
            "message": f"Found {len(compartments)} compartments in {actual_compartment_id}",
            "next_page": getattr(resp, "opc_next_page", None)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to list compartments: {str(e)}"
        }


def get_user(user_id: str, profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    """Get specific user with clear response"""
    try:
        client = create_client(profile=profile, region=region)
        resp = client.get_user(user_id)
        
        if hasattr(resp, 'data'):
            user_data = resp.data.__dict__
        else:
            user_data = resp.__dict__

        user_info = {
            "id": user_data.get("id"),
            "name": user_data.get("name"),
            "description": user_data.get("description"),
            "lifecycle_state": user_data.get("lifecycle_state"),
            "time_created": user_data.get("time_created"),
            "email": user_data.get("email"),
            "email_verified": user_data.get("email_verified"),
            "is_mfa_activated": user_data.get("is_mfa_activated"),
            "compartment_id": user_data.get("compartment_id")
        }

        return {
            "success": True,
            "user": user_info,
            "message": f"Retrieved user: {user_info.get('name', 'Unknown')}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get user {user_id}: {str(e)}"
        }


def list_groups(compartment_id: str, limit: int | None = None, page: str | None = None,
                profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    """List IAM groups with clear response"""
    try:
        client = create_client(profile=profile, region=region)
        kwargs: dict[str, Any] = {}
        if limit:
            kwargs["limit"] = limit
        if page:
            kwargs["page"] = page

        resp = client.list_groups(compartment_id=compartment_id, **kwargs)
        
        # Extract groups with proper formatting
        groups = []
        if hasattr(resp, 'data') and resp.data:
            for group in resp.data:
                if hasattr(group, 'data'):
                    group_data = group.data.__dict__
                else:
                    group_data = group.__dict__
                
                groups.append({
                    "id": group_data.get("id"),
                    "name": group_data.get("name"),
                    "description": group_data.get("description"),
                    "lifecycle_state": group_data.get("lifecycle_state"),
                    "time_created": group_data.get("time_created"),
                    "compartment_id": group_data.get("compartment_id")
                })

        return {
            "success": True,
            "compartment_id": compartment_id,
            "count": len(groups),
            "groups": groups,
            "message": f"Found {len(groups)} groups in compartment {compartment_id}",
            "next_page": getattr(resp, "opc_next_page", None)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to list groups: {str(e)}"
        }


def list_policies(compartment_id: str, limit: int | None = None, page: str | None = None,
                  profile: str | None = None, region: str | None = None) -> dict[str, Any]:
    """List IAM policies with clear response"""
    try:
        client = create_client(profile=profile, region=region)
        kwargs: dict[str, Any] = {}
        if limit:
            kwargs["limit"] = limit
        if page:
            kwargs["page"] = page

        resp = client.list_policies(compartment_id=compartment_id, **kwargs)
        
        # Extract policies with proper formatting
        policies = []
        if hasattr(resp, 'data') and resp.data:
            for policy in resp.data:
                if hasattr(policy, 'data'):
                    policy_data = policy.data.__dict__
                else:
                    policy_data = policy.__dict__
                
                policies.append({
                    "id": policy_data.get("id"),
                    "name": policy_data.get("name"),
                    "description": policy_data.get("description"),
                    "lifecycle_state": policy_data.get("lifecycle_state"),
                    "time_created": policy_data.get("time_created"),
                    "compartment_id": policy_data.get("compartment_id"),
                    "statements": policy_data.get("statements", [])
                })

        return {
            "success": True,
            "compartment_id": compartment_id,
            "count": len(policies),
            "policies": policies,
            "message": f"Found {len(policies)} policies in compartment {compartment_id}",
            "next_page": getattr(resp, "opc_next_page", None)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to list policies: {str(e)}"
        }
