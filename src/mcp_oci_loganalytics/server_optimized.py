"""
Optimized MCP Server: OCI Log Analytics
Auto-discovers namespace, provides clear responses for Claude
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


def get_namespace(profile: Optional[str] = None, region: Optional[str] = None) -> str:
    """Auto-discover Log Analytics namespace"""
    try:
        # Get the tenancy ID from the config
        from mcp_oci_common import make_client
        import oci
        identity_client = make_client(oci.identity.IdentityClient, profile=profile, region=region)
        
        # Get the tenancy ID from the current user's compartment
        current_user = identity_client.get_user(identity_client.get_user().data.id)
        tenancy_id = current_user.data.compartment_id
        
        # Get the namespace from the tenancy
        client = create_client(profile=profile, region=region)
        resp = client.list_namespaces(compartment_id=tenancy_id)
        if resp.data and len(resp.data) > 0:
            return resp.data[0].namespace_name
        else:
            raise RuntimeError("No Log Analytics namespace found in your tenancy")
    except Exception as e:
        raise RuntimeError(f"Failed to discover Log Analytics namespace: {str(e)}")


def run_query(query_string: str, time_start: str, time_end: str,
              subsystem: Optional[str] = None, max_total_count: Optional[int] = None,
              profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    """Run a Log Analytics query - namespace auto-discovered"""
    try:
        # Auto-discover namespace
        namespace = get_namespace(profile=profile, region=region)
        
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
            "message": f"Failed to run query: {str(e)}"
        }


def list_entities(compartment_id: str, limit: Optional[int] = None,
                  page: Optional[str] = None, profile: Optional[str] = None,
                  region: Optional[str] = None) -> Dict[str, Any]:
    """List Log Analytics entities - namespace auto-discovered"""
    try:
        # Auto-discover namespace
        namespace = get_namespace(profile=profile, region=region)
        
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
            "message": f"Failed to list entities: {str(e)}"
        }


def list_sources(compartment_id: str, limit: Optional[int] = None,
                 page: Optional[str] = None, profile: Optional[str] = None,
                 region: Optional[str] = None) -> Dict[str, Any]:
    """List Log Analytics sources - namespace auto-discovered"""
    try:
        # Auto-discover namespace
        namespace = get_namespace(profile=profile, region=region)
        
        client = create_client(profile=profile, region=region)
        
        kwargs = {"compartment_id": compartment_id}
        if limit:
            kwargs["limit"] = limit
        if page:
            kwargs["page"] = page

        # Try different source list methods
        try:
            resp = client.list_sources(namespace_name=namespace, **kwargs)
        except AttributeError:
            resp = client.list_log_sources(namespace_name=namespace, **kwargs)

        # Extract sources
        if hasattr(resp, 'data') and hasattr(resp.data, 'items'):
            sources = resp.data.items
        else:
            sources = []

        # Format sources for better readability
        formatted_sources = []
        for source in sources:
            if hasattr(source, 'data'):
                source_data = source.data.__dict__
            else:
                source_data = source.__dict__
            
            formatted_sources.append({
                "id": source_data.get("id"),
                "name": source_data.get("name"),
                "source_type": source_data.get("source_type"),
                "lifecycle_state": source_data.get("lifecycle_state"),
                "time_created": source_data.get("time_created"),
                "compartment_id": source_data.get("compartment_id")
            })

        return {
            "success": True,
            "namespace": namespace,
            "compartment_id": compartment_id,
            "count": len(formatted_sources),
            "sources": formatted_sources,
            "message": f"Found {len(formatted_sources)} sources in namespace '{namespace}'"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to list sources: {str(e)}"
        }


def get_namespace_info(profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    """Get Log Analytics namespace information"""
    try:
        namespace = get_namespace(profile=profile, region=region)
        return {
            "success": True,
            "namespace": namespace,
            "message": f"Log Analytics namespace: {namespace}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get namespace: {str(e)}"
        }
