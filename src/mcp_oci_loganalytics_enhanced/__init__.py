"""Enhanced OCI Log Analytics MCP Server

This module provides advanced Log Analytics capabilities including:
- Security event analysis
- MITRE ATT&CK technique mapping
- IP activity analysis
- Advanced analytics and statistical operations
- Query validation and documentation
"""

from .server import register_tools

__all__ = ["register_tools"]
