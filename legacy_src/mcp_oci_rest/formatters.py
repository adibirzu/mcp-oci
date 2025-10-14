"""
Optimized response formatters for minimal token usage
"""

from typing import Any


def format_instance(instance: dict[str, Any]) -> dict[str, Any]:
    """Format compute instance with only essential fields"""
    return {
        "id": instance.get("id"),
        "display_name": instance.get("display_name"),
        "lifecycle_state": instance.get("lifecycle_state"),
        "shape": instance.get("shape"),
        "availability_domain": instance.get("availability_domain"),
        "time_created": instance.get("time_created"),
        "compartment_id": instance.get("compartment_id")
    }


def format_volume(volume: dict[str, Any]) -> dict[str, Any]:
    """Format block storage volume with only essential fields"""
    return {
        "id": volume.get("id"),
        "display_name": volume.get("display_name"),
        "lifecycle_state": volume.get("lifecycle_state"),
        "size_in_gbs": volume.get("size_in_gbs"),
        "volume_group_id": volume.get("volume_group_id"),
        "time_created": volume.get("time_created"),
        "compartment_id": volume.get("compartment_id")
    }


def format_vcn(vcn: dict[str, Any]) -> dict[str, Any]:
    """Format VCN with only essential fields"""
    return {
        "id": vcn.get("id"),
        "display_name": vcn.get("display_name"),
        "lifecycle_state": vcn.get("lifecycle_state"),
        "cidr_block": vcn.get("cidr_block"),
        "dns_label": vcn.get("dns_label"),
        "time_created": vcn.get("time_created"),
        "compartment_id": vcn.get("compartment_id")
    }


def format_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    """Format object storage bucket with only essential fields"""
    return {
        "name": bucket.get("name"),
        "namespace": bucket.get("namespace"),
        "compartment_id": bucket.get("compartment_id"),
        "time_created": bucket.get("time_created"),
        "etag": bucket.get("etag"),
        "public_access_type": bucket.get("public_access_type")
    }


def format_database(db: dict[str, Any]) -> dict[str, Any]:
    """Format database with only essential fields"""
    return {
        "id": db.get("id"),
        "display_name": db.get("display_name"),
        "lifecycle_state": db.get("lifecycle_state"),
        "db_name": db.get("db_name"),
        "cpu_core_count": db.get("cpu_core_count"),
        "data_storage_size_in_tbs": db.get("data_storage_size_in_tbs"),
        "time_created": db.get("time_created"),
        "compartment_id": db.get("compartment_id")
    }


def format_user(user: dict[str, Any]) -> dict[str, Any]:
    """Format IAM user with only essential fields"""
    return {
        "id": user.get("id"),
        "name": user.get("name"),
        "description": user.get("description"),
        "lifecycle_state": user.get("lifecycle_state"),
        "time_created": user.get("time_created"),
        "compartment_id": user.get("compartment_id")
    }


def format_compartment(comp: dict[str, Any]) -> dict[str, Any]:
    """Format compartment with only essential fields"""
    return {
        "id": comp.get("id"),
        "name": comp.get("name"),
        "description": comp.get("description"),
        "lifecycle_state": comp.get("lifecycle_state"),
        "time_created": comp.get("time_created"),
        "compartment_id": comp.get("compartment_id")
    }


def format_log_entity(entity: dict[str, Any]) -> dict[str, Any]:
    """Format Log Analytics entity with only essential fields"""
    return {
        "id": entity.get("id"),
        "name": entity.get("name"),
        "entity_type_name": entity.get("entity_type_name"),
        "lifecycle_state": entity.get("lifecycle_state"),
        "time_created": entity.get("time_created"),
        "compartment_id": entity.get("compartment_id")
    }


def format_response(data: list[dict[str, Any]], formatter_func, 
                   limit: int | None = None, next_page: str | None = None) -> dict[str, Any]:
    """Format API response with minimal token usage"""
    # Apply formatter to each item
    items = [formatter_func(item) for item in data]
    
    # Apply limit if specified
    if limit and len(items) > limit:
        items = items[:limit]
    
    # Build minimal response
    response = {
        "items": items,
        "count": len(items)
    }
    
    if next_page:
        response["next_page"] = next_page
        
    return response


def format_error(error: Exception) -> dict[str, Any]:
    """Format error with minimal token usage"""
    error_msg = str(error)
    # Take only first line to reduce tokens
    first_line = error_msg.split('\n')[0]
    
    return {
        "error": first_line,
        "success": False
    }


def format_success(data: Any = None, message: str = "Success") -> dict[str, Any]:
    """Format success response with minimal token usage"""
    response = {
        "success": True,
        "message": message
    }
    
    if data is not None:
        response["data"] = data
        
    return response
