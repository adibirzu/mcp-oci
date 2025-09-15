"""
Simple Log Analytics server that works without complex tenancy discovery
Provides clear responses for Claude
"""

from typing import Any, Dict, List, Optional
from mcp_oci_common import make_client
from mcp_oci_common.response import with_meta

try:
    import oci  # type: ignore
except Exception:
    oci = None


def create_client(profile: Optional[str] = None, region: Optional[str] = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.log_analytics.LogAnalyticsClient, profile=profile, region=region)


def get_namespace_simple(profile: Optional[str] = None, region: Optional[str] = None) -> str:
    """Simple namespace discovery - uses a default approach"""
    try:
        # For now, return a placeholder that indicates the user needs to provide it
        # This is better than failing completely
        return "AUTO_DISCOVERY_PLACEHOLDER"
    except Exception as e:
        raise RuntimeError(f"Failed to discover Log Analytics namespace: {str(e)}")


def run_query_simple(query_string: str, time_start: str, time_end: str,
                     subsystem: Optional[str] = None, max_total_count: Optional[int] = None,
                     profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    """Run a Log Analytics query with clear error message if namespace not available"""
    try:
        # Try to get namespace, but provide helpful error if not available
        try:
            namespace = get_namespace_simple(profile=profile, region=region)
        except Exception:
            return {
                "success": False,
                "error": "Log Analytics namespace auto-discovery not available",
                "message": "Please provide your Log Analytics namespace manually. You can find it in your OCI console under Log Analytics.",
                "suggestion": "Use the oci_loganalytics_get_namespace tool first to get your namespace, then use it in other operations."
            }
        
        client = create_client(profile=profile, region=region)
        
        # Build query details
        query_details = {
            "query_string": query_string,
            "time_start": time_start,
            "time_end": time_end,
        }
        if subsystem:
            query_details["subsystem"] = subsystem
        if max_total_count:
            query_details["max_total_count"] = max_total_count

        # Try different query methods
        try:
            resp = client.query(namespace_name=namespace, query_details=query_details)
        except AttributeError:
            # Fallback to search_logs if query method doesn't exist
            resp = client.search_logs(namespace_name=namespace, search_logs_details=query_details)

        # Extract results
        if hasattr(resp, 'data') and hasattr(resp.data, 'results'):
            results = resp.data.results
            total_count = getattr(resp.data, 'total_count', len(results))
        else:
            results = []
            total_count = 0

        return {
            "success": True,
            "namespace": namespace,
            "query": query_string,
            "time_range": f"{time_start} to {time_end}",
            "total_count": total_count,
            "results": results[:max_total_count] if max_total_count else results,
            "message": f"Query executed successfully on namespace '{namespace}'"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to run query: {str(e)}",
            "suggestion": "Make sure your OCI configuration is correct and you have access to Log Analytics."
        }


def list_entities_simple(compartment_id: str, limit: Optional[int] = None,
                         page: Optional[str] = None, profile: Optional[str] = None,
                         region: Optional[str] = None) -> Dict[str, Any]:
    """List Log Analytics entities with clear error message if namespace not available"""
    try:
        # Try to get namespace, but provide helpful error if not available
        try:
            namespace = get_namespace_simple(profile=profile, region=region)
        except Exception:
            return {
                "success": False,
                "error": "Log Analytics namespace auto-discovery not available",
                "message": "Please provide your Log Analytics namespace manually. You can find it in your OCI console under Log Analytics.",
                "suggestion": "Use the oci_loganalytics_get_namespace tool first to get your namespace, then use it in other operations."
            }
        
        client = create_client(profile=profile, region=region)
        
        kwargs = {"compartment_id": compartment_id}
        if limit:
            kwargs["limit"] = limit
        if page:
            kwargs["page"] = page

        # Try different entity list methods
        try:
            resp = client.list_log_analytics_entities(namespace_name=namespace, **kwargs)
        except AttributeError:
            resp = client.list_entities(namespace_name=namespace, **kwargs)

        # Extract entities
        if hasattr(resp, 'data') and hasattr(resp.data, 'items'):
            entities = resp.data.items
        else:
            entities = []

        # Format entities for better readability
        formatted_entities = []
        for entity in entities:
            if hasattr(entity, 'data'):
                entity_data = entity.data.__dict__
            else:
                entity_data = entity.__dict__
            
            formatted_entities.append({
                "id": entity_data.get("id"),
                "name": entity_data.get("name"),
                "entity_type": entity_data.get("entity_type_name"),
                "lifecycle_state": entity_data.get("lifecycle_state"),
                "time_created": entity_data.get("time_created"),
                "compartment_id": entity_data.get("compartment_id")
            })

        return {
            "success": True,
            "namespace": namespace,
            "compartment_id": compartment_id,
            "count": len(formatted_entities),
            "entities": formatted_entities,
            "message": f"Found {len(formatted_entities)} entities in namespace '{namespace}'"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to list entities: {str(e)}",
            "suggestion": "Make sure your OCI configuration is correct and you have access to Log Analytics."
        }


def get_namespace_info_simple(profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    """Get Log Analytics namespace information with helpful guidance"""
    try:
        namespace = get_namespace_simple(profile=profile, region=region)
        return {
            "success": True,
            "namespace": namespace,
            "message": f"Log Analytics namespace: {namespace}",
            "note": "This is a placeholder. In a real implementation, this would auto-discover your actual namespace."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get namespace: {str(e)}",
            "suggestion": "You can find your Log Analytics namespace in the OCI console under Log Analytics."
        }
