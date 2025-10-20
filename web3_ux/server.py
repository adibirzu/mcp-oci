#!/usr/bin/env python3
from __future__ import annotations

import os
import json
from typing import Optional
from fastapi import FastAPI, Request
import requests
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
import oracledb
import subprocess

app = FastAPI(title="OCI MCP Web3 UX")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Ensure repo root and src are importable (so we can import mcp_servers.* and src.*)
import sys
REPO_ROOT = os.path.abspath(os.path.join(BASE_DIR, os.pardir))
SRC_DIR = os.path.join(REPO_ROOT, "src")
for _p in (REPO_ROOT, SRC_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

def _env_compartment_only() -> Optional[str]:
    return os.getenv("COMPARTMENT_OCID")

@app.get("/api/config")
def api_config():
    cid = _env_compartment_only()
    return {
        "default_compartment_id": cid,
        "has_default_compartment": bool(cid),
        "oci_profile": os.getenv("OCI_PROFILE"),
        "oci_region": os.getenv("OCI_REGION"),
    }


def _load_json(x):
    try:
        return json.loads(x) if isinstance(x, str) else x
    except Exception:
        return x


def connect_db():
    """Connect to Autonomous DB using wallet or DSN based on env."""
    user = os.getenv("ORACLE_DB_USER")
    pwd = os.getenv("ORACLE_DB_PASSWORD")
    dsn = os.getenv("ORACLE_DB_DSN")
    svc = os.getenv("ORACLE_DB_SERVICE")
    wallet_zip = os.getenv("ORACLE_DB_WALLET_ZIP")
    wallet_pwd = os.getenv("ORACLE_DB_WALLET_PASSWORD")
    if wallet_zip and svc and user and pwd:
        import zipfile, tempfile
        tmp = tempfile.mkdtemp(prefix="mcp_wallet_")
        with zipfile.ZipFile(wallet_zip, 'r') as z:
            z.extractall(tmp)
        return oracledb.connect(user=user, password=pwd, dsn=svc, config_dir=tmp, wallet_location=tmp, wallet_password=wallet_pwd)
    elif user and pwd and dsn:
        return oracledb.connect(user=user, password=pwd, dsn=dsn)
    else:
        raise RuntimeError("DB connection envs not set. Use wallet or DSN mode.")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/discovery")
def api_discovery(compartment_id: Optional[str] = None, limit: int = 25):
    try:
        if not compartment_id:
            compartment_id = _env_compartment_only()
        if not compartment_id:
            return JSONResponse({"error": "Missing compartment_id. Set COMPARTMENT_OCID env var or pass ?compartment_id=..."}, status_code=400)
        from mcp_servers.inventory.server import list_all_discovery
        out = list_all_discovery(compartment_id=compartment_id, limit_per_type=limit)
        return out
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/relations")
def api_relations(compartment_id: Optional[str] = None, limit: int = 200):
    try:
        # If compartment_id provided, build resource relations graph from discovery/capacity
        if compartment_id or _env_compartment_only():
            if not compartment_id:
                compartment_id = _env_compartment_only()
            if not compartment_id:
                return JSONResponse({"error": "Missing compartment_id. Set COMPARTMENT_OCID env var or pass ?compartment_id=..."}, status_code=400)
            from mcp_servers.inventory.server import list_all_discovery, generate_compute_capacity_report
            disc = list_all_discovery(compartment_id=compartment_id, limit_per_type=limit)
            cap = generate_compute_capacity_report(compartment_id=compartment_id)
            if isinstance(cap, str):
                cap = json.loads(cap)
            inst_details = cap.get('instance_details', []) or []
            # Build mermaid with resources
            mer = "graph TD\n"
            # VCNs
            vcns = (disc.get('vcns') or {}).get('items', [])
            for v in vcns:
                vid = v.get('id') or v.get('_id'); name = v.get('display_name') or v.get('_display_name') or vid
                mer += f"\n{vid}[\"VCN: {name}\"]"
            # Subnets and edges VCN->Subnet
            subnets = (disc.get('subnets') or {}).get('items', [])
            for s in subnets:
                sid = s.get('id') or s.get('_id'); sname = s.get('display_name') or s.get('_display_name') or sid
                vcn_id = s.get('vcn_id') or s.get('_vcn_id')
                mer += f"\n{sid}[\"Subnet: {sname}\"]"
                if vcn_id:
                    mer += f"\n{vcn_id}--> {sid}"
            # Instances and edges Subnet->Instance using capacity instance_details subnet_id
            for inst in inst_details[:limit]:
                iid = inst.get('id'); iname = inst.get('display_name') or iid
                mer += f"\n{iid}[\"Instance: {iname}\"]"
                for ip in inst.get('ips', []) or []:
                    subnet_id = ip.get('subnet_id')
                    if subnet_id:
                        mer += f"\n{subnet_id}--> {iid}"
            # Load Balancers
            lbs = (disc.get('load_balancers') or {}).get('items', [])
            for lb in lbs:
                lid = lb.get('id') or lb.get('_id'); lname = lb.get('display_name') or lb.get('_display_name') or lid
                mer += f"\n{lid}[\"LB: {lname}\"]"
            # Functions Apps
            fnapps = (disc.get('functions_apps') or {}).get('items', [])
            for fa in fnapps:
                fid = fa.get('id') or fa.get('_id'); fname = fa.get('display_name') or fa.get('_display_name') or fid
                mer += f"\n{fid}[\"Fn: {fname}\"]"
            # Streams
            streams = (disc.get('streams') or {}).get('items', [])
            for st in streams:
                sid = st.get('id') or st.get('_id'); sname = st.get('name') or st.get('_name') or sid
                mer += f"\n{sid}[\"Stream: {sname}\"]"

            # Agents and Endpoints (OCI GenAI Agents)
            try:
                from mcp_servers.agents.server import list_agents as _la, list_agent_endpoints as _le
                agents = _la(compartment_id=compartment_id).get('items', [])
                for ag in agents:
                    aid = ag.get('id') or ag.get('ocid') or ag.get('_id'); aname = ag.get('display_name') or ag.get('name') or aid
                    mer += f"\n{aid}[\"Agent: {aname}\"]"
                    eps = _le(compartment_id=compartment_id, agent_id=aid).get('items', [])
                    for ep in eps:
                        eid = ep.get('id'); ename = ep.get('display_name') or eid
                        mer += f"\n{eid}[\"Endpoint: {ename}\"]"
                        mer += f"\n{aid}--> {eid}"
            except Exception:
                pass

            # Knowledge Bases and Data Sources
            try:
                from mcp_servers.agents.server import list_knowledge_bases as _lkb, list_data_sources as _lds
                kbs = _lkb(compartment_id=compartment_id).get('items', [])
                for kb in kbs:
                    kbid = kb.get('id'); kbname = kb.get('display_name') or kbid
                    mer += f"\n{kbid}[\"KB: {kbname}\"]"
                    dss = _lds(compartment_id=compartment_id, knowledge_base_id=kbid).get('items', [])
                    for ds in dss:
                        dsid = ds.get('id'); dsname = ds.get('display_name') or dsid
                        mer += f"\n{dsid}[\"DS: {dsname}\"]"
                        mer += f"\n{kbid}--> {dsid}"
            except Exception:
                pass
            return {"mermaid": mer}
        else:
            # Fall back to server-level relations from mcp.json (repo root)
            root = os.path.abspath(os.path.join(REPO_ROOT, "mcp.json"))
            with open(root, 'r') as f:
                servers = json.load(f)
            mer = "graph TD\nClient-->MCP\nsubgraph MCP\n"
            for s in servers:
                mer += f"{s['name']}\n"
            mer += "end\nMCP-->OCI\nsubgraph OCI\nSDK\nend\n"
            return {"mermaid": mer}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/capacity")
def api_capacity(compartment_id: Optional[str] = None, region: Optional[str] = None):
    try:
        if not compartment_id:
            compartment_id = _default_compartment_id()
        if not compartment_id:
            return JSONResponse({"error": "Missing compartment_id. Set COMPARTMENT_OCID env var or pass ?compartment_id=..."}, status_code=400)
        from mcp_servers.inventory.server import generate_compute_capacity_report
        out = generate_compute_capacity_report(compartment_id=compartment_id, region=region)
        return out
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/costs")
def api_costs(time_window: str = "7d", granularity: str = "DAILY", compartment_id: Optional[str] = None, region: Optional[str] = None):
    try:
        import sys
        sys.path.append(os.path.join(os.path.dirname(BASE_DIR), "src"))
        from mcp_servers.cost.server import get_cost_summary
        out = get_cost_summary(time_window=time_window, granularity=granularity, compartment_id=compartment_id, region=region)
        return out
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/showoci")
def api_showoci(profile: Optional[str] = None, regions: Optional[str] = None, compartments: Optional[str] = None, resource_types: Optional[str] = None, output_format: str = "text", limit: int = 200):
    try:
        import sys
        sys.path.append(os.path.join(os.path.dirname(BASE_DIR), "src"))
        from mcp_servers.inventory.server import run_showoci_simple
        out = run_showoci_simple(profile=profile, regions=regions, compartments=compartments, resource_types=resource_types, output_format=output_format, diff_mode=False, limit=limit)
        return out
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/showusage")
def api_showusage(profile: Optional[str] = None, time_range: Optional[str] = None, granularity: str = "DAILY", compartment_id: Optional[str] = None, limit: int = 200):
    try:
        import sys
        sys.path.append(os.path.join(os.path.dirname(BASE_DIR), "src"))
        from mcp_servers.cost.server import run_showusage
        out = run_showusage(profile=profile, time_range=time_range, granularity=granularity, compartment_id=compartment_id, output_format="text", diff_mode=False, limit=limit)
        return out
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/db/summary")
def api_db_summary():
    try:
        conn = connect_db(); cur = conn.cursor()
        tables = [
            'VCNS','SUBNETS','INSTANCES','LOAD_BALANCERS','FUNCTIONS_APPS','STREAMS','COSTS_SUMMARY','CAPACITY_REPORT'
        ]
        summary = {}
        for t in tables:
            try:
                cur.execute(f"select count(*) from {t}"); summary[t.lower()] = int(cur.fetchone()[0])
            except Exception:
                summary[t.lower()] = None
        return summary
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/db/table")
def api_db_table(table: str, limit: int = 100):
    try:
        conn = connect_db(); cur = conn.cursor()
        cur.execute(f"select * from {table} fetch next :1 rows only", [limit])
        cols = [d[0].lower() for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return {"columns": cols, "rows": rows}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/db/sync")
def api_db_sync():
    """Create tables (idempotent) then populate from MCP extraction into AJD.
    Requires DB envs to be configured (wallet or DSN).
    """
    try:
        # Create tables
        r1 = subprocess.run([sys.executable or "python", "scripts/create_tables.py"], capture_output=True, text=True)
        # Populate
        r2 = subprocess.run([sys.executable or "python", "scripts/populate_db_from_mcp.py"], capture_output=True, text=True)
        ok1 = (r1.returncode == 0); ok2 = (r2.returncode == 0)
        return {
            "create_tables": {"ok": ok1, "stdout": r1.stdout, "stderr": r1.stderr},
            "populate": {"ok": ok2, "stdout": r2.stdout, "stderr": r2.stderr},
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/db/chart/costs")
def api_db_chart_costs(limit: int = 30):
    try:
        conn = connect_db(); cur = conn.cursor()
        cur.execute("select to_char(as_of,'YYYY-MM-DD HH24:MI:SS') as ts, total_cost, currency from costs_summary order by as_of desc fetch next :1 rows only", [limit])
        rows = [ {"ts": r[0], "total_cost": float(r[1] or 0), "currency": r[2]} for r in cur.fetchall() ]
        return {"series": rows[::-1]}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/db/chart/capacity")
def api_db_chart_capacity(limit: int = 30):
    try:
        conn = connect_db(); cur = conn.cursor()
        cur.execute("select to_char(as_of,'YYYY-MM-DD HH24:MI:SS') as ts,total_instances,running_instances,stopped_instances from capacity_report order by as_of desc fetch next :1 rows only", [limit])
        rows = [ {"ts": r[0], "total": int(r[1] or 0), "running": int(r[2] or 0), "stopped": int(r[3] or 0)} for r in cur.fetchall() ]
        return {"series": rows[::-1]}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/finops/analyze")
def api_finops_analyze(time_window: str = "30d", threshold: float = 3.0, compartment_id: Optional[str] = None, region: Optional[str] = None):
    """AI FinOps analysis: builds cost time series, detects anomalies, summarizes usage by service, and emits recommendations.
    If an Agent endpoint is configured, also returns an LLM summary.
    """
    try:
        import sys
        sys.path.append(os.path.join(os.path.dirname(BASE_DIR), "src"))
        from mcp_servers.cost.server import get_cost_timeseries, detect_cost_anomaly, get_usage_breakdown
        # Time series
        ts = get_cost_timeseries(time_window=time_window, compartment_id=compartment_id, region=region)
        if 'series' not in ts:
            return ts
        series = ts['series']
        values = [s['amount'] for s in series]
        # Anomaly detection (zscore by default)
        anomalies = detect_cost_anomaly(values, method="zscore", threshold=threshold)
        # Top services usage (last 30d)
        usage = get_usage_breakdown(service=None, compartment_id=compartment_id, region=region)
        if isinstance(usage, str):
            try:
                usage = json.loads(usage)
            except Exception:
                usage = []
        # Basic recommendations
        avg = (sum(values)/len(values)) if values else 0
        recs = []
        if anomalies.get('anomalies'):
            recs.append({"type":"anomaly","message": f"Detected {len(anomalies['anomalies'])} anomalies over {time_window}. Investigate spikes above threshold {threshold}."})
        top_services = sorted([u for u in usage if isinstance(u, dict) and 'service' in u], key=lambda x: x.get('usage',0), reverse=True)[:5]
        if top_services:
            recs.append({"type":"focus","message":"Top cost drivers identified.","services":[{"service":s['service'],"usage":s.get('usage'),"currency":s.get('currency')} for s in top_services]})
        if avg == 0:
            recs.append({"type":"info","message":"Average cost is zero for the window; ensure Usage API permissions and data availability."})
        # Optional LLM summary via Agents
        llm_summary = None
        agent_endpoint = os.getenv("GAI_AGENT_ENDPOINT")
        if agent_endpoint:
            prompt = {
                "message": f"Summarize FinOps: average={avg:.2f}, anomalies={anomalies.get('anomalies')}, top_services={[s['service'] for s in top_services]}. Recommend optimizations."
            }
            headers = {"Content-Type":"application/json"}
            api_key = os.getenv("GAI_AGENT_API_KEY")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            try:
                r = requests.post(agent_endpoint, json=prompt, headers=headers, timeout=30)
                if r.ok:
                    try:
                        llm_summary = r.json().get('reply') or r.text
                    except Exception:
                        llm_summary = r.text
            except Exception:
                pass
        return {
            "time_window": time_window,
            "series": series,
            "anomalies": anomalies,
            "top_services": top_services,
            "recommendations": recs,
            "llm_summary": llm_summary
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/chat")
async def api_chat(req: Request):
    try:
        payload = await req.json()
        message = payload.get("message", "")
        # Proxy to Java microservice using OCI Generative AI Agents SDK.
        # Configure:
        #   GAI_AGENT_ENDPOINT: base URL for the Java service (e.g., http://localhost:8088/agents/chat)
        #   GAI_AGENT_API_KEY: optional API key header
        agent_endpoint = os.getenv("GAI_AGENT_ENDPOINT")
        if not agent_endpoint:
            return {"reply": "OCI Generative AI Agent not configured. Set GAI_AGENT_ENDPOINT to enable.", "echo": message}
        headers = {"Content-Type": "application/json"}
        api_key = os.getenv("GAI_AGENT_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        resp = requests.post(agent_endpoint, json={"message": message}, headers=headers, timeout=30)
        if resp.ok:
            try:
                data = resp.json()
                reply = data.get("reply") or data.get("message") or str(data)
            except Exception:
                reply = resp.text
            return {"reply": reply}
        return JSONResponse({"error": resp.text or "Agent error"}, status_code=resp.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ===== Agents admin API proxies via MCP server implementation =====
@app.get("/api/agents")
def api_agents_list():
    try:
        sys.path.append(os.path.join(os.path.dirname(BASE_DIR), "src"))
        from mcp_servers.agents.server import list_agents as _list
        return _list()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/agents/create")
async def api_agents_create(req: Request):
    try:
        payload = await req.json()
        sys.path.append(os.path.join(os.path.dirname(BASE_DIR), "src"))
        from mcp_servers.agents.server import create_agent as _create
        return _create(
            name=payload.get('name',''),
            agent_type=payload.get('type',''),
            model=payload.get('model',''),
            description=payload.get('description'),
            config=payload.get('config') or {},
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/agents/{agent_id}")
def api_agents_delete(agent_id: str):
    try:
        sys.path.append(os.path.join(os.path.dirname(BASE_DIR), "src"))
        from mcp_servers.agents.server import delete_agent as _del
        return _del(agent_id=agent_id)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/agents/{agent_id}/update")
async def api_agents_update(agent_id: str, req: Request):
    try:
        payload = await req.json()
        sys.path.append(os.path.join(os.path.dirname(BASE_DIR), "src"))
        from mcp_servers.agents.server import update_agent as _upd
        return _upd(
            agent_id=agent_id,
            name=payload.get('name'),
            agent_type=payload.get('type'),
            model=payload.get('model'),
            description=payload.get('description'),
            config=payload.get('config'),
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/agents/{agent_id}/test")
async def api_agents_test(agent_id: str, req: Request):
    try:
        payload = await req.json()
        msg = payload.get('message','')
        sys.path.append(os.path.join(os.path.dirname(BASE_DIR), "src"))
        from mcp_servers.agents.server import test_agent_message as _test
        return _test(agent_id=agent_id, message=msg)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/kbs")
def api_kbs_list():
    try:
        from mcp_servers.agents.server import list_knowledge_bases as _list
        return _list()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/kbs/create")
async def api_kbs_create(req: Request):
    try:
        payload = await req.json()
        from mcp_servers.agents.server import create_knowledge_base as _create
        return _create(display_name=payload.get('display_name',''), description=payload.get('description'))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/kbs/{kb_id}/update")
async def api_kbs_update(kb_id: str, req: Request):
    try:
        payload = await req.json()
        from mcp_servers.agents.server import update_knowledge_base as _upd
        return _upd(knowledge_base_id=kb_id, display_name=payload.get('display_name'), description=payload.get('description'))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/kbs/{kb_id}")
def api_kbs_delete(kb_id: str):
    try:
        from mcp_servers.agents.server import delete_knowledge_base as _del
        return _del(knowledge_base_id=kb_id)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/kbs/{kb_id}/datasources")
def api_kb_datasources_list(kb_id: str):
    try:
        from mcp_servers.agents.server import list_data_sources as _list
        return _list(knowledge_base_id=kb_id)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/kbs/{kb_id}/datasources/create")
async def api_kb_datasources_create(kb_id: str, req: Request):
    try:
        payload = await req.json()
        from mcp_servers.agents.server import create_data_source as _create
        return _create(
            display_name=payload.get('display_name',''),
            description=payload.get('description'),
            knowledge_base_id=kb_id,
            object_storage_prefixes=payload.get('object_storage_prefixes') or [],
            metadata=payload.get('metadata') or {},
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/datasources/{ds_id}")
def api_datasource_delete(ds_id: str):
    try:
        from mcp_servers.agents.server import delete_data_source as _del
        return _del(data_source_id=ds_id)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/endpoints")
def api_endpoints_list(agent_id: Optional[str] = None):
    try:
        from mcp_servers.agents.server import list_agent_endpoints as _list
        return _list(agent_id=agent_id)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/endpoints/create")
async def api_endpoints_create(req: Request):
    try:
        payload = await req.json()
        from mcp_servers.agents.server import create_agent_endpoint as _create
        return _create(
            display_name=payload.get('display_name',''),
            agent_id=payload.get('agent_id',''),
            description=payload.get('description'),
            should_enable_trace=payload.get('should_enable_trace'),
            should_enable_citation=payload.get('should_enable_citation'),
            should_enable_session=payload.get('should_enable_session'),
            should_enable_multi_language=payload.get('should_enable_multi_language'),
            metadata=payload.get('metadata') or {},
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/endpoints/{ep_id}/update")
async def api_endpoints_update(ep_id: str, req: Request):
    try:
        payload = await req.json()
        from mcp_servers.agents.server import update_agent_endpoint as _upd
        return _upd(
            agent_endpoint_id=ep_id,
            display_name=payload.get('display_name'),
            description=payload.get('description'),
            should_enable_trace=payload.get('should_enable_trace'),
            should_enable_citation=payload.get('should_enable_citation'),
            should_enable_multi_language=payload.get('should_enable_multi_language'),
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# Optional metrics exporter for Prometheus
try:
    from prometheus_client import start_http_server as _start_http_server
    _start_http_server(int(os.getenv("METRICS_PORT", "8012")))
except Exception:
    pass

# Optional OpenTelemetry FastAPI instrumentation
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor as _FastAPIInstrumentor
    _FastAPIInstrumentor.instrument_app(app)
except Exception:
    pass

# Optional Pyroscope profiling
try:
    ENABLE_PYROSCOPE = os.getenv("ENABLE_PYROSCOPE", "false").lower() in ("1","true","yes","on")
    if ENABLE_PYROSCOPE:
        import pyroscope
        pyroscope.configure(
            application_name=os.getenv("PYROSCOPE_APP_NAME", "oci-web3-ux"),
            server_address=os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040"),
            sample_rate=int(os.getenv("PYROSCOPE_SAMPLE_RATE", "100")),
            detect_subprocesses=True,
            enable_logging=True,
        )
except Exception:
    pass


@app.delete("/api/endpoints/{ep_id}")
def api_endpoints_delete(ep_id: str):
    try:
        from mcp_servers.agents.server import delete_agent_endpoint as _del
        return _del(agent_endpoint_id=ep_id)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/observability/quick_checks")
def api_observability_quick_checks(compartment_id: Optional[str] = None, time_range: str = "24h", sample_size: int = 5):
    """Run basic Log Analytics checks (head, fields, stats by source)."""
    try:
        if not compartment_id:
            compartment_id = _env_compartment_only()
        if not compartment_id:
            return JSONResponse({"error": "Missing compartment_id. Set COMPARTMENT_OCID env var or pass ?compartment_id=..."}, status_code=400)
        from mcp_servers.observability.server import quick_checks as _qc
        out = _qc(compartment_id=compartment_id, time_range=time_range, sample_size=sample_size)
        return out
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("WEB3_UX_PORT", os.getenv("PORT", "8080")))
    uvicorn.run(app, host="0.0.0.0", port=port)
