"""
Response formatting utilities for consistent output.

Supports both markdown (human-readable) and JSON (machine-readable) formats.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel


class ResponseFormat(str, Enum):
    """Output format options for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


class Formatter:
    """Base formatter with common utilities."""

    @staticmethod
    def format_currency(amount: float | Decimal, currency: str = "USD") -> str:
        """Format monetary amount with symbol and commas."""
        return f"${amount:,.2f} {currency}"

    @staticmethod
    def format_datetime(dt: datetime | str, human_readable: bool = True) -> str:
        """Format datetime for display."""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except ValueError:
                return dt

        if human_readable:
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        return dt.isoformat()

    @staticmethod
    def format_date(dt: datetime | str) -> str:
        """Format date only (no time)."""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except ValueError:
                return dt
        return dt.strftime("%Y-%m-%d")

    @staticmethod
    def format_ocid(ocid: str, show_full: bool = False) -> str:
        """Format OCID with optional truncation for display."""
        if show_full or len(ocid) < 40:
            return ocid
        return f"{ocid[:20]}...{ocid[-10:]}"

    @staticmethod
    def format_bytes(size: int) -> str:
        """Format byte size to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"

    @staticmethod
    def format_percentage(value: float, decimals: int = 1) -> str:
        """Format percentage value."""
        return f"{value:.{decimals}f}%"

    @staticmethod
    def trend_indicator(current: float, previous: float) -> str:
        """Generate trend indicator (↑↓→) with percentage."""
        if previous == 0:
            return "→ N/A"
        change = ((current - previous) / previous) * 100
        if change > 5:
            return f"↑ {change:.1f}%"
        elif change < -5:
            return f"↓ {abs(change):.1f}%"
        return f"→ {abs(change):.1f}%"

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in human-readable form."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            mins = seconds / 60
            return f"{mins:.1f}m"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{hours:.1f}h"
        else:
            days = seconds / 86400
            return f"{days:.1f}d"


class MarkdownFormatter(Formatter):
    """Markdown-specific formatting utilities."""

    @staticmethod
    def header(text: str, level: int = 1) -> str:
        """Create markdown header."""
        return f"{'#' * level} {text}\n\n"

    @staticmethod
    def bold(text: str) -> str:
        """Format text as bold."""
        return f"**{text}**"

    @staticmethod
    def code(text: str) -> str:
        """Format text as inline code."""
        return f"`{text}`"

    @staticmethod
    def table(headers: list[str], rows: list[list[Any]]) -> str:
        """Generate markdown table."""
        if not headers or not rows:
            return ""

        lines = []
        # Header row
        lines.append("| " + " | ".join(str(h) for h in headers) + " |")
        # Separator
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        # Data rows
        for row in rows:
            cells = [str(cell) if cell is not None else "" for cell in row]
            lines.append("| " + " | ".join(cells) + " |")

        return "\n".join(lines) + "\n"

    @staticmethod
    def code_block(code: str, language: str = "") -> str:
        """Create markdown code block."""
        return f"```{language}\n{code}\n```\n"

    @staticmethod
    def bullet_list(items: list[str], indent: int = 0) -> str:
        """Create bullet point list."""
        prefix = "  " * indent
        return "\n".join(f"{prefix}- {item}" for item in items) + "\n"

    @staticmethod
    def numbered_list(items: list[str]) -> str:
        """Create numbered list."""
        return "\n".join(f"{i}. {item}" for i, item in enumerate(items, 1)) + "\n"

    @staticmethod
    def key_value(key: str, value: Any) -> str:
        """Format key-value pair."""
        return f"**{key}:** {value}\n"

    @staticmethod
    def horizontal_rule() -> str:
        """Create horizontal rule."""
        return "\n---\n\n"

    @staticmethod
    def blockquote(text: str) -> str:
        """Create blockquote."""
        lines = text.split("\n")
        return "\n".join(f"> {line}" for line in lines) + "\n"

    @staticmethod
    def status_badge(status: str) -> str:
        """Create status indicator with emoji."""
        status_lower = status.lower()
        badges = {
            "running": "🟢",
            "active": "🟢",
            "available": "🟢",
            "succeeded": "🟢",
            "stopped": "🔴",
            "terminated": "🔴",
            "failed": "🔴",
            "stopping": "🟡",
            "starting": "🟡",
            "pending": "🟡",
            "provisioning": "🟡",
            "updating": "🟡",
        }
        badge = badges.get(status_lower, "⚪")
        return f"{badge} {status}"


class JSONFormatter(Formatter):
    """JSON-specific formatting utilities."""

    @staticmethod
    def format(data: Any, indent: int = 2) -> str:
        """Format data as JSON string."""
        def default_serializer(obj: Any) -> Any:
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, BaseModel):
                return obj.model_dump()
            if isinstance(obj, Enum):
                return obj.value
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            return str(obj)

        return json.dumps(data, indent=indent, default=default_serializer)

    @staticmethod
    def format_compact(data: Any) -> str:
        """Format data as compact JSON (no indentation)."""
        def default_serializer(obj: Any) -> Any:
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, BaseModel):
                return obj.model_dump()
            if isinstance(obj, Enum):
                return obj.value
            return str(obj)

        return json.dumps(data, separators=(',', ':'), default=default_serializer)


def format_response(
    data: Any,
    response_format: ResponseFormat,
    markdown_template: Callable[[Any], str] | None = None
) -> str:
    """
    Format response based on requested format.

    Args:
        data: The data to format
        response_format: Output format (markdown or json)
        markdown_template: Optional function to generate custom markdown

    Returns:
        Formatted string response
    """
    if response_format == ResponseFormat.JSON:
        return JSONFormatter.format(data)

    if markdown_template:
        return markdown_template(data)

    # Default markdown formatting
    if isinstance(data, dict):
        return _dict_to_markdown(data)
    if isinstance(data, list):
        return MarkdownFormatter.bullet_list([str(item) for item in data])
    return str(data)


def _dict_to_markdown(data: dict, level: int = 1) -> str:
    """Convert dictionary to markdown format."""
    lines = []

    for key, value in data.items():
        formatted_key = key.replace("_", " ").title()

        if isinstance(value, dict):
            lines.append(MarkdownFormatter.header(formatted_key, level + 1))
            lines.append(_dict_to_markdown(value, level + 1))
        elif isinstance(value, list):
            lines.append(f"**{formatted_key}:**\n")
            if value and isinstance(value[0], dict):
                # List of dicts - try to make a table
                if all(isinstance(item, dict) for item in value):
                    headers = list(value[0].keys())
                    rows = [[item.get(h, "") for h in headers] for item in value]
                    lines.append(MarkdownFormatter.table(headers, rows))
            else:
                lines.append(MarkdownFormatter.bullet_list([str(item) for item in value]))
        else:
            lines.append(f"**{formatted_key}:** {value}\n")

    return "".join(lines)


def format_success_response(
    message: str,
    data: Any | None = None,
    response_format: ResponseFormat = ResponseFormat.MARKDOWN
) -> str:
    """
    Format a success response.

    Args:
        message: Success message
        data: Optional additional data
        response_format: Output format

    Returns:
        Formatted success response
    """
    if response_format == ResponseFormat.JSON:
        result = {"success": True, "message": message}
        if data is not None:
            result["data"] = data
        return JSONFormatter.format(result)

    md = f"## ✅ Success\n\n{message}\n"
    if data is not None:
        md += "\n" + _dict_to_markdown(data) if isinstance(data, dict) else str(data)
    return md
