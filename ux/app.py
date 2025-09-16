import json
import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="ux/static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="ux/templates")

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
        'oci-mcp-cost': 'mcp_servers.cost.server'
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
    return templates.TemplateResponse(request, "index.html", {
        "servers": servers,
        "relations": relations
    })

@app.get("/dashboards")
async def dashboards(request: Request):
    dashboards = [
        {'name': 'MCP Overview', 'url': 'http://localhost:3000/d/mcp-overview/mcp-overview'},
        {'name': 'Cost Analysis', 'url': 'http://localhost:3000/d/cost-analysis/cost-analysis'},
        # Add more as needed
    ]
    return templates.TemplateResponse(request, "dashboard.html", {
        "dashboards": dashboards
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
