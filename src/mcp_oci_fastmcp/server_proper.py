#!/usr/bin/env python3
"""
Proper FastMCP Server Implementation
Following the patterns from oci-mcp-core-server, oci-mcp-security-services, and oci-mcp-logan-server

Key Features:
- Uses root tenancy as default compartment
- Auto-discovers compartments from config
- Asks for compartment only when really needed by SDK
- Proper OCI config file handling
- Clear, Claude-friendly responses
- Comprehensive error handling
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

SERVER_NAME = "oci-proper"
app = FastMCP(SERVER_NAME)

# Performance settings
MAX_ITEMS = 1000
MAX_STRING = 10000
MAX_DEPTH = 10
CACHE_TTL = 300  # 5 minutes

# ================================ CACHING ================================

@dataclass
class CacheEntry:
    data: Any
    timestamp: float
    ttl: float

class ResponseCache:
    def __init__(self, default_ttl: float = CACHE_TTL):
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if time.time() - entry.timestamp > entry.ttl:
            del self.cache[key]
            return None
        
        return entry.data
    
    def set(self, key: str, data: Any, ttl: Optional[float] = None) -> None:
        self.cache[key] = CacheEntry(
            data=data,
            timestamp=time.time(),
            ttl=ttl or self.default_ttl
        )
    
    def clear(self) -> None:
        self.cache.clear()

# Global cache instance
cache = ResponseCache()

# ================================ ERROR HANDLING ================================

class OCIError(Exception):
    """Base OCI error with enhanced context."""
    def __init__(self, message: str, error_code: str = None, service: str = None, operation: str = None):
        super().__init__(message)
        self.error_code = error_code
        self.service = service
        self.operation = operation
        self.timestamp = datetime.now().isoformat()

def handle_oci_error(error: Exception, operation: str, service: str = None) -> OCIError:
    """Convert OCI exceptions to our custom error types."""
    if isinstance(error, ServiceError):
        return OCIError(
            f"OCI error: {error.message}",
            error_code=str(error.code),
            service=service,
            operation=operation
        )
    elif isinstance(error, (ConfigFileNotFound, InvalidConfig)):
        return OCIError(
            f"Configuration error: {str(error)}",
            service=service,
            operation=operation
        )
    else:
        return OCIError(
            f"Unexpected error: {str(error)}",
            service=service,
            operation=operation
        )

# ================================ UTILITY FUNCTIONS ================================

def _shrink_for_context(data: Any, max_items: int = MAX_ITEMS, max_string: int = MAX_STRING, max_depth: int = MAX_DEPTH, current_depth: int = 0) -> tuple[Any, bool]:
    """Shrink data for MCP context limits."""
    if current_depth > max_depth:
        return "[Max depth reached]", True
    
    if isinstance(data, str):
        if len(data) > max_string:
            return data[:max_string] + "...", True
        return data, False
    
    if isinstance(data, list):
        if len(data) > max_items:
            return data[:max_items] + [f"... and {len(data) - max_items} more items"], True
        return [_shrink_for_context(item, max_items, max_string, max_depth, current_depth + 1)[0] for item in data], False
    
    if isinstance(data, dict):
        if len(data) > max_items:
            items = list(data.items())[:max_items]
            result = {k: _shrink_for_context(v, max_items, max_string, max_depth, current_depth + 1)[0] for k, v in items}
            result["..."] = f"and {len(data) - max_items} more keys"
            return result, True
        return {k: _shrink_for_context(v, max_items, max_string, max_depth, current_depth + 1)[0] for k, v in data.items()}, False
    
    return data, False

def _ok(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create success response with context shrinking."""
    payload.setdefault("success", True)
    payload.setdefault("timestamp", datetime.now().isoformat())
    shrunk, truncated = _shrink_for_context(payload)
    if isinstance(shrunk, dict) and truncated:
        shrunk.setdefault("_truncated", True)
        shrunk.setdefault("_truncation_limits", {"max_items": MAX_ITEMS, "max_string": MAX_STRING, "max_depth": MAX_DEPTH})
    return shrunk

def _err(error: Exception, operation: str, service: str = None) -> Dict[str, Any]:
    """Create error response with enhanced context."""
    return {
        "success": False,
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "operation": operation,
        "service": service,
        "timestamp": datetime.now().isoformat(),
    }

# ================================ CONFIGURATION MANAGEMENT ================================

def _load_local_env() -> None:
    """Load local .env file for configuration defaults."""
    try:
        env_path = Path(__file__).resolve().parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if "=" in s:
                    k, v = s.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        pass

_load_local_env()

# ================================ CLIENT MANAGEMENT ================================

class OptimizedClients:
    """Optimized OCI client manager with lazy loading and connection pooling."""
    
    def __init__(self) -> None:
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
            self.config  # This will populate _tenancy_id
        return self._tenancy_id
    
    @property
    def root_compartment_id(self) -> str:
        """Get the root compartment ID (same as tenancy)."""
        if self._root_compartment_id is None:
            self.config  # This will populate _root_compartment_id
        return self._root_compartment_id
    
    def _get_client(self, client_type: str, client_class):
        """Get or create OCI client with error handling."""
        if client_type not in self._clients:
            try:
                self._clients[client_type] = client_class(self.config)
            except Exception as e:
                raise handle_oci_error(e, f"create_{client_type}_client", client_type)
        
        return self._clients[client_type]
    
    @property
    def compute(self):
        return self._get_client("compute", oci.core.ComputeClient)
    
    @property
    def identity(self):
        return self._get_client("identity", oci.identity.IdentityClient)
    
    @property
    def log_analytics(self):
        return self._get_client("log_analytics", oci.log_analytics.LogAnalyticsClient)
    
    @property
    def object_storage(self):
        return self._get_client("object_storage", oci.object_storage.ObjectStorageClient)
    
    @property
    def virtual_network(self):
        return self._get_client("vcn", oci.core.VirtualNetworkClient)

# Global client instance
clients = OptimizedClients()

def get_clients() -> OptimizedClients:
    """Get the global clients instance."""
    return clients

# ================================ COMPARTMENT DISCOVERY ================================

def get_available_compartments(limit: int = 100) -> List[Dict[str, Any]]:
    """Get available compartments starting from root tenancy."""
    try:
        identity_client = clients.identity
        root_compartment_id = clients.root_compartment_id
        
        # List compartments from root
        response = identity_client.list_compartments(
            compartment_id=root_compartment_id,
            limit=limit,
            access_level="ACCESSIBLE"
        )
        compartments = []
        
        for comp in response.data:
            compartments.append({
                "id": comp.id,
                "name": comp.name,
                "description": comp.description,
                "lifecycle_state": comp.lifecycle_state,
                "time_created": comp.time_created.isoformat() if comp.time_created else None,
                "compartment_id": comp.compartment_id
            })
        
        return compartments
    except Exception as e:
        raise handle_oci_error(e, "get_available_compartments", "identity")

def validate_compartment_id(compartment_id: str) -> bool:
    """Validate compartment ID format."""
    return compartment_id and (compartment_id.startswith("ocid1.compartment.") or compartment_id.startswith("ocid1.tenancy."))

def _get_compartment_guidance() -> Dict[str, Any]:
    """Get helpful guidance for compartment selection."""
    try:
        compartments = get_available_compartments(20)  # Get first 20 compartments
        return {
            "message": "Here are your available compartments. Use any of these compartment IDs:",
            "compartments": compartments,
            "count": len(compartments),
            "note": "You can use the root tenancy compartment ID as well: " + clients.root_compartment_id,
            "suggestion": "If you don't see the compartment you need, try increasing the limit or check your permissions."
        }
    except Exception as e:
        return {
            "error": f"Failed to list compartments: {str(e)}",
            "fallback": f"You can use the root tenancy compartment ID: {clients.root_compartment_id}",
            "suggestion": "Make sure your OCI configuration is correct and you have the necessary permissions."
        }

# ================================ CORE TOOLS ================================

@app.tool()
async def test_connection() -> str:
    """Test OCI connection and return configuration status."""
    try:
        config = clients.config
        result = _ok({
            "message": "OCI connection successful",
            "region": config.get("region", "unknown"),
            "tenancy": config.get("tenancy", "unknown"),
            "user": config.get("user", "unknown"),
            "fingerprint": config.get("fingerprint", "unknown")[:8] + "...",
            "config_file": os.getenv("OCI_CONFIG_FILE", OCI_CFG_DEFAULT),
            "profile": os.getenv("OCI_PROFILE", "DEFAULT"),
            "root_compartment_id": clients.root_compartment_id,
        })
        return json.dumps(result)
    except Exception as e:
        return json.dumps(_err(handle_oci_error(e, "test_connection"), "test_connection"))

@app.tool()
async def get_server_info() -> str:
    """Get server information and status."""
    try:
        result = _ok({
            "server_name": SERVER_NAME,
            "version": "1.0.0-proper",
            "features": [
                "root_tenancy_default",
                "compartment_auto_discovery", 
                "claude_friendly_responses",
                "comprehensive_error_handling",
                "proper_oci_config_handling",
                "caching_and_performance"
            ],
            "max_items": MAX_ITEMS,
            "max_string": MAX_STRING,
            "max_depth": MAX_DEPTH,
            "cache_ttl": CACHE_TTL,
            "root_compartment_id": clients.root_compartment_id,
        })
        return json.dumps(result)
    except Exception as e:
        return json.dumps(_err(handle_oci_error(e, "get_server_info"), "get_server_info"))

@app.tool()
async def list_compartments(limit: int = 100) -> str:
    """List available compartments in your tenancy."""
    try:
        # Input validation
        if limit < 1 or limit > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        
        # Check cache
        cache_key = f"compartments:{limit}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return json.dumps(cached_result)
        
        compartments = get_available_compartments(limit)
        
        result = _ok({
            "compartments": compartments,
            "count": len(compartments),
            "root_compartment_id": clients.root_compartment_id,
            "message": f"Found {len(compartments)} accessible compartments. Use any of these compartment IDs in other operations."
        })
        
        # Cache result
        cache.set(cache_key, result, 600)  # Cache for 10 minutes
        return json.dumps(result)
    except Exception as e:
        return json.dumps(_err(handle_oci_error(e, "list_compartments", "identity"), "list_compartments"))

@app.tool()
async def get_compartment_guidance() -> str:
    """Get helpful guidance for selecting compartments."""
    try:
        guidance = _get_compartment_guidance()
        result = _ok(guidance)
        return json.dumps(result)
    except Exception as e:
        return json.dumps(_err(handle_oci_error(e, "get_compartment_guidance", "identity"), "get_compartment_guidance"))

# ================================ COMPUTE TOOLS ================================

@app.tool()
async def list_compute_instances(compartment_id: str = None, limit: int = 100) -> str:
    """List compute instances. Uses root tenancy if compartment_id not provided."""
    try:
        # Use root compartment if not provided
        if not compartment_id:
            compartment_id = clients.root_compartment_id
            message_suffix = f" (using root tenancy: {compartment_id})"
        else:
            if not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format. Must start with 'ocid1.compartment.'")
            message_suffix = f" in compartment {compartment_id}"
        
        # Input validation
        if limit < 1 or limit > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        
        # Check cache
        cache_key = f"compute_instances:{compartment_id}:{limit}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return json.dumps(cached_result)
        
        client = clients.compute
        request = oci.core.models.ListInstancesRequest(
            compartment_id=compartment_id,
            limit=limit
        )
        
        response = client.list_instances(request)
        instances = response.data
        
        result = _ok({
            "instances": [
                {
                    "id": inst.id,
                    "display_name": inst.display_name,
                    "lifecycle_state": inst.lifecycle_state,
                    "availability_domain": inst.availability_domain,
                    "shape": inst.shape,
                    "time_created": inst.time_created.isoformat() if inst.time_created else None,
                    "compartment_id": inst.compartment_id,
                }
                for inst in instances
            ],
            "count": len(instances),
            "compartment_id": compartment_id,
            "message": f"Found {len(instances)} compute instances{message_suffix}"
        })
        
        # Cache result
        cache.set(cache_key, result, 300)  # Cache for 5 minutes
        return json.dumps(result)
    except Exception as e:
        return json.dumps(_err(handle_oci_error(e, "list_compute_instances", "compute"), "list_compute_instances"))

# ================================ LOG ANALYTICS TOOLS ================================

@app.tool()
async def get_log_analytics_namespace() -> str:
    """Get Log Analytics namespace for your tenancy."""
    try:
        # Check cache
        cache_key = "log_analytics_namespace"
        cached_result = cache.get(cache_key)
        if cached_result:
            return json.dumps(cached_result)
        
        client = clients.log_analytics
        namespace_response = client.list_namespaces()
        # Get the first namespace (there should be only one per tenancy)
        if namespace_response.data and len(namespace_response.data) > 0:
            namespace = namespace_response.data[0].namespace_name
        else:
            raise RuntimeError("No Log Analytics namespace found for this tenancy")
        
        result = _ok({
            "namespace": namespace,
            "message": f"Log Analytics namespace: {namespace}",
            "note": "Use this namespace for Log Analytics operations"
        })
        
        # Cache result
        cache.set(cache_key, result, 1800)  # Cache for 30 minutes
        return json.dumps(result)
    except Exception as e:
        return json.dumps(_err(handle_oci_error(e, "get_log_analytics_namespace", "log_analytics"), "get_log_analytics_namespace"))

@app.tool()
async def list_log_analytics_entities(compartment_id: str = None, limit: int = 100) -> str:
    """List Log Analytics entities. Uses root tenancy if compartment_id not provided."""
    try:
        # Use root compartment if not provided
        if not compartment_id:
            compartment_id = clients.root_compartment_id
            message_suffix = f" (using root tenancy: {compartment_id})"
        else:
            if not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format. Must start with 'ocid1.compartment.'")
            message_suffix = f" in compartment {compartment_id}"
        
        # Get namespace first
        namespace_response = clients.log_analytics.list_namespaces(compartment_id=clients.tenancy_id)
        # Get the first namespace (there should be only one per tenancy)
        if namespace_response.data and namespace_response.data.items:
            namespace = namespace_response.data.items[0].namespace_name
        else:
            raise RuntimeError("No Log Analytics namespace found for this tenancy")
        
        # Input validation
        if limit < 1 or limit > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        
        # Check cache
        cache_key = f"log_analytics_entities:{compartment_id}:{limit}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return json.dumps(cached_result)
        
        client = clients.log_analytics
        request = oci.log_analytics.models.ListLogAnalyticsEntitiesRequest(
            namespace_name=namespace,
            compartment_id=compartment_id,
            limit=limit
        )
        
        response = client.list_log_analytics_entities(request)
        entities = response.data
        
        result = _ok({
            "entities": [
                {
                    "id": entity.id,
                    "name": entity.name,
                    "entity_type_name": entity.entity_type_name,
                    "lifecycle_state": entity.lifecycle_state,
                    "time_created": entity.time_created.isoformat() if entity.time_created else None,
                    "compartment_id": entity.compartment_id,
                }
                for entity in entities
            ],
            "count": len(entities),
            "compartment_id": compartment_id,
            "namespace": namespace,
            "message": f"Found {len(entities)} Log Analytics entities{message_suffix}"
        })
        
        # Cache result
        cache.set(cache_key, result, 300)  # Cache for 5 minutes
        return json.dumps(result)
    except Exception as e:
        return json.dumps(_err(handle_oci_error(e, "list_log_analytics_entities", "log_analytics"), "list_log_analytics_entities"))

# ================================ UTILITY TOOLS ================================

@app.tool()
async def clear_cache() -> str:
    """Clear the response cache."""
    try:
        cache.clear()
        result = _ok({"message": "Cache cleared successfully"})
        return json.dumps(result)
    except Exception as e:
        return json.dumps(_err(handle_oci_error(e, "clear_cache"), "clear_cache"))

@app.tool()
async def get_cache_stats() -> str:
    """Get cache statistics."""
    try:
        result = _ok({
            "cache_size": len(cache.cache),
            "max_items": MAX_ITEMS,
            "max_string": MAX_STRING,
            "max_depth": MAX_DEPTH,
            "cache_ttl": CACHE_TTL,
        })
        return json.dumps(result)
    except Exception as e:
        return json.dumps(_err(handle_oci_error(e, "get_cache_stats"), "get_cache_stats"))

# ================================ MAIN EXECUTION ================================

if __name__ == "__main__":
    app.run()
