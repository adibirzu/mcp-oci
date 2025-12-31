"""Security domain-specific formatters.

Provides markdown and JSON formatting for IAM, Cloud Guard, and security data.
"""

from __future__ import annotations

import json
from typing import Any

from mcp_server_oci.core.formatters import Formatter, MarkdownFormatter


class SecurityFormatter:
    """Security-specific formatting utilities."""

    @staticmethod
    def to_json(data: Any) -> str:
        """Format as JSON."""
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def users_markdown(data: dict) -> str:
        """Format users list as markdown."""
        md = MarkdownFormatter.header("IAM Users", 1)

        md += f"**Total Users:** {data.get('total', 0)}\n"
        md += f"**Compartment:** {data.get('compartment_name', 'Tenancy Root')}\n\n"

        users = data.get("users", [])
        if not users:
            md += "_No users found matching the criteria._\n"
            return md

        headers = ["Name", "Email", "State", "Created"]
        rows = []
        for user in users:
            rows.append([
                user.get("name", "N/A"),
                user.get("email", "N/A"),
                user.get("lifecycle_state", "N/A"),
                Formatter.format_datetime(user.get("time_created", "")) if user.get("time_created") else "N/A",
            ])

        md += MarkdownFormatter.table(headers, rows)

        # Add summary
        active_count = sum(1 for u in users if u.get("lifecycle_state") == "ACTIVE")
        md += f"\n**Active Users:** {active_count} / {len(users)}\n"

        return md

    @staticmethod
    def user_detail_markdown(data: dict) -> str:
        """Format user details as markdown."""
        user = data.get("user", {})

        md = MarkdownFormatter.header(f"User: {user.get('name', 'Unknown')}", 1)

        md += "## Details\n"
        md += f"- **OCID:** `{Formatter.format_ocid(user.get('id', ''))}`\n"
        md += f"- **Email:** {user.get('email', 'N/A')}\n"
        md += f"- **State:** {user.get('lifecycle_state', 'N/A')}\n"
        md += f"- **Created:** {Formatter.format_datetime(user.get('time_created', '')) if user.get('time_created') else 'N/A'}\n"
        md += f"- **Description:** {user.get('description', 'N/A')}\n"

        # Groups
        groups = data.get("groups", [])
        if groups:
            md += "\n## Group Memberships\n"
            for group in groups:
                md += f"- {group.get('name', 'Unknown')}\n"

        # API Keys
        api_keys = data.get("api_keys", [])
        if api_keys:
            md += "\n## API Keys\n"
            headers = ["Fingerprint", "State", "Created"]
            rows = []
            for key in api_keys:
                rows.append([
                    key.get("fingerprint", "N/A")[:20] + "...",
                    key.get("lifecycle_state", "N/A"),
                    Formatter.format_datetime(key.get("time_created", "")) if key.get("time_created") else "N/A",
                ])
            md += MarkdownFormatter.table(headers, rows)

        return md

    @staticmethod
    def groups_markdown(data: dict) -> str:
        """Format groups list as markdown."""
        md = MarkdownFormatter.header("IAM Groups", 1)

        md += f"**Total Groups:** {data.get('total', 0)}\n\n"

        groups = data.get("groups", [])
        if not groups:
            md += "_No groups found._\n"
            return md

        headers = ["Name", "Description", "Created"]
        rows = []
        for group in groups:
            rows.append([
                group.get("name", "N/A"),
                (group.get("description", "N/A") or "N/A")[:50],
                Formatter.format_datetime(group.get("time_created", "")) if group.get("time_created") else "N/A",
            ])

        md += MarkdownFormatter.table(headers, rows)
        return md

    @staticmethod
    def policies_markdown(data: dict) -> str:
        """Format policies list as markdown."""
        md = MarkdownFormatter.header("IAM Policies", 1)

        md += f"**Total Policies:** {data.get('total', 0)}\n"
        md += f"**Compartment:** {data.get('compartment_name', 'N/A')}\n\n"

        policies = data.get("policies", [])
        if not policies:
            md += "_No policies found._\n"
            return md

        for policy in policies:
            md += f"### {policy.get('name', 'Unknown')}\n"
            md += f"**OCID:** `{Formatter.format_ocid(policy.get('id', ''))}`\n"
            md += f"**Description:** {policy.get('description', 'N/A')}\n"

            statements = policy.get("statements", [])
            if statements:
                md += "**Statements:**\n"
                for i, stmt in enumerate(statements[:5], 1):  # Limit to first 5
                    md += f"{i}. `{stmt[:80]}{'...' if len(stmt) > 80 else ''}`\n"
                if len(statements) > 5:
                    md += f"_...and {len(statements) - 5} more statements_\n"
            md += "\n"

        return md

    @staticmethod
    def cloud_guard_problems_markdown(data: dict) -> str:
        """Format Cloud Guard problems as markdown."""
        md = MarkdownFormatter.header("Cloud Guard Problems", 1)

        md += f"**Total Problems:** {data.get('total', 0)}\n"

        # Risk level summary
        summary = data.get("summary", {})
        if summary:
            md += "\n## Risk Summary\n"
            md += f"- 🔴 **Critical:** {summary.get('CRITICAL', 0)}\n"
            md += f"- 🟠 **High:** {summary.get('HIGH', 0)}\n"
            md += f"- 🟡 **Medium:** {summary.get('MEDIUM', 0)}\n"
            md += f"- 🟢 **Low:** {summary.get('LOW', 0)}\n"
            md += f"- ⚪ **Minor:** {summary.get('MINOR', 0)}\n"

        problems = data.get("problems", [])
        if not problems:
            md += "\n_No problems found._\n"
            return md

        md += "\n## Problems\n"

        # Group by risk level
        risk_icons = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢",
            "MINOR": "⚪",
        }

        for problem in problems:
            risk = problem.get("risk_level", "UNKNOWN")
            icon = risk_icons.get(risk, "❓")

            md += f"### {icon} {problem.get('problem_name', 'Unknown Problem')}\n"
            md += f"- **Risk Level:** {risk}\n"
            md += f"- **Resource:** {problem.get('resource_name', 'N/A')}\n"
            md += f"- **Type:** {problem.get('resource_type', 'N/A')}\n"
            md += f"- **Region:** {problem.get('region', 'N/A')}\n"
            md += f"- **First Detected:** {Formatter.format_datetime(problem.get('time_first_detected', '')) if problem.get('time_first_detected') else 'N/A'}\n"

            recommendation = problem.get("recommendation", "")
            if recommendation:
                md += f"- **Recommendation:** {recommendation[:100]}{'...' if len(recommendation) > 100 else ''}\n"
            md += "\n"

        return md

    @staticmethod
    def security_audit_markdown(data: dict) -> str:
        """Format security audit results as markdown."""
        md = MarkdownFormatter.header("Security Audit Report", 1)

        md += f"**Audit Time:** {data.get('audit_time', 'N/A')}\n"
        md += f"**Compartment:** {data.get('compartment_name', 'Tenancy Root')}\n\n"

        # Overall score
        score = data.get("security_score", {})
        if score:
            md += "## Security Score\n"
            overall = score.get("overall", 0)
            grade = "🟢 Good" if overall >= 80 else "🟡 Fair" if overall >= 60 else "🔴 Needs Attention"
            md += f"**Overall Score:** {overall}/100 - {grade}\n\n"

        # IAM Summary
        iam = data.get("iam_summary", {})
        if iam:
            md += "## IAM Summary\n"
            md += f"- **Users:** {iam.get('total_users', 0)} (Active: {iam.get('active_users', 0)})\n"
            md += f"- **Groups:** {iam.get('total_groups', 0)}\n"
            md += f"- **Policies:** {iam.get('total_policies', 0)}\n"

            findings = iam.get("findings", [])
            if findings:
                md += "\n**Findings:**\n"
                for finding in findings:
                    md += f"- ⚠️ {finding}\n"
            md += "\n"

        # Cloud Guard Summary
        cloud_guard = data.get("cloud_guard_summary", {})
        if cloud_guard:
            md += "## Cloud Guard Summary\n"
            md += f"- **Critical Problems:** {cloud_guard.get('critical', 0)}\n"
            md += f"- **High Problems:** {cloud_guard.get('high', 0)}\n"
            md += f"- **Medium Problems:** {cloud_guard.get('medium', 0)}\n"
            md += f"- **Total Active Problems:** {cloud_guard.get('total', 0)}\n\n"

        # Network Security Summary
        network = data.get("network_summary", {})
        if network:
            md += "## Network Security Summary\n"
            md += f"- **VCNs:** {network.get('total_vcns', 0)}\n"
            md += f"- **Public Subnets:** {network.get('public_subnets', 0)}\n"
            md += f"- **Open Security Rules:** {network.get('open_rules', 0)}\n"

            findings = network.get("findings", [])
            if findings:
                md += "\n**Findings:**\n"
                for finding in findings:
                    md += f"- ⚠️ {finding}\n"
            md += "\n"

        # Recommendations
        recommendations = data.get("recommendations", [])
        if recommendations:
            md += "## Recommendations\n"
            for i, rec in enumerate(recommendations, 1):
                md += f"{i}. {rec}\n"

        return md
