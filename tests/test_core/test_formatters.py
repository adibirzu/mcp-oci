"""
Tests for core formatters module.
"""
from __future__ import annotations

import json
import pytest
from datetime import datetime
from decimal import Decimal

from mcp_server_oci.core.formatters import (
    ResponseFormat,
    Formatter,
    MarkdownFormatter,
    JSONFormatter,
    format_response,
)


class TestFormatter:
    """Tests for base Formatter class."""
    
    def test_format_currency_usd(self):
        """Test USD currency formatting."""
        result = Formatter.format_currency(1234.56, "USD")
        assert result == "$1,234.56 USD"
    
    def test_format_currency_large_amount(self):
        """Test large amount formatting with commas."""
        result = Formatter.format_currency(1234567.89)
        assert result == "$1,234,567.89 USD"
    
    def test_format_currency_zero(self):
        """Test zero amount formatting."""
        result = Formatter.format_currency(0)
        assert result == "$0.00 USD"
    
    def test_format_currency_decimal(self):
        """Test Decimal input."""
        result = Formatter.format_currency(Decimal("99.99"))
        assert result == "$99.99 USD"
    
    def test_format_datetime_human_readable(self):
        """Test human-readable datetime formatting."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = Formatter.format_datetime(dt, human_readable=True)
        assert "2024-01-15" in result
        assert "10:30:45" in result
    
    def test_format_datetime_iso(self):
        """Test ISO datetime formatting."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = Formatter.format_datetime(dt, human_readable=False)
        assert "2024-01-15" in result
    
    def test_format_datetime_string_input(self):
        """Test string datetime input."""
        result = Formatter.format_datetime("2024-01-15T10:30:45Z", human_readable=True)
        assert "2024-01-15" in result
    
    def test_format_ocid_truncation(self):
        """Test OCID truncation for display."""
        long_ocid = "ocid1.instance.oc1.iad.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        result = Formatter.format_ocid(long_ocid, show_full=False)
        assert "..." in result
        assert len(result) < len(long_ocid)
    
    def test_format_ocid_full(self):
        """Test full OCID display."""
        long_ocid = "ocid1.instance.oc1.iad.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        result = Formatter.format_ocid(long_ocid, show_full=True)
        assert result == long_ocid
    
    def test_format_ocid_short(self):
        """Test short OCID (no truncation needed)."""
        short_ocid = "ocid1.instance.oc1"
        result = Formatter.format_ocid(short_ocid)
        assert result == short_ocid
    
    def test_format_bytes_bytes(self):
        """Test byte formatting."""
        assert Formatter.format_bytes(512) == "512.00 B"
    
    def test_format_bytes_kilobytes(self):
        """Test KB formatting."""
        result = Formatter.format_bytes(2048)
        assert "KB" in result
    
    def test_format_bytes_megabytes(self):
        """Test MB formatting."""
        result = Formatter.format_bytes(5 * 1024 * 1024)
        assert "MB" in result
    
    def test_format_bytes_gigabytes(self):
        """Test GB formatting."""
        result = Formatter.format_bytes(10 * 1024 * 1024 * 1024)
        assert "GB" in result
    
    def test_trend_indicator_up(self):
        """Test upward trend indicator."""
        result = Formatter.trend_indicator(120, 100)
        assert "↑" in result
        assert "20" in result
    
    def test_trend_indicator_down(self):
        """Test downward trend indicator."""
        result = Formatter.trend_indicator(80, 100)
        assert "↓" in result
        assert "20" in result
    
    def test_trend_indicator_stable(self):
        """Test stable trend indicator."""
        result = Formatter.trend_indicator(101, 100)
        assert "→" in result
    
    def test_trend_indicator_zero_previous(self):
        """Test trend with zero previous value."""
        result = Formatter.trend_indicator(100, 0)
        assert "→" in result


class TestMarkdownFormatter:
    """Tests for MarkdownFormatter class."""
    
    def test_header_h1(self):
        """Test H1 header generation."""
        result = MarkdownFormatter.header("Title", level=1)
        assert result == "# Title\n\n"
    
    def test_header_h2(self):
        """Test H2 header generation."""
        result = MarkdownFormatter.header("Subtitle", level=2)
        assert result == "## Subtitle\n\n"
    
    def test_header_h3(self):
        """Test H3 header generation."""
        result = MarkdownFormatter.header("Section", level=3)
        assert result == "### Section\n\n"
    
    def test_table_basic(self):
        """Test basic table generation."""
        headers = ["Name", "Value"]
        rows = [["Item 1", "100"], ["Item 2", "200"]]
        result = MarkdownFormatter.table(headers, rows)
        
        assert "| Name | Value |" in result
        assert "| --- | --- |" in result
        assert "| Item 1 | 100 |" in result
        assert "| Item 2 | 200 |" in result
    
    def test_table_empty_rows(self):
        """Test table with no rows returns empty string."""
        headers = ["Name", "Value"]
        rows = []
        result = MarkdownFormatter.table(headers, rows)
        
        # Empty rows returns empty string (no table rendered)
        assert result == ""
    
    def test_code_block_python(self):
        """Test code block with language."""
        result = MarkdownFormatter.code_block("print('hello')", language="python")
        assert "```python\n" in result
        assert "print('hello')" in result
        assert "```\n" in result
    
    def test_code_block_no_language(self):
        """Test code block without language."""
        result = MarkdownFormatter.code_block("some code")
        assert "```\n" in result
    
    def test_bullet_list(self):
        """Test bullet list generation."""
        items = ["First item", "Second item", "Third item"]
        result = MarkdownFormatter.bullet_list(items)
        
        assert "- First item" in result
        assert "- Second item" in result
        assert "- Third item" in result


class TestJSONFormatter:
    """Tests for JSONFormatter class."""
    
    def test_format_dict(self):
        """Test dictionary formatting."""
        data = {"key": "value", "number": 42}
        result = JSONFormatter.format(data)
        parsed = json.loads(result)
        
        assert parsed["key"] == "value"
        assert parsed["number"] == 42
    
    def test_format_list(self):
        """Test list formatting."""
        data = [1, 2, 3, "four"]
        result = JSONFormatter.format(data)
        parsed = json.loads(result)
        
        assert parsed == [1, 2, 3, "four"]
    
    def test_format_datetime(self):
        """Test datetime serialization."""
        data = {"timestamp": datetime(2024, 1, 15, 10, 30, 0)}
        result = JSONFormatter.format(data)
        parsed = json.loads(result)
        
        assert "2024-01-15" in parsed["timestamp"]
    
    def test_format_decimal(self):
        """Test Decimal serialization."""
        data = {"amount": Decimal("123.45")}
        result = JSONFormatter.format(data)
        parsed = json.loads(result)
        
        assert parsed["amount"] == 123.45
    
    def test_format_nested(self):
        """Test nested structure formatting."""
        data = {
            "level1": {
                "level2": {
                    "value": 42
                }
            }
        }
        result = JSONFormatter.format(data)
        parsed = json.loads(result)
        
        assert parsed["level1"]["level2"]["value"] == 42
    
    def test_format_indent(self):
        """Test custom indentation."""
        data = {"key": "value"}
        result = JSONFormatter.format(data, indent=4)
        
        # Count spaces in indentation
        lines = result.split("\n")
        assert any("    " in line for line in lines)


class TestFormatResponse:
    """Tests for format_response function."""
    
    def test_format_json(self):
        """Test JSON format selection."""
        data = {"key": "value"}
        result = format_response(data, ResponseFormat.JSON)
        parsed = json.loads(result)
        
        assert parsed["key"] == "value"
    
    def test_format_markdown_with_template(self):
        """Test Markdown format with custom template."""
        data = {"title": "Test", "value": 42}
        
        def template(d):
            return f"# {d['title']}\nValue: {d['value']}"
        
        result = format_response(data, ResponseFormat.MARKDOWN, markdown_template=template)
        
        assert "# Test" in result
        assert "Value: 42" in result
    
    def test_format_markdown_fallback(self):
        """Test Markdown format converts dict to readable markdown."""
        data = {"key": "value"}
        result = format_response(data, ResponseFormat.MARKDOWN)
        
        # Should convert to markdown key-value format
        assert "Key" in result  # Title-cased key
        assert "value" in result
    
    def test_format_list_markdown(self):
        """Test list formatting in Markdown."""
        data = ["item1", "item2", "item3"]
        result = format_response(data, ResponseFormat.MARKDOWN)
        
        assert "- item1" in result
        assert "- item2" in result
