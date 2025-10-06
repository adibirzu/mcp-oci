import os
import json
import logging
from typing import Dict, Optional, Any

import requests
import oci
from fastmcp import FastMCP
from fastmcp.tools import Tool
from opentelemetry import trace

from mcp_oci_common.observability import init_tracing, init_metrics, tool_span
from mcp_oci_common import get_oci_config, get_compartment_id

logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)

os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-agents")
init_tracing(service_name="oci-mcp-agents")
init_metrics()
tracer = trace.get_tracer("oci-mcp-agents")


def _admin_base() -> str:
    base = os.getenv("GAI_ADMIN_ENDPOINT") or os.getenv("GAI_AGENT_ENDPOINT")
    if not base:
        raise RuntimeError("GAI_ADMIN_ENDPOINT not set. Set it to your Agents admin base URL (e.g., http://localhost:8088/agents/admin)")
    return base.rstrip('/')


def _headers() -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    api_key = os.getenv("GAI_AGENT_API_KEY")
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


def _mode() -> str:
    # 'oci' (default, uses OCI SDK) or 'proxy' (legacy admin endpoint)
    return (os.getenv("GAI_MODE") or "oci").lower()


def _oci_client(profile: Optional[str] = None, region: Optional[str] = None):
    cfg = get_oci_config(profile_name=profile)
    if region:
        cfg['region'] = region
    return oci.generative_ai_agent.GenerativeAiAgentClient(cfg)


def _poll_work_request(client: Any, work_request_id: str, timeout_sec: int = 600, interval_sec: float = 2.0) -> Dict[str, Any]:
    import time
    end = time.time() + timeout_sec
    status = None
    while time.time() < end:
        try:
            resp = client.get_work_request(work_request_id)
            data = getattr(resp, 'data', None)
            status = getattr(data, 'status', None)
            if status in ("SUCCEEDED", "FAILED", "CANCELED"):
                return {"status": status}
        except Exception:
            pass
        time.sleep(interval_sec)
    return {"status": status or "TIMEOUT"}


def _min_item(obj: Any, fields: tuple[str, ...] = ("id", "display_name")) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for f in fields:
        if isinstance(obj, dict):
            out[f] = obj.get(f)
        else:
            out[f] = getattr(obj, f, None)
    return out


def list_agents(compartment_id: Optional[str] = None, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "list_agents", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() == 'oci':
                comp = compartment_id or get_compartment_id()
                client = _oci_client(profile=profile, region=region)
                resp = client.list_agents(compartment_id=comp)
                items = []
                for it in getattr(resp, 'data', {}).items or []:
                    items.append(_min_item(it))
                return {"items": items}
            # proxy mode
            url = f"{_admin_base()}/agents"
            r = requests.get(url, headers=_headers(), timeout=20)
            if not r.ok:
                return {"error": r.text, "status": r.status_code}
            data = r.json() if r.headers.get('Content-Type','').startswith('application/json') else {"raw": r.text}
            return {"items": data.get('items') or data.get('agents') or data}
        except Exception as e:
            return {"error": str(e)}


def create_agent(name: str, agent_type: Optional[str] = None, model: Optional[str] = None, description: Optional[str] = None, config: Optional[Dict[str, Any]] = None,
                 compartment_id: Optional[str] = None, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "create_agent", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() == 'oci':
                client = _oci_client(profile=profile, region=region)
                comp = compartment_id or get_compartment_id()
                from oci.generative_ai_agent.models import CreateAgentDetails
                details = CreateAgentDetails(display_name=name, description=description, compartment_id=comp)
                resp = client.create_agent(details)
                wr = getattr(resp, 'headers', {}).get('opc-work-request-id') if hasattr(resp, 'headers') else None
                if wr:
                    _poll_work_request(client, wr)
                data = getattr(resp, 'data', None)
                return {"item": _min_item(data) if data else {}}
            # proxy mode
            url = f"{_admin_base()}/agents"
            payload = {"name": name}
            if agent_type: payload["type"] = agent_type
            if model: payload["model"] = model
            if description: payload["description"] = description
            if config: payload["config"] = config
            r = requests.post(url, headers=_headers(), data=json.dumps(payload), timeout=30)
            if not r.ok:
                return {"error": r.text, "status": r.status_code}
            return r.json() if r.headers.get('Content-Type','').startswith('application/json') else {"raw": r.text}
        except Exception as e:
            return {"error": str(e)}


def get_agent(agent_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "get_agent", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() == 'oci':
                client = _oci_client(profile=profile, region=region)
                resp = client.get_agent(agent_id)
                data = getattr(resp, 'data', None)
                return {"item": _min_item(data) if data else {}}
            url = f"{_admin_base()}/agents/{agent_id}"
            r = requests.get(url, headers=_headers(), timeout=20)
            if not r.ok:
                return {"error": r.text, "status": r.status_code}
            return r.json() if r.headers.get('Content-Type','').startswith('application/json') else {"raw": r.text}
        except Exception as e:
            return {"error": str(e)}


def delete_agent(agent_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "delete_agent", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() == 'oci':
                client = _oci_client(profile=profile, region=region)
                resp = client.delete_agent(agent_id)
                wr = getattr(resp, 'headers', {}).get('opc-work-request-id') if hasattr(resp, 'headers') else None
                if wr:
                    _poll_work_request(client, wr)
                return {"status": "deleted"}
            url = f"{_admin_base()}/agents/{agent_id}"
            r = requests.delete(url, headers=_headers(), timeout=20)
            if not r.ok:
                return {"error": r.text, "status": r.status_code}
            try:
                data = r.json()
            except Exception:
                data = {"status": "deleted"}
            return data
        except Exception as e:
            return {"error": str(e)}


def test_agent_message(agent_id: str, message: str) -> Dict[str, Any]:
    with tool_span(tracer, "test_agent_message", mcp_server="oci-mcp-agents") as span:
        try:
            # Allow either admin base or chat base; prefer admin path
            base = os.getenv("GAI_AGENT_ENDPOINT") or os.getenv("GAI_ADMIN_ENDPOINT")
            if not base:
                raise RuntimeError("GAI_AGENT_ENDPOINT or GAI_ADMIN_ENDPOINT not set (direct chat requires client API)")
            url = f"{base.rstrip('/')}/agents/{agent_id}/chat"
            r = requests.post(url, headers=_headers(), data=json.dumps({"message": message}), timeout=30)
            if not r.ok:
                return {"error": r.text, "status": r.status_code}
            return r.json() if r.headers.get('Content-Type','').startswith('application/json') else {"raw": r.text}
        except Exception as e:
            return {"error": str(e)}


def update_agent(agent_id: str, name: Optional[str] = None, agent_type: Optional[str] = None, model: Optional[str] = None, description: Optional[str] = None, config: Optional[Dict[str, Any]] = None,
                 profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "update_agent", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() == 'oci':
                client = _oci_client(profile=profile, region=region)
                from oci.generative_ai_agent.models import UpdateAgentDetails
                details = UpdateAgentDetails()
                if name is not None: setattr(details, 'display_name', name)
                if description is not None: setattr(details, 'description', description)
                resp = client.update_agent(agent_id, details)
                return {"status": "updated", "opc_request_id": getattr(resp, 'headers', {}).get('opc-request-id')}
            url = f"{_admin_base()}/agents/{agent_id}"
            payload: Dict[str, Any] = {}
            if name is not None: payload["name"] = name
            if agent_type is not None: payload["type"] = agent_type
            if model is not None: payload["model"] = model
            if description is not None: payload["description"] = description
            if config is not None: payload["config"] = config
            r = requests.put(url, headers=_headers(), data=json.dumps(payload), timeout=30)
            if r.status_code in (405, 501):
                r = requests.patch(url, headers=_headers(), data=json.dumps(payload), timeout=30)
            if not r.ok:
                return {"error": r.text, "status": r.status_code}
            return r.json() if r.headers.get('Content-Type','').startswith('application/json') else {"raw": r.text}
        except Exception as e:
            return {"error": str(e)}


# ===== Agent Endpoints (OCI mode) =====
def create_agent_endpoint(display_name: str, agent_id: str, description: Optional[str] = None,
                          compartment_id: Optional[str] = None, profile: Optional[str] = None, region: Optional[str] = None,
                          should_enable_trace: Optional[bool] = None, should_enable_citation: Optional[bool] = None,
                          should_enable_session: Optional[bool] = None, should_enable_multi_language: Optional[bool] = None,
                          metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    with tool_span(tracer, "create_agent_endpoint", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() != 'oci':
                return {"error": "Agent endpoints are only supported in OCI mode (set GAI_MODE=oci)"}
            client = _oci_client(profile=profile, region=region)
            comp = compartment_id or get_compartment_id()
            from oci.generative_ai_agent.models import CreateAgentEndpointDetails
            d = CreateAgentEndpointDetails(display_name=display_name, description=description, agent_id=agent_id, compartment_id=comp)
            if should_enable_trace is not None: setattr(d, 'should_enable_trace', bool(should_enable_trace))
            if should_enable_citation is not None: setattr(d, 'should_enable_citation', bool(should_enable_citation))
            if should_enable_session is not None: setattr(d, 'should_enable_session', bool(should_enable_session))
            if should_enable_multi_language is not None: setattr(d, 'should_enable_multi_language', bool(should_enable_multi_language))
            if metadata is not None: setattr(d, 'metadata', metadata)
            resp = client.create_agent_endpoint(d)
            wr = getattr(resp, 'headers', {}).get('opc-work-request-id') if hasattr(resp, 'headers') else None
            if wr:
                _poll_work_request(client, wr)
            data = getattr(resp, 'data', None)
            return {"item": _min_item(data) if data else {}}
        except Exception as e:
            return {"error": str(e)}


def list_agent_endpoints(compartment_id: Optional[str] = None, agent_id: Optional[str] = None, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "list_agent_endpoints", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() != 'oci':
                return {"error": "Agent endpoints are only supported in OCI mode (set GAI_MODE=oci)"}
            client = _oci_client(profile=profile, region=region)
            comp = compartment_id or get_compartment_id()
            kwargs: Dict[str, Any] = {"compartment_id": comp}
            if agent_id: kwargs["agent_id"] = agent_id
            resp = client.list_agent_endpoints(**kwargs)
            items = []
            for it in getattr(resp, 'data', {}).items or []:
                items.append(_min_item(it))
            return {"items": items}
        except Exception as e:
            return {"error": str(e)}


def get_agent_endpoint(agent_endpoint_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "get_agent_endpoint", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() != 'oci':
                return {"error": "Agent endpoints are only supported in OCI mode (set GAI_MODE=oci)"}
            client = _oci_client(profile=profile, region=region)
            resp = client.get_agent_endpoint(agent_endpoint_id)
            data = getattr(resp, 'data', None)
            return {"item": _min_item(data) if data else {}}
        except Exception as e:
            return {"error": str(e)}


def update_agent_endpoint(agent_endpoint_id: str, display_name: Optional[str] = None, description: Optional[str] = None,
                          should_enable_trace: Optional[bool] = None, should_enable_citation: Optional[bool] = None,
                          should_enable_multi_language: Optional[bool] = None,
                          profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "update_agent_endpoint", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() != 'oci':
                return {"error": "Agent endpoints are only supported in OCI mode (set GAI_MODE=oci)"}
            client = _oci_client(profile=profile, region=region)
            from oci.generative_ai_agent.models import UpdateAgentEndpointDetails
            d = UpdateAgentEndpointDetails()
            if display_name is not None: setattr(d, 'display_name', display_name)
            if description is not None: setattr(d, 'description', description)
            if should_enable_trace is not None: setattr(d, 'should_enable_trace', bool(should_enable_trace))
            if should_enable_citation is not None: setattr(d, 'should_enable_citation', bool(should_enable_citation))
            if should_enable_multi_language is not None: setattr(d, 'should_enable_multi_language', bool(should_enable_multi_language))
            resp = client.update_agent_endpoint(agent_endpoint_id, d)
            return {"status": "updated"}
        except Exception as e:
            return {"error": str(e)}


def delete_agent_endpoint(agent_endpoint_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "delete_agent_endpoint", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() != 'oci':
                return {"error": "Agent endpoints are only supported in OCI mode (set GAI_MODE=oci)"}
            client = _oci_client(profile=profile, region=region)
            resp = client.delete_agent_endpoint(agent_endpoint_id)
            wr = getattr(resp, 'headers', {}).get('opc-work-request-id') if hasattr(resp, 'headers') else None
            if wr:
                _poll_work_request(client, wr)
            return {"status": "deleted"}
        except Exception as e:
            return {"error": str(e)}

# ===== Knowledge Bases (OCI mode) =====
def create_knowledge_base(display_name: str, description: Optional[str] = None,
                          compartment_id: Optional[str] = None, profile: Optional[str] = None, region: Optional[str] = None,
                          freeform_tags: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    with tool_span(tracer, "create_knowledge_base", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() != 'oci':
                return {"error": "Knowledge Bases are only supported in OCI mode (set GAI_MODE=oci)"}
            client = _oci_client(profile=profile, region=region)
            comp = compartment_id or get_compartment_id()
            from oci.generative_ai_agent.models import CreateKnowledgeBaseDetails
            d = CreateKnowledgeBaseDetails(display_name=display_name, description=description, compartment_id=comp)
            if freeform_tags is not None: setattr(d, 'freeform_tags', freeform_tags)
            resp = client.create_knowledge_base(d)
            data = getattr(resp, 'data', None)
            return {"item": getattr(data, '__dict__', data)}
        except Exception as e:
            return {"error": str(e)}


def list_knowledge_bases(compartment_id: Optional[str] = None, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "list_knowledge_bases", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() != 'oci':
                return {"error": "Knowledge Bases are only supported in OCI mode (set GAI_MODE=oci)"}
            client = _oci_client(profile=profile, region=region)
            comp = compartment_id or get_compartment_id()
            resp = client.list_knowledge_bases(compartment_id=comp)
            items = []
            for it in getattr(resp, 'data', {}).items or []:
                items.append(_min_item(it))
            return {"items": items}
        except Exception as e:
            return {"error": str(e)}


def get_knowledge_base(knowledge_base_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "get_knowledge_base", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() != 'oci':
                return {"error": "Knowledge Bases are only supported in OCI mode (set GAI_MODE=oci)"}
            client = _oci_client(profile=profile, region=region)
            resp = client.get_knowledge_base(knowledge_base_id)
            data = getattr(resp, 'data', None)
            return {"item": getattr(data, '__dict__', data)}
        except Exception as e:
            return {"error": str(e)}


def update_knowledge_base(knowledge_base_id: str, display_name: Optional[str] = None, description: Optional[str] = None,
                          profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "update_knowledge_base", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() != 'oci':
                return {"error": "Knowledge Bases are only supported in OCI mode (set GAI_MODE=oci)"}
            client = _oci_client(profile=profile, region=region)
            from oci.generative_ai_agent.models import UpdateKnowledgeBaseDetails
            d = UpdateKnowledgeBaseDetails()
            if display_name is not None: setattr(d, 'display_name', display_name)
            if description is not None: setattr(d, 'description', description)
            resp = client.update_knowledge_base(knowledge_base_id, d)
            return {"status": "updated", "opc_request_id": getattr(resp, 'headers', {}).get('opc-request-id')}
        except Exception as e:
            return {"error": str(e)}


def delete_knowledge_base(knowledge_base_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "delete_knowledge_base", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() != 'oci':
                return {"error": "Knowledge Bases are only supported in OCI mode (set GAI_MODE=oci)"}
            client = _oci_client(profile=profile, region=region)
            resp = client.delete_knowledge_base(knowledge_base_id)
            wr = getattr(resp, 'headers', {}).get('opc-work-request-id') if hasattr(resp, 'headers') else None
            if wr:
                _poll_work_request(client, wr)
            return {"status": "deleted"}
        except Exception as e:
            return {"error": str(e)}


# ===== Data Sources (OCI mode) =====
def create_data_source(display_name: str, knowledge_base_id: str, description: Optional[str] = None,
                       object_storage_prefixes: Optional[list] = None, compartment_id: Optional[str] = None,
                       metadata: Optional[Dict[str, str]] = None, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "create_data_source", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() != 'oci':
                return {"error": "Data Sources are only supported in OCI mode (set GAI_MODE=oci)"}
            client = _oci_client(profile=profile, region=region)
            comp = compartment_id or get_compartment_id()
            from oci.generative_ai_agent.models import CreateDataSourceDetails, OciObjectStorageDataSourceConfig, ObjectStoragePrefix
            cfg = OciObjectStorageDataSourceConfig()
            if object_storage_prefixes:
                cfg.object_storage_prefixes = [ObjectStoragePrefix(**p) if isinstance(p, dict) else p for p in object_storage_prefixes]
            d = CreateDataSourceDetails(display_name=display_name, description=description, knowledge_base_id=knowledge_base_id, data_source_config=cfg, compartment_id=comp)
            if metadata is not None: setattr(d, 'metadata', metadata)
            resp = client.create_data_source(d)
            wr = getattr(resp, 'headers', {}).get('opc-work-request-id') if hasattr(resp, 'headers') else None
            if wr:
                _poll_work_request(client, wr)
            data = getattr(resp, 'data', None)
            return {"item": _min_item(data) if data else {}}
        except Exception as e:
            return {"error": str(e)}


def list_data_sources(compartment_id: Optional[str] = None, knowledge_base_id: Optional[str] = None, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "list_data_sources", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() != 'oci':
                return {"error": "Data Sources are only supported in OCI mode (set GAI_MODE=oci)"}
            client = _oci_client(profile=profile, region=region)
            comp = compartment_id or get_compartment_id()
            kwargs: Dict[str, Any] = {"compartment_id": comp}
            if knowledge_base_id: kwargs["knowledge_base_id"] = knowledge_base_id
            resp = client.list_data_sources(**kwargs)
            items = []
            for it in getattr(resp, 'data', {}).items or []:
                items.append(_min_item(it))
            return {"items": items}
        except Exception as e:
            return {"error": str(e)}


def get_data_source(data_source_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "get_data_source", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() != 'oci':
                return {"error": "Data Sources are only supported in OCI mode (set GAI_MODE=oci)"}
            client = _oci_client(profile=profile, region=region)
            resp = client.get_data_source(data_source_id)
            data = getattr(resp, 'data', None)
            return {"item": _min_item(data) if data else {}}
        except Exception as e:
            return {"error": str(e)}


def update_data_source(data_source_id: str, display_name: Optional[str] = None, description: Optional[str] = None,
                       profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "update_data_source", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() != 'oci':
                return {"error": "Data Sources are only supported in OCI mode (set GAI_MODE=oci)"}
            client = _oci_client(profile=profile, region=region)
            from oci.generative_ai_agent.models import UpdateDataSourceDetails
            d = UpdateDataSourceDetails()
            if display_name is not None: setattr(d, 'display_name', display_name)
            if description is not None: setattr(d, 'description', description)
            resp = client.update_data_source(data_source_id, d)
            return {"status": "updated"}
        except Exception as e:
            return {"error": str(e)}


def delete_data_source(data_source_id: str, profile: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    with tool_span(tracer, "delete_data_source", mcp_server="oci-mcp-agents") as span:
        try:
            if _mode() != 'oci':
                return {"error": "Data Sources are only supported in OCI mode (set GAI_MODE=oci)"}
            client = _oci_client(profile=profile, region=region)
            resp = client.delete_data_source(data_source_id)
            wr = getattr(resp, 'headers', {}).get('opc-work-request-id') if hasattr(resp, 'headers') else None
            if wr:
                _poll_work_request(client, wr)
            return {"status": "deleted"}
        except Exception as e:
            return {"error": str(e)}
tools = [
    Tool.from_function(fn=lambda: {"status": "ok", "server": "oci-mcp-agents", "pid": os.getpid()}, name="healthcheck", description="Liveness check for agents server"),
    Tool.from_function(fn=lambda: (lambda _cfg=get_oci_config(): {"server": "oci-mcp-agents", "ok": True, "region": _cfg.get("region"), "profile": os.getenv("OCI_PROFILE") or "DEFAULT", "tools": [t.name for t in tools]})(), name="doctor", description="Return server health, config summary, and masking status"),
    Tool.from_function(fn=list_agents,        name="list_agents",        description="List Generative AI Agents (OCI/proxy)"),
    Tool.from_function(fn=create_agent,       name="create_agent",       description="Create a Generative AI Agent (OCI/proxy)"),
    Tool.from_function(fn=get_agent,          name="get_agent",          description="Get agent details by id"),
    Tool.from_function(fn=update_agent,       name="update_agent",       description="Update agent fields (name/type/model/description/config)"),
    Tool.from_function(fn=delete_agent,       name="delete_agent",       description="Delete agent by id"),
    Tool.from_function(fn=test_agent_message, name="test_agent_message", description="Send a test message to an agent and get reply"),
    # Endpoints (OCI mode)
    Tool.from_function(fn=create_agent_endpoint,   name="create_agent_endpoint",   description="Create an Agent Endpoint (OCI mode)"),
    Tool.from_function(fn=list_agent_endpoints,    name="list_agent_endpoints",    description="List Agent Endpoints in a compartment (OCI mode)"),
    Tool.from_function(fn=get_agent_endpoint,      name="get_agent_endpoint",      description="Get Agent Endpoint by OCID (OCI mode)"),
    Tool.from_function(fn=update_agent_endpoint,   name="update_agent_endpoint",   description="Update Agent Endpoint fields (OCI mode)"),
    Tool.from_function(fn=delete_agent_endpoint,   name="delete_agent_endpoint",   description="Delete Agent Endpoint (OCI mode)"),
    # Knowledge Bases (OCI mode)
    Tool.from_function(fn=create_knowledge_base,   name="create_knowledge_base",   description="Create a Knowledge Base (OCI mode)"),
    Tool.from_function(fn=list_knowledge_bases,    name="list_knowledge_bases",    description="List Knowledge Bases in a compartment (OCI mode)"),
    Tool.from_function(fn=get_knowledge_base,      name="get_knowledge_base",      description="Get Knowledge Base by OCID (OCI mode)"),
    Tool.from_function(fn=update_knowledge_base,   name="update_knowledge_base",   description="Update Knowledge Base fields (OCI mode)"),
    Tool.from_function(fn=delete_knowledge_base,   name="delete_knowledge_base",   description="Delete Knowledge Base (OCI mode)")
]


if __name__ == "__main__":
    # Optional Prometheus metrics
    try:
        from prometheus_client import start_http_server as _start_http_server
        _start_http_server(int(os.getenv("METRICS_PORT", "8011")))
    except Exception:
        pass

    # Optional Pyroscope profiling (non-breaking)
    try:
        ENABLE_PYROSCOPE = os.getenv("ENABLE_PYROSCOPE", "false").lower() in ("1", "true", "yes", "on")
        if ENABLE_PYROSCOPE:
            import pyroscope
            pyroscope.configure(
                application_name=os.getenv("PYROSCOPE_APP_NAME", "oci-mcp-agents"),
                server_address=os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040"),
                sample_rate=int(os.getenv("PYROSCOPE_SAMPLE_RATE", "100")),
                detect_subprocesses=True,
                enable_logging=True,
            )
    except Exception:
        pass

    # Apply privacy masking to all tools (wrapper)
    try:
        from mcp_oci_common.privacy import privacy_enabled as _pe, redact_payload as _rp
        from fastmcp.tools import Tool as _Tool
        _wrapped = []
        for _t in tools:
            _f = getattr(_t, "func", None) or getattr(_t, "handler", None)
            if not _f:
                _wrapped.append(_t)
                continue
            def _mk(f):
                def _w(*a, **k):
                    out = f(*a, **k)
                    return _rp(out) if _pe() else out
                _w.__name__ = getattr(f, "__name__", "tool")
                _w.__doc__ = getattr(f, "__doc__", "")
                return _w
            _wrapped.append(_Tool.from_function(_mk(_f), name=_t.name, description=_t.description))
        tools = _wrapped
    except Exception:
        pass

    mcp = FastMCP(tools=tools, name="oci-mcp-agents")
    mcp.run()
