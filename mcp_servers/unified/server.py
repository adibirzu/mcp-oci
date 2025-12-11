"""
Unified OCI MCP Server

Combines ALL tools from all OCI MCP servers into a single server for agent access.
This provides a one-stop-shop for all OCI operations.

Includes tools from:
- Cost Server (FinOpsAI, usage analysis)
- Database Server (ADB, DB Systems)
- Compute Server (instances, shapes)
- Network Server (VCNs, subnets)
- Security Server (Cloud Guard, IAM)
- Inventory Server (ShowOCI, discovery)
- Block Storage Server
- Load Balancer Server
- Log Analytics Server
- Skills Layer (high-level operations)
"""
import os
import logging
from typing import Dict, Any, List, Optional

# Set up logging first
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)
logger = logging.getLogger(__name__)

# Optional imports with fallbacks
try:
    from fastmcp import FastMCP
    from fastmcp.tools import Tool
except ImportError:
    logger.error("fastmcp not installed. Run: pip install fastmcp")
    raise

try:
    from opentelemetry import trace
    from mcp_oci_common.observability import init_tracing, init_metrics
    os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-unified")
    init_tracing(service_name="oci-mcp-unified")
    init_metrics()
    tracer = trace.get_tracer("oci-mcp-unified")
except ImportError:
    logger.warning("OpenTelemetry not available - tracing disabled")
    tracer = None

try:
    from mcp_oci_common import get_oci_config, validate_and_log_tools
except ImportError:
    logger.warning("mcp_oci_common not available")
    def get_oci_config():
        return {"region": os.getenv("OCI_REGION", "us-ashburn-1")}
    def validate_and_log_tools(tools, server_name):
        return True

# Create FastMCP app
app = FastMCP("oci-mcp-unified")

# =============================================================================
# Server Manifest Resource
# =============================================================================

@app.resource("server://manifest")
def server_manifest() -> str:
    """Server manifest for capability discovery."""
    import json
    tool_names = [t.name for t in all_tools]
    manifest = {
        "name": "OCI Unified MCP Server",
        "version": "1.0.0",
        "description": "Unified OCI MCP Server combining all OCI services",
        "total_tools": len(tool_names),
        "capabilities": {
            "services": [
                "cost", "database", "compute", "network", 
                "security", "inventory", "blockstorage", 
                "loadbalancer", "loganalytics"
            ],
            "skills": [
                "cost-analysis", "inventory-audit", "network-diagnostics"
            ]
        },
        "tools": tool_names
    }
    return json.dumps(manifest, indent=2)


# =============================================================================
# Healthcheck Tools
# =============================================================================

def healthcheck() -> Dict[str, Any]:
    """Lightweight readiness/liveness check for the unified server"""
    return {
        "status": "ok",
        "server": "oci-mcp-unified",
        "pid": os.getpid(),
        "total_tools": len(all_tools)
    }


def doctor() -> Dict[str, Any]:
    """Return server health, config summary, and available tools"""
    try:
        from mcp_oci_common.privacy import privacy_enabled
        cfg = get_oci_config()
        
        # Group tools by category
        tool_categories = {}
        for t in all_tools:
            prefix = t.name.split("_")[0] if "_" in t.name else "general"
            if prefix not in tool_categories:
                tool_categories[prefix] = []
            tool_categories[prefix].append(t.name)
        
        return {
            "server": "oci-mcp-unified",
            "ok": True,
            "privacy": bool(privacy_enabled()),
            "region": cfg.get("region"),
            "profile": os.getenv("OCI_PROFILE") or "DEFAULT",
            "total_tools": len(all_tools),
            "tool_categories": {k: len(v) for k, v in tool_categories.items()},
        }
    except Exception as e:
        return {"server": "oci-mcp-unified", "ok": False, "error": str(e)}


# =============================================================================
# Import Tools from All Servers
# =============================================================================

all_tools: List[Tool] = []

# Core tools
all_tools.extend([
    Tool.from_function(fn=healthcheck, name="healthcheck", description="Unified server health check"),
    Tool.from_function(fn=doctor, name="doctor", description="Server configuration and tool summary"),
])

# Import Database Server Tools
try:
    from mcp_servers.db.server import (
        list_autonomous_databases, list_db_systems,
        start_db_system, stop_db_system, restart_db_system,
        start_autonomous_database, stop_autonomous_database, restart_autonomous_database,
        get_db_cpu_snapshot, get_autonomous_database, get_db_metrics,
        query_multicloud_costs, get_cost_summary_by_cloud
    )
    db_tools = [
        Tool.from_function(fn=list_autonomous_databases, name="list_autonomous_databases", description="List autonomous databases in compartment"),
        Tool.from_function(fn=list_db_systems, name="list_db_systems", description="List DB systems in compartment"),
        Tool.from_function(fn=start_db_system, name="start_db_system", description="Start a DB system"),
        Tool.from_function(fn=stop_db_system, name="stop_db_system", description="Stop a DB system"),
        Tool.from_function(fn=restart_db_system, name="restart_db_system", description="Restart a DB system"),
        Tool.from_function(fn=start_autonomous_database, name="start_autonomous_database", description="Start an autonomous database"),
        Tool.from_function(fn=stop_autonomous_database, name="stop_autonomous_database", description="Stop an autonomous database"),
        Tool.from_function(fn=restart_autonomous_database, name="restart_autonomous_database", description="Restart an autonomous database"),
        Tool.from_function(fn=get_db_cpu_snapshot, name="get_db_cpu_snapshot", description="Get CPU metrics snapshot for a database"),
        Tool.from_function(fn=get_autonomous_database, name="get_autonomous_database", description="Get detailed ADB information"),
        Tool.from_function(fn=get_db_metrics, name="get_db_metrics", description="Get performance metrics for a database"),
        Tool.from_function(fn=query_multicloud_costs, name="query_multicloud_costs", description="Query multi-cloud cost data"),
        Tool.from_function(fn=get_cost_summary_by_cloud, name="get_cost_summary_by_cloud", description="Get cost summary by cloud provider"),
    ]
    all_tools.extend(db_tools)
    logger.info(f"Loaded {len(db_tools)} database tools")
except ImportError as e:
    logger.warning(f"Could not import database tools: {e}")

# Import Compute Server Tools
try:
    from mcp_servers.compute.server import (
        list_instances, get_instance, start_instance, stop_instance, 
        terminate_instance, list_shapes, get_compute_capacity
    )
    compute_tools = [
        Tool.from_function(fn=list_instances, name="compute_list_instances", description="List compute instances"),
        Tool.from_function(fn=get_instance, name="compute_get_instance", description="Get instance details"),
        Tool.from_function(fn=start_instance, name="compute_start_instance", description="Start a compute instance"),
        Tool.from_function(fn=stop_instance, name="compute_stop_instance", description="Stop a compute instance"),
        Tool.from_function(fn=terminate_instance, name="compute_terminate_instance", description="Terminate a compute instance"),
        Tool.from_function(fn=list_shapes, name="compute_list_shapes", description="List available compute shapes"),
        Tool.from_function(fn=get_compute_capacity, name="compute_get_capacity", description="Get compute capacity in compartment"),
    ]
    all_tools.extend(compute_tools)
    logger.info(f"Loaded {len(compute_tools)} compute tools")
except ImportError as e:
    logger.warning(f"Could not import compute tools: {e}")
except AttributeError as e:
    logger.warning(f"Compute server missing functions: {e}")

# Import Network Server Tools
try:
    from mcp_servers.network.server import (
        list_vcns, list_subnets, get_vcn, get_subnet,
        create_vcn, create_subnet, summarize_public_endpoints
    )
    network_tools = [
        Tool.from_function(fn=list_vcns, name="network_list_vcns", description="List VCNs in compartment"),
        Tool.from_function(fn=list_subnets, name="network_list_subnets", description="List subnets in compartment"),
        Tool.from_function(fn=get_vcn, name="network_get_vcn", description="Get VCN details"),
        Tool.from_function(fn=get_subnet, name="network_get_subnet", description="Get subnet details"),
        Tool.from_function(fn=create_vcn, name="network_create_vcn", description="Create a new VCN"),
        Tool.from_function(fn=create_subnet, name="network_create_subnet", description="Create a new subnet"),
        Tool.from_function(fn=summarize_public_endpoints, name="network_public_endpoints", description="Summarize public endpoints"),
    ]
    all_tools.extend(network_tools)
    logger.info(f"Loaded {len(network_tools)} network tools")
except ImportError as e:
    logger.warning(f"Could not import network tools: {e}")
except AttributeError as e:
    logger.warning(f"Network server missing functions: {e}")

# Import Security Server Tools
try:
    from mcp_servers.security.server import (
        list_cloud_guard_problems, get_cloud_guard_risk_score,
        list_users, list_groups, list_policies
    )
    security_tools = [
        Tool.from_function(fn=list_cloud_guard_problems, name="security_cloud_guard_problems", description="List Cloud Guard problems"),
        Tool.from_function(fn=get_cloud_guard_risk_score, name="security_risk_score", description="Get Cloud Guard risk score"),
        Tool.from_function(fn=list_users, name="security_list_users", description="List IAM users"),
        Tool.from_function(fn=list_groups, name="security_list_groups", description="List IAM groups"),
        Tool.from_function(fn=list_policies, name="security_list_policies", description="List IAM policies"),
    ]
    all_tools.extend(security_tools)
    logger.info(f"Loaded {len(security_tools)} security tools")
except ImportError as e:
    logger.warning(f"Could not import security tools: {e}")
except AttributeError as e:
    logger.warning(f"Security server missing functions: {e}")

# Import Inventory Server Tools
try:
    from mcp_servers.inventory.server import (
        run_showoci, list_all_discovery, generate_compute_capacity_report
    )
    inventory_tools = [
        Tool.from_function(fn=run_showoci, name="inventory_run_showoci", description="Run ShowOCI inventory scan"),
        Tool.from_function(fn=list_all_discovery, name="inventory_full_discovery", description="Run full infrastructure discovery"),
        Tool.from_function(fn=generate_compute_capacity_report, name="inventory_capacity_report", description="Generate compute capacity report"),
    ]
    all_tools.extend(inventory_tools)
    logger.info(f"Loaded {len(inventory_tools)} inventory tools")
except ImportError as e:
    logger.warning(f"Could not import inventory tools: {e}")
except AttributeError as e:
    logger.warning(f"Inventory server missing functions: {e}")

# Import Block Storage Server Tools
try:
    from mcp_servers.blockstorage.server import (
        list_volumes, get_volume, list_boot_volumes
    )
    blockstorage_tools = [
        Tool.from_function(fn=list_volumes, name="blockstorage_list_volumes", description="List block volumes"),
        Tool.from_function(fn=get_volume, name="blockstorage_get_volume", description="Get volume details"),
        Tool.from_function(fn=list_boot_volumes, name="blockstorage_list_boot_volumes", description="List boot volumes"),
    ]
    all_tools.extend(blockstorage_tools)
    logger.info(f"Loaded {len(blockstorage_tools)} block storage tools")
except ImportError as e:
    logger.warning(f"Could not import block storage tools: {e}")
except AttributeError as e:
    logger.warning(f"Block storage server missing functions: {e}")

# Import Load Balancer Server Tools
try:
    from mcp_servers.loadbalancer.server import (
        list_load_balancers, get_load_balancer
    )
    lb_tools = [
        Tool.from_function(fn=list_load_balancers, name="lb_list", description="List load balancers"),
        Tool.from_function(fn=get_load_balancer, name="lb_get", description="Get load balancer details"),
    ]
    all_tools.extend(lb_tools)
    logger.info(f"Loaded {len(lb_tools)} load balancer tools")
except ImportError as e:
    logger.warning(f"Could not import load balancer tools: {e}")
except AttributeError as e:
    logger.warning(f"Load balancer server missing functions: {e}")

# Import Log Analytics Server Tools
try:
    from mcp_servers.loganalytics.server import (
        execute_logan_query, list_log_sources
    )
    logan_tools = [
        Tool.from_function(fn=execute_logan_query, name="logan_execute_query", description="Execute Log Analytics query"),
        Tool.from_function(fn=list_log_sources, name="logan_list_sources", description="List log sources"),
    ]
    all_tools.extend(logan_tools)
    logger.info(f"Loaded {len(logan_tools)} log analytics tools")
except ImportError as e:
    logger.warning(f"Could not import log analytics tools: {e}")
except AttributeError as e:
    logger.warning(f"Log analytics server missing functions: {e}")

# =============================================================================
# Import Skill Tools (High-Level Operations) - 19 Total Skills
# =============================================================================

try:
    from mcp_servers.skills.tools_skills import (
        # Cost Analysis (4)
        skill_analyze_cost_trend,
        skill_detect_cost_anomalies,
        skill_get_service_breakdown,
        skill_generate_cost_optimization_report,
        # Inventory Audit (4)
        skill_run_infrastructure_discovery,
        skill_generate_capacity_report,
        skill_detect_infrastructure_changes,
        skill_generate_infrastructure_audit,
        # Network Diagnostics (4)
        skill_analyze_network_topology,
        skill_assess_network_security,
        skill_diagnose_network_connectivity,
        skill_generate_network_report,
        # Compute Management (4)
        skill_assess_compute_fleet_health,
        skill_analyze_instance_performance,
        skill_recommend_compute_rightsizing,
        skill_generate_compute_fleet_report,
        # Security Posture (3)
        skill_assess_cloud_guard_posture,
        skill_assess_iam_security,
        skill_generate_security_report,
    )
    skill_tools = [
        # Cost Analysis Skills
        Tool.from_function(fn=skill_analyze_cost_trend, name="skill_analyze_cost_trend",
            description="Analyze cost trends with forecasting and recommendations"),
        Tool.from_function(fn=skill_detect_cost_anomalies, name="skill_detect_cost_anomalies",
            description="Detect cost anomalies with root cause explanations"),
        Tool.from_function(fn=skill_get_service_breakdown, name="skill_get_service_breakdown",
            description="Get service cost breakdown with optimization potential"),
        Tool.from_function(fn=skill_generate_cost_optimization_report, name="skill_generate_cost_optimization_report",
            description="Generate comprehensive cost optimization report"),
        # Inventory Audit Skills
        Tool.from_function(fn=skill_run_infrastructure_discovery, name="skill_run_infrastructure_discovery",
            description="Run full infrastructure discovery with health assessment"),
        Tool.from_function(fn=skill_generate_capacity_report, name="skill_generate_capacity_report",
            description="Generate compute capacity planning report"),
        Tool.from_function(fn=skill_detect_infrastructure_changes, name="skill_detect_infrastructure_changes",
            description="Detect infrastructure changes using diff mode"),
        Tool.from_function(fn=skill_generate_infrastructure_audit, name="skill_generate_infrastructure_audit",
            description="Generate comprehensive infrastructure audit report"),
        # Network Diagnostics Skills
        Tool.from_function(fn=skill_analyze_network_topology, name="skill_analyze_network_topology",
            description="Analyze network topology including VCNs and subnets"),
        Tool.from_function(fn=skill_assess_network_security, name="skill_assess_network_security",
            description="Assess network security posture with scoring"),
        Tool.from_function(fn=skill_diagnose_network_connectivity, name="skill_diagnose_network_connectivity",
            description="Diagnose network connectivity configuration"),
        Tool.from_function(fn=skill_generate_network_report, name="skill_generate_network_report",
            description="Generate comprehensive network diagnostic report"),
        # Compute Management Skills
        Tool.from_function(fn=skill_assess_compute_fleet_health, name="skill_assess_compute_fleet_health",
            description="Assess compute fleet health with scoring and recommendations"),
        Tool.from_function(fn=skill_analyze_instance_performance, name="skill_analyze_instance_performance",
            description="Analyze instance performance metrics with insights"),
        Tool.from_function(fn=skill_recommend_compute_rightsizing, name="skill_recommend_compute_rightsizing",
            description="Get rightsizing recommendations for compute instances"),
        Tool.from_function(fn=skill_generate_compute_fleet_report, name="skill_generate_compute_fleet_report",
            description="Generate comprehensive compute fleet management report"),
        # Security Posture Skills
        Tool.from_function(fn=skill_assess_cloud_guard_posture, name="skill_assess_cloud_guard_posture",
            description="Assess Cloud Guard security posture with problem analysis"),
        Tool.from_function(fn=skill_assess_iam_security, name="skill_assess_iam_security",
            description="Assess IAM security configuration"),
        Tool.from_function(fn=skill_generate_security_report, name="skill_generate_security_report",
            description="Generate comprehensive security posture report"),
    ]
    all_tools.extend(skill_tools)
    logger.info(f"Loaded {len(skill_tools)} skill tools")
except ImportError as e:
    logger.warning(f"Could not import skill tools: {e}")

# =============================================================================
# Register All Tools with App
# =============================================================================

for tool in all_tools:
    app.add_tool(tool)

logger.info(f"Unified MCP Server initialized with {len(all_tools)} total tools")


if __name__ == "__main__":
    # Validate MCP tool names at startup
    if not validate_and_log_tools(all_tools, "oci-mcp-unified"):
        logging.error("MCP tool validation failed. Server will not start.")
        exit(1)
    
    # Start Prometheus metrics server
    try:
        from prometheus_client import start_http_server as _start_http_server
        port = int(os.getenv("METRICS_PORT", "8010"))
        _start_http_server(port)
        logger.info(f"Prometheus metrics on port {port}")
    except Exception:
        pass
    
    logger.info(f"Starting unified server with {len(all_tools)} tools")
    app.run()
