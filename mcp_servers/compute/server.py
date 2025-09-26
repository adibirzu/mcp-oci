import os
import logging
import oci
from typing import List, Dict, Optional, Any
from fastmcp import FastMCP
from fastmcp.tools import Tool
from datetime import datetime, timedelta
from opentelemetry import trace
from oci.pagination import list_call_get_all_results
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span, add_oci_call_attributes
from mcp_oci_common.session import get_client

from mcp_oci_common import get_oci_config, get_compartment_id, allow_mutations, validate_and_log_tools
from mcp_oci_common.cache import get_cache

# Set up logging
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)

# Set up tracing with proper Resource so service.name is set (avoids unknown_service)
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-compute")
init_tracing(service_name="oci-mcp-compute")
init_metrics()
tracer = trace.get_tracer("oci-mcp-compute")

def _fetch_instances(compartment_id: Optional[str] = None, region: Optional[str] = None, lifecycle_state: Optional[str] = None):
    """Internal function to fetch instances from OCI"""
    config = get_oci_config()
    if region:
        config['region'] = region
    compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))
    compartment = compartment_id or get_compartment_id()

    # Normalize and validate lifecycle_state before calling OCI SDK
    lifecycle_state_param = None
    if lifecycle_state:
        # Handle empty strings or whitespace
        lifecycle_state = str(lifecycle_state).strip()
        if lifecycle_state:
            allowed_states = {"MOVING", "PROVISIONING", "RUNNING", "STARTING", "STOPPING", "STOPPED", "CREATING_IMAGE", "TERMINATING", "TERMINATED"}
            norm = lifecycle_state.upper()
            if norm not in allowed_states:
                raise ValueError(f"Invalid value for lifecycle_state. Allowed: {sorted(list(allowed_states))}")
            lifecycle_state_param = norm

    # Only pass lifecycle_state if it's not None
    kwargs = {'compartment_id': compartment}
    if lifecycle_state_param is not None:
        kwargs['lifecycle_state'] = lifecycle_state_param
    response = list_call_get_all_results(compute_client.list_instances, **kwargs)
    instances = response.data

    # Enhance instance data with IP addresses
    enhanced_instances = []
    for inst in instances:
        instance_data = {
            'id': inst.id,
            'display_name': inst.display_name,
            'lifecycle_state': inst.lifecycle_state,
            'shape': inst.shape,
            'availability_domain': getattr(inst, 'availability_domain', ''),
            'compartment_id': getattr(inst, 'compartment_id', compartment),
            'time_created': getattr(inst, 'time_created', '').isoformat() if hasattr(inst, 'time_created') and inst.time_created else ''
        }

        # Add IP addresses if instance is running
        if inst.lifecycle_state == 'RUNNING':
            ip_info = _get_instance_ips(inst.id)
            instance_data.update({
                'private_ip': ip_info.get('primary_private_ip'),
                'public_ip': ip_info.get('primary_public_ip'),
                'all_private_ips': ip_info.get('private_ips', []),
                'all_public_ips': ip_info.get('public_ips', [])
            })
        else:
            instance_data.update({
                'private_ip': None,
                'public_ip': None,
                'all_private_ips': [],
                'all_public_ips': []
            })

        enhanced_instances.append(instance_data)

    return enhanced_instances

def list_instances(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None,
    lifecycle_state: Optional[str] = None,
    force_refresh: bool = False
) -> List[Dict]:
    with tool_span(tracer, "list_instances", mcp_server="oci-mcp-compute") as span:
        cache = get_cache()

        # Create params dict for caching
        params = {
            'compartment_id': compartment_id,
            'region': region,
            'lifecycle_state': lifecycle_state
        }

        try:
            # Get cached data or refresh
            instances = cache.get_or_refresh(
                server_name="oci-mcp-compute",
                operation="list_instances",
                params=params,
                fetch_func=lambda: _fetch_instances(compartment_id, region, lifecycle_state),
                force_refresh=force_refresh
            )

            span.set_attribute("instances.count", len(instances) if instances else 0)
            if compartment_id:
                span.set_attribute("compartment_id", compartment_id)
            if region:
                span.set_attribute("region", region)
            if lifecycle_state:
                span.set_attribute("lifecycle_state", lifecycle_state)

            return instances or []

        except ValueError as e:
            # Handle validation errors (like invalid lifecycle_state)
            return [{'error': str(e)}]
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing instances: {e}")
            span.record_exception(e)
            return [{'error': str(e)}]

def start_instance(instance_id: str) -> Dict:
    with tool_span(tracer, "start_instance", mcp_server="oci-mcp-compute") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}
        
        config = get_oci_config()
        compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))
        # Enrich span with backend call metadata
        try:
            endpoint = getattr(compute_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Compute",
            oci_operation="InstanceAction(START)",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = compute_client.instance_action(instance_id, 'START')
            try:
                req_id = getattr(response, "headers", {}).get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            return {'status': response.data.lifecycle_state}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error starting instance: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def stop_instance(instance_id: str) -> Dict:
    with tool_span(tracer, "stop_instance", mcp_server="oci-mcp-compute") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}
        
        config = get_oci_config()
        compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))
        # Enrich span with backend call metadata
        try:
            endpoint = getattr(compute_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Compute",
            oci_operation="InstanceAction(STOP)",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = compute_client.instance_action(instance_id, 'STOP')
            try:
                req_id = getattr(response, "headers", {}).get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            return {'status': response.data.lifecycle_state}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error stopping instance: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def restart_instance(instance_id: str, hard: bool = False) -> Dict:
    with tool_span(tracer, "restart_instance", mcp_server="oci-mcp-compute") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}
        
        config = get_oci_config()
        compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))
        # Enrich span with backend call metadata
        try:
            endpoint = getattr(compute_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Compute",
            oci_operation="InstanceAction(RESET)",
            region=config.get("region"),
            endpoint=endpoint,
        )
        action = 'RESET' if hard else 'SOFTRESET'
        try:
            response = compute_client.instance_action(instance_id, action)
            try:
                req_id = getattr(response, "headers", {}).get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass
            return {'status': response.data.lifecycle_state}
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error restarting instance: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def create_instance(
    display_name: str,
    shape: str,
    subnet_id: str,
    source_type: str = "image",
    source_id: Optional[str] = None,
    compartment_id: Optional[str] = None,
    availability_domain: Optional[str] = None,
    ssh_public_keys: Optional[List[str]] = None
) -> Dict:
    with tool_span(tracer, "create_instance", mcp_server="oci-mcp-compute") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}

        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))
        try:
            endpoint = getattr(compute_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="Compute",
            oci_operation="LaunchInstance",
            region=config.get("region"),
            endpoint=endpoint,
        )

        # Create instance source details
        if source_type == "image":
            source_details = oci.core.models.InstanceSourceViaImageDetails(
                source_type="image",
                image_id=source_id or "ocid1.image.oc1.eu-frankfurt-1.aaaaaaaav3v6z6z6z6z6z6z6z6z6z6z6z6z6z6z6z6z6z6z6z6z6z6z"  # Default Ubuntu image
            )
        else:
            return {'error': f'Unsupported source_type: {source_type}. Use "image".'}

        # Create instance details
        create_instance_details = oci.core.models.LaunchInstanceDetails(
            compartment_id=compartment,
            display_name=display_name,
            shape=shape,
            source_details=source_details,
            create_vnic_details=oci.core.models.CreateVnicDetails(
                subnet_id=subnet_id
            )
        )

        if availability_domain:
            create_instance_details.availability_domain = availability_domain

        if ssh_public_keys:
            create_instance_details.metadata = {
                'ssh_authorized_keys': '\n'.join(ssh_public_keys)
            }

def _safe_serialize(obj):
    """Safely serialize OCI SDK objects and other complex types"""
    if obj is None:
        return None

    # Handle OCI SDK objects
    if hasattr(obj, '__dict__'):
        try:
            # Try to convert OCI objects to dict
            if hasattr(obj, 'to_dict'):
                return obj.to_dict()
            elif hasattr(obj, '_data') and hasattr(obj._data, '__dict__'):
                return obj._data.__dict__
            else:
                # Fallback to manual serialization of object attributes
                result = {}
                for key, value in obj.__dict__.items():
                    if not key.startswith('_'):
                        result[key] = _safe_serialize(value)
                return result
        except Exception as e:
            return {"serialization_error": str(e), "original_type": str(type(obj))}

    # Handle lists and tuples
    elif isinstance(obj, (list, tuple)):
        return [_safe_serialize(item) for item in obj]

    # Handle dictionaries
    elif isinstance(obj, dict):
        return {key: _safe_serialize(value) for key, value in obj.items()}

    # Handle primitive types
    elif isinstance(obj, (str, int, float, bool)):
        return obj

    # For unknown types, try to convert to string
    else:
        try:
            return str(obj)
        except Exception:
            return {"unknown_type": str(type(obj))}

def _get_instance_ips(instance_id: str) -> Dict[str, Any]:
    """Get IP addresses for an instance by querying its VNICs"""
    try:
        config = get_oci_config()
        compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))
        network_client = get_client(oci.core.VirtualNetworkClient, region=config.get("region"))

        # Get instance details first to get compartment_id
        instance = compute_client.get_instance(instance_id).data
        compartment_id = instance.compartment_id

        # List VNICs attached to this instance
        vnic_attachments = list_call_get_all_results(
            compute_client.list_vnic_attachments,
            compartment_id=compartment_id,
            instance_id=instance_id
        ).data

        ips = {
            'private_ips': [],
            'public_ips': [],
            'primary_private_ip': None,
            'primary_public_ip': None
        }

        for attachment in vnic_attachments:
            if attachment.lifecycle_state == 'ATTACHED':
                try:
                    vnic = network_client.get_vnic(attachment.vnic_id).data

                    # Add private IP
                    if vnic.private_ip:
                        ips['private_ips'].append(vnic.private_ip)
                        if attachment.is_primary and not ips['primary_private_ip']:
                            ips['primary_private_ip'] = vnic.private_ip

                    # Add public IP
                    if vnic.public_ip:
                        ips['public_ips'].append(vnic.public_ip)
                        if attachment.is_primary and not ips['primary_public_ip']:
                            ips['primary_public_ip'] = vnic.public_ip

                except Exception as e:
                    logging.warning(f"Error getting VNIC details for {attachment.vnic_id}: {e}")
                    continue

        return ips

    except Exception as e:
        logging.error(f"Error getting instance IPs for {instance_id}: {e}")
        return {
            'private_ips': [],
            'public_ips': [],
            'primary_private_ip': None,
            'primary_public_ip': None,
            'error': str(e)
        }

def get_instance_details_with_ips(instance_id: str) -> Dict[str, Any]:
    """Get detailed instance information including IP addresses - optimized for ShowOCI"""
    with tool_span(tracer, "get_instance_details_with_ips", mcp_server="oci-mcp-compute") as span:
        try:
            config = get_oci_config()
            compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))

            # Get instance details
            instance_response = compute_client.get_instance(instance_id)
            instance = instance_response.data

            # Build basic instance info
            instance_info = {
                'id': instance.id,
                'display_name': instance.display_name,
                'lifecycle_state': instance.lifecycle_state,
                'shape': instance.shape,
                'availability_domain': getattr(instance, 'availability_domain', ''),
                'compartment_id': getattr(instance, 'compartment_id', ''),
                'time_created': getattr(instance, 'time_created', '').isoformat() if hasattr(instance, 'time_created') and instance.time_created else '',
                'region': config.get('region', ''),
                'shape_config': getattr(instance, 'shape_config', None)
            }

            # Add IP address information
            ip_info = _get_instance_ips(instance_id)
            instance_info.update({
                'private_ip': ip_info.get('primary_private_ip'),
                'public_ip': ip_info.get('primary_public_ip'),
                'all_private_ips': ip_info.get('private_ips', []),
                'all_public_ips': ip_info.get('public_ips', [])
            })

            # Add metadata if available
            if hasattr(instance, 'metadata') and instance.metadata:
                instance_info['metadata'] = instance.metadata

            # Safe serialize the result
            return _safe_serialize(instance_info)

        except oci.exceptions.ServiceError as e:
            logging.error(f"Error getting instance details: {e}")
            span.record_exception(e)
            return {'error': str(e), 'instance_id': instance_id}
        except Exception as e:
            logging.error(f"Unexpected error getting instance details: {e}")
            span.record_exception(e)
            return {'error': str(e), 'instance_id': instance_id}

def get_instance_metrics(instance_id: str, window: str = "1h") -> Dict:
    with tool_span(tracer, "get_instance_metrics", mcp_server="oci-mcp-compute") as span:
        config = get_oci_config()
        compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))
        monitoring_client = get_client(oci.monitoring.MonitoringClient, region=config.get("region"))

        # First get instance details to include name and get compartment_id
        instance_details = None
        compartment_id = None
        try:
            response = compute_client.get_instance(instance_id)
            instance = response.data
            compartment_id = getattr(instance, 'compartment_id', None)
            instance_details = {
                'id': instance.id,
                'display_name': instance.display_name,
                'shape': instance.shape,
                'lifecycle_state': instance.lifecycle_state,
                'availability_domain': getattr(instance, 'availability_domain', ''),
                'compartment_id': compartment_id,
                'time_created': getattr(instance, 'time_created', '').isoformat() if hasattr(instance, 'time_created') and instance.time_created else ''
            }
        except oci.exceptions.ServiceError as e:
            logging.warning(f"Could not fetch instance details: {e}")
            # Fallback to environment variable if instance details can't be fetched
            compartment_id = get_compartment_id()

        # Ensure we have a compartment_id for the monitoring query
        if not compartment_id:
            return {
                'error': 'Could not determine compartment ID. Set COMPARTMENT_OCID environment variable or ensure instance exists.',
                'instance_id': instance_id,
                'time_window': window
            }

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1) if window == "1h" else end_time - timedelta(days=1)

        query = f'CpuUtilization[1m]{{resourceId="{instance_id}"}}.mean()'
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
        try:
            response = monitoring_client.summarize_metrics_data(
                compartment_id=compartment_id,
                summarize_metrics_data_details=oci.monitoring.models.SummarizeMetricsDataDetails(
                    namespace="oci_computeagent",
                    query=query,
                    start_time=start_time,
                    end_time=end_time
                )
            )
            try:
                req_id = getattr(response, "headers", {}).get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass

            if response.data:
                metrics = response.data[0].aggregated_datapoints
                cpu_metrics = {
                    'average': sum(dp.value for dp in metrics) / len(metrics) if metrics else 0,
                    'max': max(dp.value for dp in metrics) if metrics else 0,
                    'min': min(dp.value for dp in metrics) if metrics else 0,
                    'datapoints_count': len(metrics)
                }

                result = {'cpu_metrics': cpu_metrics, 'time_window': window}
                if instance_details:
                    result['instance'] = instance_details
                else:
                    result['instance_id'] = instance_id
                    result['instance_details_error'] = 'Could not fetch instance details'

                return result
            else:
                result = {'error': 'No metrics found', 'time_window': window}
                if instance_details:
                    result['instance'] = instance_details
                else:
                    result['instance_id'] = instance_id
                return result

        except oci.exceptions.ServiceError as e:
            logging.error(f"Error getting metrics: {e}")
            span.record_exception(e)
            result = {'error': str(e), 'time_window': window}
            if instance_details:
                result['instance'] = instance_details
            else:
                result['instance_id'] = instance_id
            return result

def healthcheck() -> dict:
    return {"status": "ok", "server": "oci-mcp-compute", "pid": os.getpid()}

tools = [
    Tool.from_function(
        fn=healthcheck,
        name="healthcheck",
        description="Lightweight readiness/liveness check for the compute server"
    ),
    Tool.from_function(
        fn=list_instances,
        name="list_instances",
        description="List compute instances"
    ),
    Tool.from_function(
        fn=create_instance,
        name="create_instance",
        description="Create a new compute instance"
    ),
    Tool.from_function(
        fn=start_instance,
        name="start_instance",
        description="Start a compute instance"
    ),
    Tool.from_function(
        fn=stop_instance,
        name="stop_instance",
        description="Stop a compute instance"
    ),
    Tool.from_function(
        fn=restart_instance,
        name="restart_instance",
        description="Restart a compute instance (soft by default, or hard reset if specified)"
    ),
    Tool.from_function(
        fn=get_instance_metrics,
        name="get_instance_metrics",
        description="Get CPU metrics summary and instance details for an instance"
    ),
    Tool.from_function(
        fn=get_instance_details_with_ips,
        name="get_instance_details_with_ips",
        description="Get detailed instance information including all IP addresses (primary and secondary, public and private) - optimized for ShowOCI"
    ),
]

# FastAPI instrumentation is imported lazily in __main__ to avoid hard dependency at import time

if __name__ == "__main__":
    # Lazy imports: avoid failing when optional deps are missing during module import
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
            _start_http_server(int(os.getenv("METRICS_PORT", "8001")))
        except Exception:
            pass

    # Validate MCP tool names at startup
    if not validate_and_log_tools(tools, "oci-mcp-compute"):
        logging.error("MCP tool validation failed. Server will not start.")
        exit(1)

    mcp = FastMCP(tools=tools, name="oci-mcp-compute")
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
                application_name=os.getenv("PYROSCOPE_APP_NAME", "oci-mcp-compute"),
                server_address=os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040"),
                sample_rate=int(os.getenv("PYROSCOPE_SAMPLE_RATE", "100")),
                detect_subprocesses=True,
                enable_logging=True,
            )
    except Exception:
        # Never break server if profiler not available
        pass

    mcp.run()
