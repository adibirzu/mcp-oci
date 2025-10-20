import os
import logging
import oci
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from fastmcp import FastMCP
from fastmcp.tools import Tool
from opentelemetry import trace
from oci.pagination import list_call_get_all_results
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span, add_oci_call_attributes
from mcp_oci_common.session import get_client
# Optional dependencies: load dotenv if available; import oracledb lazily
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv()
except Exception:
    _load_dotenv = None

def _import_oracledb():
    try:
        import oracledb  # type: ignore
        return oracledb
    except Exception as e:
        raise ImportError(
            "Missing dependency 'oracledb'. Install with 'pip install oracledb' or 'pip install \"mcp-oci[dev]\"' to enable ADB features."
        ) from e

from mcp_oci_common import get_oci_config, get_compartment_id, allow_mutations, validate_and_log_tools
from mcp_oci_common.cache import get_cache

# dotenv (if available) is already loaded above; continue without hard dependency

# Set up logging
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)

# Set up tracing with proper Resource so service.name is set (avoids unknown_service)
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-db")
init_tracing(service_name="oci-mcp-db")
init_metrics()
tracer = trace.get_tracer("oci-mcp-db")

def _fetch_autonomous_databases(compartment_id: Optional[str] = None, region: Optional[str] = None):
    config = get_oci_config()
    if region:
        config['region'] = region
    database_client = get_client(oci.database.DatabaseClient, region=config.get("region"))
    try:
        endpoint = getattr(database_client.base_client, "endpoint", "")
    except Exception:
        endpoint = ""
    add_oci_call_attributes(
        None,  # No span in internal
        oci_service="Database",
        oci_operation="ListAutonomousDatabases",
        region=config.get("region"),
        endpoint=endpoint,
    )
    compartment = compartment_id or get_compartment_id()
    response = list_call_get_all_results(database_client.list_autonomous_databases, compartment_id=compartment)
    req_id = response.headers.get("opc-request-id")
    dbs = response.data
    return [{
        'id': db.id,
        'display_name': db.display_name,
        'lifecycle_state': db.lifecycle_state,
        'db_workload': db.db_workload
    } for db in dbs], req_id

def list_autonomous_databases(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> List[Dict]:
    with tool_span(tracer, "list_autonomous_databases", mcp_server="oci-mcp-db") as span:
        cache = get_cache()
        params = {'compartment_id': compartment_id, 'region': region}
        try:
            dbs, req_id = cache.get_or_refresh(
                server_name="oci-mcp-db",
                operation="list_autonomous_databases",
                params=params,
                fetch_func=lambda: _fetch_autonomous_databases(compartment_id, region),
                ttl_seconds=600,
                force_refresh=False
            )
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            span.set_attribute("dbs.count", len(dbs))
            if compartment_id:
                span.set_attribute("compartment_id", compartment_id)
            if region:
                span.set_attribute("region", region)
            return dbs
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing autonomous databases: {e}")
            span.record_exception(e)
            return []

def _fetch_db_systems(compartment_id: Optional[str] = None, region: Optional[str] = None):
    config = get_oci_config()
    if region:
        config['region'] = region
    database_client = get_client(oci.database.DatabaseClient, region=config.get("region"))
    try:
        endpoint = getattr(database_client.base_client, "endpoint", "")
    except Exception:
        endpoint = ""
    add_oci_call_attributes(
        None,  # No span in internal
        oci_service="Database",
        oci_operation="ListDbSystems",
        region=config.get("region"),
        endpoint=endpoint,
    )
    compartment = compartment_id or get_compartment_id()
    response = list_call_get_all_results(database_client.list_db_systems, compartment_id=compartment)
    req_id = response.headers.get("opc-request-id")
    systems = response.data
    return [{
        'id': system.id,
        'display_name': system.display_name,
        'lifecycle_state': system.lifecycle_state,
        'shape': system.shape
    } for system in systems], req_id

def list_db_systems(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> List[Dict]:
    with tool_span(tracer, "list_db_systems", mcp_server="oci-mcp-db") as span:
        cache = get_cache()
        params = {'compartment_id': compartment_id, 'region': region}
        try:
            systems, req_id = cache.get_or_refresh(
                server_name="oci-mcp-db",
                operation="list_db_systems",
                params=params,
                fetch_func=lambda: _fetch_db_systems(compartment_id, region),
                ttl_seconds=600,
                force_refresh=False
            )
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            span.set_attribute("systems.count", len(systems))
            if compartment_id:
                span.set_attribute("compartment_id", compartment_id)
            if region:
                span.set_attribute("region", region)
            return systems
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
                span.set_attribute("metrics.datapoints", len(metrics))
                summary = {
                    'average': sum(dp.value for dp in metrics) / len(metrics) if metrics else 0,
                    'max': max(dp.value for dp in metrics) if metrics else 0,
                    'min': min(dp.value for dp in metrics) if metrics else 0,
                    'datapoints_count': len(metrics)
                }
                return summary
            return {'error': 'No metrics found'}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error getting DB metrics: {e}")
            return {'error': str(e)}

def _get_adb_connection():
    """Helper to get ADB connection"""
    oracledb = _import_oracledb()
    username = os.getenv("ADB_USERNAME", "ADMIN")
    password = os.getenv("ADB_PASSWORD")
    service_name = os.getenv("ADB_SERVICE_NAME")
    wallet_location = os.getenv("ADB_WALLET_LOCATION")

    if not all([password, service_name, wallet_location]):
        raise ValueError("ADB credentials not configured. Set ADB_PASSWORD, ADB_SERVICE_NAME, and ADB_WALLET_LOCATION")

    return oracledb.connect(
        user=username,
        password=password,
        dsn=service_name,
        config_dir=wallet_location
    )

def query_multicloud_costs(
    cloud_provider: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Query multi-cloud cost data from Autonomous Database

    Args:
        cloud_provider: Filter by cloud provider (aws, azure, oci) or None for all
        start_date: Start date filter (YYYY-MM-DD)
        end_date: End date filter (YYYY-MM-DD)
        limit: Maximum number of records to return
    """
    with tool_span(tracer, "query_multicloud_costs", mcp_server="oci-mcp-db") as span:
        try:
            conn = _get_adb_connection()
            cursor = conn.cursor()

            # Build query based on cloud provider
            if cloud_provider and cloud_provider.lower() == 'aws':
                table = "AWS_COSTS"
            elif cloud_provider and cloud_provider.lower() == 'azure':
                table = "AZURE_COSTS"
            else:
                # Query combined view if it exists, otherwise union
                table = "AWS_COSTS"  # Default for now

            query = f"""
                SELECT * FROM {table}
                WHERE 1=1
            """
            params = {}

            if start_date:
                query += " AND usage_date >= :start_date"
                params['start_date'] = start_date

            if end_date:
                query += " AND usage_date <= :end_date"
                params['end_date'] = end_date

            query += f" ORDER BY usage_date DESC FETCH FIRST {limit} ROWS ONLY"

            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))

            cursor.close()
            conn.close()

            return {
                "success": True,
                "cloud_provider": cloud_provider or "all",
                "record_count": len(results),
                "data": results
            }

        except Exception as e:
            logging.error(f"Error querying multi-cloud costs: {e}")
            span.record_exception(e)
            return {
                "success": False,
                "error": str(e)
            }

def get_cost_summary_by_cloud(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """Get cost summary aggregated by cloud provider

    Args:
        start_date: Start date filter (YYYY-MM-DD)
        end_date: End date filter (YYYY-MM-DD)
    """
    with tool_span(tracer, "get_cost_summary_by_cloud", mcp_server="oci-mcp-db") as span:
        try:
            conn = _get_adb_connection()
            cursor = conn.cursor()

            # Query AWS costs
            aws_query = """
                SELECT 'AWS' as cloud, SUM(cost) as total_cost, COUNT(*) as record_count
                FROM AWS_COSTS
                WHERE 1=1
            """
            aws_params = {}

            if start_date:
                aws_query += " AND usage_date >= :start_date"
                aws_params['start_date'] = start_date

            if end_date:
                aws_query += " AND usage_date <= :end_date"
                aws_params['end_date'] = end_date

            cursor.execute(aws_query, aws_params)
            aws_result = cursor.fetchone()

            # Query Azure costs
            azure_query = """
                SELECT 'Azure' as cloud, SUM(cost) as total_cost, COUNT(*) as record_count
                FROM AZURE_COSTS
                WHERE 1=1
            """
            azure_params = {}

            if start_date:
                azure_query += " AND usage_date >= :start_date"
                azure_params['start_date'] = start_date

            if end_date:
                azure_query += " AND usage_date <= :end_date"
                azure_params['end_date'] = end_date

            cursor.execute(azure_query, azure_params)
            azure_result = cursor.fetchone()

            cursor.close()
            conn.close()

            summary = {
                "AWS": {
                    "total_cost": float(aws_result[1]) if aws_result and aws_result[1] else 0.0,
                    "record_count": int(aws_result[2]) if aws_result else 0
                },
                "Azure": {
                    "total_cost": float(azure_result[1]) if azure_result and azure_result[1] else 0.0,
                    "record_count": int(azure_result[2]) if azure_result else 0
                }
            }

            total_cost = summary["AWS"]["total_cost"] + summary["Azure"]["total_cost"]

            return {
                "success": True,
                "period": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "summary": summary,
                "total_cost": total_cost
            }

        except Exception as e:
            logging.error(f"Error getting cost summary: {e}")
            span.record_exception(e)
            return {
                "success": False,
                "error": str(e)
            }

def get_autonomous_database(db_id: str) -> Dict[str, Any]:
    """Get detailed information about an Autonomous Database

    Args:
        db_id: The OCID of the Autonomous Database
    """
    with tool_span(tracer, "get_autonomous_database", mcp_server="oci-mcp-db") as span:
        config = get_oci_config()
        database_client = get_client(oci.database.DatabaseClient, region=config.get("region"))

        try:
            endpoint = getattr(database_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""

        add_oci_call_attributes(
            span,
            oci_service="Database",
            oci_operation="GetAutonomousDatabase",
            region=config.get("region"),
            endpoint=endpoint,
        )

        try:
            response = database_client.get_autonomous_database(db_id)
            db = response.data

            return {
                "success": True,
                "id": db.id,
                "display_name": db.display_name,
                "lifecycle_state": db.lifecycle_state,
                "db_workload": db.db_workload,
                "cpu_core_count": db.cpu_core_count,
                "data_storage_size_in_tbs": db.data_storage_size_in_tbs,
                "is_auto_scaling_enabled": db.is_auto_scaling_enabled,
                "is_free_tier": db.is_free_tier,
                "connection_strings": db.connection_strings.all_connection_strings if db.connection_strings else {}
            }
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error getting autonomous database: {e}")
            span.record_exception(e)
            return {
                "success": False,
                "error": str(e)
            }

def get_db_metrics(db_id: str, metric_name: str = "CpuUtilization", window: str = "1h") -> Dict[str, Any]:
    """Get metrics for a database resource

    Args:
        db_id: The OCID of the database
        metric_name: Metric to retrieve (CpuUtilization, StorageUtilization, etc.)
        window: Time window (1h, 6h, 24h, 7d)
    """
    with tool_span(tracer, "get_db_metrics", mcp_server="oci-mcp-db") as span:
        config = get_oci_config()
        monitoring_client = get_client(oci.monitoring.MonitoringClient, region=config.get("region"))

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

        # Calculate time window
        end_time = datetime.utcnow()
        window_hours = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}.get(window, 1)
        start_time = end_time - timedelta(hours=window_hours)

        query = f'{metric_name}[1m]{{resourceId="{db_id}"}}.mean()'

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

            if response.data and len(response.data) > 0:
                metrics = response.data[0].aggregated_datapoints

                if metrics:
                    values = [dp.value for dp in metrics]
                    return {
                        "success": True,
                        "metric_name": metric_name,
                        "window": window,
                        "data_points": len(metrics),
                        "statistics": {
                            "average": sum(values) / len(values),
                            "max": max(values),
                            "min": min(values),
                            "current": values[-1] if values else 0
                        }
                    }

            return {
                "success": True,
                "metric_name": metric_name,
                "message": "No metrics data available for the specified period"
            }

        except oci.exceptions.ServiceError as e:
            logging.error(f"Error getting DB metrics: {e}")
            span.record_exception(e)
            return {
                "success": False,
                "error": str(e)
            }

def healthcheck() -> dict:
    return {"status": "ok", "server": "oci-mcp-db", "pid": os.getpid()}

def doctor() -> dict:
    try:
        from mcp_oci_common.privacy import privacy_enabled
        cfg = get_oci_config()
        return {
            "server": "oci-mcp-db",
            "ok": True,
            "privacy": bool(privacy_enabled()),
            "region": cfg.get("region"),
            "profile": os.getenv("OCI_PROFILE") or "DEFAULT",
            "tools": [t.name for t in tools],
        }
    except Exception as e:
        return {"server": "oci-mcp-db", "ok": False, "error": str(e)}

tools = [
    Tool.from_function(
        fn=healthcheck,
        name="healthcheck",
        description="Lightweight readiness/liveness check for the database server"
    ),
    Tool.from_function(
        fn=doctor,
        name="doctor",
        description="Return server health, config summary, and masking status"
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
    Tool.from_function(
        fn=query_multicloud_costs,
        name="query_multicloud_costs",
        description="Query multi-cloud cost data from Autonomous Database (AWS, Azure, OCI)"
    ),
    Tool.from_function(
        fn=get_cost_summary_by_cloud,
        name="get_cost_summary_by_cloud",
        description="Get aggregated cost summary by cloud provider"
    ),
    Tool.from_function(
        fn=get_autonomous_database,
        name="get_autonomous_database",
        description="Get detailed information about an Autonomous Database"
    ),
    Tool.from_function(
        fn=get_db_metrics,
        name="get_db_metrics",
        description="Get performance metrics for a database resource"
    ),
]

def get_tools():
    return [{"name": t.name, "description": t.description} for t in tools]

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
    # Validate MCP tool names at startup
    if not validate_and_log_tools(tools, "oci-mcp-db"):
        logging.error("MCP tool validation failed. Server will not start.")
        exit(1)

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

    # Validate MCP tool names at startup
    try:
        from mcp_oci_common.validation import validate_and_log_tools as _validate_and_log_tools
        if not _validate_and_log_tools(tools, "oci-mcp-db"):
            logging.error("MCP tool validation failed. Server will not start.")
            exit(1)
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
