"""
Optimized Networking service using direct REST API calls
Minimal token usage, based on Oracle Postman collection patterns
"""

from typing import Any

from .client import create_client
from .formatters import format_error, format_response, format_success, format_vcn


def list_vcns(compartment_id: str, limit: int | None = None,
              page: str | None = None, profile: str = "DEFAULT", 
              region: str = None) -> dict[str, Any]:
    """List VCNs using REST API - optimized for minimal tokens"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Build query parameters
        params = {"compartmentId": compartment_id}
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page
            
        # Make REST API call
        response = client.get("/20160918/vcns", params=params)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract VCNs
        vcns = response.get("data", [])
        
        # Format response
        return format_response(
            vcns, 
            format_vcn, 
            limit=limit,
            next_page=response.get("opc_next_page")
        )
        
    except Exception as e:
        return format_error(e)


def get_vcn(vcn_id: str, profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """Get specific VCN using REST API"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Make REST API call
        response = client.get(f"/20160918/vcns/{vcn_id}")
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'VCN not found')}"))
        
        # Format single VCN
        vcn = response.get("data", {})
        return format_success(format_vcn(vcn))
        
    except Exception as e:
        return format_error(e)


def list_subnets(compartment_id: str, vcn_id: str | None = None,
                 limit: int | None = None, page: str | None = None,
                 profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """List subnets using REST API - optimized for minimal tokens"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Build query parameters
        params = {"compartmentId": compartment_id}
        if vcn_id:
            params["vcnId"] = vcn_id
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page
            
        # Make REST API call
        response = client.get("/20160918/subnets", params=params)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract subnets
        subnets = response.get("data", [])
        
        # Format subnets with minimal fields
        formatted_subnets = [{
            "id": subnet.get("id"),
            "display_name": subnet.get("display_name"),
            "lifecycle_state": subnet.get("lifecycle_state"),
            "cidr_block": subnet.get("cidr_block"),
            "vcn_id": subnet.get("vcn_id"),
            "time_created": subnet.get("time_created"),
            "compartment_id": subnet.get("compartment_id")
        } for subnet in subnets]
        
        # Format response
        return format_response(
            formatted_subnets, 
            lambda x: x,  # Already formatted
            limit=limit,
            next_page=response.get("opc_next_page")
        )
        
    except Exception as e:
        return format_error(e)


def get_subnet(subnet_id: str, profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """Get specific subnet using REST API"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Make REST API call
        response = client.get(f"/20160918/subnets/{subnet_id}")
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Subnet not found')}"))
        
        # Format single subnet
        subnet = response.get("data", {})
        formatted_subnet = {
            "id": subnet.get("id"),
            "display_name": subnet.get("display_name"),
            "lifecycle_state": subnet.get("lifecycle_state"),
            "cidr_block": subnet.get("cidr_block"),
            "vcn_id": subnet.get("vcn_id"),
            "time_created": subnet.get("time_created"),
            "compartment_id": subnet.get("compartment_id")
        }
        
        return format_success(formatted_subnet)
        
    except Exception as e:
        return format_error(e)


def list_security_lists(compartment_id: str, vcn_id: str | None = None,
                       limit: int | None = None, page: str | None = None,
                       profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """List security lists using REST API - optimized for minimal tokens"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Build query parameters
        params = {"compartmentId": compartment_id}
        if vcn_id:
            params["vcnId"] = vcn_id
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page
            
        # Make REST API call
        response = client.get("/20160918/securityLists", params=params)
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Unknown error')}"))
        
        # Extract security lists
        security_lists = response.get("data", [])
        
        # Format security lists with minimal fields
        formatted_lists = [{
            "id": sl.get("id"),
            "display_name": sl.get("display_name"),
            "lifecycle_state": sl.get("lifecycle_state"),
            "vcn_id": sl.get("vcn_id"),
            "time_created": sl.get("time_created"),
            "compartment_id": sl.get("compartment_id")
        } for sl in security_lists]
        
        # Format response
        return format_response(
            formatted_lists, 
            lambda x: x,  # Already formatted
            limit=limit,
            next_page=response.get("opc_next_page")
        )
        
    except Exception as e:
        return format_error(e)


def get_security_list(security_list_id: str, profile: str = "DEFAULT", region: str = None) -> dict[str, Any]:
    """Get specific security list using REST API"""
    try:
        client = create_client(profile=profile, region=region)
        
        # Make REST API call
        response = client.get(f"/20160918/securityLists/{security_list_id}")
        
        if not response.get("_status", {}).get("ok"):
            return format_error(Exception(f"API Error: {response.get('error', 'Security list not found')}"))
        
        # Format single security list
        security_list = response.get("data", {})
        formatted_sl = {
            "id": security_list.get("id"),
            "display_name": security_list.get("display_name"),
            "lifecycle_state": security_list.get("lifecycle_state"),
            "vcn_id": security_list.get("vcn_id"),
            "time_created": security_list.get("time_created"),
            "compartment_id": security_list.get("compartment_id")
        }
        
        return format_success(formatted_sl)
        
    except Exception as e:
        return format_error(e)


def get_server_info() -> dict[str, Any]:
    """Get server information"""
    return {
        "name": "oci-networking-rest",
        "version": "1.0.0",
        "type": "REST API",
        "optimized": True,
        "token_usage": "minimal"
    }
