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

# Load repo-local .env.local so OCI/OTEL config is applied consistently.
try:
    from pathlib import Path
    from dotenv import load_dotenv

    _repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(_repo_root / ".env.local")
except Exception:
    pass

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
    from mcp_oci_common.otel import trace
    from mcp_oci_common.observability import init_tracing, init_metrics
    from mcp_oci_common.oci_apm import init_oci_apm_tracing
    os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-unified")
    init_tracing(service_name="oci-mcp-unified")
    init_metrics()
    # Initialize OCI APM tracing (uses OCI_APM_ENDPOINT and OCI_APM_PRIVATE_DATA_KEY)
    init_oci_apm_tracing(service_name="oci-mcp-unified")
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
                "loadbalancer", "loganalytics", "objectstorage"
            ],
            "skills": [
                "cost-analysis",
                "inventory-audit",
                "network-diagnostics",
                "compute-management",
                "security-posture"
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
        list_instances, start_instance, stop_instance, restart_instance,
        create_instance, get_instance_metrics, get_instance_details_with_ips
    )
    compute_tools = [
        Tool.from_function(fn=list_instances, name="compute_list_instances", description="List compute instances"),
        Tool.from_function(fn=get_instance_details_with_ips, name="compute_get_instance", description="Get detailed instance information including IP addresses"),
        Tool.from_function(fn=start_instance, name="compute_start_instance", description="Start a compute instance"),
        Tool.from_function(fn=stop_instance, name="compute_stop_instance", description="Stop a compute instance"),
        Tool.from_function(fn=restart_instance, name="compute_restart_instance", description="Restart a compute instance"),
        Tool.from_function(fn=create_instance, name="compute_create_instance", description="Create a new compute instance"),
        Tool.from_function(fn=get_instance_metrics, name="compute_get_metrics", description="Get CPU metrics for a compute instance"),
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
        list_vcns, list_subnets, create_vcn, create_subnet,
        summarize_public_endpoints, create_vcn_with_subnets
    )
    network_tools = [
        Tool.from_function(fn=list_vcns, name="network_list_vcns", description="List VCNs in compartment"),
        Tool.from_function(fn=list_subnets, name="network_list_subnets", description="List subnets in a VCN"),
        Tool.from_function(fn=create_vcn, name="network_create_vcn", description="Create a new VCN"),
        Tool.from_function(fn=create_subnet, name="network_create_subnet", description="Create a new subnet"),
        Tool.from_function(fn=summarize_public_endpoints, name="network_public_endpoints", description="Summarize public endpoints"),
        Tool.from_function(fn=create_vcn_with_subnets, name="network_create_vcn_with_subnets", description="Create VCN with public/private subnets, gateways, route tables"),
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
        list_cloud_guard_problems, list_compartments,
        list_iam_users, list_groups, list_policies, list_data_safe_findings
    )
    security_tools = [
        Tool.from_function(fn=list_cloud_guard_problems, name="security_cloud_guard_problems", description="List Cloud Guard problems"),
        Tool.from_function(fn=list_compartments, name="security_list_compartments", description="List all compartments in the tenancy"),
        Tool.from_function(fn=list_iam_users, name="security_list_users", description="List IAM users"),
        Tool.from_function(fn=list_groups, name="security_list_groups", description="List IAM groups"),
        Tool.from_function(fn=list_policies, name="security_list_policies", description="List IAM policies"),
        Tool.from_function(fn=list_data_safe_findings, name="security_data_safe_findings", description="List Data Safe findings"),
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
        list_volumes, create_volume
    )
    blockstorage_tools = [
        Tool.from_function(fn=list_volumes, name="blockstorage_list_volumes", description="List block storage volumes"),
        Tool.from_function(fn=create_volume, name="blockstorage_create_volume", description="Create a new block storage volume"),
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
        list_load_balancers, create_load_balancer
    )
    lb_tools = [
        Tool.from_function(fn=list_load_balancers, name="lb_list", description="List load balancers"),
        Tool.from_function(fn=create_load_balancer, name="lb_create", description="Create a new load balancer"),
    ]
    all_tools.extend(lb_tools)
    logger.info(f"Loaded {len(lb_tools)} load balancer tools")
except ImportError as e:
    logger.warning(f"Could not import load balancer tools: {e}")
except AttributeError as e:
    logger.warning(f"Load balancer server missing functions: {e}")

# Import Object Storage Server Tools
try:
    from mcp_servers.objectstorage.server import (
        list_buckets,
        get_bucket,
        list_objects,
        get_bucket_usage,
        get_storage_report,
        list_db_backups,
        get_backup_details,
        create_preauthenticated_request,
    )
    objectstorage_tools = [
        Tool.from_function(fn=list_buckets, name="objectstorage_list_buckets", description="List Object Storage buckets"),
        Tool.from_function(fn=get_bucket, name="objectstorage_get_bucket", description="Get Object Storage bucket details"),
        Tool.from_function(fn=list_objects, name="objectstorage_list_objects", description="List objects in a bucket"),
        Tool.from_function(fn=get_bucket_usage, name="objectstorage_get_bucket_usage", description="Get usage summary for a bucket"),
        Tool.from_function(fn=get_storage_report, name="objectstorage_storage_report", description="Get storage report across buckets"),
        Tool.from_function(fn=list_db_backups, name="objectstorage_list_db_backups", description="List database backup artifacts in Object Storage"),
        Tool.from_function(fn=get_backup_details, name="objectstorage_get_backup_details", description="Get backup artifact details"),
        Tool.from_function(fn=create_preauthenticated_request, name="objectstorage_create_par", description="Create a pre-authenticated request (PAR)"),
    ]
    all_tools.extend(objectstorage_tools)
    logger.info(f"Loaded {len(objectstorage_tools)} object storage tools")
except ImportError as e:
    logger.warning(f"Could not import object storage tools: {e}")
except AttributeError as e:
    logger.warning(f"Object storage server missing functions: {e}")

# Import Log Analytics Server Tools
try:
    from mcp_servers.loganalytics.server import (
        execute_query, search_security_events, get_mitre_techniques,
        validate_query, check_oci_connection
    )
    logan_tools = [
        Tool.from_function(fn=execute_query, name="logan_execute_query", description="Execute Log Analytics query with security analysis"),
        Tool.from_function(fn=search_security_events, name="logan_search_security", description="Search for security events using patterns"),
        Tool.from_function(fn=get_mitre_techniques, name="logan_mitre_techniques", description="Search for MITRE ATT&CK techniques in logs"),
        Tool.from_function(fn=validate_query, name="logan_validate_query", description="Validate and enhance Log Analytics query syntax"),
        Tool.from_function(fn=check_oci_connection, name="logan_check_connection", description="Check Log Analytics connection"),
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


def main():
    """Run the MCP server with transport selection based on environment variables."""
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

    transport = os.getenv("MCP_TRANSPORT", os.getenv("FASTMCP_TRANSPORT", "stdio")).lower()
    host = os.getenv("MCP_HOST", os.getenv("MCP_HTTP_HOST", "0.0.0.0"))
    try:
        port = int(os.getenv("MCP_PORT", os.getenv("MCP_HTTP_PORT", os.getenv("FASTMCP_PORT", "7010"))))
    except Exception:
        port = 7010

    logger.info(
        f"Starting unified server with {len(all_tools)} tools, "
        f"transport={transport}, host={host}, port={port}"
    )

    valid_transports = {"stdio", "http", "sse", "streamable-http"}
    if transport not in valid_transports:
        logger.warning("Unknown transport '%s'; falling back to stdio", transport)
        transport = "stdio"

    try:
        if transport == "stdio":
            app.run(transport="stdio")
        else:
            app.run(transport=transport, host=host, port=port)
    except (ValueError, NotImplementedError) as exc:
        logger.warning("Transport '%s' not available (%s); falling back to stdio", transport, exc)
        app.run(transport="stdio")
    except Exception as exc:
        logger.exception("Failed to start MCP server", exc_info=exc)
        raise


if __name__ == "__main__":
    main()
