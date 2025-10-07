import json
import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app, Counter, Histogram
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
import subprocess

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


def get_server_tools(server_name, status):
    """Dynamically get tool information by importing the server module"""
    import importlib
    try:
        # Infer module path from server_name (e.g., oci-mcp-compute -> mcp_servers.compute.server)
        module_name = server_name.replace('oci-mcp-', '').replace('-', '_')
        module = importlib.import_module(f'mcp_servers.{module_name}.server')
        
        # Assume servers have a get_tools() function returning list of dicts
        tools = module.get_tools() if hasattr(module, 'get_tools') else []
        
        if not tools:
            tools = [{'name': 'Tools not defined', 'description': 'Add get_tools() to server.py'}]
    except Exception as e:
        tools = [{'name': 'Import failed', 'description': f'Error: {str(e)}'}]

    # Add status indicator
    if status != 'running':
        for tool in tools:
            tool['description'] += f' (Server {status})'

    return tools

def load_mcp_servers():
    """Dynamically discover servers from mcp_servers/ directories and mcp.json"""
    import glob
    discovered = []

    # Scan for server directories with server.py
    server_dirs = glob.glob('mcp_servers/*/server.py')
    dynamic_servers = []
    for path in server_dirs:
        dir_name = os.path.dirname(path).split('/')[-1]
        server_name = f'oci-mcp-{dir_name}'
        dynamic_servers.append({
            'name': server_name,
            'command': ['python', f'mcp_servers/{dir_name}/server.py'],
            'port': 8000 + len(discovered) + 1  # Assign incremental ports
        })

    # Load from mcp.json if exists, merge with discovered
    try:
        with open('mcp.json', 'r') as f:
            config_servers = json.load(f)
        # Merge: prioritize config, add discovered if not present
        server_map = {s['name']: s for s in config_servers}
        for ds in dynamic_servers:
            if ds['name'] not in server_map:
                server_map[ds['name']] = ds
        all_servers = list(server_map.values())
    except FileNotFoundError:
        all_servers = dynamic_servers

    enhanced = []
    for server in all_servers:
        server_name = server['name']
        port = server.get('port', 8000)

        # Check status
        status = "unknown"
        try:
            import requests
            response = requests.get(f'http://localhost:{port}/metrics', timeout=2)
            status = "running" if response.status_code == 200 else "error"
        except Exception:
            status = "stopped"

        tools = get_server_tools(server_name, status)

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
        discovered.append(server_name)

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
    LLM[LLM Client]
    MCP[MCP Protocol]
    OCI[Oracle Cloud Infrastructure]

    LLM --> MCP
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
    LLM[LLM Client]
    MCP[MCP Protocol]
    OCI[Oracle Cloud Infrastructure]

    LLM --> MCP
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

@app.get("/start/{server_name}")
async def start_server(server_name: str):
    try:
        result = subprocess.run(["bash", "scripts/mcp-launchers/start-mcp-server.sh", server_name.replace("oci-mcp-", ""), "--daemon"], check=True, capture_output=True, text=True)
        return {"status": "started", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": e.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
