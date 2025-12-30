"""
OCI Database Domain Tools

Provides tools for managing Oracle Cloud Infrastructure database services:
- Autonomous Database (ADB)
- DB Systems (BaseDB, Exadata)
- MySQL Database Service
"""

from .tools import register_database_tools

__all__ = ["register_database_tools"]
