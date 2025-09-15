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
- Claude-friendly response format
"""

import os
import sys
import json
import time
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from functools import wraps, lru_cache
from dataclasses import dataclass

# OCI SDK
try:
    import oci
    from oci.config import from_file as oci_from_file, DEFAULT_LOCATION as OCI_CFG_DEFAULT
    from oci.exceptions import ServiceError, ConfigFileNotFound, InvalidConfig
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

# ================================ CORE CLASSES ================================

@dataclass
class OCIResponse:
    """Standardized OCI response format for LLM consumption."""
    success: bool
    message: str
    data: Any
    count: Optional[int] = None
    compartment_id: Optional[str] = None
    namespace: Optional[str] = None
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

def get_available_compartments(limit: int = 50) -> List[Dict[str, Any]]:
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
    compartment_id: Optional[str] = None,
    availability_domain: Optional[str] = None,
    display_name: Optional[str] = None,
    lifecycle_state: Optional[str] = None,
    limit: int = 50
) -> str:
    """List compute instances using official OCI SDK patterns."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        else:
            if not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
        
        compute_client = clients.compute
        
        # Use official OCI SDK method pattern
        response = compute_client.list_instances(
            compartment_id=compartment_id,
            availability_domain=availability_domain,
            display_name=display_name,
            lifecycle_state=lifecycle_state,
            limit=limit
        )
        
        instances = []
        for instance in response.data:
            instances.append({
                "id": instance.id,
                "display_name": instance.display_name,
                "lifecycle_state": instance.lifecycle_state,
                "availability_domain": instance.availability_domain,
                "shape": instance.shape,
                "time_created": instance.time_created.isoformat() if instance.time_created else None,
                "compartment_id": instance.compartment_id,
                "region": instance.region
            })
        
        formatted_instances = format_for_llm(instances, limit)
        
        result = OCIResponse(
            success=True,
            message=f"Found {len(formatted_instances)} compute instances",
            data=formatted_instances,
            count=len(formatted_instances),
            compartment_id=compartment_id
        )
        return json.dumps(result.__dict__)
    except Exception as e:
        result = handle_oci_error(e, "list_compute_instances", "compute")
        return json.dumps(result.__dict__)

@app.tool()
async def list_log_analytics_sources(
    compartment_id: Optional[str] = None,
    display_name: Optional[str] = None,
    is_system: Optional[bool] = None,
    limit: int = 50
) -> str:
    """List Log Analytics sources using official OCI SDK patterns."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        else:
            if not validate_compartment_id(compartment_id):
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
    compartment_id: Optional[str] = None,
    display_name: Optional[str] = None,
    limit: int = 50
) -> str:
    """List Log Analytics log groups using official OCI SDK patterns."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        else:
            if not validate_compartment_id(compartment_id):
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
    compartment_id: Optional[str] = None,
    display_name: Optional[str] = None,
    entity_type: Optional[str] = None,
    lifecycle_state: Optional[str] = None,
    limit: int = 50
) -> str:
    """List Log Analytics entities using official OCI SDK patterns."""
    try:
        # Use root compartment if not specified
        if compartment_id is None:
            compartment_id = clients.root_compartment_id
        else:
            if not validate_compartment_id(compartment_id):
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

# ================================ MAIN EXECUTION ================================

if __name__ == "__main__":
    app.run()
