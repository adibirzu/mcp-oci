"""
Optimized Object Storage service using direct REST API calls
Minimal token usage, based on Oracle Postman collection patterns
"""

from typing import Any

from .client import create_client
from .formatters import format_bucket, format_error, format_response, format_success


def list_buckets(namespace: str, compartment_id: str, limit: int | None = None,
                 page: str | None = None, profile: str = "DEFAULT", 
                 region: str = None) -> dict[str, Any]:
    """List object storage buckets using REST API - optimized for minimal tokens"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Build query parameters
        params = {
            "namespaceName": namespace,
            "compartmentId": compartment_id
        }
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page
            
        # Make REST API call
        response = client.get("/n/{namespace}/b", params=params)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract buckets
        buckets = response.get("data", [])
        
        # Format response
        return format_response(
            buckets, 
            format_bucket, 
            limit=limit,
            next_page=response.get("opc_next_page")
        )
        
    except Exception as e:
        return format_error(e)


def get_bucket(namespace: str, bucket_name: str, profile: str = "DEFAULT", 
               region: str = None) -> dict[str, Any]:
    """Get specific bucket using REST API"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Make REST API call
        response = client.get(f"/n/{namespace}/b/{bucket_name}")
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Bucket not found')}"))
        
        # Format single bucket
        bucket = response.get("data", {})
        return format_success(format_bucket(bucket))
        
    except Exception as e:
        return format_error(e)


def list_objects(namespace: str, bucket_name: str, prefix: str | None = None,
                 limit: int | None = None, page: str | None = None,
                 profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """List objects in bucket using REST API - optimized for minimal tokens"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Build query parameters
        params = {}
        if prefix:
            params["prefix"] = prefix
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page
            
        # Make REST API call
        response = client.get(f"/n/{namespace}/b/{bucket_name}/o", params=params)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract objects
        objects = response.get("data", [])
        
        # Format objects with minimal fields
        formatted_objects = [{
            "name": obj.get("name"),
            "size": obj.get("size"),
            "etag": obj.get("etag"),
            "time_created": obj.get("time_created"),
            "md5": obj.get("md5")
        } for obj in objects]
        
        # Format response
        return format_response(
            formatted_objects, 
            lambda x: x,  # Already formatted
            limit=limit,
            next_page=response.get("opc_next_page")
        )
        
    except Exception as e:
        return format_error(e)


def get_object(namespace: str, bucket_name: str, object_name: str,
               profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """Get object metadata using REST API"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Make REST API call
        response = client.get(f"/n/{namespace}/b/{bucket_name}/o/{object_name}")
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Object not found')}"))
        
        # Format object metadata
        obj = response.get("data", {})
        formatted_obj = {
            "name": obj.get("name"),
            "size": obj.get("size"),
            "etag": obj.get("etag"),
            "time_created": obj.get("time_created"),
            "md5": obj.get("md5"),
            "content_type": obj.get("content_type")
        }
        
        return format_success(formatted_obj)
        
    except Exception as e:
        return format_error(e)


def get_namespace(profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """Get object storage namespace using REST API"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Make REST API call
        response = client.get("/n/")
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract namespace
        namespace = response.get("data", {}).get("value")
        
        return format_success({"namespace": namespace})
        
    except Exception as e:
        return format_error(e)


def get_server_info() -> dict[str, Any]:
    """Get server information"""
    return {
        "name": "oci-objectstorage-rest",
        "version": "1.0.0",
        "type": "REST API",
        "optimized": True,
        "token_usage": "minimal"
    }
