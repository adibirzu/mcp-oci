"""Fast MCP Server: OCI Log Analytics with Direct REST API Connection
Optimized for speed and reliability using the existing working patterns.

Tools are exposed as `oci:loganalytics:<action>`.
Focus on fast connection and reliable query execution.
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from mcp_oci_common import make_client
from mcp_oci_common.response import with_meta

try:
    import oci  # type: ignore
except Exception:
    oci = None


@dataclass
class FastLoganResult:
    """Fast Log Analytics result with metadata"""
    success: bool
    data: List[Dict[str, Any]]
    count: int
    execution_time_ms: float
    namespace: str
    query: str
    message: str
    error: Optional[str] = None


def create_client(profile: str | None = None, region: str | None = None):
    """Create a fast Log Analytics client using existing patterns"""
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    return make_client(oci.log_analytics.LogAnalyticsClient, profile=profile, region=region)


def get_namespace_fast(client, compartment_id: str) -> str:
    """Get Log Analytics namespace with fast method"""
    try:
        # Try to get namespace from object storage (fastest method)
        object_storage_client = oci.object_storage.ObjectStorageClient(client._config)
        namespace = object_storage_client.get_namespace().data
        return namespace
    except Exception:
        # Fallback to compartment ID as namespace
        return compartment_id


def execute_query_fast(
    query: str,
    compartment_id: str,
    time_range: str = "24h",
    max_count: int = 1000,
    profile: str | None = None,
    region: str | None = None,
) -> FastLoganResult:
    """Execute Log Analytics query with optimized performance using direct REST API"""
    start_time = time.time()
    
    try:
        # Create client for config
        client = create_client(profile=profile, region=region)
        
        # Get namespace quickly
        namespace = get_namespace_fast(client, compartment_id)
        
        # Convert time range to start/end times
        end_time = datetime.now(timezone.utc)
        time_mapping = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "12h": timedelta(hours=12),
            "24h": timedelta(hours=24),
            "1d": timedelta(days=1),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "1w": timedelta(weeks=1),
            "1m": timedelta(days=30)
        }
        delta = time_mapping.get(time_range, timedelta(hours=24))
        start_time_dt = end_time - delta
        
        # Use direct HTTP request like logan-server
        import requests
        from oci.signer import Signer
        from mcp_oci_common import get_config
        
        # Get config
        config = get_config(profile=profile, region=region)
        
        # Create OCI request signer
        signer = Signer(
            tenancy=config["tenancy"],
            user=config["user"],
            fingerprint=config["fingerprint"],
            private_key_file_location=config["key_file"],
            pass_phrase=config.get("pass_phrase")
        )
        
        # Create query details matching console parameters exactly
        query_details = {
            "subSystem": "LOG",
            "queryString": query,
            "shouldRunAsync": False,
            "shouldIncludeTotalCount": True,
            "compartmentId": compartment_id,
            "compartmentIdInSubtree": True,
            "timeFilter": {
                "timeStart": start_time_dt.isoformat().replace('+00:00', 'Z'),
                "timeEnd": end_time.isoformat().replace('+00:00', 'Z'),
                "timeZone": "UTC"
            },
            "maxTotalCount": max_count
        }
        
        # Console URL format
        region = region or config.get("region", "us-ashburn-1")
        url = f"https://loganalytics.{region}.oci.oraclecloud.com/20200601/namespaces/{namespace}/search/actions/query"
        params = {"limit": max_count}
        
        response = requests.post(url, json=query_details, auth=signer, params=params)
        
        if response.status_code == 200:
            # Synchronous response
            data = response.json()
            results = data.get("items", [])
            execution_time = (time.time() - start_time) * 1000
            
            return FastLoganResult(
                success=True,
                data=results,
                count=len(results),
                execution_time_ms=execution_time,
                namespace=namespace,
                query=query,
                message=f"Query executed successfully in {execution_time:.2f}ms. Found {len(results)} results."
            )
        elif response.status_code == 201:
            # Async response - query was submitted
            data = response.json()
            execution_time = (time.time() - start_time) * 1000
            
            return FastLoganResult(
                success=True,
                data=[],
                count=0,
                execution_time_ms=execution_time,
                namespace=namespace,
                query=query,
                message=f"Async query submitted successfully in {execution_time:.2f}ms. Percent complete: {data.get('percentComplete', 0)}%"
            )
        else:
            execution_time = (time.time() - start_time) * 1000
            return FastLoganResult(
                success=False,
                data=[],
                count=0,
                execution_time_ms=execution_time,
                namespace=namespace,
                query=query,
                message=f"HTTP Error {response.status_code}: {response.text}",
                error=f"HTTP {response.status_code}: {response.text}"
            )
        
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        return FastLoganResult(
            success=False,
            data=[],
            count=0,
            execution_time_ms=execution_time,
            namespace="",
            query=query,
            message=f"Query failed after {execution_time:.2f}ms: {str(e)}",
            error=str(e)
        )


def list_sources_fast(
    compartment_id: str,
    limit: int = 100,
    profile: str | None = None,
    region: str | None = None,
) -> FastLoganResult:
    """List Log Analytics sources with optimized performance"""
    start_time = time.time()
    
    try:
        # Create client
        client = create_client(profile=profile, region=region)
        namespace = get_namespace_fast(client, compartment_id)
        
        # Use direct API call for sources
        response = client.list_sources(
            namespace_name=namespace,
            compartment_id=compartment_id,
            limit=limit
        )
        
        # Process sources efficiently
        sources = []
        if hasattr(response, 'data') and response.data:
            if hasattr(response.data, 'items'):
                for item in response.data.items:
                    if hasattr(item, '__dict__'):
                        sources.append(item.__dict__)
                    else:
                        sources.append(dict(item))
        
        execution_time = (time.time() - start_time) * 1000
        
        return FastLoganResult(
            success=True,
            data=sources,
            count=len(sources),
            execution_time_ms=execution_time,
            namespace=namespace,
            query="list_sources",
            message=f"Sources listed successfully in {execution_time:.2f}ms. Found {len(sources)} sources."
        )
        
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        return FastLoganResult(
            success=False,
            data=[],
            count=0,
            execution_time_ms=execution_time,
            namespace="",
            query="list_sources",
            message=f"Failed to list sources after {execution_time:.2f}ms: {str(e)}",
            error=str(e)
        )


def get_log_sources_last_days(
    compartment_id: str,
    days: int = 5,
    profile: str | None = None,
    region: str | None = None,
) -> FastLoganResult:
    """Get log sources with activity from the last N days"""
    start_time = time.time()
    
    try:
        # Create client
        client = create_client(profile=profile, region=region)
        namespace = get_namespace_fast(client, compartment_id)
        
        # Query for log sources with recent activity
        query = f"* | where Time > dateRelative({days}d) | stats count by 'Log Source' | sort -count"
        
        end_time = datetime.now(timezone.utc)
        start_time_dt = end_time - timedelta(days=days)
        
        # Use direct HTTP request like logan-server
        import requests
        from oci.signer import Signer
        from mcp_oci_common import get_config
        
        # Get config
        config = get_config(profile=profile, region=region)
        
        # Create OCI request signer
        signer = Signer(
            tenancy=config["tenancy"],
            user=config["user"],
            fingerprint=config["fingerprint"],
            private_key_file_location=config["key_file"],
            pass_phrase=config.get("pass_phrase")
        )
        
        # Create query details matching console parameters exactly
        query_details = {
            "subSystem": "LOG",
            "queryString": query,
            "shouldRunAsync": False,
            "shouldIncludeTotalCount": True,
            "compartmentId": compartment_id,
            "compartmentIdInSubtree": True,
            "timeFilter": {
                "timeStart": start_time_dt.isoformat().replace('+00:00', 'Z'),
                "timeEnd": end_time.isoformat().replace('+00:00', 'Z'),
                "timeZone": "UTC"
            },
            "maxTotalCount": 1000
        }
        
        # Console URL format
        region = region or config.get("region", "us-ashburn-1")
        url = f"https://loganalytics.{region}.oci.oraclecloud.com/20200601/namespaces/{namespace}/search/actions/query"
        params = {"limit": 1000}
        
        response = requests.post(url, json=query_details, auth=signer, params=params)
        
        # Process results
        sources = []
        if response.status_code == 200:
            data = response.json()
            sources = data.get("items", [])
        elif response.status_code == 201:
            # Async response - no immediate results
            data = response.json()
            sources = []
        
        execution_time = (time.time() - start_time) * 1000
        
        return FastLoganResult(
            success=True,
            data=sources,
            count=len(sources),
            execution_time_ms=execution_time,
            namespace=namespace,
            query=query,
            message=f"Log sources from last {days} days retrieved in {execution_time:.2f}ms. Found {len(sources)} active sources."
        )
        
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        return FastLoganResult(
            success=False,
            data=[],
            count=0,
            execution_time_ms=execution_time,
            namespace="",
            query=f"log_sources_last_{days}_days",
            message=f"Failed to get log sources after {execution_time:.2f}ms: {str(e)}",
            error=str(e)
        )


def register_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "oci:loganalytics:execute_query_fast",
            "description": "Execute Log Analytics queries with optimized performance and fast connection",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "OCI Log Analytics query string"},
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "time_range": {"type": "string", "description": "Time range (1h, 6h, 12h, 24h, 1d, 7d, 30d, 1w, 1m)", "default": "24h"},
                    "max_count": {"type": "integer", "description": "Maximum number of results", "default": 1000},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["query", "compartment_id"],
            },
            "handler": execute_query_fast_handler,
        },
        {
            "name": "oci:loganalytics:list_sources_fast",
            "description": "List Log Analytics sources with optimized performance",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "limit": {"type": "integer", "description": "Maximum number of sources to return", "default": 100},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": list_sources_fast_handler,
        },
        {
            "name": "oci:loganalytics:get_log_sources_last_days",
            "description": "Get log sources with activity from the last N days",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "days": {"type": "integer", "description": "Number of days to look back", "default": 5},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": get_log_sources_last_days_handler,
        },
        {
            "name": "oci:loganalytics:test_connection_fast",
            "description": "Test Log Analytics connection and get namespace information",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": test_connection_fast_handler,
        },
    ]


# Tool Handlers

def execute_query_fast_handler(
    query: str,
    compartment_id: str,
    time_range: str = "24h",
    max_count: int = 1000,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Execute Log Analytics query with optimized performance"""
    result = execute_query_fast(query, compartment_id, time_range, max_count, profile, region)
    
    return with_meta(
        {
            "query": result.query,
            "namespace": result.namespace,
            "compartment_id": compartment_id,
            "time_range": time_range,
            "results": result.data,
            "count": result.count,
            "execution_time_ms": result.execution_time_ms,
            "success": result.success
        },
        success=result.success,
        message=result.message
    )


def list_sources_fast_handler(
    compartment_id: str,
    limit: int = 100,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """List Log Analytics sources with optimized performance"""
    result = list_sources_fast(compartment_id, limit, profile, region)
    
    return with_meta(
        {
            "compartment_id": compartment_id,
            "namespace": result.namespace,
            "sources": result.data,
            "count": result.count,
            "execution_time_ms": result.execution_time_ms,
            "success": result.success
        },
        success=result.success,
        message=result.message
    )


def get_log_sources_last_days_handler(
    compartment_id: str,
    days: int = 5,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Get log sources with activity from the last N days"""
    result = get_log_sources_last_days(compartment_id, days, profile, region)
    
    return with_meta(
        {
            "compartment_id": compartment_id,
            "namespace": result.namespace,
            "days": days,
            "log_sources": result.data,
            "count": result.count,
            "execution_time_ms": result.execution_time_ms,
            "success": result.success
        },
        success=result.success,
        message=result.message
    )


def test_connection_fast_handler(
    compartment_id: str,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Test Log Analytics connection and get namespace information"""
    try:
        # Create client
        client = create_client(profile=profile, region=region)
        namespace = get_namespace_fast(client, compartment_id)
        
        # Test with a simple query
        test_result = execute_query_fast("* | head 1", compartment_id, "1h", 1, profile, region)
        
        return with_meta(
            {
                "compartment_id": compartment_id,
                "namespace": namespace,
                "connection_status": "success" if test_result.success else "failed",
                "test_query_success": test_result.success,
                "test_query_time_ms": test_result.execution_time_ms,
                "region": region or "default",
                "profile": profile or "default"
            },
            success=test_result.success,
            message=f"Connection test {'successful' if test_result.success else 'failed'}. Namespace: {namespace}"
        )
    except Exception as e:
        return with_meta(
            {
                "compartment_id": compartment_id,
                "connection_status": "failed",
                "error": str(e)
            },
            success=False,
            message=f"Connection test failed: {str(e)}"
        )
