"""
Optimized Log Analytics service using direct REST API calls
Minimal token usage, based on Oracle Postman collection patterns
"""

from typing import Any

from .client import create_client
from .formatters import format_error, format_response, format_success


def get_namespace(profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """Get Log Analytics namespace using REST API - no parameters needed!"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Make REST API call to get namespace
        response = client.get("/20200601/namespaces")
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract namespace from response
        namespaces = response.get("data", [])
        if namespaces:
            namespace = namespaces[0].get("namespace_name")
            return format_success({"namespace": namespace})
        else:
            return format_error(Exception("No Log Analytics namespace found"))
        
    except Exception as e:
        return format_error(e)


def list_entities(compartment_id: str, limit: int | None = None,
                 page: str | None = None, profile: str = "DEFAULT", 
                 region: str = None) -> dict[str, Any]:
    """List Log Analytics entities using REST API - only compartment_id needed!"""
    try:
        client = create_client(profile=profile, region=region)
        
        # First get the namespace
        namespace_result = get_namespace(profile=profile, region=region)
        if not namespace_result.get("success"):
            return format_error(Exception(f"Failed to get namespace: {namespace_result.get('error')}"))
        
        namespace = namespace_result.get("data", {}).get("namespace")
        if not namespace:
            return format_error(Exception("No namespace available"))
        
        # Build query parameters
        params = {
            "compartmentId": compartment_id,
            "namespaceName": namespace
        }
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page
            
        # Make REST API call
        response = client.get(f"/20200601/namespaces/{namespace}/logAnalyticsEntities", params=params)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract entities
        entities = response.get("data", [])
        
        # Format entities with minimal fields
        formatted_entities = [{
            "id": entity.get("id"),
            "name": entity.get("name"),
            "entity_type_name": entity.get("entity_type_name"),
            "lifecycle_state": entity.get("lifecycle_state"),
            "time_created": entity.get("time_created"),
            "time_updated": entity.get("time_updated")
        } for entity in entities]
        
        # Format response
        return format_response(
            formatted_entities, 
            lambda x: x,  # Already formatted
            limit=limit,
            next_page=response.get("opc_next_page")
        )
        
    except Exception as e:
        return format_error(e)


def run_query(query_string: str, time_start: str, time_end: str,
              subsystem: str | None = None, max_total_count: int | None = None,
              profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """Run Log Analytics query using REST API - auto-detects namespace!"""
    try:
        client = create_client(profile=profile, region=region)
        
        # First get the namespace
        namespace_result = get_namespace(profile=profile, region=region)
        if not namespace_result.get("success"):
            return format_error(Exception(f"Failed to get namespace: {namespace_result.get('error')}"))
        
        namespace = namespace_result.get("data", {}).get("namespace")
        if not namespace:
            return format_error(Exception("No namespace available"))
        
        # Build query payload to match QueryDetails model
        query_payload = {
            "queryString": query_string,
            "subSystem": subsystem or "LOG",
            "maxTotalCount": max_total_count or 1000,
            "timeFilter": {
                "timeStart": time_start,
                "timeEnd": time_end,
            }
        }
            
        # Make REST API call
        response = client.post(f"/20200601/namespaces/{namespace}/search/actions/query", 
                              json_data=query_payload)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract query results
        results = response.get("data", {}) or {}
        
        # Format response with minimal data
        return format_success({
            "query_string": query_string,
            "time_start": time_start,
            "time_end": time_end,
            "results": results.get("results", []) or [],
            "total_count": results.get("totalCount", results.get("total_count", 0))
        })
        
    except Exception as e:
        return format_error(e)


def list_sources(compartment_id: str, limit: int | None = None,
                 page: str | None = None, profile: str = "DEFAULT", 
                 region: str = None) -> dict[str, Any]:
    """List Log Analytics sources using REST API - only compartment_id needed!"""
    try:
        client = create_client(profile=profile, region=region)
        
        # First get the namespace
        namespace_result = get_namespace(profile=profile, region=region)
        if not namespace_result.get("success"):
            return format_error(Exception(f"Failed to get namespace: {namespace_result.get('error')}"))
        
        namespace = namespace_result.get("data", {}).get("namespace")
        if not namespace:
            return format_error(Exception("No namespace available"))
        
        # Build query parameters
        params = {
            "compartmentId": compartment_id,
            "namespaceName": namespace
        }
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page
            
        # Make REST API call
        response = client.get(f"/20200601/namespaces/{namespace}/sources", params=params)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract sources
        sources = response.get("data", [])
        
        # Format sources with minimal fields
        formatted_sources = [{
            "id": source.get("id"),
            "name": source.get("name"),
            "source_type": source.get("source_type"),
            "lifecycle_state": source.get("lifecycle_state"),
            "time_created": source.get("time_created"),
            "time_updated": source.get("time_updated")
        } for source in sources]
        
        # Format response
        return format_response(
            formatted_sources, 
            lambda x: x,  # Already formatted
            limit=limit,
            next_page=response.get("opc_next_page")
        )
        
    except Exception as e:
        return format_error(e)


def get_server_info() -> dict[str, Any]:
    """Get server information"""
    return {
        "name": "oci-loganalytics-rest",
        "version": "1.0.0",
        "type": "REST API",
        "optimized": True,
        "token_usage": "minimal",
        "auto_namespace": True
    }
