"""
MCP-OCI Skills Layer

Composable skills for OCI infrastructure management following the skillz pattern.
Each skill orchestrates multiple tools to accomplish complex tasks.

Skills:
- CostAnalysisSkill: Cost analysis, trending, and optimization
- InventoryAuditSkill: Resource discovery and capacity planning
- NetworkDiagnosticsSkill: Network topology analysis and troubleshooting

Skill Tools (MCP-exposed):
- skill_analyze_cost_trend: Analyze cost trends with forecasting
- skill_detect_cost_anomalies: Detect cost anomalies with explanations
- skill_get_service_breakdown: Get service cost breakdown
- skill_generate_cost_optimization_report: Generate full cost report
- skill_run_infrastructure_discovery: Run full infrastructure discovery
- skill_generate_capacity_report: Generate capacity planning report
- skill_detect_infrastructure_changes: Detect infrastructure changes
- skill_generate_infrastructure_audit: Generate infrastructure audit
- skill_analyze_network_topology: Analyze network topology
- skill_assess_network_security: Assess network security posture
- skill_diagnose_network_connectivity: Diagnose connectivity
- skill_generate_network_report: Generate network diagnostic report
"""

from .adapters import (
    CostClientAdapter,
    InventoryClientAdapter,
    NetworkClientAdapter
)
from .cost_analysis import CostAnalysisSkill
from .inventory_audit import InventoryAuditSkill
from .network_diagnostics import NetworkDiagnosticsSkill
from .tools_skills import (
    # Cost Analysis Skill Tools
    skill_analyze_cost_trend,
    skill_detect_cost_anomalies,
    skill_get_service_breakdown,
    skill_generate_cost_optimization_report,
    # Inventory Audit Skill Tools
    skill_run_infrastructure_discovery,
    skill_generate_capacity_report,
    skill_detect_infrastructure_changes,
    skill_generate_infrastructure_audit,
    # Network Diagnostics Skill Tools
    skill_analyze_network_topology,
    skill_assess_network_security,
    skill_diagnose_network_connectivity,
    skill_generate_network_report,
    # Utilities
    get_skill_tools,
    get_skill_tool,
    SKILL_TOOLS
)

__all__ = [
    # Adapters
    'CostClientAdapter',
    'InventoryClientAdapter',
    'NetworkClientAdapter',
    # Skills
    'CostAnalysisSkill',
    'InventoryAuditSkill',
    'NetworkDiagnosticsSkill',
    # Skill Tools (MCP-exposed functions)
    'skill_analyze_cost_trend',
    'skill_detect_cost_anomalies',
    'skill_get_service_breakdown',
    'skill_generate_cost_optimization_report',
    'skill_run_infrastructure_discovery',
    'skill_generate_capacity_report',
    'skill_detect_infrastructure_changes',
    'skill_generate_infrastructure_audit',
    'skill_analyze_network_topology',
    'skill_assess_network_security',
    'skill_diagnose_network_connectivity',
    'skill_generate_network_report',
    # Utilities
    'get_skill_tools',
    'get_skill_tool',
    'SKILL_TOOLS',
]
