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
    OCIResponse,
    clients,
    create_common_tools,
    format_for_llm,
    handle_oci_error,
    validate_compartment_id,
)


def run_networking(*, profile: str | None = None, region: str | None = None, server_name: str = "mcp_oci_networking") -> None:
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
            elif not validate_compartment_id(compartment_id):
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
            elif not validate_compartment_id(compartment_id):
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
            elif not validate_compartment_id(compartment_id):
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

    @app.tool()
    async def create_vcn(
        compartment_id: str | None = None,
        display_name: str | None = None,
        cidr_block: str = "10.0.0.0/16",
        dns_label: str | None = None
    ) -> str:
        """Create a new Virtual Cloud Network (VCN)."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            network_client = clients.network
            
            # Create VCN details
            from oci.core.models import CreateVcnDetails
            
            create_vcn_details = CreateVcnDetails(
                compartment_id=compartment_id,
                display_name=display_name or f"VCN-{cidr_block.replace('/', '-')}",
                cidr_block=cidr_block,
                dns_label=dns_label
            )
            
            # Create the VCN
            response = network_client.create_vcn(create_vcn_details)
            
            result = OCIResponse(
                success=True,
                message="VCN creation initiated successfully",
                data={
                    "vcn_id": response.data.id,
                    "display_name": response.data.display_name,
                    "cidr_block": response.data.cidr_block,
                    "lifecycle_state": response.data.lifecycle_state,
                    "compartment_id": response.data.compartment_id
                },
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "create_vcn", "network")
            return result.to_dict()

    @app.tool()
    async def create_subnet(
        compartment_id: str | None = None,
        vcn_id: str | None = None,
        display_name: str | None = None,
        cidr_block: str = "10.0.1.0/24",
        availability_domain: str | None = None,
        dns_label: str | None = None,
        prohibit_public_ip_on_vnic: bool = False
    ) -> str:
        """Create a new subnet in a VCN."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            if not vcn_id:
                raise ValueError("VCN ID is required")
            if not vcn_id.startswith("ocid1.vcn."):
                raise ValueError("Invalid VCN ID format")
            
            network_client = clients.network
            
            # Get availability domain if not provided
            if not availability_domain:
                identity_client = clients.identity
                ad_response = identity_client.list_availability_domains(compartment_id=compartment_id)
                if not ad_response.data:
                    raise ValueError("No availability domains found")
                availability_domain = ad_response.data[0].name
            
            # Create subnet details
            from oci.core.models import CreateSubnetDetails
            
            create_subnet_details = CreateSubnetDetails(
                compartment_id=compartment_id,
                vcn_id=vcn_id,
                display_name=display_name or f"Subnet-{cidr_block.replace('/', '-')}",
                cidr_block=cidr_block,
                availability_domain=availability_domain,
                dns_label=dns_label,
                prohibit_public_ip_on_vnic=prohibit_public_ip_on_vnic
            )
            
            # Create the subnet
            response = network_client.create_subnet(create_subnet_details)
            
            result = OCIResponse(
                success=True,
                message="Subnet creation initiated successfully",
                data={
                    "subnet_id": response.data.id,
                    "display_name": response.data.display_name,
                    "cidr_block": response.data.cidr_block,
                    "vcn_id": response.data.vcn_id,
                    "availability_domain": response.data.availability_domain,
                    "lifecycle_state": response.data.lifecycle_state,
                    "compartment_id": response.data.compartment_id
                },
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "create_subnet", "network")
            return result.to_dict()

    @app.tool()
    async def delete_vcn(vcn_id: str, force: bool = False) -> str:
        """Delete a VCN."""
        try:
            if not vcn_id.startswith("ocid1.vcn."):
                raise ValueError("Invalid VCN ID format")
            
            network_client = clients.network
            
            # Delete the VCN
            response = network_client.delete_vcn(
                vcn_id=vcn_id,
                if_match="*" if force else None
            )
            
            result = OCIResponse(
                success=True,
                message=f"VCN {vcn_id} deletion initiated successfully",
                data={
                    "vcn_id": vcn_id,
                    "status": "DELETION_INITIATED"
                }
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "delete_vcn", "network")
            return result.to_dict()

    @app.tool()
    async def delete_subnet(subnet_id: str, force: bool = False) -> str:
        """Delete a subnet."""
        try:
            if not subnet_id.startswith("ocid1.subnet."):
                raise ValueError("Invalid subnet ID format")
            
            network_client = clients.network
            
            # Delete the subnet
            response = network_client.delete_subnet(
                subnet_id=subnet_id,
                if_match="*" if force else None
            )
            
            result = OCIResponse(
                success=True,
                message=f"Subnet {subnet_id} deletion initiated successfully",
                data={
                    "subnet_id": subnet_id,
                    "status": "DELETION_INITIATED"
                }
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "delete_subnet", "network")
            return result.to_dict()

    @app.tool()
    async def create_internet_gateway(
        compartment_id: str | None = None,
        vcn_id: str | None = None,
        display_name: str | None = None,
        is_enabled: bool = True
    ) -> str:
        """Create an internet gateway for a VCN."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            if not vcn_id:
                raise ValueError("VCN ID is required")
            if not vcn_id.startswith("ocid1.vcn."):
                raise ValueError("Invalid VCN ID format")
            
            network_client = clients.network
            
            # Create internet gateway details
            from oci.core.models import CreateInternetGatewayDetails
            
            create_ig_details = CreateInternetGatewayDetails(
                compartment_id=compartment_id,
                vcn_id=vcn_id,
                display_name=display_name or "Internet Gateway",
                is_enabled=is_enabled
            )
            
            # Create the internet gateway
            response = network_client.create_internet_gateway(create_ig_details)
            
            result = OCIResponse(
                success=True,
                message="Internet gateway creation initiated successfully",
                data={
                    "internet_gateway_id": response.data.id,
                    "display_name": response.data.display_name,
                    "vcn_id": response.data.vcn_id,
                    "is_enabled": response.data.is_enabled,
                    "lifecycle_state": response.data.lifecycle_state,
                    "compartment_id": response.data.compartment_id
                },
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "create_internet_gateway", "network")
            return result.to_dict()

    @app.tool()
    async def create_route_table(
        compartment_id: str | None = None,
        vcn_id: str | None = None,
        display_name: str | None = None,
        route_rules: list | None = None
    ) -> str:
        """Create a route table for a VCN."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            if not vcn_id:
                raise ValueError("VCN ID is required")
            if not vcn_id.startswith("ocid1.vcn."):
                raise ValueError("Invalid VCN ID format")
            
            network_client = clients.network
            
            # Create route table details
            from oci.core.models import CreateRouteTableDetails, RouteRule
            
            # Default route rules if none provided
            if not route_rules:
                route_rules = [
                    {
                        "destination": "0.0.0.0/0",
                        "destination_type": "CIDR_BLOCK",
                        "network_entity_id": "internet_gateway"  # This would need to be replaced with actual IG ID
                    }
                ]
            
            # Convert route rules to RouteRule objects
            route_rule_objects = []
            for rule in route_rules:
                route_rule_objects.append(RouteRule(
                    destination=rule.get("destination"),
                    destination_type=rule.get("destination_type"),
                    network_entity_id=rule.get("network_entity_id")
                ))
            
            create_rt_details = CreateRouteTableDetails(
                compartment_id=compartment_id,
                vcn_id=vcn_id,
                display_name=display_name or "Route Table",
                route_rules=route_rule_objects
            )
            
            # Create the route table
            response = network_client.create_route_table(create_rt_details)
            
            result = OCIResponse(
                success=True,
                message="Route table creation initiated successfully",
                data={
                    "route_table_id": response.data.id,
                    "display_name": response.data.display_name,
                    "vcn_id": response.data.vcn_id,
                    "lifecycle_state": response.data.lifecycle_state,
                    "compartment_id": response.data.compartment_id
                },
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "create_route_table", "network")
            return result.to_dict()

    app.run()
