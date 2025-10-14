"""
Optimized IAM service using direct REST API calls
Minimal token usage, based on Oracle Postman collection patterns
"""

from typing import Any

from .client import create_client
from .formatters import (
    format_compartment,
    format_error,
    format_response,
    format_success,
    format_user,
)


def list_users(compartment_id: str, limit: int | None = None, 
               page: str | None = None, profile: str = "DEFAULT", 
               region: str = None) -> dict[str, Any]:
    """List IAM users using REST API - optimized for minimal tokens"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Build query parameters
        params = {"compartmentId": compartment_id}
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page
            
        # Make REST API call
        response = client.get("/20160918/users", params=params)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract users
        users = response.get("data", [])
        
        # Format response
        return format_response(
            users, 
            format_user, 
            limit=limit,
            next_page=response.get("opc_next_page")
        )
        
    except Exception as e:
        return format_error(e)


def get_user(user_id: str, profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """Get specific IAM user using REST API"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Make REST API call
        response = client.get(f"/20160918/users/{user_id}")
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'User not found')}"))
        
        # Format single user
        user = response.get("data", {})
        return format_success(format_user(user))
        
    except Exception as e:
        return format_error(e)


def list_compartments(compartment_id: str, limit: int | None = None,
                     page: str | None = None, access_level: str = "ANY",
                     compartment_id_in_subtree: bool = False,
                     profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """List compartments using REST API - optimized for minimal tokens"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Build query parameters
        params = {
            "compartmentId": compartment_id,
            "accessLevel": access_level,
            "compartmentIdInSubtree": compartment_id_in_subtree
        }
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page
            
        # Make REST API call
        response = client.get("/20160918/compartments", params=params)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract compartments
        compartments = response.get("data", [])
        
        # Format response
        return format_response(
            compartments, 
            format_compartment, 
            limit=limit,
            next_page=response.get("opc_next_page")
        )
        
    except Exception as e:
        return format_error(e)


def get_compartment(compartment_id: str, profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """Get specific compartment using REST API"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Make REST API call
        response = client.get(f"/20160918/compartments/{compartment_id}")
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Compartment not found')}"))
        
        # Format single compartment
        compartment = response.get("data", {})
        return format_success(format_compartment(compartment))
        
    except Exception as e:
        return format_error(e)


def list_groups(compartment_id: str, limit: int | None = None,
                page: str | None = None, profile: str = "DEFAULT", 
                region: str = None) -> dict[str, Any]:
    """List IAM groups using REST API - optimized for minimal tokens"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Build query parameters
        params = {"compartmentId": compartment_id}
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page
            
        # Make REST API call
        response = client.get("/20160918/groups", params=params)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract groups
        groups = response.get("data", [])
        
        # Format response
        return format_response(
            groups, 
            format_user,  # Groups use similar format to users
            limit=limit,
            next_page=response.get("opc_next_page")
        )
        
    except Exception as e:
        return format_error(e)


def list_policies(compartment_id: str, limit: int | None = None,
                  page: str | None = None, profile: str = "DEFAULT", 
                  region: str = None) -> dict[str, Any]:
    """List IAM policies using REST API - optimized for minimal tokens"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Build query parameters
        params = {"compartmentId": compartment_id}
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page
            
        # Make REST API call
        response = client.get("/20160918/policies", params=params)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract policies
        policies = response.get("data", [])
        
        # Format response
        return format_response(
            policies, 
            format_user,  # Policies use similar format
            limit=limit,
            next_page=response.get("opc_next_page")
        )
        
    except Exception as e:
        return format_error(e)


def get_server_info() -> dict[str, Any]:
    """Get server information"""
    return {
        "name": "oci-iam-rest",
        "version": "1.0.0",
        "type": "REST API",
        "optimized": True,
        "token_usage": "minimal"
    }
