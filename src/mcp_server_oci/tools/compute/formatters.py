"""
Compute domain-specific formatters.

Provides both markdown (human-readable) and JSON (machine-readable) outputs.
"""
from __future__ import annotations

import json
from typing import Any

from mcp_server_oci.core.formatters import MarkdownFormatter


class ComputeFormatter:
    """Compute-specific formatting utilities."""

    @staticmethod
    def to_json(data: Any) -> str:
        """Format as JSON."""
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def instances_markdown(data: dict) -> str:
        """Format instance list as markdown."""
        instances = data.get("instances", [])

        if not instances:
            return "# Compute Instances\n\nNo instances found matching the criteria."

        md = MarkdownFormatter.header("Compute Instances", 1)
        md += f"\n**Total:** {data.get('total', len(instances))} | "
        md += f"**Showing:** {data.get('count', len(instances))} | "
        md += f"**Offset:** {data.get('offset', 0)}\n\n"

        # Summary by state
        states = {}
        for inst in instances:
            state = inst.get("lifecycle_state", "UNKNOWN")
            states[state] = states.get(state, 0) + 1

        state_icons = {
            "RUNNING": "🟢",
            "STOPPED": "🔴",
            "STARTING": "🟡",
            "STOPPING": "🟡",
            "TERMINATED": "⚫",
            "PROVISIONING": "🔵",
        }

        state_summary = " | ".join([
            f"{state_icons.get(s, '⚪')} {s}: {c}"
            for s, c in sorted(states.items())
        ])
        md += f"**States:** {state_summary}\n\n"

        # Instance table
        headers = ["Name", "State", "Shape", "IP Address", "Created"]
        rows = []
        for inst in instances:
            ips = []
            if inst.get("public_ip"):
                ips.append(f"🌐 {inst['public_ip']}")
            if inst.get("private_ip"):
                ips.append(f"🔒 {inst['private_ip']}")
            ip_str = ", ".join(ips) if ips else "—"

            state = inst.get("lifecycle_state", "UNKNOWN")
            state_icon = state_icons.get(state, "⚪")

            created = inst.get("time_created", "—")
            if created and created != "—":
                # Simplify timestamp
                created = created.split("T")[0] if "T" in created else created

            rows.append([
                inst.get("display_name", "unnamed"),
                f"{state_icon} {state}",
                inst.get("shape", "—"),
                ip_str,
                created
            ])

        md += MarkdownFormatter.table(headers, rows)

        # Pagination info
        if data.get("has_more"):
            md += f"\n*More results available. Use `offset={data.get('next_offset')}` to see next page.*\n"

        return md

    @staticmethod
    def instance_detail_markdown(data: dict) -> str:
        """Format single instance details as markdown."""
        md = MarkdownFormatter.header(f"Instance: {data.get('display_name', 'Unknown')}", 1)

        state = data.get("lifecycle_state", "UNKNOWN")
        state_icons = {
            "RUNNING": "🟢",
            "STOPPED": "🔴",
            "STARTING": "🟡",
            "STOPPING": "🟡",
        }
        state_icon = state_icons.get(state, "⚪")

        md += f"\n**Status:** {state_icon} {state}\n\n"

        # Basic info section
        md += MarkdownFormatter.header("Configuration", 2)
        md += f"- **Shape:** {data.get('shape', '—')}\n"
        md += f"- **Availability Domain:** {data.get('availability_domain', '—')}\n"
        md += f"- **Fault Domain:** {data.get('fault_domain', '—')}\n"
        md += f"- **Created:** {data.get('time_created', '—')}\n"

        # Network section
        if data.get("public_ip") or data.get("private_ip"):
            md += MarkdownFormatter.header("Network", 2)
            if data.get("public_ip"):
                md += f"- **Public IP:** {data['public_ip']}\n"
            if data.get("private_ip"):
                md += f"- **Private IP:** {data['private_ip']}\n"

        # Metrics section if present
        if data.get("metrics"):
            md += MarkdownFormatter.header("Recent Metrics", 2)
            for metric_name, metric_data in data["metrics"].items():
                avg = metric_data.get("average", 0)
                max_val = metric_data.get("max", 0)
                md += f"- **{metric_name}:** Avg: {avg:.1f}%, Max: {max_val:.1f}%\n"

        # OCID (truncated for readability)
        ocid = data.get("id", "")
        if ocid:
            md += f"\n*OCID: `{ocid[:20]}...{ocid[-10:]}`*\n"

        return md

    @staticmethod
    def action_result_markdown(data: dict) -> str:
        """Format action result as markdown."""
        success = data.get("success", False)
        action = data.get("action", "action")

        if success:
            md = f"# ✅ Instance {action.title()} Initiated\n\n"
        else:
            md = f"# ❌ Instance {action.title()} Failed\n\n"

        md += f"**Instance:** `{data.get('instance_id', '—')}`\n"

        if data.get("previous_state"):
            md += f"**Previous State:** {data['previous_state']}\n"

        md += f"**Target State:** {data.get('target_state', '—')}\n"
        md += f"\n{data.get('message', '')}\n"

        return md

    @staticmethod
    def metrics_markdown(data: dict) -> str:
        """Format instance metrics as markdown."""
        md = MarkdownFormatter.header("Instance Metrics", 1)

        if data.get("instance_name"):
            md += f"**Instance:** {data['instance_name']}\n"
        md += f"**Period:** {data.get('period_start', '—')} to {data.get('period_end', '—')}\n\n"

        metrics = data.get("metrics", {})

        if not metrics:
            md += "*No metrics data available for the specified period.*\n"
            return md

        for metric_name, metric_data in metrics.items():
            md += MarkdownFormatter.header(metric_name, 2)

            stats = metric_data.get("statistics", {})
            if stats:
                md += f"- **Average:** {stats.get('average', 0):.2f}%\n"
                md += f"- **Maximum:** {stats.get('max', 0):.2f}%\n"
                md += f"- **Minimum:** {stats.get('min', 0):.2f}%\n"

                # Add visual indicator for CPU
                avg = stats.get('average', 0)
                if avg > 80:
                    md += "- **Status:** 🔴 High utilization\n"
                elif avg > 50:
                    md += "- **Status:** 🟡 Moderate utilization\n"
                else:
                    md += "- **Status:** 🟢 Normal\n"

            md += "\n"

        return md
