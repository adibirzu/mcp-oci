import os
import logging
import oci
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from fastmcp import FastMCP
from fastmcp.tools import Tool
from opentelemetry import trace
from oci.pagination import list_call_get_all_results
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span, add_oci_call_attributes
from mcp_oci_common.session import get_client

from mcp_oci_common import get_oci_config, get_compartment_id, allow_mutations

# Set up logging
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)

# Set up tracing with proper Resource so service.name is set (avoids unknown_service)
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-db")
init_tracing(service_name="oci-mcp-db")
init_metrics()
tracer = trace.get_tracer("oci-mcp-db")

def list_autonomous_databases(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> List[Dict]:
    with tool_span(tracer, "list_autonomous_databases", mcp_server="oci-mcp-db") as span:
        config = get_oci_config()
        if region:
            config['region'] = region
        database_client = get_client(oci.database.DatabaseClient, region=config.get("region"))
        # Enrich span with backend call metadata
        try:
            endpoint = getattr(database_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Database",
            oci_operation="ListAutonomousDatabases",
            region=config.get("region"),
            endpoint=endpoint,
        )
        compartment = compartment_id or get_compartment_id()
        
        try:
            response = list_call_get_all_results(database_client.list_autonomous_databases, compartment_id=compartment)
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            dbs = response.data
            return [{
                'id': db.id,
                'display_name': db.display_name,
                'lifecycle_state': db.lifecycle_state,
                'db_workload': db.db_workload
            } for db in dbs]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing autonomous databases: {e}")
            span.record_exception(e)
            return []

def list_db_systems(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> List[Dict]:
    with tool_span(tracer, "list_db_systems", mcp_server="oci-mcp-db") as span:
        config = get_oci_config()
        if region:
            config['region'] = region
        database_client = get_client(oci.database.DatabaseClient, region=config.get("region"))
        # Enrich span with backend call metadata
        try:
            endpoint = getattr(database_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Database",
            oci_operation="ListDbSystems",
            region=config.get("region"),
            endpoint=endpoint,
        )
        compartment = compartment_id or get_compartment_id()
        
        try:
            response = list_call_get_all_results(database_client.list_db_systems, compartment_id=compartment)
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            systems = response.data
            return [{
                'id': system.id,
                'display_name': system.display_name,
                'lifecycle_state': system.lifecycle_state,
                'shape': system.shape
            } for system in systems]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing DB systems: {e}")
            span.record_exception(e)
            return []

def start_db_system(db_system_id: str) -> Dict:
    with tool_span(tracer, "start_db_system", mcp_server="oci-mcp-db") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}
        
        config = get_oci_config()
        database_client = get_client(oci.database.DatabaseClient, region=config.get("region"))
        try:
            endpoint = getattr(database_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Database",
            oci_operation="DbSystemAction(START)",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = database_client.db_system_action(db_system_id, 'START')
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            return {'status': response.data.lifecycle_state}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error starting DB system: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def stop_db_system(db_system_id: str) -> Dict:
    with tool_span(tracer, "stop_db_system", mcp_server="oci-mcp-db") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}
        
        config = get_oci_config()
        database_client = get_client(oci.database.DatabaseClient, region=config.get("region"))
        try:
            endpoint = getattr(database_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Database",
            oci_operation="DbSystemAction(STOP)",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = database_client.db_system_action(db_system_id, 'STOP')
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            return {'status': response.data.lifecycle_state}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error stopping DB system: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def restart_db_system(db_system_id: str) -> Dict:
    with tool_span(tracer, "restart_db_system", mcp_server="oci-mcp-db") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}
        
        config = get_oci_config()
        database_client = get_client(oci.database.DatabaseClient, region=config.get("region"))
        try:
            endpoint = getattr(database_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Database",
            oci_operation="DbSystemAction(RESTART)",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = database_client.db_system_action(db_system_id, 'RESTART')
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            return {'status': response.data.lifecycle_state}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error restarting DB system: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def start_autonomous_database(db_id: str) -> Dict:
    with tool_span(tracer, "start_autonomous_database", mcp_server="oci-mcp-db") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}
        
        config = get_oci_config()
        database_client = get_client(oci.database.DatabaseClient, region=config.get("region"))
        try:
            endpoint = getattr(database_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Database",
            oci_operation="StartAutonomousDatabase",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = database_client.start_autonomous_database(db_id)
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            return {'status': response.data.lifecycle_state}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error starting autonomous database: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def stop_autonomous_database(db_id: str) -> Dict:
    with tool_span(tracer, "stop_autonomous_database", mcp_server="oci-mcp-db") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}
        
        config = get_oci_config()
        database_client = get_client(oci.database.DatabaseClient, region=config.get("region"))
        try:
            endpoint = getattr(database_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Database",
            oci_operation="StopAutonomousDatabase",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = database_client.stop_autonomous_database(db_id)
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            return {'status': response.data.lifecycle_state}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error stopping autonomous database: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def restart_autonomous_database(db_id: str) -> Dict:
    with tool_span(tracer, "restart_autonomous_database", mcp_server="oci-mcp-db") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}
        
        config = get_oci_config()
        database_client = get_client(oci.database.DatabaseClient, region=config.get("region"))
        try:
            endpoint = getattr(database_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Database",
            oci_operation="RestartAutonomousDatabase",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = database_client.restart_autonomous_database(db_id)
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            return {'status': response.data.lifecycle_state}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error restarting autonomous database: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def get_db_cpu_snapshot(db_id: str, window: str = "1h") -> Dict:
    with tool_span(tracer, "get_db_cpu_snapshot", mcp_server="oci-mcp-db") as span:
        config = get_oci_config()
        monitoring_client = get_client(oci.monitoring.MonitoringClient, region=config.get("region"))
        # Enrich span with backend call metadata
        try:
            endpoint = getattr(monitoring_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Monitoring",
            oci_operation="SummarizeMetricsData",
            region=config.get("region"),
            endpoint=endpoint,
        )
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1) if window == "1h" else end_time - timedelta(days=1)
        
        query = f'CpuUtilization[1m]{{resourceId="{db_id}"}}.mean()'
        
        try:
            response = monitoring_client.summarize_metrics_data(
                compartment_id=get_compartment_id(),
                summarize_metrics_data_details=oci.monitoring.models.SummarizeMetricsDataDetails(
                    namespace="oci_database",
                    query=query,
                    start_time=start_time,
                    end_time=end_time
                )
            )
            try:
                req_id = response.headers.get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            if response.data:
                metrics = response.data[0].aggregated_datapoints
                summary = {
                    'average': sum(dp.value for dp in metrics) / len(metrics) if metrics else 0,
                    'max': max(dp.value for dp in metrics) if metrics else 0,
                    'min': min(dp.value for dp in metrics) if metrics else 0
                }
                return summary
            return {'error': 'No metrics found'}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error getting DB metrics: {e}")
            return {'error': str(e)}

def healthcheck() -> dict:
    return {"status": "ok", "server": "oci-mcp-db", "pid": os.getpid()}

tools = [
    Tool.from_function(
        fn=healthcheck,
        name="healthcheck",
        description="Lightweight readiness/liveness check for the database server"
    ),
    Tool.from_function(
        fn=list_autonomous_databases,
        name="list_autonomous_databases",
        description="List autonomous databases"
    ),
    Tool.from_function(
        fn=list_db_systems,
        name="list_db_systems",
        description="List DB systems"
    ),
    Tool.from_function(
        fn=start_db_system,
        name="start_db_system",
        description="Start a DB system"
    ),
    Tool.from_function(
        fn=stop_db_system,
        name="stop_db_system",
        description="Stop a DB system"
    ),
    Tool.from_function(
        fn=restart_db_system,
        name="restart_db_system",
        description="Restart a DB system"
    ),
    Tool.from_function(
        fn=start_autonomous_database,
        name="start_autonomous_database",
        description="Start an autonomous database"
    ),
    Tool.from_function(
        fn=stop_autonomous_database,
        name="stop_autonomous_database",
        description="Stop an autonomous database"
    ),
    Tool.from_function(
        fn=restart_autonomous_database,
        name="restart_autonomous_database",
        description="Restart an autonomous database"
    ),
    Tool.from_function(
        fn=get_db_cpu_snapshot,
        name="get_db_cpu_snapshot",
        description="Get CPU metrics snapshot for a database"
    ),
]

# FastAPI instrumentation is imported lazily in __main__ to avoid hard dependency at import time

if __name__ == "__main__":
    # Lazy imports so importing this module (for UX tool discovery) doesn't require optional deps
    try:
        from prometheus_client import start_http_server as _start_http_server
    except Exception:
        _start_http_server = None
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor as _FastAPIInstrumentor
    except Exception:
        _FastAPIInstrumentor = None

    # Expose Prometheus /metrics regardless of DEBUG (configurable via METRICS_PORT)
    if _start_http_server:
        try:
            _start_http_server(int(os.getenv("METRICS_PORT", "8002")))
        except Exception:
            pass
    mcp = FastMCP(tools=tools, name="oci-mcp-db")
    if _FastAPIInstrumentor:
        try:
            if hasattr(mcp, "app"):
                _FastAPIInstrumentor.instrument_app(getattr(mcp, "app"))
            elif hasattr(mcp, "fastapi_app"):
                _FastAPIInstrumentor.instrument_app(getattr(mcp, "fastapi_app"))
            else:
                _FastAPIInstrumentor().instrument()
        except Exception:
            try:
                _FastAPIInstrumentor().instrument()
            except Exception:
                pass

    # Optional Pyroscope profiling (non-breaking)
    try:
        ENABLE_PYROSCOPE = os.getenv("ENABLE_PYROSCOPE", "false").lower() in ("1", "true", "yes", "on")
        if ENABLE_PYROSCOPE:
            import pyroscope
            pyroscope.configure(
                application_name=os.getenv("PYROSCOPE_APP_NAME", "oci-mcp-db"),
                server_address=os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040"),
                sample_rate=int(os.getenv("PYROSCOPE_SAMPLE_RATE", "100")),
                detect_subprocesses=True,
                enable_logging=True,
            )
    except Exception:
        # Never break server if profiler not available
        pass

    mcp.run()
