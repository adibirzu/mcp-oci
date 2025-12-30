import oci
from typing import Dict, Any, Optional, List
from mcp_server_oci.auth import get_client, get_compartment_id, get_oci_config

# Global cache for the resolved namespace to avoid repeated API calls
_CACHED_NAMESPACE: Optional[str] = None

def _get_namespace(config: Dict[str, Any]) -> str:
    """
    Resolve Log Analytics namespace.
    Priority:
    1. LA_NAMESPACE env var
    2. Cached value
    3. API lookup (auto-detect if only one exists)
    """
    global _CACHED_NAMESPACE
    
    # 1. Environment variable
    import os
    env_ns = os.getenv("LA_NAMESPACE")
    if env_ns:
        return env_ns

    # 2. Cache
    if _CACHED_NAMESPACE:
        return _CACHED_NAMESPACE

    # 3. API Lookup
    # We need the tenancy ID for namespace lookup, which is often the compartment ID
    # if it's the root compartment, or explicitly in config.
    tenancy_id = config.get("tenancy") or os.getenv("TENANCY_OCID") or get_compartment_id()
    if not tenancy_id:
        raise ValueError("Cannot resolve Tenancy OCID for Log Analytics namespace lookup. Set TENANCY_OCID or COMPARTMENT_OCID.")

    client = get_client(oci.log_analytics.LogAnalyticsClient, region=config.get("region"))
    
    try:
        response = client.list_namespaces(compartment_id=tenancy_id)
        items = response.data.items
        
        if not items:
            raise ValueError("No Log Analytics namespaces found in this tenancy.")
            
        # If multiple, we can't guess (unless we default to the first one, but that's risky)
        # For now, let's take the first one but log a warning if multiple? 
        # The old server errored if multiple. Let's error for safety.
        if len(items) > 1:
            names = [ns.namespace_name for ns in items]
            raise ValueError(f"Multiple Log Analytics namespaces found: {names}. Set LA_NAMESPACE env var to select one.")
            
        _CACHED_NAMESPACE = items[0].namespace_name
        return _CACHED_NAMESPACE
        
    except Exception as e:
        raise RuntimeError(f"Failed to list Log Analytics namespaces: {str(e)}")

def _format_logs_markdown(results: List[Dict[str, Any]]) -> str:
    """Format log query results as a Markdown table."""
    if not results:
        return "No log results found."
        
    # Extract headers from the first row keys
    headers = list(results[0].keys())
    
    # Build MD table
    md = "| " + " | ".join(headers) + " |\n"
    md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    
    for row in results[:20]: # Limit rows in MD view
        values = [str(row.get(h, "")) for h in headers]
        md += "| " + " | ".join(values) + " |\n"
        
    if len(results) > 20:
        md += f"\n*...and {len(results) - 20} more rows.*"
        
    return md

def get_logs(
    query: str,
    time_range: str = "60m",
    compartment_id: Optional[str] = None,
    limit: int = 100,
    format: str = "markdown"
) -> str | List[Dict]:
    """
    Run a query against OCI Log Analytics.
    
    Args:
        query: The Log Analytics query string (e.g., "* | stats count by 'Log Source'")
        time_range: Time window (e.g. "60m", "24h", "7d")
        compartment_id: Scope for the query (defaults to env var)
        limit: Max results
        format: "markdown" or "json"
    """
    comp_id = compartment_id or get_compartment_id()
    if not comp_id:
        return "Error: Compartment OCID required."

    try:
        config = get_oci_config()
        namespace = _get_namespace(config)
        client = get_client(oci.log_analytics.LogAnalyticsClient, region=config.get("region"))
        
        # Parse time range simple handling
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        time_filter = None
        
        # OCI SDK expects TimeRange object or string? 
        # The QueryDetails object takes `time_filter` as TimeRange.
        from oci.log_analytics.models import QueryDetails, TimeRange
        
        start_time = now
        tr = time_range.strip().lower()
        if tr.endswith("m"):
            start_time = now - timedelta(minutes=int(tr[:-1]))
        elif tr.endswith("h"):
            start_time = now - timedelta(hours=int(tr[:-1]))
        elif tr.endswith("d"):
            start_time = now - timedelta(days=int(tr[:-1]))
        
        t_filter = TimeRange(
            time_start=start_time,
            time_end=now
        )

        details = QueryDetails(
            query_string=query,
            sub_system="LOG",
            max_total_count=limit,
            time_filter=t_filter,
            compartment_id=comp_id
        )
        
        response = client.query(
            namespace_name=namespace,
            query_details=details,
            limit=limit,
            compartment_id=comp_id
        )
        
        # Process results
        data = response.data
        results = []
        
        # Extract column names
        cols = [c.display_name or c.name for c in (data.columns or [])]
        
        for row in (data.rows or []):
            item = {}
            # row.values is the list of values matching columns
            for i, val in enumerate(row.values or []):
                if i < len(cols):
                    item[cols[i]] = val
            results.append(item)
            
        if format == "markdown":
            return _format_logs_markdown(results)
        return results

    except Exception as e:
        return f"Error executing log query: {str(e)}"