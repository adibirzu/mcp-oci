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
# Default disabled to avoid noisy errors if backend is not available (docker/k8s)
ENABLE_PYROSCOPE = os.getenv("ENABLE_PYROSCOPE", "false").lower() in ("1", "true", "yes", "on")
try:
    if ENABLE_PYROSCOPE:
        import pyroscope  # provided by pyroscope-io
        import requests
        server_addr = os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://127.0.0.1:4040")
        # Quick reachability check; if not reachable, disable profiling silently
        try:
            requests.get(server_addr, timeout=0.5)
            pyroscope.configure(
                application_name=os.getenv("PYROSCOPE_APP_NAME", "mcp-ux"),
                server_address=server_addr,
                # reasonable defaults
                sample_rate=int(os.getenv("PYROSCOPE_SAMPLE_RATE", "100")),  # Hz
                detect_subprocesses=True,
                enable_logging=True,
            )
        except Exception:
            ENABLE_PYROSCOPE = False
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

import importlib, sys, inspect

def get_server_tools_dynamic(server: dict, status: str) -> list[dict]:
    """
    Dynamically discover tool names/descriptions (and input schemas when possible)
    from the MCP server module referenced by mcp.json. This avoids static drift and
    reflects code changes (module reload on each request).

    Supports command forms:
      - ["python", "mcp_servers/<name>/server.py"]
      - ["python", "-m", "mcp_servers.<name>.server"]
    """
    module_path = None
    try:
        cmd = server.get("command", [])
        if len(cmd) >= 3 and cmd[1] == "-m":
            # Module form
            module_path = cmd[2]
        elif len(cmd) >= 2 and isinstance(cmd[0], str) and "python" in cmd[0]:
            # Script path form -> convert to module
            script_path = cmd[1]
            if isinstance(script_path, str) and script_path.endswith(".py"):
                module_path = script_path[:-3].replace("/", ".").replace("\\", ".")
        # Fallback: try to infer from name
        if not module_path and server.get("name", "").startswith("oci-mcp-"):
            inferred = server["name"].replace("-", ".")
            module_path = f"{inferred}.server" if not inferred.endswith(".server") else inferred
    except Exception:
        module_path = None

    tools_list: list[dict] = []
    if module_path:
        try:
            # Import module fresh each request to reflect latest code
            importlib.invalidate_caches()
            mod = sys.modules.get(module_path)
            if mod is not None:
                mod = importlib.reload(mod)
            else:
                mod = importlib.import_module(module_path)

            # Prefer explicit tools attribute
            mod_tools = getattr(mod, "tools", None)
            if isinstance(mod_tools, list) and mod_tools:
                for t in mod_tools:
                    # fastmcp.tools.Tool typically exposes name/description and underlying function
                    name = getattr(t, "name", None) or getattr(t, "tool", None) or "tool"
                    desc = getattr(t, "description", "") or ""
                    schema = None

                    # Attempt to capture schema from known attributes
                    schema = getattr(t, "input_schema", None) or getattr(t, "schema", None)
                    # If a method was returned (e.g., Pydantic BaseModel.schema), prefer model_json_schema
                    try:
                        if callable(schema):
                            owner = getattr(schema, "__self__", None)
                            if owner is not None and hasattr(owner, "model_json_schema"):
                                schema = owner.model_json_schema()
                            else:
                                schema = schema()
                    except Exception:
                        schema = None
                    if schema is None:
                        # Some wrappers expose a Pydantic model
                        model = getattr(t, "input_model", None) or getattr(t, "model", None)
                        try:
                            if model and hasattr(model, "model_json_schema"):
                                schema = model.model_json_schema()
                            elif model and hasattr(model, "schema"):
                                schema = model.schema()
                        except Exception:
                            schema = None

                    # Fallback: derive a basic JSON schema from the function signature
                    if schema is None:
                        func = getattr(t, "func", None) or getattr(t, "handler", None) or getattr(t, "fn", None)
                        try:
                            if callable(func):
                                sig = inspect.signature(func)
                                properties = {}
                                required = []
                                for pname, param in sig.parameters.items():
                                    # Skip typical instance/class parameters
                                    if pname in ("self", "cls"):
                                        continue
                                    # Infer a simple type
                                    ann = param.annotation
                                    json_type = "string"
                                    try:
                                        if ann in (int,):
                                            json_type = "integer"
                                        elif ann in (float,):
                                            json_type = "number"
                                        elif ann in (bool,):
                                            json_type = "boolean"
                                        elif ann in (list,):
                                            json_type = "array"
                                        elif ann in (dict,):
                                            json_type = "object"
                                        elif ann in (str,) or ann is inspect._empty:
                                            json_type = "string"
                                        else:
                                            origin = getattr(ann, "__origin__", None)
                                            if origin in (list,):
                                                json_type = "array"
                                            elif origin in (dict,):
                                                json_type = "object"
                                            elif getattr(ann, "__name__", None) in ("int", "Integer"):
                                                json_type = "integer"
                                            elif getattr(ann, "__name__", None) in ("float", "Float"):
                                                json_type = "number"
                                            elif getattr(ann, "__name__", None) in ("bool", "Boolean"):
                                                json_type = "boolean"
                                            else:
                                                json_type = "string"
                                    except Exception:
                                        json_type = "string"

                                    properties[pname] = {"type": json_type}
                                    if param.default is inspect._empty:
                                        required.append(pname)

                                schema = {"type": "object", "properties": properties}
                                if required:
                                    schema["required"] = required
                        except Exception:
                            schema = None

                    entry = {"name": name, "description": desc}
                    if schema:
                        entry["input_schema"] = schema
                    tools_list.append(entry)
            else:
                # Some modules expose register_tools() returning dict-like signatures
                reg = getattr(mod, "register_tools", None)
                if callable(reg):
                    try:
                        for t in reg():
                            name = t.get("name", "tool")
                            desc = t.get("description", "")
                            entry = {"name": name, "description": desc}
                            if "input_schema" in t and t["input_schema"]:
                                entry["input_schema"] = t["input_schema"]
                            tools_list.append(entry)
                    except Exception:
                        pass
        except Exception:
            # Dynamic import failed; fall back to MCP protocol placeholder
            pass

    if not tools_list:
        tools_list = [{
            "name": "MCP Protocol",
            "description": "Server communicates via MCP protocol over stdio"
        }]

    # Annotate with status for UX consistency
    if status != "running":
        for tool in tools_list:
            try:
                tool["description"] = (tool.get("description", "") + f" (Server {status})").strip()
            except Exception:
                pass

    return tools_list

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

        # Get tool information dynamically from server's Python module
        tools = get_server_tools_dynamic(server, status)

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
