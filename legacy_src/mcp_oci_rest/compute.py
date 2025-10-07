"""
Optimized Compute service using direct REST API calls
Minimal token usage, based on Oracle Postman collection patterns
"""

from typing import Any

from .client import create_client
from .formatters import format_error, format_instance, format_response, format_success


def list_instances(compartment_id: str, limit: int | None = None, 
                  page: str | None = None, lifecycle_state: str | None = None,
                  display_name: str | None = None, profile: str = "DEFAULT", 
                  region: str = None) -> dict[str, Any]:
    """List compute instances using REST API - optimized for minimal tokens"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Build query parameters
        params = {"compartmentId": compartment_id}
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page
        if lifecycle_state:
            params["lifecycleState"] = lifecycle_state
        if display_name:
            params["displayName"] = display_name
            
        # Make REST API call
        response = client.get("/20160918/instances", params=params)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract instances
        instances = response.get("data", [])
        
        # Apply client-side filtering if needed
        if lifecycle_state and not params.get("lifecycleState"):
            instances = [i for i in instances if i.get("lifecycle_state") == lifecycle_state]
        if display_name and not params.get("displayName"):
            instances = [i for i in instances if display_name.lower() in i.get("display_name", "").lower()]
        
        # Format response
        return format_response(
            instances, 
            format_instance, 
            limit=limit,
            next_page=response.get("opc_next_page")
        )
        
    except Exception as e:
        return format_error(e)


def get_instance(instance_id: str, profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """Get specific compute instance using REST API"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Make REST API call
        response = client.get(f"/20160918/instances/{instance_id}")
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Instance not found')}"))
        
        # Format single instance
        instance = response.get("data", {})
        return format_success(format_instance(instance))
        
    except Exception as e:
        return format_error(e)


def list_stopped_instances(compartment_id: str, limit: int | None = None,
                          profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """List stopped instances - optimized version"""
    return list_instances(
        compartment_id=compartment_id,
        lifecycle_state="STOPPED",
        limit=limit,
        profile=profile,
        region=region
    )


def list_running_instances(compartment_id: str, limit: int | None = None,
                          profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """List running instances - optimized version"""
    return list_instances(
        compartment_id=compartment_id,
        lifecycle_state="RUNNING",
        limit=limit,
        profile=profile,
        region=region
    )


def search_instances(compartment_id: str, query: str, limit: int | None = None,
                    profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """Search instances using OCI Resource Search API"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Use Resource Search API
        search_data = {
            "query": query,
            "type": "StructuredSearch",
            "matchingContextType": "NONE"
        }
        
        response = client.post("/20180409/resources/actions/search", data=search_data)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"Search API Error: {response.get('error', 'Search failed')}"))
        
        # Extract instances from search results
        items = response.get("data", {}).get("items", [])
        instances = [item for item in items if item.get("resource_type") == "Instance"]
        
        # Format response
        return format_response(instances, format_instance, limit=limit)
        
    except Exception as e:
        return format_error(e)


def get_server_info() -> dict[str, Any]:
    """Get server information"""
    return {
        "name": "oci-compute-rest",
        "version": "1.0.0",
        "type": "REST API",
        "optimized": True,
        "token_usage": "minimal"
    }
