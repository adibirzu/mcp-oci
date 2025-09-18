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
            server_address=os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040"),
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

def load_mcp_servers():
    with open('mcp.json', 'r') as f:
        data = json.load(f)
    
    module_map = {
        'oci-mcp-compute': 'mcp_servers.compute.server',
        'oci-mcp-db': 'mcp_servers.db.server',
        'oci-mcp-network': 'mcp_servers.network.server',
        'oci-mcp-security': 'mcp_servers.security.server',
        'oci-mcp-observability': 'mcp_servers.observability.server',
        'oci-mcp-cost': 'mcp_servers.cost.server',
        'oci-mcp-inventory': 'mcp_servers.inventory.server'
    }
    
    enhanced = []
    for server in data:
        mod_path = module_map.get(server['name'])
        if mod_path:
            try:
                mod = importlib.import_module(mod_path)
                # Build tool metadata with resilient schema extraction (compatible with FunctionTool)
                tools = []
                for t in mod.tools:
                    schema = {}
                    # Try OpenAPI-style accessors if available
                    try:
                        if hasattr(t, 'openapi') and callable(getattr(t, 'openapi')):
                            schema = t.openapi()
                        elif hasattr(t, 'to_openapi') and callable(getattr(t, 'to_openapi')):
                            schema = t.to_openapi()
                    except Exception:
                        schema = {}
                    # Fallback: reflect function signature for basic schema
                    if not schema:
                        fn = None
                        for cand in ('fn', 'function', '_fn', '_function', 'callable', 'handler'):
                            f = getattr(t, cand, None)
                            if callable(f):
                                fn = f
                                break
                        if fn:
                            import inspect
                            try:
                                sig = inspect.signature(fn)
                                props = {}
                                required = []
                                for name, param in sig.parameters.items():
                                    if name.startswith('_'):
                                        continue
                                    ann = param.annotation
                                    type_name = 'string'
                                    if ann is not inspect._empty:
                                        if ann in (int,):
                                            type_name = 'integer'
                                        elif ann in (float,):
                                            type_name = 'number'
                                        elif ann in (bool,):
                                            type_name = 'boolean'
                                        elif ann in (list, tuple, set):
                                            type_name = 'array'
                                        elif ann in (dict,):
                                            type_name = 'object'
                                        else:
                                            type_name = 'string'
                                    prop = {'type': type_name}
                                    if param.default is not inspect._empty:
                                        prop['default'] = param.default
                                    else:
                                        required.append(name)
                                    props[name] = prop
                                schema = {'type': 'object', 'properties': props}
                                if required:
                                    schema['required'] = required
                            except Exception:
                                schema = {}
                    tools.append({
                        'name': t.name,
                        'description': t.description,
                        'input_schema': schema
                    })
                server['tools'] = tools
            except Exception as e:
                server['tools'] = [{'name': 'error', 'description': str(e), 'input_schema': {}}]
        else:
            server['tools'] = []
        enhanced.append(server)
    
    return enhanced

@app.get("/")
async def index(request: Request):
    servers = load_mcp_servers()
    # Simple relations: assume all connect to OCI via SDK
    relations = "graph TD\nClaude-->MCP\nsubgraph MCP\n" + "\n".join([f"{s['name']}" for s in servers]) + "\nend\nMCP-->OCI\nsubgraph OCI\nSDK\nend"
    for s in servers:
        if s.get('tools'):
            if s.get('tools') and all('name' in t for t in s['tools']):
                relations += f"\nsubgraph {s['name']}_tools\n" + "\n".join([f"{s['name']}_{t['name']}" for t in s['tools']]) + "\nend\n" + f"{s['name']}-- tools -->{s['name']}_tools\n"
            else:
                relations += f"{s['name']}-- no tools --\n"
    # Use OTLP gRPC default (4317) consistent with servers (OTLPSpanExporter/MetricExporter)
    obs = {
        "grafana_url": os.getenv("GRAFANA_URL", "http://localhost:3000"),
        "prometheus_url": os.getenv("PROMETHEUS_URL", "http://localhost:9090"),
        "tempo_url": os.getenv("TEMPO_URL", "http://localhost:3200"),
        "otlp_endpoint": os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    }
    payload = {
        "servers": servers,
        "relations": relations,
        "observability": obs
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
