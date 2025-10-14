#!/usr/bin/env python3
"""
Optimized FastMCP Server Implementation
Based on official OCI Python SDK patterns and best practices

Key Features:
- Uses official OCI Python SDK as source of truth
- Optimized for FastMCP and LLM consumption
- Auto-discovery of compartments and namespaces
- Token-optimized responses
- Comprehensive error handling
- LLM-friendly response format
"""

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

# OCI SDK
try:
    import oci
    from oci.config import DEFAULT_LOCATION as OCI_CFG_DEFAULT
    from oci.config import from_file as oci_from_file
    from oci.exceptions import ConfigFileNotFound, InvalidConfig, ServiceError
except ImportError:
    raise SystemExit("OCI Python SDK not installed. Install with: pip install oci")

# FastMCP
try:
    from fastmcp import FastMCP
except ImportError:
    raise SystemExit("fastmcp is not installed. Install with: pip install fastmcp")

# ================================ CONFIGURATION ================================

SERVER_NAME = "oci-optimized"
app = FastMCP(SERVER_NAME)

# Performance settings
MAX_ITEMS = 1000
MAX_STRING = 10000
MAX_DEPTH = 10
CACHE_TTL = 300  # 5 minutes

# Feature flags
ENABLE_LOGAN = os.getenv("MCP_OCI_ENABLE_FASTMCP_LOGAN", "0").lower() in ("1", "true", "yes", "on")

# ================================ CORE CLASSES ================================

@dataclass
class OCIResponse:
    """Standardized OCI response format for LLM consumption."""
    success: bool
    message: str
    data: Any
    count: int | None = None
    compartment_id: str | None = None
    namespace: str | None = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class OCIClientManager:
    """Manages OCI clients with caching and error handling."""
    
    def __init__(self):
        self._config = None
        self._clients = {}
        self._last_config_check = 0
        self._config_check_interval = 300  # 5 minutes
        self._tenancy_id = None
        self._root_compartment_id = None
    
    @property
    def config(self):
        """Get OCI configuration with periodic refresh."""
        now = time.time()
        if self._config is None or (now - self._last_config_check) > self._config_check_interval:
            try:
                profile = os.getenv("OCI_PROFILE", "DEFAULT")
                cfg_path = os.getenv("OCI_CONFIG_FILE", OCI_CFG_DEFAULT)
                self._config = oci_from_file(cfg_path, profile)
                
                # Apply region override if provided
                region = os.getenv("OCI_REGION")
                if region:
                    self._config["region"] = region
                
                # Cache tenancy ID and root compartment ID
                self._tenancy_id = self._config.get("tenancy")
                self._root_compartment_id = self._tenancy_id  # Root compartment is same as tenancy
                
                self._last_config_check = now
            except Exception as e:
                raise handle_oci_error(e, "config_load")
        
        return self._config
    
    @property
    def tenancy_id(self) -> str:
        """Get the tenancy ID (root compartment)."""
        if self._tenancy_id is None:
            self._tenancy_id = self.config.get("tenancy")
        return self._tenancy_id
    
    @property
    def root_compartment_id(self) -> str:
        """Get the root compartment ID (same as tenancy)."""
        if self._root_compartment_id is None:
            self._root_compartment_id = self.tenancy_id
        return self._root_compartment_id
    
    def get_client(self, service_name: str):
        """Get or create OCI client with caching."""
        if service_name not in self._clients:
            try:
                config = self.config
                if service_name == "compute":
                    self._clients[service_name] = oci.core.ComputeClient(config)
                elif service_name == "identity":
                    self._clients[service_name] = oci.identity.IdentityClient(config)
                elif service_name == "log_analytics":
                    self._clients[service_name] = oci.log_analytics.LogAnalyticsClient(config)
                elif service_name == "object_storage":
                    self._clients[service_name] = oci.object_storage.ObjectStorageClient(config)
                elif service_name == "network":
                    self._clients[service_name] = oci.core.VirtualNetworkClient(config)
                elif service_name == "database":
                    self._clients[service_name] = oci.database.DatabaseClient(config)
                else:
                    raise ValueError(f"Unknown service: {service_name}")
            except Exception as e:
                raise handle_oci_error(e, f"client_creation_{service_name}")
        
        return self._clients[service_name]
    
    @property
    def compute(self):
        return self.get_client("compute")
    
    @property
    def identity(self):
        return self.get_client("identity")
    
    @property
    def log_analytics(self):
        return self.get_client("log_analytics")
    
    @property
    def object_storage(self):
        return self.get_client("object_storage")
    
    @property
    def network(self):
        return self.get_client("network")
    
    @property
    def database(self):
        return self.get_client("database")

# Global client manager
clients = OCIClientManager()

# ================================ UTILITY FUNCTIONS ================================

def handle_oci_error(error: Exception, operation: str, service: str = "oci") -> OCIResponse:
    """Handle OCI errors and return standardized response."""
    error_msg = str(error)
    
    if isinstance(error, ServiceError):
        if error.status == 404:
            return OCIResponse(
                success=False,
                message=f"Resource not found during {operation}",
                data={"error": "NOT_FOUND", "details": error_msg}
            )
        elif error.status == 403:
            return OCIResponse(
                success=False,
                message=f"Access denied during {operation}",
                data={"error": "ACCESS_DENIED", "details": error_msg}
            )
        elif error.status == 401:
            return OCIResponse(
                success=False,
                message=f"Authentication failed during {operation}",
                data={"error": "AUTH_FAILED", "details": error_msg}
            )
        else:
            return OCIResponse(
                success=False,
                message=f"Service error during {operation}: {error.status}",
                data={"error": "SERVICE_ERROR", "status": error.status, "details": error_msg}
            )
    elif isinstance(error, (ConfigFileNotFound, InvalidConfig)):
        return OCIResponse(
            success=False,
            message=f"Configuration error during {operation}",
            data={"error": "CONFIG_ERROR", "details": error_msg}
        )
    else:
        return OCIResponse(
            success=False,
            message=f"Unexpected error during {operation}",
            data={"error": "UNKNOWN_ERROR", "details": error_msg}
        )

def format_for_llm(data: Any, max_items: int = MAX_ITEMS) -> Any:
    """Format data for optimal LLM consumption."""
    if isinstance(data, list):
        # Limit items and format each item
        limited_data = data[:max_items]
        formatted_items = []
        
        for item in limited_data:
            if isinstance(item, dict):
                # Keep only essential fields for LLM consumption
                formatted_item = {}
                for key, value in item.items():
                    if key in ['id', 'display_name', 'name', 'lifecycle_state', 'time_created', 
                              'compartment_id', 'availability_domain', 'shape', 'region']:
                        formatted_item[key] = value
                formatted_items.append(formatted_item)
            else:
                formatted_items.append(item)
        
        return formatted_items
    elif isinstance(data, dict):
        # Format dictionary for LLM consumption
        formatted_dict = {}
        for key, value in data.items():
            if key in ['id', 'display_name', 'name', 'lifecycle_state', 'time_created',
                      'compartment_id', 'availability_domain', 'shape', 'region', 'namespace']:
                formatted_dict[key] = value
        return formatted_dict
    else:
        return data

def validate_compartment_id(compartment_id: str) -> bool:
    """Validate compartment ID format."""
    return compartment_id and (compartment_id.startswith("ocid1.compartment.") or compartment_id.startswith("ocid1.tenancy."))

def get_available_compartments(limit: int = 50) -> list[dict[str, Any]]:
    """Get available compartments using official OCI SDK patterns."""
    try:
        identity_client = clients.identity
        root_compartment_id = clients.root_compartment_id
        
        # Use official OCI SDK method pattern
        response = identity_client.list_compartments(
            compartment_id=root_compartment_id,
            limit=limit,
            access_level="ACCESSIBLE"
        )
        
        compartments = []
        for compartment in response.data:
            compartments.append({
                "id": compartment.id,
                "name": compartment.name,
                "description": compartment.description,
                "lifecycle_state": compartment.lifecycle_state,
                "time_created": compartment.time_created.isoformat() if compartment.time_created else None,
                "compartment_id": compartment.compartment_id
            })
        
        return compartments
    except Exception as e:
        raise handle_oci_error(e, "list_compartments", "identity")

def get_log_analytics_namespace() -> str:
    """Get Log Analytics namespace using official OCI SDK patterns."""
    try:
        log_analytics_client = clients.log_analytics
        compartment_id = clients.tenancy_id
        
        # Use official OCI SDK method
        response = log_analytics_client.list_namespaces(compartment_id=compartment_id)
        
        if response.data and response.data.items:
            return response.data.items[0].namespace_name
        else:
            raise RuntimeError("No Log Analytics namespace found for this tenancy")
    except Exception as e:
        raise handle_oci_error(e, "get_log_analytics_namespace", "log_analytics")

# ================================ ENHANCED LOG ANALYTICS TOOLS ================================

if ENABLE_LOGAN:

    @app.tool()
    async def execute_logan_query(
        query: str,
        compartment_id: str | None = None,
        query_name: str | None = None,
        time_range: str = "24h",
        max_count: int = 1000
    ) -> str:
    """Execute a Log Analytics query with enhanced security analysis capabilities."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        elif not validate_compartment_id(compartment_id):
            raise ValueError("Invalid compartment ID format")
        
        # Auto-discover namespace
        namespace = get_log_analytics_namespace()
        
        # Convert time range to minutes for query
        time_mapping = {
            "1h": 60, "6h": 360, "12h": 720, "24h": 1440, "1d": 1440,
            "7d": 10080, "30d": 43200, "1w": 10080, "1m": 43200
        }
        time_period_minutes = time_mapping.get(time_range, 1440)
        
        log_analytics_client = clients.log_analytics
        
        # Build proper QueryDetails payload (SDK requires model or camelCase dict)
        time_filter = oci.log_analytics.models.TimeRange(
            time_start=(datetime.now(timezone.utc) - timedelta(minutes=time_period_minutes)),
            time_end=datetime.now(timezone.utc)
        )
        query_details = oci.log_analytics.models.QueryDetails(
            compartment_id=compartment_id,
            query_string=query,
            sub_system=oci.log_analytics.models.QueryDetails.SUB_SYSTEM_LOG,
            max_total_count=max_count,
            time_filter=time_filter,
            should_include_columns=True,
            should_include_fields=False,
            should_include_total_count=True,
        )

        # Execute the query
        response = log_analytics_client.query(
            namespace_name=namespace,
            query_details=query_details,
            limit=max_count,
        )
        
        results = []
        for item in getattr(response.data, 'results', []) or []:
            results.append({
                "timestamp": getattr(item, "Datetime", getattr(item, "Time", "")),
                "log_source": getattr(item, "Log Source", ""),
                "event_name": getattr(item, "Event Name", ""),
                "message": getattr(item, "Log Entry", getattr(item, "Message", "")),
                "raw_data": item.__dict__
            })
        
        formatted_results = format_for_llm(results, max_count)
        
        result = OCIResponse(
            success=True,
            message=f"Log Analytics query executed successfully. Found {len(formatted_results)} results.",
            data=formatted_results,
            count=len(formatted_results),
            compartment_id=compartment_id,
            namespace=namespace
        )
        return json.dumps(result.__dict__)
    except Exception as e:
        result = handle_oci_error(e, "execute_logan_query", "log_analytics")
        return json.dumps(result.__dict__)

    @app.tool()
    async def search_security_events(
        search_term: str,
        compartment_id: str | None = None,
        event_type: str = "all",
        time_range: str = "24h",
        limit: int = 100
    ) -> str:
    """Search for security events using natural language or predefined patterns."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        elif not validate_compartment_id(compartment_id):
            raise ValueError("Invalid compartment ID format")
        
        # Map search term to security query patterns
        security_queries = {
            "failed_logins": [
                "* | where contains('Log Entry', 'Failed password') or contains('Log Entry', 'authentication failure')",
                "* | where 'Event Name' = 'AuthenticationFailure'",
                "* | where contains('Message', 'login failed') or contains('Message', 'authentication failed')"
            ],
            "privilege_escalation": [
                "* | where contains('Log Entry', 'sudo') or contains('Log Entry', 'su:')",
                "* | where contains('Event Name', 'Assume') or contains('Event Name', 'Escalate')"
            ],
            "suspicious_network": [
                "* | where contains('Log Entry', 'connection refused') or contains('Log Entry', 'blocked')",
                "* | where 'Action' = 'BLOCK' or 'Action' = 'DENY' or 'Action' = 'REJECT'"
            ],
            "data_exfiltration": [
                "* | where contains('Log Entry', 'large download') or contains('Log Entry', 'bulk transfer')",
                "* | where 'Event Name' = 'DataAccess' and 'Action' = 'READ'"
            ],
            "malware": [
                "* | where contains('Log Entry', 'malware') or contains('Log Entry', 'virus')",
                "* | where 'Event Name' = 'MalwareDetected' or 'Event Name' = 'ThreatDetected'"
            ]
        }
        
        # Determine event type from search term
        search_lower = search_term.lower()
        if event_type == "all":
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
        
        # Get query for the event type
        queries = security_queries.get(event_type, security_queries["failed_logins"])
        query = queries[0]  # Use the first query
        
        # Execute the query
        result = await execute_logan_query(
            query=query,
            compartment_id=compartment_id,
            query_name=f"security_search_{event_type}",
            time_range=time_range,
            max_count=limit
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        enhanced_result = OCIResponse(
            success=result_data.get("success", False),
            message=f"Security event search completed. Found {result_data.get('count', 0)} events for '{search_term}'.",
            data=result_data.get("data", []),
            count=result_data.get("count", 0),
            compartment_id=compartment_id
        )
        return json.dumps(enhanced_result.__dict__)
    except Exception as e:
        result = handle_oci_error(e, "search_security_events", "log_analytics")
        return json.dumps(result.__dict__)

@app.tool()
async def get_mitre_techniques(
    compartment_id: str | None = None,
    technique_id: str = "all",
    category: str = "all",
    time_range: str = "30d"
) -> str:
    """Search for MITRE ATT&CK techniques in the logs."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        elif not validate_compartment_id(compartment_id):
            raise ValueError("Invalid compartment ID format")
        
        mitre_techniques = {
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
        
        if technique_id == "all":
            # Return all available techniques
            result = OCIResponse(
                success=True,
                message=f"Found {len(mitre_techniques)} MITRE techniques",
                data=list(mitre_techniques.items()),
                count=len(mitre_techniques),
                compartment_id=compartment_id
            )
            return json.dumps(result.__dict__)
        
        # Get specific technique
        if technique_id not in mitre_techniques:
            result = OCIResponse(
                success=False,
                message=f"Unknown MITRE technique: {technique_id}",
                data={"available_techniques": list(mitre_techniques.keys())},
                compartment_id=compartment_id
            )
            return json.dumps(result.__dict__)
        
        technique_name = mitre_techniques[technique_id]
        
        # Build query for the technique
        technique_queries = {
            "T1003": "* | where contains('Log Entry', 'credential') or contains('Log Entry', 'password')",
            "T1005": "* | where contains('Log Entry', 'file access') or contains('Log Entry', 'data access')",
            "T1041": "* | where contains('Log Entry', 'network') or contains('Log Entry', 'connection')",
            "T1043": "* | where contains('Log Entry', 'port') or contains('Log Entry', 'service')",
            "T1046": "* | where contains('Log Entry', 'scan') or contains('Log Entry', 'probe')",
            "T1055": "* | where contains('Log Entry', 'injection') or contains('Log Entry', 'process')",
            "T1059": "* | where contains('Log Entry', 'command') or contains('Log Entry', 'script')",
            "T1078": "* | where contains('Log Entry', 'login') or contains('Log Entry', 'authentication')",
            "T1110": "* | where contains('Log Entry', 'failed') or contains('Log Entry', 'brute')",
            "T1548": "* | where contains('Log Entry', 'sudo') or contains('Log Entry', 'elevate')"
        }
        
        query = technique_queries.get(technique_id, f"* | where contains('Log Entry', '{technique_name.lower()}')")
        
        # Execute the query
        result = await execute_logan_query(
            query=query,
            compartment_id=compartment_id,
            query_name=f"mitre_technique_{technique_id}",
            time_range=time_range
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        enhanced_result = OCIResponse(
            success=result_data.get("success", False),
            message=f"MITRE technique analysis completed. Found {result_data.get('count', 0)} events for technique {technique_id} ({technique_name}).",
            data=result_data.get("data", []),
            count=result_data.get("count", 0),
            compartment_id=compartment_id
        )
        return json.dumps(enhanced_result.__dict__)
    except Exception as e:
        result = handle_oci_error(e, "get_mitre_techniques", "log_analytics")
        return json.dumps(result.__dict__)

@app.tool()
async def analyze_ip_activity(
    ip_address: str,
    compartment_id: str | None = None,
    analysis_type: str = "full",
    time_range: str = "24h"
) -> str:
    """Analyze activity for specific IP addresses."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        elif not validate_compartment_id(compartment_id):
            raise ValueError("Invalid compartment ID format")
        
        # Build query based on analysis type
        if analysis_type == "authentication":
            query = f"* | where contains('Source IP', '{ip_address}') and (contains('Log Entry', 'login') or contains('Log Entry', 'auth')) | stats count by 'Event Name', 'User'"
        elif analysis_type == "network":
            query = f"* | where contains('Source IP', '{ip_address}') or contains('Destination IP', '{ip_address}') | stats count by 'Source IP', 'Destination IP', 'Port'"
        elif analysis_type == "threat_intel":
            query = f"* | where contains('Source IP', '{ip_address}') and (contains('Log Entry', 'threat') or contains('Log Entry', 'malware') or contains('Log Entry', 'suspicious'))"
        elif analysis_type == "communication_patterns":
            query = f"* | where contains('Source IP', '{ip_address}') or contains('Destination IP', '{ip_address}') | stats count by 'Protocol', 'Port' | sort -count"
        else:  # full
            query = f"* | where contains('Source IP', '{ip_address}') or contains('Destination IP', '{ip_address}') | stats count by 'Event Name', 'Log Source' | sort -count"
        
        # Execute the query
        result = await execute_logan_query(
            query=query,
            compartment_id=compartment_id,
            query_name=f"ip_analysis_{analysis_type}_{ip_address}",
            time_range=time_range
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        enhanced_result = OCIResponse(
            success=result_data.get("success", False),
            message=f"IP activity analysis completed. Found {result_data.get('count', 0)} events for IP {ip_address}.",
            data=result_data.get("data", []),
            count=result_data.get("count", 0),
            compartment_id=compartment_id
        )
        return json.dumps(enhanced_result.__dict__)
    except Exception as e:
        result = handle_oci_error(e, "analyze_ip_activity", "log_analytics")
        return json.dumps(result.__dict__)

    # ================================ ROBUST LOG ANALYTICS TOOLS ================================

    @app.tool()
    async def execute_logan_query_robust(
        query: str,
        compartment_id: str | None = None,
        time_range: str = "24h",
        max_count: int = 1000
    ) -> str:
    """Execute Log Analytics queries with optimized performance and fast connection."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        elif not validate_compartment_id(compartment_id):
            raise ValueError("Invalid compartment ID format")
        
        # Import robust client
        from mcp_oci_loganalytics_robust.server import create_client as create_robust_client
        
        # Create robust client
        robust_client = create_robust_client()
        
        # Execute query with robust client
        result = robust_client.execute_query_fast(query, compartment_id, time_range, max_count)
        
        return json.dumps({
            "success": result.success,
            "message": result.message,
            "data": {
                "query": result.query,
                "namespace": result.namespace,
                "compartment_id": compartment_id,
                "time_range": time_range,
                "results": result.data,
                "count": result.count,
                "execution_time_ms": result.execution_time_ms
            },
            "error": result.error
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Robust query execution failed: {str(e)}",
            "data": {},
            "error": str(e)
        })

    @app.tool()
    async def list_log_sources_robust(
        compartment_id: str | None = None,
        limit: int = 100
    ) -> str:
    """List Log Analytics sources with optimized performance."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        elif not validate_compartment_id(compartment_id):
            raise ValueError("Invalid compartment ID format")
        
        # Import robust client
        from mcp_oci_loganalytics_robust.server import create_client as create_robust_client
        
        # Create robust client
        robust_client = create_robust_client()
        
        # List sources with robust client
        result = robust_client.list_sources_fast(compartment_id, limit)
        
        return json.dumps({
            "success": result.success,
            "message": result.message,
            "data": {
                "compartment_id": compartment_id,
                "namespace": result.namespace,
                "sources": result.data,
                "count": result.count,
                "execution_time_ms": result.execution_time_ms
            },
            "error": result.error
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Robust source listing failed: {str(e)}",
            "data": {},
            "error": str(e)
        })

    @app.tool()
    async def get_log_sources_last_days(
        compartment_id: str | None = None,
        days: int = 5
    ) -> str:
    """Get log sources with activity from the last N days."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        elif not validate_compartment_id(compartment_id):
            raise ValueError("Invalid compartment ID format")
        
        # Import robust client
        from mcp_oci_loganalytics_robust.server import create_client as create_robust_client
        
        # Create robust client
        robust_client = create_robust_client()
        
        # Get log sources from last N days
        result = robust_client.get_log_sources_last_days(compartment_id, days)
        
        return json.dumps({
            "success": result.success,
            "message": result.message,
            "data": {
                "compartment_id": compartment_id,
                "namespace": result.namespace,
                "days": days,
                "log_sources": result.data,
                "count": result.count,
                "execution_time_ms": result.execution_time_ms
            },
            "error": result.error
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Failed to get log sources from last {days} days: {str(e)}",
            "data": {},
            "error": str(e)
        })

    @app.tool()
    async def test_logan_connection_robust(
        compartment_id: str | None = None
    ) -> str:
    """Test Log Analytics connection with robust client."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        elif not validate_compartment_id(compartment_id):
            raise ValueError("Invalid compartment ID format")
        
        # Import robust client
        from mcp_oci_loganalytics_robust.server import create_client as create_robust_client
        
        # Create robust client
        robust_client = create_robust_client()
        
        # Get namespace
        namespace = robust_client.get_namespace_fast(compartment_id)
        
        # Test with a simple query
        test_result = robust_client.execute_query_fast("* | head 1", compartment_id, "1h", 1)
        
        return json.dumps({
            "success": test_result.success,
            "message": f"Connection test {'successful' if test_result.success else 'failed'}. Namespace: {namespace}",
            "data": {
                "compartment_id": compartment_id,
                "namespace": namespace,
                "connection_status": "success" if test_result.success else "failed",
                "test_query_success": test_result.success,
                "test_query_time_ms": test_result.execution_time_ms
            },
            "error": test_result.error
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Connection test failed: {str(e)}",
            "data": {},
            "error": str(e)
        })

# ================================ FAST LOG ANALYTICS TOOLS ================================

    @app.tool()
    async def execute_logan_query_fast(
        query: str,
        compartment_id: str | None = None,
        time_range: str = "24h",
        max_count: int = 1000
    ) -> str:
    """Execute Log Analytics queries with optimized performance and fast connection."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        elif not validate_compartment_id(compartment_id):
            raise ValueError("Invalid compartment ID format")
        
        # Import fast client
        from mcp_oci_loganalytics_fast.server import execute_query_fast
        
        # Execute query with fast client
        result = execute_query_fast(query, compartment_id, time_range, max_count)
        
        return json.dumps({
            "success": result.success,
            "message": result.message,
            "data": {
                "query": result.query,
                "namespace": result.namespace,
                "compartment_id": compartment_id,
                "time_range": time_range,
                "results": result.data,
                "count": result.count,
                "execution_time_ms": result.execution_time_ms
            },
            "error": result.error
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Fast query execution failed: {str(e)}",
            "data": {},
            "error": str(e)
        })

    @app.tool()
    async def list_log_sources_fast(
        compartment_id: str | None = None,
        limit: int = 100
    ) -> str:
    """List Log Analytics sources with optimized performance."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        elif not validate_compartment_id(compartment_id):
            raise ValueError("Invalid compartment ID format")
        
        # Import fast client
        from mcp_oci_loganalytics_fast.server import list_sources_fast
        
        # List sources with fast client
        result = list_sources_fast(compartment_id, limit)
        
        return json.dumps({
            "success": result.success,
            "message": result.message,
            "data": {
                "compartment_id": compartment_id,
                "namespace": result.namespace,
                "sources": result.data,
                "count": result.count,
                "execution_time_ms": result.execution_time_ms
            },
            "error": result.error
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Fast source listing failed: {str(e)}",
            "data": {},
            "error": str(e)
        })

    @app.tool()
    async def get_log_sources_last_days_fast(
        compartment_id: str | None = None,
        days: int = 5
    ) -> str:
    """Get log sources with activity from the last N days using fast client."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        elif not validate_compartment_id(compartment_id):
            raise ValueError("Invalid compartment ID format")
        
        # Import fast client
        from mcp_oci_loganalytics_fast.server import get_log_sources_last_days
        
        # Get log sources from last N days
        result = get_log_sources_last_days(compartment_id, days)
        
        return json.dumps({
            "success": result.success,
            "message": result.message,
            "data": {
                "compartment_id": compartment_id,
                "namespace": result.namespace,
                "days": days,
                "log_sources": result.data,
                "count": result.count,
                "execution_time_ms": result.execution_time_ms
            },
            "error": result.error
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Failed to get log sources from last {days} days: {str(e)}",
            "data": {},
            "error": str(e)
        })

    @app.tool()
    async def test_logan_connection_fast(
        compartment_id: str | None = None
    ) -> str:
    """Test Log Analytics connection with fast client."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        elif not validate_compartment_id(compartment_id):
            raise ValueError("Invalid compartment ID format")
        
        # Import fast client
        from mcp_oci_loganalytics_fast.server import create_client, get_namespace_fast, execute_query_fast
        
        # Create fast client
        client = create_client()
        namespace = get_namespace_fast(client, compartment_id)
        
        # Test with a simple query
        test_result = execute_query_fast("* | head 1", compartment_id, "1h", 1)
        
        return json.dumps({
            "success": test_result.success,
            "message": f"Fast connection test {'successful' if test_result.success else 'failed'}. Namespace: {namespace}",
            "data": {
                "compartment_id": compartment_id,
                "namespace": namespace,
                "connection_status": "success" if test_result.success else "failed",
                "test_query_success": test_result.success,
                "test_query_time_ms": test_result.execution_time_ms
            },
            "error": test_result.error
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Fast connection test failed: {str(e)}",
            "data": {},
            "error": str(e)
        })

# ================================ FASTMCP TOOLS ================================

@app.tool()
async def get_server_info() -> str:
    """Get server information and capabilities."""
    try:
        info = {
            "name": SERVER_NAME,
            "version": "2.0.0",
            "framework": "fastmcp",
            "oci_sdk_version": oci.__version__,
            "capabilities": [
                "compute_instances",
                "identity_compartments", 
                "log_analytics_queries",
                "object_storage_buckets",
                "network_resources",
                "database_resources"
            ],
            "features": [
                "auto_discovery",
                "token_optimized",
                "llm_friendly",
                "error_handling"
            ],
            "default_compartment": clients.root_compartment_id,
            "region": clients.config.get("region", "unknown")
        }
        
        result = OCIResponse(
            success=True,
            message="Server information retrieved successfully",
            data=info
        )
        return json.dumps(result.__dict__)
    except Exception as e:
        result = handle_oci_error(e, "get_server_info")
        return json.dumps(result.__dict__)

@app.tool()
async def list_compartments(limit: int = 50) -> str:
    """List available compartments with auto-discovery."""
    try:
        compartments = get_available_compartments(limit)
        formatted_compartments = format_for_llm(compartments, limit)
        
        result = OCIResponse(
            success=True,
            message=f"Found {len(formatted_compartments)} compartments",
            data=formatted_compartments,
            count=len(formatted_compartments),
            compartment_id=clients.root_compartment_id
        )
        return json.dumps(result.__dict__)
    except Exception as e:
        result = handle_oci_error(e, "list_compartments", "identity")
        return json.dumps(result.__dict__)

@app.tool()
async def list_compute_instances(
    compartment_id: str | None = None,
    availability_domain: str | None = None,
    display_name: str | None = None,
    lifecycle_state: str | None = None,
    limit: int = 50
) -> str:
    """List compute instances across all accessible compartments using official OCI SDK patterns."""
    try:
        compute_client = clients.compute
        all_instances = []
        
        # If specific compartment is requested, search only there
        if compartment_id is not None:
            if not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            compartments_to_search = [compartment_id]
        else:
            # Search across all accessible compartments
            try:
                all_compartments = get_available_compartments(100)  # Get up to 100 compartments
                compartments_to_search = [comp["id"] for comp in all_compartments]
                # Also include the root compartment
                compartments_to_search.append(clients.root_compartment_id)
                # Remove duplicates
                compartments_to_search = list(set(compartments_to_search))
            except Exception:
                # Fallback to root compartment only
                compartments_to_search = [clients.root_compartment_id]
        
        # Search each compartment
        for comp_id in compartments_to_search:
            try:
                response = compute_client.list_instances(
                    compartment_id=comp_id,
                    availability_domain=availability_domain,
                    display_name=display_name,
                    lifecycle_state=lifecycle_state,
                    limit=limit
                )
                
                for instance in response.data:
                    all_instances.append({
                        "id": instance.id,
                        "display_name": instance.display_name,
                        "lifecycle_state": instance.lifecycle_state,
                        "availability_domain": instance.availability_domain,
                        "shape": instance.shape,
                        "time_created": instance.time_created.isoformat() if instance.time_created else None,
                        "compartment_id": instance.compartment_id,
                        "region": instance.region
                    })
            except Exception as e:
                # Log the error but continue with other compartments
                print(f"Warning: Failed to search compartment {comp_id}: {str(e)}")
                continue
        
        # Remove duplicates based on instance ID
        seen_ids = set()
        unique_instances = []
        for instance in all_instances:
            if instance["id"] not in seen_ids:
                seen_ids.add(instance["id"])
                unique_instances.append(instance)
        
        formatted_instances = format_for_llm(unique_instances, limit)
        
        result = OCIResponse(
            success=True,
            message=f"Found {len(formatted_instances)} compute instances across {len(compartments_to_search)} compartments",
            data=formatted_instances,
            count=len(formatted_instances),
            compartment_id=compartment_id or "all_accessible"
        )
        return json.dumps(result.__dict__)
    except Exception as e:
        result = handle_oci_error(e, "list_compute_instances", "compute")
        return json.dumps(result.__dict__)

if ENABLE_LOGAN:
    @app.tool()
    async def list_log_analytics_sources(
        compartment_id: str | None = None,
        display_name: str | None = None,
        is_system: bool | None = None,
        limit: int = 50
    ) -> str:
    """List Log Analytics sources using official OCI SDK patterns."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        elif not validate_compartment_id(compartment_id):
            raise ValueError("Invalid compartment ID format")
        
        # Auto-discover namespace
        namespace = get_log_analytics_namespace()
        
        log_analytics_client = clients.log_analytics
        
        # Use official OCI SDK method pattern
        response = log_analytics_client.list_sources(
            namespace_name=namespace,
            compartment_id=compartment_id,
            display_name=display_name,
            is_system=is_system,
            limit=limit
        )
        
        sources = []
        for source in response.data.items:
            sources.append({
                "id": source.id,
                "display_name": source.display_name,
                "description": source.description,
                "is_system": source.is_system,
                "source_type": source.source_type,
                "time_created": source.time_created.isoformat() if source.time_created else None,
                "time_updated": source.time_updated.isoformat() if source.time_updated else None,
                "status": source.status
            })
        
        formatted_sources = format_for_llm(sources, limit)
        
        result = OCIResponse(
            success=True,
            message=f"Found {len(formatted_sources)} Log Analytics sources",
            data=formatted_sources,
            count=len(formatted_sources),
            compartment_id=compartment_id,
            namespace=namespace
        )
        return json.dumps(result.__dict__)
    except Exception as e:
        result = handle_oci_error(e, "list_log_analytics_sources", "log_analytics")
        return json.dumps(result.__dict__)

    @app.tool()
    async def list_log_analytics_groups(
        compartment_id: str | None = None,
        display_name: str | None = None,
        limit: int = 50
    ) -> str:
    """List Log Analytics log groups using official OCI SDK patterns."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        elif not validate_compartment_id(compartment_id):
            raise ValueError("Invalid compartment ID format")
        
        # Auto-discover namespace
        namespace = get_log_analytics_namespace()
        
        log_analytics_client = clients.log_analytics
        
        # Use official OCI SDK method pattern
        response = log_analytics_client.list_log_groups(
            namespace_name=namespace,
            compartment_id=compartment_id,
            display_name=display_name,
            limit=limit
        )
        
        groups = []
        for group in response.data.items:
            groups.append({
                "id": group.id,
                "display_name": group.display_name,
                "description": group.description,
                "compartment_id": group.compartment_id,
                "time_created": group.time_created.isoformat() if group.time_created else None,
                "time_updated": group.time_updated.isoformat() if group.time_updated else None,
                "lifecycle_state": group.lifecycle_state
            })
        
        formatted_groups = format_for_llm(groups, limit)
        
        result = OCIResponse(
            success=True,
            message=f"Found {len(formatted_groups)} Log Analytics log groups",
            data=formatted_groups,
            count=len(formatted_groups),
            compartment_id=compartment_id,
            namespace=namespace
        )
        return json.dumps(result.__dict__)
    except Exception as e:
        result = handle_oci_error(e, "list_log_analytics_groups", "log_analytics")
        return json.dumps(result.__dict__)

    @app.tool()
    async def list_log_analytics_entities(
        compartment_id: str | None = None,
        display_name: str | None = None,
        entity_type: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 50
    ) -> str:
    """List Log Analytics entities using official OCI SDK patterns."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        elif not validate_compartment_id(compartment_id):
            raise ValueError("Invalid compartment ID format")
        
        # Auto-discover namespace
        namespace = get_log_analytics_namespace()
        
        log_analytics_client = clients.log_analytics
        
        # Use official OCI SDK method pattern
        response = log_analytics_client.list_log_analytics_entities(
            namespace_name=namespace,
            compartment_id=compartment_id,
            display_name=display_name,
            entity_type=entity_type,
            lifecycle_state=lifecycle_state,
            limit=limit
        )
        
        entities = []
        for entity in response.data.items:
            entities.append({
                "id": entity.id,
                "display_name": entity.display_name,
                "entity_type_name": entity.entity_type_name,
                "compartment_id": entity.compartment_id,
                "lifecycle_state": entity.lifecycle_state,
                "time_created": entity.time_created.isoformat() if entity.time_created else None,
                "time_updated": entity.time_updated.isoformat() if entity.time_updated else None,
                "hostname": entity.hostname
            })
        
        formatted_entities = format_for_llm(entities, limit)
        
        result = OCIResponse(
            success=True,
            message=f"Found {len(formatted_entities)} Log Analytics entities",
            data=formatted_entities,
            count=len(formatted_entities),
            compartment_id=compartment_id,
            namespace=namespace
        )
        return json.dumps(result.__dict__)
    except Exception as e:
        result = handle_oci_error(e, "list_log_analytics_entities", "log_analytics")
        return json.dumps(result.__dict__)

@app.tool()
async def get_compartment_guidance() -> str:
    """Get helpful guidance for compartment selection."""
    try:
        compartments = get_available_compartments(20)  # Get first 20 compartments
        guidance = {
            "message": "Here are your available compartments. Use any of these compartment IDs:",
            "compartments": format_for_llm(compartments, 20),
            "count": len(compartments),
            "note": f"You can use the root tenancy compartment ID as well: {clients.root_compartment_id}",
            "usage_tip": "If no compartment is specified, the root tenancy will be used automatically"
        }
        
        result = OCIResponse(
            success=True,
            message="Compartment guidance provided successfully",
            data=guidance,
            count=len(compartments),
            compartment_id=clients.root_compartment_id
        )
        return json.dumps(result.__dict__)
    except Exception as e:
        result = handle_oci_error(e, "get_compartment_guidance", "identity")
        return json.dumps(result.__dict__)

# ================================ MCP COMPATIBILITY ================================

def register_tools() -> list[dict[str, Any]]:
    """Register tools for MCP compatibility."""
    # This is a placeholder function for MCP compatibility
    # The actual tools are registered via @app.tool() decorators
    return []

# ================================ MAIN EXECUTION ================================

if __name__ == "__main__":
    app.run()
