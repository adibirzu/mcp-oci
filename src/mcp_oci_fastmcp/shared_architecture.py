#!/usr/bin/env python3
"""
Shared Architecture Components for MCP-OCI Servers
Based on official OCI Python SDK patterns and optimized for FastMCP and LLM consumption

This module provides shared components that all MCP-OCI servers can use:
- OCIClientManager: Manages OCI clients with caching and error handling
- OCIResponse: Standardized response format for LLM consumption
- Utility functions: Common functions for all servers
- Error handling: Comprehensive error management
"""

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# OCI SDK
try:
    import oci
    from oci.config import DEFAULT_LOCATION as OCI_CFG_DEFAULT
    from oci.config import from_file as oci_from_file
    from oci.exceptions import ConfigFileNotFound, InvalidConfig, ServiceError
except ImportError:
    raise SystemExit("OCI Python SDK not installed. Install with: pip install oci")

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
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "count": self.count,
            "compartment_id": self.compartment_id,
            "namespace": self.namespace,
            "timestamp": self.timestamp
        }

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
                elif service_name == "monitoring":
                    self._clients[service_name] = oci.monitoring.MonitoringClient(config)
                elif service_name == "usage_api":
                    self._clients[service_name] = oci.usage_api.UsageapiClient(config)
                elif service_name == "block_storage":
                    self._clients[service_name] = oci.core.BlockstorageClient(config)
                elif service_name == "container_engine":
                    self._clients[service_name] = oci.container_engine.ContainerEngineClient(config)
                elif service_name == "functions":
                    self._clients[service_name] = oci.functions.FunctionsManagementClient(config)
                elif service_name == "vault":
                    self._clients[service_name] = oci.vault.VaultsClient(config)
                elif service_name == "load_balancer":
                    self._clients[service_name] = oci.load_balancer.LoadBalancerClient(config)
                elif service_name == "dns":
                    self._clients[service_name] = oci.dns.DnsClient(config)
                elif service_name == "kms":
                    self._clients[service_name] = oci.key_management.KmsVaultClient(config)
                elif service_name == "events":
                    self._clients[service_name] = oci.events.EventsClient(config)
                elif service_name == "streaming":
                    self._clients[service_name] = oci.streaming.StreamAdminClient(config)
                else:
                    raise ValueError(f"Unknown service: {service_name}")
            except Exception as e:
                raise handle_oci_error(e, f"client_creation_{service_name}")
        
        return self._clients[service_name]
    
    # Property accessors for common services
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
    
    @property
    def monitoring(self):
        return self.get_client("monitoring")
    
    @property
    def usage_api(self):
        return self.get_client("usage_api")
    
    @property
    def block_storage(self):
        return self.get_client("block_storage")
    
    @property
    def container_engine(self):
        return self.get_client("container_engine")
    
    @property
    def functions(self):
        return self.get_client("functions")
    
    @property
    def vault(self):
        return self.get_client("vault")
    
    @property
    def load_balancer(self):
        return self.get_client("load_balancer")
    
    @property
    def dns(self):
        return self.get_client("dns")
    
    @property
    def kms(self):
        return self.get_client("kms")
    
    @property
    def events(self):
        return self.get_client("events")
    
    @property
    def streaming(self):
        return self.get_client("streaming")

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

def format_for_llm(data: Any, max_items: int = 1000) -> Any:
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
                              'compartment_id', 'availability_domain', 'shape', 'region', 'namespace',
                              'description', 'status', 'type', 'hostname', 'entity_type_name']:
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
                      'compartment_id', 'availability_domain', 'shape', 'region', 'namespace',
                      'description', 'status', 'type', 'hostname', 'entity_type_name']:
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

def create_fastmcp_tool(app, tool_name: str, tool_func, description: str = ""):
    """Create a FastMCP tool with standardized error handling and response formatting."""
    
    @app.tool()
    async def tool_wrapper(*args, **kwargs):
        """Wrapper function with error handling and response formatting."""
        try:
            result = tool_func(*args, **kwargs)
            
            # If result is already an OCIResponse, convert to dict
            if isinstance(result, OCIResponse):
                return json.dumps(result.to_dict())
            
            # If result is a dict, wrap it in OCIResponse
            if isinstance(result, dict):
                response = OCIResponse(
                    success=True,
                    message=f"{tool_name} completed successfully",
                    data=result,
                    count=len(result) if isinstance(result, list) else None
                )
                return json.dumps(response.to_dict())
            
            # For other types, wrap in OCIResponse
            response = OCIResponse(
                success=True,
                message=f"{tool_name} completed successfully",
                data=result
            )
            return json.dumps(response.to_dict())
            
        except Exception as e:
            error_response = handle_oci_error(e, tool_name)
            return json.dumps(error_response.to_dict())
    
    # Set the function name and docstring
    tool_wrapper.__name__ = tool_name
    tool_wrapper.__doc__ = description or f"Execute {tool_name}"
    
    return tool_wrapper

# ================================ COMMON TOOLS ================================

def create_common_tools(app, server_name: str):
    """Create common tools that all servers should have."""
    
    @app.tool()
    async def get_server_info() -> str:
        """Get server information and capabilities."""
        try:
            info = {
                "name": server_name,
                "version": "2.0.0",
                "framework": "fastmcp",
                "oci_sdk_version": oci.__version__,
                "capabilities": [
                    "auto_discovery",
                    "token_optimized", 
                    "claude_friendly",
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
            return json.dumps(result.to_dict())
        except Exception as e:
            result = handle_oci_error(e, "get_server_info")
            return json.dumps(result.to_dict())
    
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
            return json.dumps(result.to_dict())
        except Exception as e:
            result = handle_oci_error(e, "list_compartments", "identity")
            return json.dumps(result.to_dict())
    
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
            return json.dumps(result.to_dict())
        except Exception as e:
            result = handle_oci_error(e, "get_compartment_guidance", "identity")
            return json.dumps(result.to_dict())

# ================================ UTILITY FUNCTIONS ================================

def get_all_compartments_recursive(identity_client, root_compartment_id: str, visited=None):
    """
    Recursively discover ALL compartments including sub-compartments.
    This ensures we find instances in nested compartments that may not be returned 
    by standard list_compartments calls.
    """
    if visited is None:
        visited = set()
    
    if root_compartment_id in visited:
        return []  # Avoid infinite loops
    
    visited.add(root_compartment_id)
    all_compartments = []
    
    try:
        # Get direct sub-compartments
        response = identity_client.list_compartments(
            compartment_id=root_compartment_id,
            access_level='ACCESSIBLE',
            limit=100
        )
        
        direct_compartments = response.data
        all_compartments.extend(direct_compartments)
        
        # Recursively get sub-compartments of each compartment
        for comp in direct_compartments:
            try:
                sub_compartments = get_all_compartments_recursive(
                    identity_client, comp.id, visited
                )
                all_compartments.extend(sub_compartments)
            except Exception:
                # Skip compartments that cause errors (e.g., permission issues)
                continue
                
    except Exception:
        # If we can't list compartments, return empty list
        pass
    
    return all_compartments
