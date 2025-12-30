"""
Database domain-specific formatters.
"""
from __future__ import annotations

from typing import Any

from ...core.formatters import Formatter, MarkdownFormatter, JSONFormatter, ResponseFormat


class DatabaseFormatter:
    """Database-specific formatting utilities."""
    
    @staticmethod
    def to_json(data: Any) -> str:
        """Format as JSON."""
        return JSONFormatter.format(data)
    
    @staticmethod
    def autonomous_list_markdown(data: dict) -> str:
        """Format Autonomous Database list as markdown."""
        md = MarkdownFormatter.header("Autonomous Databases", 1)
        
        # Summary
        total = data.get("total", 0)
        count = data.get("count", 0)
        md += f"**Showing:** {count} of {total} databases\n\n"
        
        if not data.get("items"):
            md += "*No Autonomous Databases found matching the criteria.*\n"
            return md
        
        # Table of databases
        headers = ["Name", "State", "Workload", "OCPUs", "Storage (TB)", "Free Tier"]
        rows = []
        for db in data["items"]:
            rows.append([
                db.get("display_name", "N/A"),
                _state_badge(db.get("lifecycle_state", "")),
                db.get("db_workload", "N/A"),
                str(db.get("cpu_core_count", 0)),
                str(db.get("data_storage_size_in_tbs", 0)),
                "✅" if db.get("is_free_tier") else "❌"
            ])
        md += MarkdownFormatter.table(headers, rows)
        
        # Pagination info
        if data.get("has_more"):
            md += f"\n*More results available. Use offset={data.get('next_offset', 0)} to continue.*\n"
        
        return md
    
    @staticmethod
    def autonomous_detail_markdown(db: dict) -> str:
        """Format single Autonomous Database details as markdown."""
        md = MarkdownFormatter.header(db.get("display_name", "Autonomous Database"), 1)
        
        # Status badge
        state = db.get("lifecycle_state", "UNKNOWN")
        md += f"**Status:** {_state_badge(state)}\n\n"
        
        # Basic info
        md += MarkdownFormatter.header("Configuration", 2)
        md += f"- **Database Name:** {db.get('db_name', 'N/A')}\n"
        md += f"- **Workload Type:** {db.get('db_workload', 'N/A')}\n"
        md += f"- **OCPUs:** {db.get('cpu_core_count', 0)}\n"
        md += f"- **Storage:** {db.get('data_storage_size_in_tbs', 0)} TB\n"
        md += f"- **Free Tier:** {'Yes' if db.get('is_free_tier') else 'No'}\n"
        md += f"- **Auto Scaling:** {'Enabled' if db.get('is_auto_scaling_enabled') else 'Disabled'}\n"
        md += f"- **Created:** {Formatter.format_datetime(db.get('time_created', ''))}\n\n"
        
        # Connection info
        if db.get("connection_strings"):
            md += MarkdownFormatter.header("Connection", 2)
            conn = db["connection_strings"]
            if conn.get("high"):
                md += f"**High (OLTP):**\n```\n{conn['high']}\n```\n"
            if conn.get("medium"):
                md += f"**Medium:**\n```\n{conn['medium']}\n```\n"
            if conn.get("low"):
                md += f"**Low (Batch):**\n```\n{conn['low']}\n```\n"
        
        # OCID
        md += MarkdownFormatter.header("Identifiers", 2)
        md += f"- **OCID:** `{db.get('id', 'N/A')}`\n"
        md += f"- **Compartment:** `{db.get('compartment_id', 'N/A')}`\n"
        
        return md
    
    @staticmethod
    def dbsystem_list_markdown(data: dict) -> str:
        """Format DB System list as markdown."""
        md = MarkdownFormatter.header("DB Systems", 1)
        
        total = data.get("total", 0)
        count = data.get("count", 0)
        md += f"**Showing:** {count} of {total} DB Systems\n\n"
        
        if not data.get("items"):
            md += "*No DB Systems found matching the criteria.*\n"
            return md
        
        headers = ["Name", "State", "Shape", "Nodes", "Storage (GB)", "AD"]
        rows = []
        for db in data["items"]:
            rows.append([
                db.get("display_name", "N/A"),
                _state_badge(db.get("lifecycle_state", "")),
                db.get("shape", "N/A"),
                str(db.get("node_count", 1)),
                str(db.get("data_storage_size_in_gbs", 0)),
                _short_ad(db.get("availability_domain", ""))
            ])
        md += MarkdownFormatter.table(headers, rows)
        
        if data.get("has_more"):
            md += f"\n*More results available. Use offset={data.get('next_offset', 0)} to continue.*\n"
        
        return md
    
    @staticmethod
    def backup_list_markdown(data: dict) -> str:
        """Format database backups as markdown."""
        md = MarkdownFormatter.header("Database Backups", 1)
        
        if not data.get("items"):
            md += "*No backups found.*\n"
            return md
        
        headers = ["Database", "Type", "State", "Size (GB)", "Created"]
        rows = []
        for backup in data["items"]:
            rows.append([
                backup.get("database_name", backup.get("database_id", "N/A")[:20] + "..."),
                backup.get("type", "N/A"),
                _state_badge(backup.get("lifecycle_state", "")),
                str(backup.get("database_size_in_gbs", 0)),
                Formatter.format_datetime(backup.get("time_started", ""), human_readable=True)
            ])
        md += MarkdownFormatter.table(headers, rows)
        
        return md
    
    @staticmethod
    def metrics_markdown(data: dict) -> str:
        """Format database metrics as markdown."""
        md = MarkdownFormatter.header("Database Metrics", 1)
        
        db_info = data.get("database", {})
        md += f"**Database:** {db_info.get('display_name', 'N/A')}\n"
        md += f"**Period:** Last {data.get('hours_back', 24)} hours\n\n"
        
        metrics = data.get("metrics", {})
        if not metrics:
            md += "*No metrics data available.*\n"
            return md
        
        for metric_name, metric_data in metrics.items():
            md += MarkdownFormatter.header(metric_name.replace("_", " ").title(), 2)
            
            if metric_data.get("current") is not None:
                md += f"- **Current:** {metric_data['current']:.2f}%\n"
            if metric_data.get("average") is not None:
                md += f"- **Average:** {metric_data['average']:.2f}%\n"
            if metric_data.get("max") is not None:
                md += f"- **Peak:** {metric_data['max']:.2f}%\n"
            if metric_data.get("min") is not None:
                md += f"- **Minimum:** {metric_data['min']:.2f}%\n"
            md += "\n"
        
        return md
    
    @staticmethod
    def action_result_markdown(action: str, database: dict, success: bool, message: str = "") -> str:
        """Format database action result as markdown."""
        md = MarkdownFormatter.header(f"Database {action.title()}", 1)
        
        if success:
            md += f"✅ **Success**\n\n"
        else:
            md += f"❌ **Failed**\n\n"
        
        md += f"**Database:** {database.get('display_name', 'N/A')}\n"
        md += f"**Current State:** {_state_badge(database.get('lifecycle_state', ''))}\n"
        
        if message:
            md += f"\n{message}\n"
        
        return md


def _state_badge(state: str) -> str:
    """Convert lifecycle state to emoji badge."""
    state_badges = {
        "AVAILABLE": "🟢 Available",
        "RUNNING": "🟢 Running",
        "PROVISIONING": "🔵 Provisioning",
        "STARTING": "🔵 Starting",
        "STOPPING": "🟡 Stopping",
        "STOPPED": "🔴 Stopped",
        "TERMINATED": "⚫ Terminated",
        "TERMINATING": "🟡 Terminating",
        "UNAVAILABLE": "🔴 Unavailable",
        "UPDATING": "🔵 Updating",
        "MAINTENANCE_IN_PROGRESS": "🟡 Maintenance",
        "BACKUP_IN_PROGRESS": "🔵 Backup in Progress",
        "RESTORE_IN_PROGRESS": "🔵 Restore in Progress",
        "SCALE_IN_PROGRESS": "🔵 Scaling",
    }
    return state_badges.get(state, f"⚪ {state}")


def _short_ad(ad: str) -> str:
    """Extract short AD name from full AD string."""
    if not ad:
        return "N/A"
    # Example: "Uocm:PHX-AD-1" -> "AD-1"
    parts = ad.split("-")
    if len(parts) >= 2:
        return f"AD-{parts[-1]}"
    return ad
