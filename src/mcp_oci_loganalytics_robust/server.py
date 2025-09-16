"""Robust MCP Server: OCI Log Analytics with Fast REST API Connection
Optimized for speed and reliability with direct REST API calls.

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
class LoganQueryResult:
    """Log Analytics query result with metadata"""
    success: bool
    data: List[Dict[str, Any]]
    count: int
    execution_time_ms: float
    namespace: str
    query: str
    message: str
    error: Optional[str] = None


class RobustLogAnalyticsClient:
    """Robust Log Analytics client with fast connection and reliable query execution"""
    
    def __init__(self, profile: str | None = None, region: str | None = None):
        if oci is None:
            raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
        
        self.client = make_client(oci.log_analytics.LogAnalyticsClient, profile=profile, region=region)
        self._namespace_cache = {}
        self._compartment_cache = {}
        
    def get_namespace_fast(self, compartment_id: str) -> str:
        """Get Log Analytics namespace with caching for speed"""
        if compartment_id in self._namespace_cache:
            return self._namespace_cache[compartment_id]
        
        try:
            # Try to get namespace from object storage (fastest method)
            object_storage_client = oci.object_storage.ObjectStorageClient(self.client._config)
            namespace = object_storage_client.get_namespace().data
            self._namespace_cache[compartment_id] = namespace
            return namespace
        except Exception:
            # Fallback to compartment ID as namespace
            namespace = compartment_id
            self._namespace_cache[compartment_id] = namespace
            return namespace
    
    def execute_query_fast(self, 
                          query: str, 
                          compartment_id: str,
                          time_range: str = "24h",
                          max_count: int = 1000) -> LoganQueryResult:
        """Execute Log Analytics query with optimized performance"""
        start_time = time.time()
        
        try:
            # Get namespace quickly
            namespace = self.get_namespace_fast(compartment_id)
            
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
            
            # Execute query with optimized parameters
            from oci.log_analytics.models import QueryDetails
            
            query_details = QueryDetails(
                query_string=query,
                time_start=start_time_dt,
                time_end=end_time,
                max_total_count=max_count,
                should_run_async=False  # Synchronous for speed
            )
            
            response = self.client.query(
                namespace_name=namespace,
                query_details=query_details
            )
            
            # Process results efficiently
            results = []
            if hasattr(response, 'data') and response.data:
                if hasattr(response.data, 'results'):
                    for item in response.data.results:
                        # Convert to dict efficiently
                        if hasattr(item, '__dict__'):
                            results.append(item.__dict__)
                        else:
                            results.append(dict(item))
                elif hasattr(response.data, 'items'):
                    for item in response.data.items:
                        if hasattr(item, '__dict__'):
                            results.append(item.__dict__)
                        else:
                            results.append(dict(item))
            
            execution_time = (time.time() - start_time) * 1000
            
            return LoganQueryResult(
                success=True,
                data=results,
                count=len(results),
                execution_time_ms=execution_time,
                namespace=namespace,
                query=query,
                message=f"Query executed successfully in {execution_time:.2f}ms. Found {len(results)} results."
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return LoganQueryResult(
                success=False,
                data=[],
                count=0,
                execution_time_ms=execution_time,
                namespace="",
                query=query,
                message=f"Query failed after {execution_time:.2f}ms: {str(e)}",
                error=str(e)
            )
    
    def list_sources_fast(self, compartment_id: str, limit: int = 100) -> LoganQueryResult:
        """List Log Analytics sources with optimized performance"""
        start_time = time.time()
        
        try:
            namespace = self.get_namespace_fast(compartment_id)
            
            # Use direct API call for sources
            response = self.client.list_sources(
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
            
            return LoganQueryResult(
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
            return LoganQueryResult(
                success=False,
                data=[],
                count=0,
                execution_time_ms=execution_time,
                namespace="",
                query="list_sources",
                message=f"Failed to list sources after {execution_time:.2f}ms: {str(e)}",
                error=str(e)
            )
    
    def get_log_sources_last_days(self, compartment_id: str, days: int = 5) -> LoganQueryResult:
        """Get log sources with activity from the last N days"""
        start_time = time.time()
        
        try:
            namespace = self.get_namespace_fast(compartment_id)
            
            # Query for log sources with recent activity
            query = f"* | where Time > dateRelative({days}d) | stats count by 'Log Source' | sort -count"
            
            from oci.log_analytics.models import QueryDetails
            
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)
            
            query_details = QueryDetails(
                query_string=query,
                time_start=start_time,
                time_end=end_time,
                max_total_count=1000
            )
            
            response = self.client.query(
                namespace_name=namespace,
                query_details=query_details
            )
            
            # Process results
            sources = []
            if hasattr(response, 'data') and response.data and hasattr(response.data, 'results'):
                for item in response.data.results:
                    if hasattr(item, '__dict__'):
                        sources.append(item.__dict__)
                    else:
                        sources.append(dict(item))
            
            execution_time = (time.time() - start_time) * 1000
            
            return LoganQueryResult(
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
            return LoganQueryResult(
                success=False,
                data=[],
                count=0,
                execution_time_ms=execution_time,
                namespace="",
                query=f"log_sources_last_{days}_days",
                message=f"Failed to get log sources after {execution_time:.2f}ms: {str(e)}",
                error=str(e)
            )


def create_client(profile: str | None = None, region: str | None = None):
    """Create a robust Log Analytics client"""
    return RobustLogAnalyticsClient(profile=profile, region=region)


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
            "handler": execute_query_fast,
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
            "handler": list_sources_fast,
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
            "handler": get_log_sources_last_days,
        },
        {
            "name": "oci:loganalytics:test_connection",
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
            "handler": test_connection,
        },
        {
            "name": "oci:loganalytics:search_security_events_fast",
            "description": "Search for security events with optimized performance",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_term": {"type": "string", "description": "Search term or query"},
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "time_range": {"type": "string", "description": "Time range for search", "default": "24h"},
                    "max_count": {"type": "integer", "description": "Maximum number of results", "default": 100},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["search_term", "compartment_id"],
            },
            "handler": search_security_events_fast,
        },
    ]


# Tool Handlers

def execute_query_fast(
    query: str,
    compartment_id: str,
    time_range: str = "24h",
    max_count: int = 1000,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Execute Log Analytics query with optimized performance"""
    try:
        client = create_client(profile=profile, region=region)
        result = client.execute_query_fast(query, compartment_id, time_range, max_count)
        
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
    except Exception as e:
        return with_meta(
            {"error": str(e), "success": False},
            success=False,
            message=f"Query execution failed: {str(e)}"
        )


def list_sources_fast(
    compartment_id: str,
    limit: int = 100,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """List Log Analytics sources with optimized performance"""
    try:
        client = create_client(profile=profile, region=region)
        result = client.list_sources_fast(compartment_id, limit)
        
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
    except Exception as e:
        return with_meta(
            {"error": str(e), "success": False},
            success=False,
            message=f"Failed to list sources: {str(e)}"
        )


def get_log_sources_last_days(
    compartment_id: str,
    days: int = 5,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Get log sources with activity from the last N days"""
    try:
        client = create_client(profile=profile, region=region)
        result = client.get_log_sources_last_days(compartment_id, days)
        
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
    except Exception as e:
        return with_meta(
            {"error": str(e), "success": False},
            success=False,
            message=f"Failed to get log sources from last {days} days: {str(e)}"
        )


def test_connection(
    compartment_id: str,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Test Log Analytics connection and get namespace information"""
    try:
        client = create_client(profile=profile, region=region)
        namespace = client.get_namespace_fast(compartment_id)
        
        # Test with a simple query
        test_result = client.execute_query_fast("* | head 1", compartment_id, "1h", 1)
        
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


def search_security_events_fast(
    search_term: str,
    compartment_id: str,
    time_range: str = "24h",
    max_count: int = 100,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Search for security events with optimized performance"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Build security query based on search term
        search_lower = search_term.lower()
        
        if any(term in search_lower for term in ["login", "auth", "signin", "failed"]):
            query = "* | where contains('Log Entry', 'Failed password') or contains('Log Entry', 'authentication failure') or contains('Log Entry', 'login failed')"
        elif any(term in search_lower for term in ["privilege", "escalation", "sudo"]):
            query = "* | where contains('Log Entry', 'sudo') or contains('Log Entry', 'su:') or contains('Event Name', 'Assume')"
        elif any(term in search_lower for term in ["network", "connection", "traffic", "blocked"]):
            query = "* | where contains('Log Entry', 'connection refused') or contains('Log Entry', 'blocked') or 'Action' = 'BLOCK'"
        elif any(term in search_lower for term in ["malware", "virus", "threat"]):
            query = "* | where contains('Log Entry', 'malware') or contains('Log Entry', 'virus') or contains('Log Entry', 'threat')"
        else:
            # Generic security search
            query = f"* | search '{search_term}'"
        
        result = client.execute_query_fast(query, compartment_id, time_range, max_count)
        
        return with_meta(
            {
                "search_term": search_term,
                "query_used": query,
                "compartment_id": compartment_id,
                "namespace": result.namespace,
                "results": result.data,
                "count": result.count,
                "execution_time_ms": result.execution_time_ms,
                "success": result.success
            },
            success=result.success,
            message=result.message
        )
    except Exception as e:
        return with_meta(
            {"error": str(e), "success": False},
            success=False,
            message=f"Security event search failed: {str(e)}"
        )
