"""
Optimized Database service using direct REST API calls
Minimal token usage, based on Oracle Postman collection patterns
"""

from typing import Any

from .client import create_client
from .formatters import format_database, format_error, format_response, format_success


def list_databases(compartment_id: str, limit: int | None = None,
                   page: str | None = None, profile: str = "DEFAULT", 
                   region: str = None) -> dict[str, Any]:
    """List databases using REST API - optimized for minimal tokens"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Build query parameters
        params = {"compartmentId": compartment_id}
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page
            
        # Make REST API call
        response = client.get("/20160918/databases", params=params)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract databases
        databases = response.get("data", [])
        
        # Format response
        return format_response(
            databases, 
            format_database, 
            limit=limit,
            next_page=response.get("opc_next_page")
        )
        
    except Exception as e:
        return format_error(e)


def get_database(database_id: str, profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """Get specific database using REST API"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Make REST API call
        response = client.get(f"/20160918/databases/{database_id}")
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Database not found')}"))
        
        # Format single database
        database = response.get("data", {})
        return format_success(format_database(database))
        
    except Exception as e:
        return format_error(e)


def list_db_systems(compartment_id: str, limit: int | None = None,
                    page: str | None = None, profile: str = "DEFAULT", 
                    region: str = None) -> dict[str, Any]:
    """List DB systems using REST API - optimized for minimal tokens"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Build query parameters
        params = {"compartmentId": compartment_id}
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page
            
        # Make REST API call
        response = client.get("/20160918/dbSystems", params=params)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract DB systems
        db_systems = response.get("data", [])
        
        # Format DB systems with minimal fields
        formatted_systems = [{
            "id": system.get("id"),
            "display_name": system.get("display_name"),
            "lifecycle_state": system.get("lifecycle_state"),
            "shape": system.get("shape"),
            "cpu_core_count": system.get("cpu_core_count"),
            "time_created": system.get("time_created"),
            "compartment_id": system.get("compartment_id")
        } for system in db_systems]
        
        # Format response
        return format_response(
            formatted_systems, 
            lambda x: x,  # Already formatted
            limit=limit,
            next_page=response.get("opc_next_page")
        )
        
    except Exception as e:
        return format_error(e)


def get_db_system(db_system_id: str, profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """Get specific DB system using REST API"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Make REST API call
        response = client.get(f"/20160918/dbSystems/{db_system_id}")
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'DB system not found')}"))
        
        # Format single DB system
        db_system = response.get("data", {})
        formatted_system = {
            "id": db_system.get("id"),
            "display_name": db_system.get("display_name"),
            "lifecycle_state": db_system.get("lifecycle_state"),
            "shape": db_system.get("shape"),
            "cpu_core_count": db_system.get("cpu_core_count"),
            "time_created": db_system.get("time_created"),
            "compartment_id": db_system.get("compartment_id")
        }
        
        return format_success(formatted_system)
        
    except Exception as e:
        return format_error(e)


def list_autonomous_databases(compartment_id: str, limit: int | None = None,
                             page: str | None = None, profile: str = "DEFAULT", 
                             region: str = None) -> dict[str, Any]:
    """List Autonomous databases using REST API - optimized for minimal tokens"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Build query parameters
        params = {"compartmentId": compartment_id}
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page
            
        # Make REST API call
        response = client.get("/20160918/autonomousDatabases", params=params)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract Autonomous databases
        adbs = response.get("data", [])
        
        # Format Autonomous databases with minimal fields
        formatted_adbs = [{
            "id": adb.get("id"),
            "display_name": adb.get("display_name"),
            "lifecycle_state": adb.get("lifecycle_state"),
            "db_name": adb.get("db_name"),
            "cpu_core_count": adb.get("cpu_core_count"),
            "data_storage_size_in_tbs": adb.get("data_storage_size_in_tbs"),
            "time_created": adb.get("time_created"),
            "compartment_id": adb.get("compartment_id")
        } for adb in adbs]
        
        # Format response
        return format_response(
            formatted_adbs, 
            lambda x: x,  # Already formatted
            limit=limit,
            next_page=response.get("opc_next_page")
        )
        
    except Exception as e:
        return format_error(e)


def get_autonomous_database(adb_id: str, profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """Get specific Autonomous database using REST API"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Make REST API call
        response = client.get(f"/20160918/autonomousDatabases/{adb_id}")
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Autonomous database not found')}"))
        
        # Format single Autonomous database
        adb = response.get("data", {})
        formatted_adb = {
            "id": adb.get("id"),
            "display_name": adb.get("display_name"),
            "lifecycle_state": adb.get("lifecycle_state"),
            "db_name": adb.get("db_name"),
            "cpu_core_count": adb.get("cpu_core_count"),
            "data_storage_size_in_tbs": adb.get("data_storage_size_in_tbs"),
            "time_created": adb.get("time_created"),
            "compartment_id": adb.get("compartment_id")
        }
        
        return format_success(formatted_adb)
        
    except Exception as e:
        return format_error(e)


def get_server_info() -> dict[str, Any]:
    """Get server information"""
    return {
        "name": "oci-database-rest",
        "version": "1.0.0",
        "type": "REST API",
        "optimized": True,
        "token_usage": "minimal"
    }
