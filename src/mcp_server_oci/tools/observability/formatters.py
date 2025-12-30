"""Observability domain-specific formatters.

Provides formatting utilities for metrics, logs, and monitoring data.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from mcp_server_oci.core.formatters import Formatter, MarkdownFormatter


class ObservabilityFormatter:
    """Observability-specific formatting utilities."""

    @staticmethod
    def to_json(data: Any) -> str:
        """Format as JSON."""
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def instance_metrics_markdown(data: dict) -> str:
        """Format instance metrics as markdown."""
        md = MarkdownFormatter.header("Instance Metrics", 1)

        md += f"**Instance:** {data.get('instance_name', data.get('instance_id', 'N/A'))}\n"
        md += f"**Time Window:** {data.get('window', 'N/A')}\n\n"

        # CPU metrics
        if "cpu" in data:
            cpu = data["cpu"]
            md += MarkdownFormatter.header("CPU Utilization", 2)
            md += f"- **Current:** {cpu.get('current', 'N/A')}%\n"
            md += f"- **Average:** {cpu.get('average', 'N/A')}%\n"
            md += f"- **Max:** {cpu.get('max', 'N/A')}%\n"
            md += f"- **Min:** {cpu.get('min', 'N/A')}%\n\n"

        # Memory metrics
        if "memory" in data:
            memory = data["memory"]
            md += MarkdownFormatter.header("Memory Utilization", 2)
            md += f"- **Current:** {memory.get('current', 'N/A')}%\n"
            md += f"- **Average:** {memory.get('average', 'N/A')}%\n"
            md += f"- **Max:** {memory.get('max', 'N/A')}%\n\n"

        # Disk metrics
        if "disk" in data:
            disk = data["disk"]
            md += MarkdownFormatter.header("Disk I/O", 2)
            md += f"- **Read IOPS:** {disk.get('read_iops', 'N/A')}\n"
            md += f"- **Write IOPS:** {disk.get('write_iops', 'N/A')}\n"
            md += f"- **Read Throughput:** {disk.get('read_throughput', 'N/A')} MB/s\n"
            md += f"- **Write Throughput:** {disk.get('write_throughput', 'N/A')} MB/s\n\n"

        # Trend indicator
        if "trend" in data:
            md += f"**Trend:** {data['trend']}\n"

        return md

    @staticmethod
    def log_results_markdown(data: dict) -> str:
        """Format Log Analytics query results as markdown."""
        md = MarkdownFormatter.header("Log Query Results", 1)

        md += f"**Query:** `{data.get('query', 'N/A')}`\n"
        md += f"**Time Range:** {data.get('time_range', 'N/A')}\n"
        md += f"**Results:** {data.get('total', 0)} rows\n\n"

        results = data.get("results", [])
        if not results:
            md += "*No results found.*\n"
            return md

        # Extract headers from first row
        headers = list(results[0].keys())

        # Build table
        rows = []
        for item in results[:20]:  # Limit rows in markdown
            row = [str(item.get(h, "")) for h in headers]
            rows.append(row)

        md += MarkdownFormatter.table(headers, rows)

        if len(results) > 20:
            md += f"\n*...and {len(results) - 20} more rows.*\n"

        return md

    @staticmethod
    def alarms_markdown(data: dict) -> str:
        """Format alarms list as markdown."""
        md = MarkdownFormatter.header("Monitoring Alarms", 1)

        md += f"**Total Alarms:** {data.get('total', 0)}\n\n"

        # Summary by severity
        if "summary" in data:
            summary = data["summary"]
            md += MarkdownFormatter.header("By Severity", 2)
            for severity, count in summary.items():
                icon = {"CRITICAL": "🔴", "WARNING": "🟠", "INFO": "🔵"}.get(severity, "⚪")
                md += f"- {icon} **{severity}:** {count}\n"
            md += "\n"

        # Alarm details
        alarms = data.get("alarms", [])
        if alarms:
            md += MarkdownFormatter.header("Alarm Details", 2)
            headers = ["Name", "Severity", "State", "Namespace", "Metric"]
            rows = [
                [
                    a.get("display_name", "N/A"),
                    a.get("severity", "N/A"),
                    a.get("lifecycle_state", "N/A"),
                    a.get("namespace", "N/A"),
                    a.get("metric_name", "N/A"),
                ]
                for a in alarms[:20]
            ]
            md += MarkdownFormatter.table(headers, rows)

        return md

    @staticmethod
    def alarm_history_markdown(data: dict) -> str:
        """Format alarm history as markdown."""
        md = MarkdownFormatter.header("Alarm History", 1)

        md += f"**Alarm:** {data.get('alarm_name', data.get('alarm_id', 'N/A'))}\n"
        md += f"**Time Window:** {data.get('window', 'N/A')}\n\n"

        events = data.get("events", [])
        if not events:
            md += "*No events in this time window.*\n"
            return md

        md += MarkdownFormatter.header("Events", 2)
        headers = ["Time", "Status", "Message"]
        rows = [
            [
                Formatter.format_datetime(e.get("timestamp", ""), human_readable=True),
                e.get("status", "N/A"),
                e.get("message", "")[:50] + "..." if len(e.get("message", "")) > 50 else e.get("message", ""),
            ]
            for e in events[:30]
        ]
        md += MarkdownFormatter.table(headers, rows)

        return md

    @staticmethod
    def log_sources_markdown(data: dict) -> str:
        """Format log sources list as markdown."""
        md = MarkdownFormatter.header("Log Analytics Sources", 1)

        md += f"**Total Sources:** {data.get('total', 0)}\n\n"

        sources = data.get("sources", [])
        if not sources:
            md += "*No log sources found.*\n"
            return md

        headers = ["Name", "Type", "Entity Types", "Status"]
        rows = [
            [
                s.get("name", "N/A"),
                s.get("source_type", "N/A"),
                ", ".join(s.get("entity_types", []))[:30],
                s.get("lifecycle_state", "N/A"),
            ]
            for s in sources[:20]
        ]
        md += MarkdownFormatter.table(headers, rows)

        if len(sources) > 20:
            md += f"\n*...and {len(sources) - 20} more sources.*\n"

        return md

    @staticmethod
    def observability_overview_markdown(data: dict) -> str:
        """Format observability overview as markdown."""
        md = MarkdownFormatter.header("Observability Overview", 1)

        md += f"**Compartment:** {data.get('compartment_name', 'Tenancy Root')}\n"
        md += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"

        # Alarms summary
        if "alarms_summary" in data:
            alarms = data["alarms_summary"]
            md += MarkdownFormatter.header("Active Alarms", 2)
            md += f"- **Total:** {alarms.get('total', 0)}\n"
            if alarms.get("by_severity"):
                for severity, count in alarms["by_severity"].items():
                    icon = {"CRITICAL": "🔴", "WARNING": "🟠", "INFO": "🔵"}.get(severity, "⚪")
                    md += f"- {icon} {severity}: {count}\n"
            md += "\n"

        # Log sources summary
        if "log_sources_summary" in data:
            sources = data["log_sources_summary"]
            md += MarkdownFormatter.header("Log Analytics Sources", 2)
            md += f"- **Total Sources:** {sources.get('total', 0)}\n"
            if sources.get("by_type"):
                for source_type, count in sources["by_type"].items():
                    md += f"- **{source_type}:** {count}\n"
            md += "\n"

        # Recommendations
        if "recommendations" in data and data["recommendations"]:
            md += MarkdownFormatter.header("Recommendations", 2)
            for rec in data["recommendations"]:
                md += f"- {rec}\n"

        return md
