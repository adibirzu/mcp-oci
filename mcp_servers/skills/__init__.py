"""
MCP-OCI Skills Layer

Composable skills for OCI infrastructure management following the skillz pattern.
Each skill orchestrates multiple tools to accomplish complex tasks.

Skills:
- CostAnalysisSkill: Cost analysis, trending, and optimization
- InventoryAuditSkill: Resource discovery and capacity planning
- NetworkDiagnosticsSkill: Network topology analysis and troubleshooting
"""

from .adapters import (
    CostClientAdapter,
    InventoryClientAdapter,
    NetworkClientAdapter
)
from .cost_analysis import CostAnalysisSkill
from .inventory_audit import InventoryAuditSkill
from .network_diagnostics import NetworkDiagnosticsSkill

__all__ = [
    # Adapters
    'CostClientAdapter',
    'InventoryClientAdapter',
    'NetworkClientAdapter',
    # Skills
    'CostAnalysisSkill',
    'InventoryAuditSkill',
    'NetworkDiagnosticsSkill',
]
