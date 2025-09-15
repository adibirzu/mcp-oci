#!/usr/bin/env python3
"""
Optimized Networking MCP Server
Based on official OCI Python SDK patterns and shared architecture
"""

from __future__ import annotations

try:
    from fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    FastMCP = None  # type: ignore
    _import_error = e
else:
    _import_error = None

from .shared_architecture import (
    clients,
    OCIResponse,
    handle_oci_error,
    format_for_llm,
    validate_compartment_id,
    create_fastmcp_tool,
    create_common_tools
)

def run_networking(*, profile: str | None = None, region: str | None = None, server_name: str = "oci-networking-optimized") -> None:
    """Serve an optimized FastMCP app for networking operations."""
    if FastMCP is None:
        raise SystemExit(
            f"fastmcp is not installed. Install with: pip install fastmcp\nOriginal import error: {_import_error}"
        )

    # Set environment variables if provided
    if profile:
        import os
        os.environ["OCI_PROFILE"] = profile
    if region:
        import os
        os.environ["OCI_REGION"] = region

    app = FastMCP(server_name)

    # Create common tools
    create_common_tools(app, server_name)

    # Networking-specific tools
    @app.tool()
    async def list_vcns(
        compartment_id: str | None = None,
        display_name: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 50
    ) -> str:
        """List Virtual Cloud Networks (VCNs) using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            network_client = clients.network
            
            # Use official OCI SDK method pattern
            response = network_client.list_vcns(
                compartment_id=compartment_id,
                display_name=display_name,
                lifecycle_state=lifecycle_state,
                limit=limit
            )
            
            vcns = []
            for vcn in response.data:
                vcns.append({
                    "id": vcn.id,
                    "display_name": vcn.display_name,
                    "cidr_block": vcn.cidr_block,
                    "lifecycle_state": vcn.lifecycle_state,
                    "time_created": vcn.time_created.isoformat() if vcn.time_created else None,
                    "compartment_id": vcn.compartment_id,
                    "dns_label": vcn.dns_label,
                    "vcn_domain_name": vcn.vcn_domain_name
                })
            
            formatted_vcns = format_for_llm(vcns, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_vcns)} VCNs",
                data=formatted_vcns,
                count=len(formatted_vcns),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_vcns", "network")
            return result.to_dict()

    @app.tool()
    async def get_vcn(vcn_id: str) -> str:
        """Get a specific VCN by ID."""
        try:
            if not vcn_id.startswith("ocid1.vcn."):
                raise ValueError("Invalid VCN ID format")
            
            network_client = clients.network
            response = network_client.get_vcn(vcn_id=vcn_id)
            
            vcn = {
                "id": response.data.id,
                "display_name": response.data.display_name,
                "cidr_block": response.data.cidr_block,
                "lifecycle_state": response.data.lifecycle_state,
                "time_created": response.data.time_created.isoformat() if response.data.time_created else None,
                "compartment_id": response.data.compartment_id,
                "dns_label": response.data.dns_label,
                "vcn_domain_name": response.data.vcn_domain_name
            }
            
            formatted_vcn = format_for_llm(vcn)
            
            result = OCIResponse(
                success=True,
                message="VCN retrieved successfully",
                data=formatted_vcn,
                compartment_id=response.data.compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_vcn", "network")
            return result.to_dict()

    @app.tool()
    async def list_subnets(
        compartment_id: str | None = None,
        vcn_id: str | None = None,
        display_name: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 50
    ) -> str:
        """List subnets using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            network_client = clients.network
            
            # Use official OCI SDK method pattern
            response = network_client.list_subnets(
                compartment_id=compartment_id,
                vcn_id=vcn_id,
                display_name=display_name,
                lifecycle_state=lifecycle_state,
                limit=limit
            )
            
            subnets = []
            for subnet in response.data:
                subnets.append({
                    "id": subnet.id,
                    "display_name": subnet.display_name,
                    "cidr_block": subnet.cidr_block,
                    "lifecycle_state": subnet.lifecycle_state,
                    "time_created": subnet.time_created.isoformat() if subnet.time_created else None,
                    "compartment_id": subnet.compartment_id,
                    "vcn_id": subnet.vcn_id,
                    "availability_domain": subnet.availability_domain,
                    "dns_label": subnet.dns_label,
                    "subnet_domain_name": subnet.subnet_domain_name
                })
            
            formatted_subnets = format_for_llm(subnets, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_subnets)} subnets",
                data=formatted_subnets,
                count=len(formatted_subnets),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_subnets", "network")
            return result.to_dict()

    @app.tool()
    async def get_subnet(subnet_id: str) -> str:
        """Get a specific subnet by ID."""
        try:
            if not subnet_id.startswith("ocid1.subnet."):
                raise ValueError("Invalid subnet ID format")
            
            network_client = clients.network
            response = network_client.get_subnet(subnet_id=subnet_id)
            
            subnet = {
                "id": response.data.id,
                "display_name": response.data.display_name,
                "cidr_block": response.data.cidr_block,
                "lifecycle_state": response.data.lifecycle_state,
                "time_created": response.data.time_created.isoformat() if response.data.time_created else None,
                "compartment_id": response.data.compartment_id,
                "vcn_id": response.data.vcn_id,
                "availability_domain": response.data.availability_domain,
                "dns_label": response.data.dns_label,
                "subnet_domain_name": response.data.subnet_domain_name
            }
            
            formatted_subnet = format_for_llm(subnet)
            
            result = OCIResponse(
                success=True,
                message="Subnet retrieved successfully",
                data=formatted_subnet,
                compartment_id=response.data.compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_subnet", "network")
            return result.to_dict()

    @app.tool()
    async def list_security_lists(
        compartment_id: str | None = None,
        vcn_id: str | None = None,
        display_name: str | None = None,
        limit: int = 50
    ) -> str:
        """List security lists using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            else:
                if not validate_compartment_id(compartment_id):
                    raise ValueError("Invalid compartment ID format")
            
            network_client = clients.network
            
            # Use official OCI SDK method pattern
            response = network_client.list_security_lists(
                compartment_id=compartment_id,
                vcn_id=vcn_id,
                display_name=display_name,
                limit=limit
            )
            
            security_lists = []
            for sl in response.data:
                security_lists.append({
                    "id": sl.id,
                    "display_name": sl.display_name,
                    "lifecycle_state": sl.lifecycle_state,
                    "time_created": sl.time_created.isoformat() if sl.time_created else None,
                    "compartment_id": sl.compartment_id,
                    "vcn_id": sl.vcn_id
                })
            
            formatted_security_lists = format_for_llm(security_lists, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_security_lists)} security lists",
                data=formatted_security_lists,
                count=len(formatted_security_lists),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_security_lists", "network")
            return result.to_dict()

    app.run()
