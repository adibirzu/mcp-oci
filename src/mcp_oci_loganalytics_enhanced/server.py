"""Enhanced MCP Server: OCI Log Analytics with Security Analysis
Based on logan-server implementation with advanced security features.

Tools are exposed as `oci:loganalytics:<action>`.
Includes security analysis, MITRE ATT&CK integration, and advanced analytics.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from mcp_oci_common import get_oci_config
from mcp_oci_common.responses import with_meta

try:
    import oci  # type: ignore
except Exception:
    oci = None


@dataclass
class SecurityQuery:
    """Security query definition"""
    name: str
    description: str
    queries: List[str]
    mitre_techniques: List[str] = None
    severity: str = "medium"


class SecurityQueryMapper:
    """Maps security analysis types to OCI Log Analytics queries"""
    
    def __init__(self):
        self.security_queries = {
            "failed_logins": SecurityQuery(
                name="Failed Login Attempts",
                description="Detect failed authentication attempts",
                queries=[
                    "* | where contains('Log Entry', 'Failed password') or contains('Log Entry', 'authentication failure')",
                    "* | where 'Event Name' = 'AuthenticationFailure'",
                    "* | where contains('Message', 'login failed') or contains('Message', 'authentication failed')",
                    "* | search 'failed' 'login' OR 'authentication' 'failure'"
                ],
                mitre_techniques=["T1110", "T1078"],
                severity="high"
            ),
            "privilege_escalation": SecurityQuery(
                name="Privilege Escalation",
                description="Detect privilege escalation attempts",
                queries=[
                    "* | where contains('Log Entry', 'sudo') or contains('Log Entry', 'su:')",
                    "* | where contains('Event Name', 'Assume') or contains('Event Name', 'Escalate')",
                    "* | search 'sudo' OR 'privilege' 'escalation' OR 'assume' 'role'"
                ],
                mitre_techniques=["T1548", "T1078"],
                severity="high"
            ),
            "suspicious_network": SecurityQuery(
                name="Suspicious Network Activity",
                description="Detect suspicious network connections",
                queries=[
                    "* | where contains('Log Entry', 'connection refused') or contains('Log Entry', 'blocked')",
                    "* | search 'blocked' 'connection' OR 'suspicious' 'traffic' OR 'firewall' 'deny'",
                    "* | where 'Action' = 'BLOCK' or 'Action' = 'DENY' or 'Action' = 'REJECT'"
                ],
                mitre_techniques=["T1046", "T1043"],
                severity="medium"
            ),
            "data_exfiltration": SecurityQuery(
                name="Data Exfiltration",
                description="Detect potential data exfiltration attempts",
                queries=[
                    "* | where contains('Log Entry', 'large download') or contains('Log Entry', 'bulk transfer')",
                    "* | search 'exfiltration' OR 'data' 'theft' OR 'unauthorized' 'download'",
                    "* | where 'Event Name' = 'DataAccess' and 'Action' = 'READ'"
                ],
                mitre_techniques=["T1041", "T1005"],
                severity="high"
            ),
            "malware": SecurityQuery(
                name="Malware Detection",
                description="Detect malware-related activities",
                queries=[
                    "* | where contains('Log Entry', 'malware') or contains('Log Entry', 'virus')",
                    "* | search 'malware' OR 'virus' OR 'trojan' OR 'ransomware'",
                    "* | where 'Event Name' = 'MalwareDetected' or 'Event Name' = 'ThreatDetected'"
                ],
                mitre_techniques=["T1055", "T1059"],
                severity="critical"
            )
        }
        
        self.mitre_techniques = {
            "T1003": "OS Credential Dumping",
            "T1005": "Data from Local System",
            "T1041": "Exfiltration Over C2 Channel",
            "T1043": "Commonly Used Port",
            "T1046": "Network Service Scanning",
            "T1055": "Process Injection",
            "T1059": "Command and Scripting Interpreter",
            "T1078": "Valid Accounts",
            "T1110": "Brute Force",
            "T1548": "Abuse Elevation Control Mechanism"
        }

    def get_security_query(self, query_type: str, time_period_minutes: int = 60) -> Dict[str, Any]:
        """Get security query for a specific type"""
        if query_type not in self.security_queries:
            return {
                "success": False,
                "error": f"Unknown security query type: {query_type}",
                "available_types": list(self.security_queries.keys())
            }
        
        query_def = self.security_queries[query_type]
        
        # Add time filter to queries
        time_filter = f"Time > dateRelative({time_period_minutes}m)"
        enhanced_queries = []
        
        for query in query_def.queries:
            if "Time >" not in query:
                enhanced_query = f"{query} and {time_filter}"
            else:
                enhanced_query = query
            enhanced_queries.append(enhanced_query)
        
        return {
            "success": True,
            "query_type": query_type,
            "description": query_def.description,
            "queries": enhanced_queries,
            "mitre_techniques": query_def.mitre_techniques,
            "severity": query_def.severity,
            "time_period_minutes": time_period_minutes
        }

    def get_mitre_technique_query(self, technique_id: str, time_period_minutes: int = 60) -> Dict[str, Any]:
        """Get query for specific MITRE technique"""
        if technique_id not in self.mitre_techniques:
            return {
                "success": False,
                "error": f"Unknown MITRE technique: {technique_id}",
                "available_techniques": list(self.mitre_techniques.keys())
            }
        
        technique_name = self.mitre_techniques[technique_id]
        time_filter = f"Time > dateRelative({time_period_minutes}m)"
        
        # Map technique to query patterns
        technique_queries = {
            "T1003": [f"* | where contains('Log Entry', 'credential') or contains('Log Entry', 'password') and {time_filter}"],
            "T1005": [f"* | where contains('Log Entry', 'file access') or contains('Log Entry', 'data access') and {time_filter}"],
            "T1041": [f"* | where contains('Log Entry', 'network') or contains('Log Entry', 'connection') and {time_filter}"],
            "T1043": [f"* | where contains('Log Entry', 'port') or contains('Log Entry', 'service') and {time_filter}"],
            "T1046": [f"* | where contains('Log Entry', 'scan') or contains('Log Entry', 'probe') and {time_filter}"],
            "T1055": [f"* | where contains('Log Entry', 'injection') or contains('Log Entry', 'process') and {time_filter}"],
            "T1059": [f"* | where contains('Log Entry', 'command') or contains('Log Entry', 'script') and {time_filter}"],
            "T1078": [f"* | where contains('Log Entry', 'login') or contains('Log Entry', 'authentication') and {time_filter}"],
            "T1110": [f"* | where contains('Log Entry', 'failed') or contains('Log Entry', 'brute') and {time_filter}"],
            "T1548": [f"* | where contains('Log Entry', 'sudo') or contains('Log Entry', 'elevate') and {time_filter}"]
        }
        
        queries = technique_queries.get(technique_id, [f"* | where contains('Log Entry', '{technique_name.lower()}') and {time_filter}"])
        
        return {
            "success": True,
            "technique_id": technique_id,
            "technique_name": technique_name,
            "queries": queries,
            "time_period_minutes": time_period_minutes
        }


def create_client(profile: str | None = None, region: str | None = None):
    if oci is None:
        raise RuntimeError("OCI SDK not available. Install oci>=2.0.0")
    config = get_oci_config(profile=profile, region=region)
    return oci.log_analytics.LogAnalyticsClient(config)


def _extract_items_from_response(resp) -> list[Any]:
    """Extract items from OCI response, handling both direct data and data.items patterns"""
    data = getattr(resp, "data", None)
    if data and hasattr(data, "items"):
        return [getattr(i, "__dict__", i) for i in data.items]
    else:
        return [getattr(i, "__dict__", i) for i in getattr(resp, "data", [])]


def _get_namespace(client, compartment_id: str) -> str:
    """Get Log Analytics namespace for a compartment"""
    try:
        # Try to get namespace from object storage
        object_storage_client = oci.object_storage.ObjectStorageClient(client._config)
        namespace = object_storage_client.get_namespace().data
        return namespace
    except Exception:
        # Fallback to compartment ID as namespace
        return compartment_id


def _format_time_range(time_range: str) -> tuple[str, str]:
    """Convert time range string to start/end times"""
    now = datetime.now(timezone.utc)
    
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
    start_time = now - delta
    
    return start_time.isoformat(), now.isoformat()


def register_tools() -> list[dict[str, Any]]:
    return [
        # Core Query Tools
        {
            "name": "oci:loganalytics:execute_query",
            "description": "Execute a Log Analytics query with enhanced security analysis capabilities",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "OCI Log Analytics query string"},
                    "query_name": {"type": "string", "description": "Optional name for the query"},
                    "time_range": {"type": "string", "description": "Time range (1h, 6h, 12h, 24h, 1d, 7d, 30d, 1w, 1m)", "default": "24h"},
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "max_count": {"type": "integer", "description": "Maximum number of results", "default": 1000},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["query", "compartment_id"],
            },
            "handler": execute_query,
        },
        {
            "name": "oci:loganalytics:search_security_events",
            "description": "Search for security events using natural language or predefined patterns",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_term": {"type": "string", "description": "Natural language description or specific security event pattern"},
                    "event_type": {"type": "string", "enum": ["login", "privilege_escalation", "network_anomaly", "data_exfiltration", "malware", "all"], "default": "all"},
                    "time_range": {"type": "string", "description": "Time range for the search", "default": "24h"},
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "limit": {"type": "integer", "description": "Maximum number of results", "default": 100},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["search_term", "compartment_id"],
            },
            "handler": search_security_events,
        },
        {
            "name": "oci:loganalytics:get_mitre_techniques",
            "description": "Search for MITRE ATT&CK techniques in the logs",
            "parameters": {
                "type": "object",
                "properties": {
                    "technique_id": {"type": "string", "description": "Specific MITRE technique ID (e.g., T1003, T1110) or 'all'"},
                    "category": {"type": "string", "enum": ["initial_access", "execution", "persistence", "privilege_escalation", "defense_evasion", "credential_access", "discovery", "lateral_movement", "collection", "command_and_control", "exfiltration", "impact", "all"], "default": "all"},
                    "time_range": {"type": "string", "description": "Time range for the analysis", "default": "30d"},
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": get_mitre_techniques,
        },
        {
            "name": "oci:loganalytics:analyze_ip_activity",
            "description": "Analyze activity for specific IP addresses",
            "parameters": {
                "type": "object",
                "properties": {
                    "ip_address": {"type": "string", "description": "IP address to analyze"},
                    "analysis_type": {"type": "string", "enum": ["full", "authentication", "network", "threat_intel", "communication_patterns"], "default": "full"},
                    "time_range": {"type": "string", "description": "Time range for the analysis", "default": "24h"},
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["ip_address", "compartment_id"],
            },
            "handler": analyze_ip_activity,
        },
        # Advanced Analytics Tools
        {
            "name": "oci:loganalytics:perform_statistical_analysis",
            "description": "Execute statistical analysis using stats, timestats, and eventstats commands",
            "parameters": {
                "type": "object",
                "properties": {
                    "base_query": {"type": "string", "description": "Base query to analyze statistically"},
                    "statistics_type": {"type": "string", "enum": ["stats", "timestats", "eventstats", "top", "bottom", "frequent", "rare"], "default": "stats"},
                    "aggregations": {"type": "array", "description": "Statistical functions to apply"},
                    "group_by": {"type": "array", "description": "Fields to group by"},
                    "time_interval": {"type": "string", "description": "Time interval for timestats (e.g., '5m', '1h', '1d')"},
                    "time_range": {"type": "string", "description": "Time range for analysis", "default": "24h"},
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["base_query", "compartment_id"],
            },
            "handler": perform_statistical_analysis,
        },
        {
            "name": "oci:loganalytics:perform_advanced_analytics",
            "description": "Execute advanced analytics queries using OCI Log Analytics specialized commands",
            "parameters": {
                "type": "object",
                "properties": {
                    "base_query": {"type": "string", "description": "Base query to analyze (without analytics command)"},
                    "analytics_type": {"type": "string", "enum": ["cluster", "link", "nlp", "classify", "outlier", "sequence", "geostats", "timecluster"], "default": "cluster"},
                    "parameters": {"type": "object", "description": "Parameters specific to the analytics type"},
                    "time_range": {"type": "string", "description": "Time range for analysis", "default": "24h"},
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["base_query", "compartment_id"],
            },
            "handler": perform_advanced_analytics,
        },
        # Utility Tools
        {
            "name": "oci:loganalytics:validate_query",
            "description": "Validate an OCI Logging Analytics query syntax",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Query to validate"},
                    "fix": {"type": "boolean", "description": "Attempt to automatically fix common syntax errors", "default": False},
                },
                "required": ["query"],
            },
            "handler": validate_query,
        },
        {
            "name": "oci:loganalytics:get_documentation",
            "description": "Get documentation and help for OCI Logging Analytics and Logan queries",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "enum": ["query_syntax", "field_names", "functions", "time_filters", "operators", "mitre_mapping", "examples", "troubleshooting"], "default": "query_syntax"},
                    "search_term": {"type": "string", "description": "Specific term to search for in documentation"},
                },
            },
            "handler": get_documentation,
        },
        {
            "name": "oci:loganalytics:check_connection",
            "description": "Check OCI Logging Analytics connection and authentication",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "test_query": {"type": "boolean", "description": "Run a test query to verify connectivity", "default": True},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": check_connection,
        },
        # Original tools for backward compatibility
        {
            "name": "oci:loganalytics:run-query",
            "description": "Run a Log Analytics query for a namespace and time range (legacy)",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace_name": {"type": "string"},
                    "query_string": {"type": "string"},
                    "time_start": {"type": "string", "description": "ISO8601"},
                    "time_end": {"type": "string", "description": "ISO8601"},
                    "subsystem": {"type": "string", "description": "Optional subsystem filter"},
                    "max_total_count": {"type": "integer", "description": "Optional cap on rows"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["namespace_name", "query_string", "time_start", "time_end"],
            },
            "handler": run_query_legacy,
        },
    ]


# Tool Handlers

def execute_query(
    query: str,
    compartment_id: str,
    query_name: str | None = None,
    time_range: str = "24h",
    max_count: int = 1000,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Execute a Log Analytics query with enhanced capabilities"""
    try:
        client = create_client(profile=profile, region=region)
        namespace = _get_namespace(client, compartment_id)
        
        # Convert time range to start/end times
        start_time, end_time = _format_time_range(time_range)
        
        # Execute the query
        response = client.query(
            namespace_name=namespace,
            query=query,
            time_start=start_time,
            time_end=end_time,
            max_total_count=max_count
        )
        
        results = _extract_items_from_response(response)
        
        return with_meta(
            {
                "query": query,
                "query_name": query_name,
                "time_range": time_range,
                "namespace": namespace,
                "compartment_id": compartment_id,
                "results": results,
                "count": len(results),
                "execution_time": getattr(response, "execution_time_ms", 0)
            },
            success=True,
            message=f"Query executed successfully. Found {len(results)} results."
        )
    except Exception as e:
        return with_meta(
            {"error": str(e)},
            success=False,
            message=f"Query execution failed: {str(e)}"
        )


def search_security_events(
    search_term: str,
    compartment_id: str,
    event_type: str = "all",
    time_range: str = "24h",
    limit: int = 100,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Search for security events using natural language or predefined patterns"""
    try:
        mapper = SecurityQueryMapper()
        
        # Map search term to security query
        if event_type == "all":
            # Try to match search term to known patterns
            search_lower = search_term.lower()
            if any(term in search_lower for term in ["login", "auth", "signin"]):
                event_type = "failed_logins"
            elif any(term in search_lower for term in ["privilege", "escalation", "sudo"]):
                event_type = "privilege_escalation"
            elif any(term in search_lower for term in ["network", "connection", "traffic"]):
                event_type = "suspicious_network"
            elif any(term in search_lower for term in ["data", "exfiltration", "theft"]):
                event_type = "data_exfiltration"
            elif any(term in search_lower for term in ["malware", "virus", "threat"]):
                event_type = "malware"
            else:
                event_type = "failed_logins"  # Default fallback
        
        # Get security query
        query_result = mapper.get_security_query(event_type, 60)  # Convert time_range to minutes
        
        if not query_result.get("success"):
            return with_meta(
                {"error": query_result.get("error")},
                success=False,
                message=f"Security query mapping failed: {query_result.get('error')}"
            )
        
        # Execute the first query
        query = query_result["queries"][0]
        result = execute_query(
            query=query,
            compartment_id=compartment_id,
            query_name=f"security_search_{event_type}",
            time_range=time_range,
            max_count=limit,
            profile=profile,
            region=region
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        return with_meta(
            {
                "search_term": search_term,
                "event_type": event_type,
                "query_used": query,
                "mitre_techniques": query_result.get("mitre_techniques", []),
                "severity": query_result.get("severity", "medium"),
                "results": result_data.get("results", []),
                "count": result_data.get("count", 0)
            },
            success=result_data.get("success", False),
            message=f"Security event search completed. Found {result_data.get('count', 0)} events."
        )
    except Exception as e:
        return with_meta(
            {"error": str(e)},
            success=False,
            message=f"Security event search failed: {str(e)}"
        )


def get_mitre_techniques(
    compartment_id: str,
    technique_id: str = "all",
    category: str = "all",
    time_range: str = "30d",
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Search for MITRE ATT&CK techniques in the logs"""
    try:
        mapper = SecurityQueryMapper()
        
        if technique_id == "all":
            # Return all available techniques
            return with_meta(
                {
                    "techniques": mapper.mitre_techniques,
                    "count": len(mapper.mitre_techniques)
                },
                success=True,
                message=f"Found {len(mapper.mitre_techniques)} MITRE techniques"
            )
        
        # Get specific technique query
        query_result = mapper.get_mitre_technique_query(technique_id, 60)  # Convert time_range to minutes
        
        if not query_result.get("success"):
            return with_meta(
                {"error": query_result.get("error")},
                success=False,
                message=f"MITRE technique query failed: {query_result.get('error')}"
            )
        
        # Execute the query
        query = query_result["queries"][0]
        result = execute_query(
            query=query,
            compartment_id=compartment_id,
            query_name=f"mitre_technique_{technique_id}",
            time_range=time_range,
            profile=profile,
            region=region
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        return with_meta(
            {
                "technique_id": technique_id,
                "technique_name": query_result.get("technique_name"),
                "query_used": query,
                "results": result_data.get("results", []),
                "count": result_data.get("count", 0)
            },
            success=result_data.get("success", False),
            message=f"MITRE technique analysis completed. Found {result_data.get('count', 0)} events for technique {technique_id}."
        )
    except Exception as e:
        return with_meta(
            {"error": str(e)},
            success=False,
            message=f"MITRE technique analysis failed: {str(e)}"
        )


def analyze_ip_activity(
    ip_address: str,
    compartment_id: str,
    analysis_type: str = "full",
    time_range: str = "24h",
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Analyze activity for specific IP addresses"""
    try:
        # Build query based on analysis type
        time_filter = f"Time > dateRelative({time_range})"
        
        if analysis_type == "authentication":
            query = f"* | where contains('Source IP', '{ip_address}') and (contains('Log Entry', 'login') or contains('Log Entry', 'auth')) and {time_filter} | stats count by 'Event Name', 'User'"
        elif analysis_type == "network":
            query = f"* | where contains('Source IP', '{ip_address}') or contains('Destination IP', '{ip_address}') and {time_filter} | stats count by 'Source IP', 'Destination IP', 'Port'"
        elif analysis_type == "threat_intel":
            query = f"* | where contains('Source IP', '{ip_address}') and (contains('Log Entry', 'threat') or contains('Log Entry', 'malware') or contains('Log Entry', 'suspicious')) and {time_filter}"
        elif analysis_type == "communication_patterns":
            query = f"* | where contains('Source IP', '{ip_address}') or contains('Destination IP', '{ip_address}') and {time_filter} | stats count by 'Protocol', 'Port' | sort -count"
        else:  # full
            query = f"* | where contains('Source IP', '{ip_address}') or contains('Destination IP', '{ip_address}') and {time_filter} | stats count by 'Event Name', 'Log Source' | sort -count"
        
        # Execute the query
        result = execute_query(
            query=query,
            compartment_id=compartment_id,
            query_name=f"ip_analysis_{analysis_type}_{ip_address}",
            time_range=time_range,
            profile=profile,
            region=region
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        return with_meta(
            {
                "ip_address": ip_address,
                "analysis_type": analysis_type,
                "query_used": query,
                "results": result_data.get("results", []),
                "count": result_data.get("count", 0)
            },
            success=result_data.get("success", False),
            message=f"IP activity analysis completed. Found {result_data.get('count', 0)} events for IP {ip_address}."
        )
    except Exception as e:
        return with_meta(
            {"error": str(e)},
            success=False,
            message=f"IP activity analysis failed: {str(e)}"
        )


def perform_statistical_analysis(
    base_query: str,
    compartment_id: str,
    statistics_type: str = "stats",
    aggregations: List[Dict] = None,
    group_by: List[str] = None,
    time_interval: str = None,
    time_range: str = "24h",
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Execute statistical analysis using stats, timestats, and eventstats commands"""
    try:
        # Build statistical query
        if statistics_type == "timestats" and time_interval:
            stats_query = f"{base_query} | timestats {time_interval} count by {', '.join(group_by) if group_by else '1'}"
        elif statistics_type == "eventstats":
            stats_query = f"{base_query} | eventstats count by {', '.join(group_by) if group_by else '1'}"
        elif statistics_type == "top":
            stats_query = f"{base_query} | top 10 by count"
        elif statistics_type == "bottom":
            stats_query = f"{base_query} | bottom 10 by count"
        elif statistics_type == "frequent":
            stats_query = f"{base_query} | frequent 10"
        elif statistics_type == "rare":
            stats_query = f"{base_query} | rare 10"
        else:  # stats
            agg_str = ", ".join([f"{agg.get('function', 'count')}({agg.get('field', '1')}) as {agg.get('alias', 'count')}" for agg in aggregations or [{"function": "count"}]])
            group_str = f" by {', '.join(group_by)}" if group_by else ""
            stats_query = f"{base_query} | stats {agg_str}{group_str}"
        
        # Execute the query
        result = execute_query(
            query=stats_query,
            compartment_id=compartment_id,
            query_name=f"statistical_analysis_{statistics_type}",
            time_range=time_range,
            profile=profile,
            region=region
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        return with_meta(
            {
                "base_query": base_query,
                "statistics_type": statistics_type,
                "statistical_query": stats_query,
                "aggregations": aggregations,
                "group_by": group_by,
                "time_interval": time_interval,
                "results": result_data.get("results", []),
                "count": result_data.get("count", 0)
            },
            success=result_data.get("success", False),
            message=f"Statistical analysis completed. Found {result_data.get('count', 0)} results."
        )
    except Exception as e:
        return with_meta(
            {"error": str(e)},
            success=False,
            message=f"Statistical analysis failed: {str(e)}"
        )


def perform_advanced_analytics(
    base_query: str,
    compartment_id: str,
    analytics_type: str = "cluster",
    parameters: Dict = None,
    time_range: str = "24h",
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Execute advanced analytics queries using OCI Log Analytics specialized commands"""
    try:
        # Build analytics query
        params = parameters or {}
        
        if analytics_type == "cluster":
            group_by = params.get("group_by", ["1"])
            max_clusters = params.get("max_clusters", 5)
            analytics_query = f"{base_query} | cluster by {', '.join(group_by)} max_clusters={max_clusters}"
        elif analytics_type == "outlier":
            threshold = params.get("threshold", 0.7)
            analytics_query = f"{base_query} | outlier threshold={threshold}"
        elif analytics_type == "nlp":
            analytics_query = f"{base_query} | nlp"
        elif analytics_type == "classify":
            analytics_query = f"{base_query} | classify"
        elif analytics_type == "sequence":
            pattern = params.get("sequence_pattern", "")
            analytics_query = f"{base_query} | sequence {pattern}"
        elif analytics_type == "geostats":
            lat_field = params.get("geoFields", {}).get("latitude", "latitude")
            lon_field = params.get("geoFields", {}).get("longitude", "longitude")
            analytics_query = f"{base_query} | geostats {lat_field}, {lon_field}"
        elif analytics_type == "timecluster":
            analytics_query = f"{base_query} | timecluster"
        else:  # link
            analytics_query = f"{base_query} | link"
        
        # Execute the query
        result = execute_query(
            query=analytics_query,
            compartment_id=compartment_id,
            query_name=f"advanced_analytics_{analytics_type}",
            time_range=time_range,
            profile=profile,
            region=region
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        return with_meta(
            {
                "base_query": base_query,
                "analytics_type": analytics_type,
                "analytics_query": analytics_query,
                "parameters": parameters,
                "results": result_data.get("results", []),
                "count": result_data.get("count", 0)
            },
            success=result_data.get("success", False),
            message=f"Advanced analytics completed. Found {result_data.get('count', 0)} results."
        )
    except Exception as e:
        return with_meta(
            {"error": str(e)},
            success=False,
            message=f"Advanced analytics failed: {str(e)}"
        )


def validate_query(
    query: str,
    fix: bool = False,
) -> str:
    """Validate an OCI Logging Analytics query syntax"""
    try:
        # Basic validation rules
        validation_errors = []
        suggestions = []
        
        # Check for common issues
        if "!=" in query and "null" in query:
            if fix:
                query = query.replace("!= null", '!= ""').replace("is not null", '!= ""')
                suggestions.append("Fixed null comparison operators for OCI API compatibility")
            else:
                validation_errors.append("Use '!= \"\"' instead of '!= null' for OCI API compatibility")
        
        if "Time >" not in query and "time >" not in query:
            suggestions.append("Consider adding a time filter like 'Time > dateRelative(24h)' for better performance")
        
        if not query.strip():
            validation_errors.append("Query cannot be empty")
        
        # Check for proper field quoting
        import re
        unquoted_fields = re.findall(r'\b[A-Z][a-zA-Z\s]+\b', query)
        if unquoted_fields:
            suggestions.append(f"Consider quoting field names with spaces: {unquoted_fields}")
        
        is_valid = len(validation_errors) == 0
        
        return with_meta(
            {
                "query": query,
                "is_valid": is_valid,
                "validation_errors": validation_errors,
                "suggestions": suggestions,
                "fixed_query": query if fix else None
            },
            success=is_valid,
            message=f"Query validation {'passed' if is_valid else 'failed'} with {len(validation_errors)} errors and {len(suggestions)} suggestions."
        )
    except Exception as e:
        return with_meta(
            {"error": str(e)},
            success=False,
            message=f"Query validation failed: {str(e)}"
        )


def get_documentation(
    topic: str = "query_syntax",
    search_term: str | None = None,
) -> str:
    """Get documentation and help for OCI Logging Analytics and Logan queries"""
    try:
        documentation = {
            "query_syntax": {
                "title": "OCI Log Analytics Query Syntax",
                "content": {
                    "field_names": "Always quote field names with spaces: 'Event Name' = 'UserLogin'",
                    "time_filters": "Use 'Time > dateRelative(24h)' for time-based filtering",
                    "operators": "Supported operators: =, !=, >, <, >=, <=, contains, in, not in",
                    "functions": "Common functions: stats, timestats, eventstats, top, bottom, frequent, rare",
                    "examples": [
                        "Failed logins: 'Event Name' = 'UserLoginFailed' and Time > dateRelative(24h) | stats count by 'User Name'",
                        "Network connections: 'Log Source' = 'VCN Flow Logs' and Time > dateRelative(1h) | stats count by 'Source IP'",
                        "MITRE techniques: 'Technique_id' is not null and Time > dateRelative(7d) | stats count by 'Technique_id'"
                    ]
                }
            },
            "mitre_mapping": {
                "title": "MITRE ATT&CK Technique Mapping",
                "content": {
                    "T1003": "OS Credential Dumping",
                    "T1005": "Data from Local System", 
                    "T1041": "Exfiltration Over C2 Channel",
                    "T1043": "Commonly Used Port",
                    "T1046": "Network Service Scanning",
                    "T1055": "Process Injection",
                    "T1059": "Command and Scripting Interpreter",
                    "T1078": "Valid Accounts",
                    "T1110": "Brute Force",
                    "T1548": "Abuse Elevation Control Mechanism"
                }
            },
            "troubleshooting": {
                "title": "Troubleshooting Guide",
                "content": {
                    "common_issues": [
                        "Missing input: Check field name capitalization and quoting",
                        "Authentication errors: Verify OCI configuration and permissions",
                        "No results: Check time range and compartment access",
                        "Syntax errors: Use validate_query tool for automatic fixes"
                    ],
                    "performance_tips": [
                        "Always include time filters for better performance",
                        "Use specific field filters early in queries",
                        "Limit result sets with '| head 100'",
                        "Use indexed fields for filtering"
                    ]
                }
            }
        }
        
        if topic not in documentation:
            available_topics = list(documentation.keys())
            return with_meta(
                {"error": f"Unknown topic: {topic}", "available_topics": available_topics},
                success=False,
                message=f"Unknown documentation topic. Available topics: {', '.join(available_topics)}"
            )
        
        doc_content = documentation[topic]
        
        # Filter by search term if provided
        if search_term:
            filtered_content = {}
            search_lower = search_term.lower()
            for key, value in doc_content["content"].items():
                if isinstance(value, str) and search_lower in value.lower():
                    filtered_content[key] = value
                elif isinstance(value, list):
                    filtered_list = [item for item in value if search_lower in str(item).lower()]
                    if filtered_list:
                        filtered_content[key] = filtered_list
            doc_content["content"] = filtered_content
        
        return with_meta(
            {
                "topic": topic,
                "search_term": search_term,
                "documentation": doc_content
            },
            success=True,
            message=f"Documentation retrieved for topic: {topic}"
        )
    except Exception as e:
        return with_meta(
            {"error": str(e)},
            success=False,
            message=f"Documentation retrieval failed: {str(e)}"
        )


def check_connection(
    compartment_id: str,
    test_query: bool = True,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Check OCI Logging Analytics connection and authentication"""
    try:
        client = create_client(profile=profile, region=region)
        namespace = _get_namespace(client, compartment_id)
        
        connection_info = {
            "compartment_id": compartment_id,
            "namespace": namespace,
            "region": region or "default",
            "profile": profile or "default",
            "connection_status": "success"
        }
        
        if test_query:
            # Run a simple test query
            test_result = execute_query(
                query="* | head 1",
                compartment_id=compartment_id,
                query_name="connection_test",
                time_range="1h",
                max_count=1,
                profile=profile,
                region=region
            )
            
            test_data = json.loads(test_result)
            connection_info["test_query_success"] = test_data.get("success", False)
            connection_info["test_query_message"] = test_data.get("message", "")
        
        return with_meta(
            connection_info,
            success=True,
            message="OCI Log Analytics connection successful"
        )
    except Exception as e:
        return with_meta(
            {
                "compartment_id": compartment_id,
                "connection_status": "failed",
                "error": str(e)
            },
            success=False,
            message=f"OCI Log Analytics connection failed: {str(e)}"
        )


def run_query_legacy(
    namespace_name: str,
    query_string: str,
    time_start: str,
    time_end: str,
    subsystem: str | None = None,
    max_total_count: int | None = None,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Legacy run query function for backward compatibility"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Execute the query
        response = client.query(
            namespace_name=namespace_name,
            query=query_string,
            time_start=time_start,
            time_end=time_end,
            subsystem=subsystem,
            max_total_count=max_total_count
        )
        
        results = _extract_items_from_response(response)
        
        return with_meta(
            {
                "namespace": namespace_name,
                "query": query_string,
                "time_start": time_start,
                "time_end": time_end,
                "subsystem": subsystem,
                "results": results,
                "count": len(results),
                "execution_time": getattr(response, "execution_time_ms", 0)
            },
            success=True,
            message=f"Legacy query executed successfully. Found {len(results)} results."
        )
    except Exception as e:
        return with_meta(
            {"error": str(e)},
            success=False,
            message=f"Legacy query execution failed: {str(e)}"
        )
