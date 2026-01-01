"""
Network domain-specific formatters.
"""
from __future__ import annotations

import json
from typing import Any

from mcp_server_oci.core.formatters import Formatter, MarkdownFormatter


class NetworkFormatter:
    """Network-specific formatting utilities."""

    @staticmethod
    def to_json(data: Any) -> str:
        """Format as JSON."""
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def vcn_list_markdown(vcns: list[dict], compartment_name: str | None = None) -> str:
        """Format VCN list as markdown."""
        if not vcns:
            return "No VCNs found matching the criteria."

        md = MarkdownFormatter.header("Virtual Cloud Networks", 1)

        if compartment_name:
            md += f"**Compartment:** {compartment_name}\n"
        md += f"**Total:** {len(vcns)} VCN(s)\n\n"

        headers = ["Name", "CIDR Block", "State", "Subnets", "Created"]
        rows = []

        for vcn in vcns:
            rows.append([
                vcn.get("display_name", "N/A"),
                vcn.get("cidr_block", "N/A"),
                vcn.get("lifecycle_state", "N/A"),
                str(vcn.get("subnet_count", "-")),
                Formatter.format_datetime(vcn.get("time_created", ""), human_readable=True)[:10]
            ])

        md += MarkdownFormatter.table(headers, rows)
        return md

    @staticmethod
    def vcn_detail_markdown(
        vcn: dict, subnets: list[dict] = None, security_lists: list[dict] = None
    ) -> str:
        """Format VCN detail as markdown."""
        md = MarkdownFormatter.header(f"VCN: {vcn.get('display_name', 'Unknown')}", 1)

        # Basic info
        md += MarkdownFormatter.header("Overview", 2)
        md += f"**OCID:** `{Formatter.format_ocid(vcn.get('id', ''))}`\n"
        md += f"**CIDR Block:** {vcn.get('cidr_block', 'N/A')}\n"
        md += f"**State:** {vcn.get('lifecycle_state', 'N/A')}\n"
        md += f"**DNS Label:** {vcn.get('dns_label', 'N/A')}\n"
        md += f"**Created:** {Formatter.format_datetime(vcn.get('time_created', ''))}\n\n"

        # Subnets
        if subnets is not None:
            md += MarkdownFormatter.header("Subnets", 2)
            if subnets:
                headers = ["Name", "CIDR", "Type", "AD", "State"]
                rows = []
                for subnet in subnets:
                    subnet_type = "Public" if subnet.get("is_public", False) else "Private"
                    ad = subnet.get("availability_domain", "Regional")
                    if ad and "-AD-" in ad:
                        ad = ad.split("-AD-")[-1]
                    rows.append([
                        subnet.get("display_name", "N/A"),
                        subnet.get("cidr_block", "N/A"),
                        subnet_type,
                        ad or "Regional",
                        subnet.get("lifecycle_state", "N/A")
                    ])
                md += MarkdownFormatter.table(headers, rows)
            else:
                md += "No subnets found.\n\n"

        # Security Lists
        if security_lists is not None:
            md += MarkdownFormatter.header("Security Lists", 2)
            if security_lists:
                headers = ["Name", "Ingress Rules", "Egress Rules"]
                rows = []
                for sl in security_lists:
                    rows.append([
                        sl.get("display_name", "N/A"),
                        str(len(sl.get("ingress_security_rules", []))),
                        str(len(sl.get("egress_security_rules", [])))
                    ])
                md += MarkdownFormatter.table(headers, rows)
            else:
                md += "No security lists found.\n\n"

        return md

    @staticmethod
    def subnet_list_markdown(subnets: list[dict], vcn_name: str | None = None) -> str:
        """Format subnet list as markdown."""
        if not subnets:
            return "No subnets found matching the criteria."

        md = MarkdownFormatter.header("Subnets", 1)

        if vcn_name:
            md += f"**VCN:** {vcn_name}\n"
        md += f"**Total:** {len(subnets)} subnet(s)\n\n"

        headers = ["Name", "CIDR Block", "Type", "AD", "State"]
        rows = []

        for subnet in subnets:
            subnet_type = "Public" if subnet.get("is_public", False) else "Private"
            ad = subnet.get("availability_domain", "Regional")
            if ad and "-AD-" in ad:
                ad = ad.split("-AD-")[-1]

            rows.append([
                subnet.get("display_name", "N/A"),
                subnet.get("cidr_block", "N/A"),
                subnet_type,
                ad or "Regional",
                subnet.get("lifecycle_state", "N/A")
            ])

        md += MarkdownFormatter.table(headers, rows)
        return md

    @staticmethod
    def subnet_detail_markdown(subnet: dict) -> str:
        """Format subnet detail as markdown."""
        md = MarkdownFormatter.header(f"Subnet: {subnet.get('display_name', 'Unknown')}", 1)

        subnet_type = "Public" if subnet.get("is_public", False) else "Private"

        md += f"**OCID:** `{Formatter.format_ocid(subnet.get('id', ''))}`\n"
        md += f"**CIDR Block:** {subnet.get('cidr_block', 'N/A')}\n"
        md += f"**Type:** {subnet_type}\n"
        md += f"**State:** {subnet.get('lifecycle_state', 'N/A')}\n"
        md += f"**Availability Domain:** {subnet.get('availability_domain', 'Regional')}\n"
        md += f"**DNS Label:** {subnet.get('dns_label', 'N/A')}\n"
        md += f"**VCN OCID:** `{Formatter.format_ocid(subnet.get('vcn_id', ''))}`\n"
        md += f"**Created:** {Formatter.format_datetime(subnet.get('time_created', ''))}\n"

        return md

    @staticmethod
    def security_list_markdown(security_lists: list[dict]) -> str:
        """Format security list as markdown."""
        if not security_lists:
            return "No security lists found matching the criteria."

        md = MarkdownFormatter.header("Security Lists", 1)
        md += f"**Total:** {len(security_lists)} security list(s)\n\n"

        for sl in security_lists:
            md += MarkdownFormatter.header(sl.get("display_name", "Unknown"), 2)
            md += f"**OCID:** `{Formatter.format_ocid(sl.get('id', ''))}`\n\n"

            # Ingress rules
            ingress = sl.get("ingress_security_rules", [])
            md += f"**Ingress Rules ({len(ingress)}):**\n"
            if ingress:
                for rule in ingress[:5]:  # Limit to 5 rules
                    md += NetworkFormatter._format_rule(rule, "ingress")
                if len(ingress) > 5:
                    md += f"  ... and {len(ingress) - 5} more rules\n"
            else:
                md += "  None\n"
            md += "\n"

            # Egress rules
            egress = sl.get("egress_security_rules", [])
            md += f"**Egress Rules ({len(egress)}):**\n"
            if egress:
                for rule in egress[:5]:  # Limit to 5 rules
                    md += NetworkFormatter._format_rule(rule, "egress")
                if len(egress) > 5:
                    md += f"  ... and {len(egress) - 5} more rules\n"
            else:
                md += "  None\n"
            md += "\n"

        return md

    @staticmethod
    def _format_rule(rule: dict, direction: str) -> str:
        """Format a single security rule."""
        protocol = rule.get("protocol", "all")
        protocol_map = {"1": "ICMP", "6": "TCP", "17": "UDP", "all": "All"}
        protocol_name = protocol_map.get(protocol, f"Protocol {protocol}")

        if direction == "ingress":
            source = rule.get("source", "any")
            line = f"  - {protocol_name} from {source}"
        else:
            destination = rule.get("destination", "any")
            line = f"  - {protocol_name} to {destination}"

        # Add port info for TCP/UDP
        if protocol in ["6", "17"]:
            tcp_options = rule.get("tcp_options", rule.get("udp_options", {}))
            if tcp_options:
                dest_port = tcp_options.get("destination_port_range", {})
                if dest_port:
                    min_port = dest_port.get("min", "*")
                    max_port = dest_port.get("max", "*")
                    if min_port == max_port:
                        line += f" port {min_port}"
                    else:
                        line += f" ports {min_port}-{max_port}"

        return line + "\n"

    @staticmethod
    def security_analysis_markdown(analysis: dict) -> str:
        """Format security analysis as markdown."""
        md = MarkdownFormatter.header("Security Rule Analysis", 1)

        risky_rules = analysis.get("risky_rules", [])
        total_rules = analysis.get("total_rules", 0)

        md += f"**Total Rules Analyzed:** {total_rules}\n"
        md += f"**Risky Rules Found:** {len(risky_rules)}\n\n"

        if risky_rules:
            md += MarkdownFormatter.header("⚠️ Risky Rules", 2)

            for rule in risky_rules:
                risk_icons = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡"}
                risk_icon = risk_icons.get(rule.get("risk_level", ""), "⚪")
                md += f"\n### {risk_icon} {rule.get('security_list_name', 'Unknown')}\n"
                md += f"**Risk Level:** {rule.get('risk_level', 'N/A')}\n"
                md += f"**Reason:** {rule.get('reason', 'N/A')}\n"
                md += f"**Recommendation:** {rule.get('recommendation', 'N/A')}\n"

                rule_detail = rule.get("rule", {})
                md += f"**Rule Detail:** {rule_detail.get('protocol', 'N/A')} "
                md += f"from/to {rule_detail.get('source_or_destination', 'N/A')}\n"
        else:
            md += "✅ No risky rules detected.\n"

        return md
