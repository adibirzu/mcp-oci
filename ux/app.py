import json
import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app, Counter, Histogram
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
except Exception:
    FastAPIInstrumentor = None
try:
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
except Exception:
    RequestsInstrumentor = None
from mcp_oci_common.observability import init_tracing
from time import perf_counter

# Optional Pyroscope (continuous profiling)
ENABLE_PYROSCOPE = os.getenv("ENABLE_PYROSCOPE", "true").lower() in ("1", "true", "yes", "on")
try:
    if ENABLE_PYROSCOPE:
        import pyroscope  # provided by pyroscope-io
        pyroscope.configure(
            application_name=os.getenv("PYROSCOPE_APP_NAME", "mcp-ux"),
            server_address=os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://localhost:4040"),
            # reasonable defaults
            sample_rate=int(os.getenv("PYROSCOPE_SAMPLE_RATE", "100")),  # Hz
            detect_subprocesses=True,
            enable_logging=True,
        )
except Exception as _e:
    # Do not fail app startup due to profiler availability
    pass

app = FastAPI()

# Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

request_counter = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'http_status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])

# Metrics middleware
@app.middleware("http")
async def metrics_middleware(request, call_next):
    method = request.method
    endpoint = request.url.path
    start = perf_counter()
    response = await call_next(request)
    duration = perf_counter() - start
    try:
        request_counter.labels(method=method, endpoint=endpoint, http_status=str(response.status_code)).inc()
        request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    except Exception:
        pass
    return response

# OpenTelemetry tracing (send to OTel Collector -> Tempo)
init_tracing(service_name=os.getenv("OTEL_SERVICE_NAME", "mcp-ux"))
if RequestsInstrumentor:
    try:
        RequestsInstrumentor().instrument()
    except Exception:
        pass
if FastAPIInstrumentor:
    try:
        FastAPIInstrumentor.instrument_app(app)
    except Exception:
        try:
            FastAPIInstrumentor().instrument()
        except Exception:
            pass

# Mount static files
app.mount("/static", StaticFiles(directory="ux/static"), name="static")

# Set up templates (fallback to JSON if jinja2 not available)
try:
    templates = Jinja2Templates(directory="ux/templates")
except Exception:
    templates = None

import importlib

def get_server_tools(server_name, status):
    """Get tool information for each MCP server type"""

    # Define tools for each server type
    server_tools = {
        'oci-mcp-compute': [
            {'name': 'list_instances', 'description': 'List compute instances in compartment'},
            {'name': 'create_instance', 'description': 'Create a new compute instance'},
            {'name': 'terminate_instance', 'description': 'Terminate a compute instance'},
            {'name': 'get_instance_details', 'description': 'Get detailed information about an instance'},
            {'name': 'list_images', 'description': 'List available compute images'},
            {'name': 'list_shapes', 'description': 'List available compute shapes'}
        ],
        'oci-mcp-db': [
            {'name': 'list_db_systems', 'description': 'List database systems'},
            {'name': 'list_autonomous_databases', 'description': 'List autonomous databases'},
            {'name': 'create_autonomous_database', 'description': 'Create a new autonomous database'},
            {'name': 'get_db_system_details', 'description': 'Get database system details'},
            {'name': 'list_backups', 'description': 'List database backups'}
        ],
        'oci-mcp-network': [
            {'name': 'list_vcns', 'description': 'List Virtual Cloud Networks'},
            {'name': 'create_vcn', 'description': 'Create a new VCN'},
            {'name': 'list_subnets', 'description': 'List subnets in VCN'},
            {'name': 'create_subnet', 'description': 'Create a new subnet'},
            {'name': 'list_security_groups', 'description': 'List network security groups'},
            {'name': 'list_route_tables', 'description': 'List route tables'}
        ],
        'oci-mcp-security': [
            {'name': 'list_security_policies', 'description': 'List security policies'},
            {'name': 'scan_vulnerabilities', 'description': 'Scan for security vulnerabilities'},
            {'name': 'list_security_lists', 'description': 'List security lists'},
            {'name': 'audit_compliance', 'description': 'Run compliance audit'}
        ],
        'oci-mcp-observability': [
            {'name': 'get_metrics', 'description': 'Get monitoring metrics'},
            {'name': 'list_alarms', 'description': 'List monitoring alarms'},
            {'name': 'create_alarm', 'description': 'Create monitoring alarm'},
            {'name': 'get_logs', 'description': 'Retrieve application logs'},
            {'name': 'export_logs', 'description': 'Export logs to external system'}
        ],
        'oci-mcp-cost': [
            {'name': 'get_cost_analysis', 'description': 'Analyze costs by service and time period'},
            {'name': 'forecast_spending', 'description': 'Forecast future spending patterns'},
            {'name': 'list_budgets', 'description': 'List configured budgets'},
            {'name': 'create_budget', 'description': 'Create spending budget'},
            {'name': 'cost_optimization', 'description': 'Get cost optimization recommendations'}
        ],
        'oci-mcp-inventory': [
            {'name': 'list_all_resources', 'description': 'Comprehensive resource inventory'},
            {'name': 'search_resources', 'description': 'Search resources by criteria'},
            {'name': 'resource_discovery', 'description': 'Discover new resources'},
            {'name': 'export_inventory', 'description': 'Export inventory to CSV/JSON'}
        ],
        'oci-mcp-blockstorage': [
            {'name': 'list_volumes', 'description': 'List block storage volumes'},
            {'name': 'create_volume', 'description': 'Create new block storage volume'},
            {'name': 'attach_volume', 'description': 'Attach volume to instance'},
            {'name': 'list_backups', 'description': 'List volume backups'},
            {'name': 'create_backup', 'description': 'Create volume backup'}
        ],
        'oci-mcp-loadbalancer': [
            {'name': 'list_load_balancers', 'description': 'List load balancers'},
            {'name': 'create_load_balancer', 'description': 'Create new load balancer'},
            {'name': 'configure_backend_set', 'description': 'Configure backend servers'},
            {'name': 'list_listeners', 'description': 'List load balancer listeners'},
            {'name': 'get_health_status', 'description': 'Get backend health status'}
        ],
        'oci-mcp-agents': [
            {'name': 'list_ai_agents', 'description': 'List available AI agents'},
            {'name': 'invoke_agent', 'description': 'Invoke AI agent for analysis'},
            {'name': 'get_agent_results', 'description': 'Get agent execution results'},
            {'name': 'schedule_agent_task', 'description': 'Schedule periodic agent execution'}
        ]
    }

    # Get tools for this server type, fallback to basic MCP info
    tools = server_tools.get(server_name, [
        {
            'name': 'MCP Protocol',
            'description': 'Server communicates via MCP protocol over stdio',
        }
    ])

    # Add status indicator to tool descriptions
    if status != 'running':
        for tool in tools:
            tool['description'] += f' (Server {status})'

    return tools

def load_mcp_servers():
    """Load MCP server configurations and check their status"""
    try:
        with open('mcp.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        return []

    # Server port mapping for status checks
    server_ports = {
        'oci-mcp-compute': 8001,
        'oci-mcp-db': 8002,
        'oci-mcp-observability': 8003,
        'oci-mcp-security': 8004,
        'oci-mcp-cost': 8005,
        'oci-mcp-network': 8006,
        'oci-mcp-blockstorage': 8007,
        'oci-mcp-loadbalancer': 8008,
        'oci-mcp-inventory': 8009,
        'oci-mcp-loganalytics': 8003,  # May share port with observability
        'oci-mcp-agents': 8011,
    }

    enhanced = []
    for server in data:
        server_name = server['name']
        port = server_ports.get(server_name, 8000)

        # Check if server is running by testing metrics endpoint
        status = "unknown"
        try:
            import requests
            response = requests.get(f'http://localhost:{port}/metrics', timeout=2)
            status = "running" if response.status_code == 200 else "error"
        except Exception:
            status = "stopped"

        # Get tool information based on server type
        tools = get_server_tools(server_name, status)

        # Add comprehensive server info
        server_info = {
            'name': server_name,
            'command': server.get('command', []),
            'env': server.get('env', {}),
            'transport': server.get('transport', 'stdio'),
            'port': port,
            'status': status,
            'tools': tools
        }
        enhanced.append(server_info)

    return enhanced

@app.get("/")
async def index(request: Request):
    servers = load_mcp_servers()
    # Registry/discovery summary (best-effort)
    registry = {"counts": {}, "suggestions": []}
    try:
        from mcp_oci_introspect.server import registry_report
        registry = registry_report()
    except Exception:
        pass
    # Generate valid Mermaid diagram with error handling
    try:
        relations = """graph TD
    Claude[Claude AI Client]
    MCP[MCP Protocol]
    OCI[Oracle Cloud Infrastructure]

    Claude --> MCP
    MCP --> OCI

    subgraph MCP_Servers["MCP Servers"]
"""

        # Add server nodes with safe naming
        for server in servers:
            # Create safe node ID (alphanumeric + underscore only)
            clean_name = server['name'].replace('-', '_').replace('oci_mcp_', '')
            display_name = server['name'].replace('oci-mcp-', '').title()
            status_icon = "✅" if server.get('status') == 'running' else "❌"
            relations += f"        {clean_name}[\"{status_icon} {display_name}\"]\n"

        relations += "    end\n\n"

        # Add connections from MCP to each server
        for server in servers:
            clean_name = server['name'].replace('-', '_').replace('oci_mcp_', '')
            relations += f"    MCP --> {clean_name}\n"
            relations += f"    {clean_name} --> OCI\n"

        # Add click events for interactive functionality
        for server in servers:
            clean_name = server['name'].replace('-', '_').replace('oci_mcp_', '')
            relations += f"    click {clean_name} call toggleServerTools(\"{server['name']}\")\n"

    except Exception as e:
        # Fallback to simple text representation if Mermaid generation fails
        relations = f"""graph TD
    Claude[Claude AI Client]
    MCP[MCP Protocol]
    OCI[Oracle Cloud Infrastructure]

    Claude --> MCP
    MCP --> OCI

    %% Error in diagram generation: {str(e)}
"""
    # Use OTLP gRPC default (4317) consistent with servers (OTLPSpanExporter/MetricExporter)
    obs = {
        "grafana_url": os.getenv("GRAFANA_URL", "http://127.0.0.1:3000"),
        "prometheus_url": os.getenv("PROMETHEUS_URL", "http://127.0.0.1:9090"),
        "tempo_url": os.getenv("TEMPO_URL", "http://127.0.0.1:3200"),
        "jaeger_url": os.getenv("JAEGER_URL", "http://127.0.0.1:16686"),
        "pyroscope_url": os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://127.0.0.1:4040"),
        "otlp_endpoint": os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
    }
    payload = {
        "servers": servers,
        "relations": relations,
        "observability": obs,
        "registry": registry,
    }
    if templates is None:
        # Fallback JSON response when jinja2 is unavailable
        from fastapi.responses import JSONResponse
        return JSONResponse(payload)
    return templates.TemplateResponse(request, "index.html", payload)

@app.get("/dashboards")
async def dashboards(request: Request):
    dashboards = [
        {'name': 'MCP Overview', 'url': 'http://localhost:3000/d/mcp-overview/mcp-overview'},
        {'name': 'Cost Analysis', 'url': 'http://localhost:3000/d/cost-analysis/cost-analysis'},
        # Add more as needed
    ]
    payload = {"dashboards": dashboards}
    if templates is None:
        from fastapi.responses import JSONResponse
        return JSONResponse(payload)
    return templates.TemplateResponse(request, "dashboard.html", payload)

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
