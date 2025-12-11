"""
MCP-OCI Skill Tool Wrappers

This module provides MCP tool wrappers for all skills, making them
directly callable by agents through the MCP protocol.

Skills are organized by category:
- Cost Analysis (4 tools)
- Inventory Audit (4 tools)
- Network Diagnostics (4 tools)
- Compute Management (4 tools)
- Security Posture (3 tools)

Total: 19 skill-based tools
"""

from typing import Dict, Any, Optional


# =============================================================================
# Cost Analysis Skills
# =============================================================================

def skill_analyze_cost_trend(
    tenancy_ocid: str,
    months_back: int = 6,
    budget_ocid: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze cost trends over time with forecasting.
    
    Args:
        tenancy_ocid: Tenancy OCID to analyze
        months_back: Number of months to analyze (default: 6)
        budget_ocid: Optional budget OCID for comparison
    
    Returns:
        Dictionary with trend analysis including direction, change percentage,
        forecast, and recommendations.
    """
    from .cost_analysis import CostAnalysisSkill
    from .adapters import get_cost_client_adapter
    skill = CostAnalysisSkill(client=get_cost_client_adapter())
    return skill.analyze_cost_trend(tenancy_ocid, months_back, budget_ocid)


def skill_detect_cost_anomalies(
    tenancy_ocid: str,
    time_start: str,
    time_end: str,
    top_n: int = 5
) -> Dict[str, Any]:
    """
    Detect cost anomalies and spikes with root cause explanations.
    
    Args:
        tenancy_ocid: Tenancy OCID to analyze
        time_start: Start time (ISO format)
        time_end: End time (ISO format)
        top_n: Number of top anomalies to return
    
    Returns:
        Dictionary with anomalies classified by severity, with service and
        compartment breakdown for each spike.
    """
    from .cost_analysis import CostAnalysisSkill
    from .adapters import get_cost_client_adapter
    skill = CostAnalysisSkill(client=get_cost_client_adapter())
    return skill.detect_anomalies(tenancy_ocid, time_start, time_end, top_n)


def skill_get_service_breakdown(
    tenancy_ocid: str,
    time_start: str,
    time_end: str,
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Get detailed service cost breakdown with optimization potential.
    
    Args:
        tenancy_ocid: Tenancy OCID to analyze
        time_start: Start time (ISO format)
        time_end: End time (ISO format)
        top_n: Number of top services to return
    
    Returns:
        Dictionary with top services by cost, including compartment details
        and optimization potential classification.
    """
    from .cost_analysis import CostAnalysisSkill
    from .adapters import get_cost_client_adapter
    skill = CostAnalysisSkill(client=get_cost_client_adapter())
    return skill.get_service_breakdown(tenancy_ocid, time_start, time_end, top_n)


def skill_generate_cost_optimization_report(
    tenancy_ocid: str,
    months_back: int = 3
) -> Dict[str, Any]:
    """
    Generate comprehensive cost optimization report.
    
    Combines trend analysis, anomaly detection, and service breakdown
    into a single executive report with actionable recommendations.
    
    Args:
        tenancy_ocid: Tenancy OCID to analyze
        months_back: Months to analyze for trends
    
    Returns:
        Comprehensive report with executive summary and recommendations.
    """
    from .cost_analysis import CostAnalysisSkill
    from .adapters import get_cost_client_adapter
    skill = CostAnalysisSkill(client=get_cost_client_adapter())
    return skill.generate_optimization_report(tenancy_ocid, months_back)


# =============================================================================
# Inventory Audit Skills
# =============================================================================

def skill_run_infrastructure_discovery(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run full infrastructure discovery with health assessment.
    
    Args:
        compartment_id: Optional compartment filter
        region: Optional region filter
    
    Returns:
        Complete resource inventory with health assessment and tagging compliance.
    """
    from .inventory_audit import InventoryAuditSkill
    from .adapters import get_inventory_client_adapter
    skill = InventoryAuditSkill(client=get_inventory_client_adapter())
    return skill.run_full_discovery(compartment_id, region)


def skill_generate_capacity_report(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate compute capacity planning report with utilization analysis.
    
    Args:
        compartment_id: Optional compartment filter
        region: Optional region filter
    
    Returns:
        Capacity report with utilization metrics, shape analysis, and
        optimization recommendations.
    """
    from .inventory_audit import InventoryAuditSkill
    from .adapters import get_inventory_client_adapter
    skill = InventoryAuditSkill(client=get_inventory_client_adapter())
    return skill.generate_capacity_report(compartment_id, region)


def skill_detect_infrastructure_changes(
    profile: Optional[str] = None,
    regions: Optional[str] = None
) -> Dict[str, Any]:
    """
    Detect infrastructure changes using diff mode.
    
    Args:
        profile: OCI profile to use
        regions: Comma-separated regions to scan
    
    Returns:
        Change detection results with additions, removals, and categorization.
    """
    from .inventory_audit import InventoryAuditSkill
    from .adapters import get_inventory_client_adapter
    skill = InventoryAuditSkill(client=get_inventory_client_adapter())
    return skill.detect_changes(profile, regions)


def skill_generate_infrastructure_audit(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive infrastructure audit report.
    
    Combines discovery, capacity analysis, and change detection.
    
    Args:
        compartment_id: Optional compartment filter
        region: Optional region filter
    
    Returns:
        Complete audit report with executive summary and recommendations.
    """
    from .inventory_audit import InventoryAuditSkill
    from .adapters import get_inventory_client_adapter
    skill = InventoryAuditSkill(client=get_inventory_client_adapter())
    return skill.generate_audit_report(compartment_id, region)


# =============================================================================
# Network Diagnostics Skills
# =============================================================================

def skill_analyze_network_topology(
    compartment_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze network topology including VCNs and subnets.
    
    Args:
        compartment_id: Optional compartment filter
    
    Returns:
        Topology analysis with VCN/subnet inventory and CIDR overlap detection.
    """
    from .network_diagnostics import NetworkDiagnosticsSkill
    from .adapters import get_network_client_adapter
    skill = NetworkDiagnosticsSkill(client=get_network_client_adapter())
    return skill.analyze_topology(compartment_id)


def skill_assess_network_security(
    compartment_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Assess network security posture with scoring.
    
    Args:
        compartment_id: Optional compartment filter
    
    Returns:
        Security assessment with score, findings, and public exposure summary.
    """
    from .network_diagnostics import NetworkDiagnosticsSkill
    from .adapters import get_network_client_adapter
    skill = NetworkDiagnosticsSkill(client=get_network_client_adapter())
    return skill.assess_security(compartment_id)


def skill_diagnose_network_connectivity(
    compartment_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Diagnose network connectivity configuration.
    
    Args:
        compartment_id: Optional compartment filter
    
    Returns:
        Connectivity diagnosis with VCN analysis and accessibility assessment.
    """
    from .network_diagnostics import NetworkDiagnosticsSkill
    from .adapters import get_network_client_adapter
    skill = NetworkDiagnosticsSkill(client=get_network_client_adapter())
    return skill.diagnose_connectivity(compartment_id)


def skill_generate_network_report(
    compartment_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive network diagnostic report.
    
    Combines topology, security, and connectivity analysis.
    
    Args:
        compartment_id: Optional compartment filter
    
    Returns:
        Complete network report with recommendations.
    """
    from .network_diagnostics import NetworkDiagnosticsSkill
    from .adapters import get_network_client_adapter
    skill = NetworkDiagnosticsSkill(client=get_network_client_adapter())
    return skill.generate_network_report(compartment_id)


# =============================================================================
# Compute Management Skills
# =============================================================================

def skill_assess_compute_fleet_health(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Assess compute fleet health with scoring and recommendations.
    
    Args:
        compartment_id: Optional compartment filter
        region: Optional region filter
    
    Returns:
        Fleet health assessment with score, state distribution, issues, and recommendations.
    """
    from .compute_management import ComputeManagementSkill
    from .adapters import get_compute_client_adapter
    skill = ComputeManagementSkill(client=get_compute_client_adapter())
    return skill.assess_fleet_health(compartment_id, region)


def skill_analyze_instance_performance(
    instance_id: str,
    window: str = "1h"
) -> Dict[str, Any]:
    """
    Analyze instance performance metrics with insights.
    
    Args:
        instance_id: Instance OCID to analyze
        window: Time window (1h or 24h)
    
    Returns:
        Performance analysis with CPU insights, score, and recommendations.
    """
    from .compute_management import ComputeManagementSkill
    from .adapters import get_compute_client_adapter
    skill = ComputeManagementSkill(client=get_compute_client_adapter())
    return skill.analyze_instance_performance(instance_id, window)


def skill_recommend_compute_rightsizing(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get rightsizing recommendations for compute instances.
    
    Args:
        compartment_id: Optional compartment filter
        region: Optional region filter
    
    Returns:
        Rightsizing candidates with potential savings estimates.
    """
    from .compute_management import ComputeManagementSkill
    from .adapters import get_compute_client_adapter
    skill = ComputeManagementSkill(client=get_compute_client_adapter())
    return skill.recommend_rightsizing(compartment_id, region)


def skill_generate_compute_fleet_report(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive compute fleet management report.
    
    Combines health assessment and rightsizing analysis.
    
    Args:
        compartment_id: Optional compartment filter
        region: Optional region filter
    
    Returns:
        Complete report with health, rightsizing, and executive summary.
    """
    from .compute_management import ComputeManagementSkill
    from .adapters import get_compute_client_adapter
    skill = ComputeManagementSkill(client=get_compute_client_adapter())
    return skill.generate_fleet_report(compartment_id, region)


# =============================================================================
# Security Posture Skills
# =============================================================================

def skill_assess_cloud_guard_posture(
    compartment_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Assess Cloud Guard security posture with problem analysis.
    
    Args:
        compartment_id: Optional compartment filter
    
    Returns:
        Cloud Guard assessment with security score, problems, and recommendations.
    """
    from .security_posture import SecurityPostureSkill
    from .adapters import get_security_client_adapter
    skill = SecurityPostureSkill(client=get_security_client_adapter())
    return skill.assess_cloud_guard_posture(compartment_id)


def skill_assess_iam_security(
    compartment_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Assess IAM security configuration.
    
    Args:
        compartment_id: Optional compartment filter
    
    Returns:
        IAM assessment with user/policy analysis and recommendations.
    """
    from .security_posture import SecurityPostureSkill
    from .adapters import get_security_client_adapter
    skill = SecurityPostureSkill(client=get_security_client_adapter())
    return skill.assess_iam_security(compartment_id)


def skill_generate_security_report(
    compartment_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive security posture report.
    
    Combines Cloud Guard and IAM assessments.
    
    Args:
        compartment_id: Optional compartment filter
    
    Returns:
        Complete security report with overall score and recommendations.
    """
    from .security_posture import SecurityPostureSkill
    from .adapters import get_security_client_adapter
    skill = SecurityPostureSkill(client=get_security_client_adapter())
    return skill.generate_security_report(compartment_id)


# =============================================================================
# Skill Registry
# =============================================================================

SKILL_TOOLS = {
    # Cost Analysis
    "skill_analyze_cost_trend": skill_analyze_cost_trend,
    "skill_detect_cost_anomalies": skill_detect_cost_anomalies,
    "skill_get_service_breakdown": skill_get_service_breakdown,
    "skill_generate_cost_optimization_report": skill_generate_cost_optimization_report,
    # Inventory Audit
    "skill_run_infrastructure_discovery": skill_run_infrastructure_discovery,
    "skill_generate_capacity_report": skill_generate_capacity_report,
    "skill_detect_infrastructure_changes": skill_detect_infrastructure_changes,
    "skill_generate_infrastructure_audit": skill_generate_infrastructure_audit,
    # Network Diagnostics
    "skill_analyze_network_topology": skill_analyze_network_topology,
    "skill_assess_network_security": skill_assess_network_security,
    "skill_diagnose_network_connectivity": skill_diagnose_network_connectivity,
    "skill_generate_network_report": skill_generate_network_report,
    # Compute Management
    "skill_assess_compute_fleet_health": skill_assess_compute_fleet_health,
    "skill_analyze_instance_performance": skill_analyze_instance_performance,
    "skill_recommend_compute_rightsizing": skill_recommend_compute_rightsizing,
    "skill_generate_compute_fleet_report": skill_generate_compute_fleet_report,
    # Security Posture
    "skill_assess_cloud_guard_posture": skill_assess_cloud_guard_posture,
    "skill_assess_iam_security": skill_assess_iam_security,
    "skill_generate_security_report": skill_generate_security_report,
}


def get_skill_tools() -> dict:
    """Get all skill tools registry."""
    return SKILL_TOOLS


def get_skill_tool(name: str):
    """Get a specific skill tool by name."""
    return SKILL_TOOLS.get(name)
