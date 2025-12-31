"""
OCI Network domain tool implementations.
"""
from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server_oci.core.client import get_oci_client
from mcp_server_oci.core.errors import format_error_response, handle_oci_error
from mcp_server_oci.core.formatters import ResponseFormat

from .formatters import NetworkFormatter
from .models import (
    AnalyzeSecurityRulesInput,
    GetVcnInput,
    ListSecurityListsInput,
    ListSubnetsInput,
    ListVcnsInput,
)


def _serialize_vcn(vcn: Any) -> dict:
    """Serialize VCN object to dictionary."""
    return {
        "id": vcn.id,
        "display_name": vcn.display_name,
        "cidr_block": vcn.cidr_block,
        "cidr_blocks": vcn.cidr_blocks if hasattr(vcn, 'cidr_blocks') else [vcn.cidr_block],
        "lifecycle_state": vcn.lifecycle_state,
        "dns_label": vcn.dns_label,
        "default_dhcp_options_id": vcn.default_dhcp_options_id,
        "default_route_table_id": vcn.default_route_table_id,
        "default_security_list_id": vcn.default_security_list_id,
        "time_created": str(vcn.time_created) if vcn.time_created else None,
        "compartment_id": vcn.compartment_id,
    }


def _serialize_subnet(subnet: Any) -> dict:
    """Serialize Subnet object to dictionary."""
    return {
        "id": subnet.id,
        "display_name": subnet.display_name,
        "cidr_block": subnet.cidr_block,
        "lifecycle_state": subnet.lifecycle_state,
        "availability_domain": subnet.availability_domain,
        "is_public": (
            not subnet.prohibit_public_ip_on_vnic
            if hasattr(subnet, 'prohibit_public_ip_on_vnic') else True
        ),
        "dns_label": subnet.dns_label,
        "vcn_id": subnet.vcn_id,
        "route_table_id": subnet.route_table_id,
        "security_list_ids": subnet.security_list_ids,
        "time_created": str(subnet.time_created) if subnet.time_created else None,
        "compartment_id": subnet.compartment_id,
    }


def _serialize_security_list(sl: Any) -> dict:
    """Serialize Security List object to dictionary."""
    def serialize_rule(rule: Any, direction: str) -> dict:
        result = {
            "direction": direction,
            "protocol": rule.protocol,
            "is_stateless": rule.is_stateless if hasattr(rule, 'is_stateless') else False,
        }

        if direction == "INGRESS":
            result["source"] = rule.source
            src_type = getattr(rule, 'source_type', "CIDR_BLOCK")
            result["source_type"] = src_type
        else:
            result["destination"] = rule.destination
            dst_type = getattr(rule, 'destination_type', "CIDR_BLOCK")
            result["destination_type"] = dst_type

        # TCP options
        if hasattr(rule, 'tcp_options') and rule.tcp_options:
            tcp = rule.tcp_options
            result["tcp_options"] = {}
            if hasattr(tcp, 'destination_port_range') and tcp.destination_port_range:
                result["tcp_options"]["destination_port_range"] = {
                    "min": tcp.destination_port_range.min,
                    "max": tcp.destination_port_range.max
                }
            if hasattr(tcp, 'source_port_range') and tcp.source_port_range:
                result["tcp_options"]["source_port_range"] = {
                    "min": tcp.source_port_range.min,
                    "max": tcp.source_port_range.max
                }

        # UDP options
        if hasattr(rule, 'udp_options') and rule.udp_options:
            udp = rule.udp_options
            result["udp_options"] = {}
            if hasattr(udp, 'destination_port_range') and udp.destination_port_range:
                result["udp_options"]["destination_port_range"] = {
                    "min": udp.destination_port_range.min,
                    "max": udp.destination_port_range.max
                }

        # ICMP options
        if hasattr(rule, 'icmp_options') and rule.icmp_options:
            icmp = rule.icmp_options
            result["icmp_options"] = {
                "type": icmp.type if hasattr(icmp, 'type') else None,
                "code": icmp.code if hasattr(icmp, 'code') else None
            }

        return result

    ingress_rules = [serialize_rule(r, "INGRESS") for r in (sl.ingress_security_rules or [])]
    egress_rules = [serialize_rule(r, "EGRESS") for r in (sl.egress_security_rules or [])]

    return {
        "id": sl.id,
        "display_name": sl.display_name,
        "lifecycle_state": sl.lifecycle_state,
        "vcn_id": sl.vcn_id,
        "time_created": str(sl.time_created) if sl.time_created else None,
        "compartment_id": sl.compartment_id,
        "ingress_security_rules": ingress_rules,
        "egress_security_rules": egress_rules,
    }


def _analyze_risky_rules(security_lists: list[dict]) -> dict:
    """Analyze security rules for potential risks."""
    risky_rules = []
    total_rules = 0

    risky_sources = ["0.0.0.0/0", "::/0"]
    # SSH, RDP, Oracle DB, MySQL, PostgreSQL, MongoDB
    risky_ports = [22, 3389, 1521, 3306, 5432, 27017]

    for sl in security_lists:
        for rule in sl.get("ingress_security_rules", []):
            total_rules += 1
            source = rule.get("source", "")
            protocol = rule.get("protocol", "")

            # Check for open to world
            if source in risky_sources:
                risk_level = "HIGH"
                reason = f"Rule allows traffic from anywhere ({source})"
                recommendation = "Restrict source to specific IP ranges or CIDR blocks"

                # Check if it's a sensitive port
                tcp_options = rule.get("tcp_options", {})
                if tcp_options:
                    port_range = tcp_options.get("destination_port_range", {})
                    min_port = port_range.get("min")
                    max_port = port_range.get("max")

                    if min_port and max_port:
                        for risky_port in risky_ports:
                            if min_port <= risky_port <= max_port:
                                risk_level = "HIGH"
                                reason = (
                                    f"Rule exposes sensitive port {risky_port} "
                                    "to the internet"
                                )
                                recommendation = (
                                    f"Restrict access to port {risky_port} "
                                    "to specific IP addresses"
                                )
                                break

                risky_rules.append({
                    "security_list_id": sl.get("id"),
                    "security_list_name": sl.get("display_name"),
                    "rule": {
                        "direction": "INGRESS",
                        "protocol": protocol,
                        "source_or_destination": source,
                        "port_range": (
                            str(tcp_options.get("destination_port_range"))
                            if tcp_options else None
                        ),
                    },
                    "risk_level": risk_level,
                    "reason": reason,
                    "recommendation": recommendation,
                })

        for _rule in sl.get("egress_security_rules", []):
            total_rules += 1

    return {
        "total_rules": total_rules,
        "risky_rules": risky_rules,
        "summary": {
            "high_risk": len(
                [r for r in risky_rules if r["risk_level"] == "HIGH"]
            ),
            "medium_risk": len(
                [r for r in risky_rules if r["risk_level"] == "MEDIUM"]
            ),
            "low_risk": len(
                [r for r in risky_rules if r["risk_level"] == "LOW"]
            ),
        }
    }


def register_network_tools(mcp: FastMCP) -> None:
    """Register all network domain tools with the MCP server."""

    @mcp.tool(
        name="oci_network_list_vcns",
        annotations={
            "title": "List Virtual Cloud Networks",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def list_vcns(params: ListVcnsInput) -> str:
        """List Virtual Cloud Networks (VCNs) in a compartment.

        Returns VCNs with their CIDR blocks, states, and subnet counts.
        """
        compartment_id = params.compartment_id or os.environ.get("COMPARTMENT_OCID")
        if not compartment_id:
            return "Error: No compartment_id provided and COMPARTMENT_OCID not set."

        try:
            client = get_oci_client("virtual_network")

            # List VCNs
            response = client.list_vcns(compartment_id=compartment_id, limit=params.limit)

            vcns = []
            for vcn in response.data:
                # Apply filters
                if params.lifecycle_state and vcn.lifecycle_state != params.lifecycle_state.value:
                    continue
                if params.display_name:
                    if params.display_name.lower() not in vcn.display_name.lower():
                        continue

                vcn_data = _serialize_vcn(vcn)

                # Count subnets
                subnet_response = client.list_subnets(compartment_id=compartment_id, vcn_id=vcn.id)
                vcn_data["subnet_count"] = len(subnet_response.data)

                vcns.append(vcn_data)

            if params.response_format == ResponseFormat.JSON:
                return NetworkFormatter.to_json({
                    "vcns": vcns,
                    "count": len(vcns),
                    "compartment_id": compartment_id
                })
            return NetworkFormatter.vcn_list_markdown(vcns)

        except Exception as e:
            error = handle_oci_error(e, "listing VCNs")
            return format_error_response(error, params.response_format.value)

    @mcp.tool(
        name="oci_network_get_vcn",
        annotations={
            "title": "Get VCN Details",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def get_vcn(params: GetVcnInput) -> str:
        """Get detailed information about a specific VCN.

        Includes subnets and security lists if requested.
        """
        try:
            client = get_oci_client("virtual_network")

            # Get VCN
            response = client.get_vcn(vcn_id=params.vcn_id)
            vcn_data = _serialize_vcn(response.data)

            subnets = None
            security_lists = None

            # Get subnets if requested
            if params.include_subnets:
                subnet_response = client.list_subnets(
                    compartment_id=response.data.compartment_id,
                    vcn_id=params.vcn_id
                )
                subnets = [_serialize_subnet(s) for s in subnet_response.data]

            # Get security lists if requested
            if params.include_security_lists:
                sl_response = client.list_security_lists(
                    compartment_id=response.data.compartment_id,
                    vcn_id=params.vcn_id
                )
                security_lists = [_serialize_security_list(sl) for sl in sl_response.data]

            if params.response_format == ResponseFormat.JSON:
                return NetworkFormatter.to_json({
                    "vcn": vcn_data,
                    "subnets": subnets,
                    "security_lists": security_lists
                })
            return NetworkFormatter.vcn_detail_markdown(vcn_data, subnets, security_lists)

        except Exception as e:
            error = handle_oci_error(e, "getting VCN details")
            return format_error_response(error, params.response_format.value)

    @mcp.tool(
        name="oci_network_list_subnets",
        annotations={
            "title": "List Subnets",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def list_subnets(params: ListSubnetsInput) -> str:
        """List subnets in a compartment or VCN.

        Returns subnet CIDR blocks, availability domains, and public/private status.
        """
        compartment_id = params.compartment_id or os.environ.get("COMPARTMENT_OCID")
        if not compartment_id:
            return "Error: No compartment_id provided and COMPARTMENT_OCID not set."

        try:
            client = get_oci_client("virtual_network")

            kwargs = {"compartment_id": compartment_id, "limit": params.limit}
            if params.vcn_id:
                kwargs["vcn_id"] = params.vcn_id

            response = client.list_subnets(**kwargs)

            subnets = []
            for subnet in response.data:
                if params.lifecycle_state:
                    if subnet.lifecycle_state != params.lifecycle_state.value:
                        continue
                if params.display_name:
                    if params.display_name.lower() not in subnet.display_name.lower():
                        continue

                subnets.append(_serialize_subnet(subnet))

            if params.response_format == ResponseFormat.JSON:
                return NetworkFormatter.to_json({
                    "subnets": subnets,
                    "count": len(subnets),
                    "compartment_id": compartment_id
                })
            return NetworkFormatter.subnet_list_markdown(subnets)

        except Exception as e:
            error = handle_oci_error(e, "listing subnets")
            return format_error_response(error, params.response_format.value)

    @mcp.tool(
        name="oci_network_list_security_lists",
        annotations={
            "title": "List Security Lists",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def list_security_lists(params: ListSecurityListsInput) -> str:
        """List security lists with their ingress and egress rules.

        Shows rule counts and basic rule information.
        """
        compartment_id = params.compartment_id or os.environ.get("COMPARTMENT_OCID")
        if not compartment_id:
            return "Error: No compartment_id provided and COMPARTMENT_OCID not set."

        try:
            client = get_oci_client("virtual_network")

            kwargs = {"compartment_id": compartment_id, "limit": params.limit}
            if params.vcn_id:
                kwargs["vcn_id"] = params.vcn_id

            response = client.list_security_lists(**kwargs)

            security_lists = []
            for sl in response.data:
                if params.display_name:
                    if params.display_name.lower() not in sl.display_name.lower():
                        continue

                security_lists.append(_serialize_security_list(sl))

            if params.response_format == ResponseFormat.JSON:
                return NetworkFormatter.to_json({
                    "security_lists": security_lists,
                    "count": len(security_lists),
                    "compartment_id": compartment_id
                })
            return NetworkFormatter.security_list_markdown(security_lists)

        except Exception as e:
            error = handle_oci_error(e, "listing security lists")
            return format_error_response(error, params.response_format.value)

    @mcp.tool(
        name="oci_network_analyze_security",
        annotations={
            "title": "Analyze Security Rules",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def analyze_security_rules(params: AnalyzeSecurityRulesInput) -> str:
        """Analyze security rules for potential risks.

        Identifies overly permissive rules (e.g., 0.0.0.0/0) and
        exposed sensitive ports.
        """
        if not params.vcn_id and not params.security_list_id:
            return "Error: Either vcn_id or security_list_id must be provided."

        try:
            client = get_oci_client("virtual_network")

            security_lists = []

            if params.security_list_id:
                # Get specific security list
                response = client.get_security_list(security_list_id=params.security_list_id)
                security_lists.append(_serialize_security_list(response.data))
            else:
                # Get VCN to find compartment
                vcn_response = client.get_vcn(vcn_id=params.vcn_id)
                compartment_id = vcn_response.data.compartment_id

                # Get all security lists in the VCN
                sl_response = client.list_security_lists(
                    compartment_id=compartment_id,
                    vcn_id=params.vcn_id
                )
                security_lists = [_serialize_security_list(sl) for sl in sl_response.data]

            # Analyze for risks
            analysis = _analyze_risky_rules(security_lists)

            if params.response_format == ResponseFormat.JSON:
                return NetworkFormatter.to_json(analysis)
            return NetworkFormatter.security_analysis_markdown(analysis)

        except Exception as e:
            error = handle_oci_error(e, "analyzing security rules")
            return format_error_response(error, params.response_format.value)
