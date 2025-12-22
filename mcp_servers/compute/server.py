import os
import logging
import oci
from typing import List, Dict, Optional, Any
from fastmcp import FastMCP
from fastmcp.tools import Tool
from datetime import datetime, timedelta
from mcp_oci_common.otel import trace
from oci.pagination import list_call_get_all_results
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span, add_oci_call_attributes
from mcp_oci_common.session import get_client
from mcp_oci_common.oci_apm import init_oci_apm_tracing

from mcp_oci_common import get_oci_config, get_compartment_id, allow_mutations, validate_and_log_tools
from mcp_oci_common.cache import get_cache

# Load repo-local .env.local so OCI/OTEL config is applied consistently.
try:
    from pathlib import Path
    from dotenv import load_dotenv

    _repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(_repo_root / ".env.local")
except Exception:
    pass

# Set up logging
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)

# Set up tracing with proper Resource so service.name is set (avoids unknown_service)
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-compute")
init_tracing(service_name="oci-mcp-compute")
init_metrics()
# Initialize OCI APM tracing (uses OCI_APM_ENDPOINT and OCI_APM_PRIVATE_DATA_KEY)
init_oci_apm_tracing(service_name="oci-mcp-compute")
tracer = trace.get_tracer("oci-mcp-compute")

def _fetch_instances(compartment_id: Optional[str] = None, region: Optional[str] = None, lifecycle_state: Optional[str] = None, include_volumes: bool = True, include_ips: bool = True):
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

    # Enhance instance data with IP addresses and volumes
    enhanced_instances = []
    for inst in instances:
        instance_compartment = getattr(inst, 'compartment_id', compartment)
        instance_data = {
            'id': inst.id,
            'display_name': inst.display_name,
            'lifecycle_state': inst.lifecycle_state,
            'shape': inst.shape,
            'availability_domain': getattr(inst, 'availability_domain', ''),
            'compartment_id': instance_compartment,
            'time_created': getattr(inst, 'time_created', '').isoformat() if hasattr(inst, 'time_created') and inst.time_created else '',
            'region': config.get('region', '')
        }

        # Add shape configuration if available
        if hasattr(inst, 'shape_config'):
            shape_config = inst.shape_config
            instance_data['shape_config'] = {
                'ocpus': getattr(shape_config, 'ocpus', None),
                'memory_in_gbs': getattr(shape_config, 'memory_in_gbs', None),
                'baseline_ocpu_utilization': getattr(shape_config, 'baseline_ocpu_utilization', None)
            }

        # Add IP addresses if requested and instance is running
        if include_ips:
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
        else:
            instance_data.update({
                'private_ip': None,
                'public_ip': None,
                'all_private_ips': [],
                'all_public_ips': []
            })

        # Add volume information (boot volumes and block volumes) if requested
        if include_volumes:
            volumes_info = _get_instance_volumes(inst.id, instance_compartment, getattr(inst, 'availability_domain', ''))
            instance_data['boot_volumes'] = volumes_info.get('boot_volumes', [])
            instance_data['block_volumes'] = volumes_info.get('block_volumes', [])
            
            # Calculate total volume size for quick reference
            total_boot_size = sum(bv.get('size_in_gbs', 0) for bv in volumes_info.get('boot_volumes', []))
            total_block_size = sum(bv.get('size_in_gbs', 0) for bv in volumes_info.get('block_volumes', []))
            instance_data['total_volume_size_gb'] = total_boot_size + total_block_size
        else:
            instance_data['boot_volumes'] = []
            instance_data['block_volumes'] = []
            instance_data['total_volume_size_gb'] = 0

        enhanced_instances.append(instance_data)

    return enhanced_instances

def list_instances(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None,
    lifecycle_state: Optional[str] = None,
    include_volumes: bool = True,
    include_ips: bool = True,
    force_refresh: bool = False
) -> List[Dict]:
    with tool_span(tracer, "list_instances", mcp_server="oci-mcp-compute") as span:
        cache = get_cache()

        # Create params dict for caching
        params = {
            'compartment_id': compartment_id,
            'region': region,
            'lifecycle_state': lifecycle_state,
            'include_volumes': include_volumes,
            'include_ips': include_ips
        }

        try:
            # Get cached data or refresh
            instances = cache.get_or_refresh(
                server_name="oci-mcp-compute",
                operation="list_instances",
                params=params,
                fetch_func=lambda: _fetch_instances(compartment_id, region, lifecycle_state, include_volumes, include_ips),
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

def _get_instance_volumes(instance_id: str, compartment_id: str, availability_domain: str) -> Dict[str, Any]:
    """Get boot volumes and block volumes attached to an instance"""
    try:
        config = get_oci_config()
        compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))
        blockstorage_client = get_client(oci.core.BlockstorageClient, region=config.get("region"))

        volumes_info = {
            'boot_volumes': [],
            'block_volumes': []
        }

        # Get boot volume attachments
        try:
            boot_volume_attachments = list_call_get_all_results(
                compute_client.list_boot_volume_attachments,
                availability_domain,
                compartment_id,
                instance_id=instance_id
            ).data

            for attachment in boot_volume_attachments:
                if attachment.lifecycle_state == 'ATTACHED':
                    try:
                        boot_volume = blockstorage_client.get_boot_volume(attachment.boot_volume_id).data
                        volumes_info['boot_volumes'].append({
                            'id': boot_volume.id,
                            'display_name': boot_volume.display_name,
                            'size_in_gbs': boot_volume.size_in_gbs,
                            'vpus_per_gb': getattr(boot_volume, 'vpus_per_gb', None),
                            'lifecycle_state': boot_volume.lifecycle_state,
                            'attachment_id': attachment.id,
                            'attachment_type': attachment.attachment_type
                        })
                    except Exception as e:
                        logging.warning(f"Error getting boot volume {attachment.boot_volume_id}: {e}")
                        continue
        except Exception as e:
            logging.warning(f"Error listing boot volume attachments for {instance_id}: {e}")

        # Get block volume attachments
        try:
            volume_attachments = list_call_get_all_results(
                compute_client.list_volume_attachments,
                compartment_id=compartment_id,
                instance_id=instance_id
            ).data

            for attachment in volume_attachments:
                if attachment.lifecycle_state == 'ATTACHED':
                    try:
                        volume = blockstorage_client.get_volume(attachment.volume_id).data
                        volumes_info['block_volumes'].append({
                            'id': volume.id,
                            'display_name': volume.display_name,
                            'size_in_gbs': volume.size_in_gbs,
                            'vpus_per_gb': getattr(volume, 'vpus_per_gb', None),
                            'lifecycle_state': volume.lifecycle_state,
                            'attachment_id': attachment.id,
                            'attachment_type': attachment.attachment_type
                        })
                    except Exception as e:
                        logging.warning(f"Error getting block volume {attachment.volume_id}: {e}")
                        continue
        except Exception as e:
            logging.warning(f"Error listing volume attachments for {instance_id}: {e}")

        return volumes_info

    except Exception as e:
        logging.error(f"Error getting instance volumes for {instance_id}: {e}")
        return {
            'boot_volumes': [],
            'block_volumes': [],
            'error': str(e)
        }

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

def get_instance_cost(
    instance_id: str,
    time_window: str = "30d",
    include_volumes: bool = True
) -> Dict:
    """Get cost breakdown for an instance including attached volumes"""
    with tool_span(tracer, "get_instance_cost", mcp_server="oci-mcp-compute") as span:
        try:
            config = get_oci_config()
            compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))
            usage_client = get_client(oci.usage_api.UsageapiClient, region=config.get("region"))

            # Get instance details
            instance_response = compute_client.get_instance(instance_id)
            instance = instance_response.data
            compartment_id = instance.compartment_id

            # Calculate time window
            end_time = datetime.utcnow()
            if time_window.endswith('d'):
                days = int(time_window[:-1])
                start_time = end_time - timedelta(days=days)
            elif time_window.endswith('h'):
                hours = int(time_window[:-1])
                start_time = end_time - timedelta(hours=hours)
            else:
                start_time = end_time - timedelta(days=30)

            # Query usage API for compute costs
            details = oci.usage_api.models.RequestSummarizedUsagesDetails(
                tenant_id=config.get("tenancy"),
                time_usage_started=start_time.replace(hour=0, minute=0, second=0, microsecond=0),
                time_usage_ended=end_time.replace(hour=0, minute=0, second=0, microsecond=0),
                granularity="DAILY",
                query_type="COST",
                group_by=["service", "resourceId"],
                compartment_depth=10
            )

            # Filter by compartment and resource ID
            details.filter = oci.usage_api.models.Filter(
                operator="AND",
                dimensions=[
                    oci.usage_api.models.Dimension(
                        key="compartmentId",
                        value=compartment_id
                    ),
                    oci.usage_api.models.Dimension(
                        key="resourceId",
                        value=instance_id
                    )
                ]
            )

            try:
                endpoint = getattr(usage_client.base_client, "endpoint", "")
            except Exception:
                endpoint = ""
            add_oci_call_attributes(
                span,
                oci_service="UsageAPI",
                oci_operation="RequestSummarizedUsages",
                region=config.get("region"),
                endpoint=endpoint,
            )

            response = usage_client.request_summarized_usages(
                request_summarized_usages_details=details
            )
            try:
                req_id = getattr(response, "headers", {}).get("opc-request-id")
                if req_id:
                    span.set_attribute("oci.request_id", req_id)
            except Exception:
                pass

            items = getattr(getattr(response, "data", None), "items", None) or []

            # Calculate costs by service
            compute_cost = 0.0
            block_storage_cost = 0.0
            currency = "USD"

            for item in items:
                service = getattr(item, 'service', '')
                amount = getattr(item, 'computed_amount', 0) or 0
                if hasattr(item, 'currency') and getattr(item, 'currency'):
                    currency = str(getattr(item, 'currency')).strip()

                if service == 'Compute':
                    compute_cost += float(amount)
                elif service == 'Block Volume':
                    block_storage_cost += float(amount)

            # If volumes are included, also query for volume costs
            volume_costs = {}
            if include_volumes:
                volumes_info = _get_instance_volumes(instance_id, compartment_id, getattr(instance, 'availability_domain', ''))
                
                # Query costs for boot volumes
                for bv in volumes_info.get('boot_volumes', []):
                    bv_details = oci.usage_api.models.RequestSummarizedUsagesDetails(
                        tenant_id=config.get("tenancy"),
                        time_usage_started=start_time.replace(hour=0, minute=0, second=0, microsecond=0),
                        time_usage_ended=end_time.replace(hour=0, minute=0, second=0, microsecond=0),
                        granularity="DAILY",
                        query_type="COST",
                        group_by=["service", "resourceId"],
                        compartment_depth=10
                    )
                    bv_details.filter = oci.usage_api.models.Filter(
                        operator="AND",
                        dimensions=[
                            oci.usage_api.models.Dimension(
                                key="compartmentId",
                                value=compartment_id
                            ),
                            oci.usage_api.models.Dimension(
                                key="resourceId",
                                value=bv['id']
                            )
                        ]
                    )
                    try:
                        bv_response = usage_client.request_summarized_usages(
                            request_summarized_usages_details=bv_details
                        )
                        bv_items = getattr(getattr(bv_response, "data", None), "items", None) or []
                        bv_cost = sum(float(getattr(item, 'computed_amount', 0) or 0) for item in bv_items)
                        if bv_cost > 0:
                            volume_costs[bv['id']] = {
                                'name': bv['display_name'],
                                'cost': bv_cost,
                                'type': 'boot_volume'
                            }
                            block_storage_cost += bv_cost
                    except Exception as e:
                        logging.warning(f"Error getting boot volume cost for {bv['id']}: {e}")

                # Query costs for block volumes
                for bv in volumes_info.get('block_volumes', []):
                    bv_details = oci.usage_api.models.RequestSummarizedUsagesDetails(
                        tenant_id=config.get("tenancy"),
                        time_usage_started=start_time.replace(hour=0, minute=0, second=0, microsecond=0),
                        time_usage_ended=end_time.replace(hour=0, minute=0, second=0, microsecond=0),
                        granularity="DAILY",
                        query_type="COST",
                        group_by=["service", "resourceId"],
                        compartment_depth=10
                    )
                    bv_details.filter = oci.usage_api.models.Filter(
                        operator="AND",
                        dimensions=[
                            oci.usage_api.models.Dimension(
                                key="compartmentId",
                                value=compartment_id
                            ),
                            oci.usage_api.models.Dimension(
                                key="resourceId",
                                value=bv['id']
                            )
                        ]
                    )
                    try:
                        bv_response = usage_client.request_summarized_usages(
                            request_summarized_usages_details=bv_details
                        )
                        bv_items = getattr(getattr(bv_response, "data", None), "items", None) or []
                        bv_cost = sum(float(getattr(item, 'computed_amount', 0) or 0) for item in bv_items)
                        if bv_cost > 0:
                            volume_costs[bv['id']] = {
                                'name': bv['display_name'],
                                'cost': bv_cost,
                                'type': 'block_volume'
                            }
                            block_storage_cost += bv_cost
                    except Exception as e:
                        logging.warning(f"Error getting block volume cost for {bv['id']}: {e}")

            total_cost = compute_cost + block_storage_cost

            result = {
                'instance_id': instance_id,
                'instance_name': instance.display_name,
                'time_period': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'window': time_window
                },
                'costs': {
                    'compute': compute_cost,
                    'block_storage': block_storage_cost,
                    'total': total_cost,
                    'currency': currency
                },
                'volume_costs': volume_costs if include_volumes else {}
            }

            span.set_attribute("instance.cost.total", total_cost)
            span.set_attribute("instance.cost.compute", compute_cost)
            span.set_attribute("instance.cost.storage", block_storage_cost)

            return result

        except oci.exceptions.ServiceError as e:
            logging.error(f"Error getting instance cost: {e}")
            span.record_exception(e)
            return {'error': str(e), 'instance_id': instance_id}
        except Exception as e:
            logging.error(f"Unexpected error getting instance cost: {e}")
            span.record_exception(e)
            return {'error': str(e), 'instance_id': instance_id}

def get_comprehensive_instance_details(
    instance_id: str,
    include_volumes: bool = True,
    include_ips: bool = True,
    include_costs: bool = False,
    cost_time_window: str = "30d"
) -> Dict[str, Any]:
    """Get comprehensive instance details including configuration, IPs, volumes, and optionally costs"""
    with tool_span(tracer, "get_comprehensive_instance_details", mcp_server="oci-mcp-compute") as span:
        try:
            config = get_oci_config()
            compute_client = get_client(oci.core.ComputeClient, region=config.get("region"))

            # Get instance details
            instance_response = compute_client.get_instance(instance_id)
            instance = instance_response.data
            compartment_id = instance.compartment_id

            # Build comprehensive instance info
            instance_info = {
                'id': instance.id,
                'display_name': instance.display_name,
                'lifecycle_state': instance.lifecycle_state,
                'shape': instance.shape,
                'availability_domain': getattr(instance, 'availability_domain', ''),
                'compartment_id': compartment_id,
                'region': config.get('region', ''),
                'time_created': getattr(instance, 'time_created', '').isoformat() if hasattr(instance, 'time_created') and instance.time_created else '',
            }

            # Add shape configuration
            if hasattr(instance, 'shape_config'):
                shape_config = instance.shape_config
                instance_info['shape_config'] = {
                    'ocpus': getattr(shape_config, 'ocpus', None),
                    'memory_in_gbs': getattr(shape_config, 'memory_in_gbs', None),
                    'baseline_ocpu_utilization': getattr(shape_config, 'baseline_ocpu_utilization', None),
                    'nvmes': getattr(shape_config, 'nvmes', None)
                }

            # Add IP addresses if requested
            if include_ips:
                ip_info = _get_instance_ips(instance_id)
                instance_info.update({
                    'private_ip': ip_info.get('primary_private_ip'),
                    'public_ip': ip_info.get('primary_public_ip'),
                    'all_private_ips': ip_info.get('private_ips', []),
                    'all_public_ips': ip_info.get('public_ips', [])
                })

            # Add volume information if requested
            if include_volumes:
                volumes_info = _get_instance_volumes(instance_id, compartment_id, getattr(instance, 'availability_domain', ''))
                instance_info['boot_volumes'] = volumes_info.get('boot_volumes', [])
                instance_info['block_volumes'] = volumes_info.get('block_volumes', [])
                
                # Calculate total volume size
                total_boot_size = sum(bv.get('size_in_gbs', 0) for bv in volumes_info.get('boot_volumes', []))
                total_block_size = sum(bv.get('size_in_gbs', 0) for bv in volumes_info.get('block_volumes', []))
                instance_info['total_volume_size_gb'] = total_boot_size + total_block_size

            # Add cost information if requested
            if include_costs:
                cost_info = get_instance_cost(instance_id, time_window=cost_time_window, include_volumes=include_volumes)
                if 'error' not in cost_info:
                    instance_info['costs'] = cost_info.get('costs', {})
                    instance_info['volume_costs'] = cost_info.get('volume_costs', {})

            # Add metadata if available
            if hasattr(instance, 'metadata') and instance.metadata:
                instance_info['metadata'] = instance.metadata

            # Add additional instance attributes
            instance_info['image_id'] = getattr(instance, 'image_id', None)
            instance_info['launch_mode'] = getattr(instance, 'launch_mode', None)
            instance_info['launch_options'] = _safe_serialize(getattr(instance, 'launch_options', None))

            span.set_attribute("instance.id", instance_id)
            span.set_attribute("instance.state", instance.lifecycle_state)

            return _safe_serialize(instance_info)

        except oci.exceptions.ServiceError as e:
            logging.error(f"Error getting comprehensive instance details: {e}")
            span.record_exception(e)
            return {'error': str(e), 'instance_id': instance_id}
        except Exception as e:
            logging.error(f"Unexpected error getting comprehensive instance details: {e}")
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

def doctor() -> dict:
    try:
        from mcp_oci_common.privacy import privacy_enabled
        cfg = get_oci_config()
        return {
            "server": "oci-mcp-compute",
            "ok": True,
            "privacy": bool(privacy_enabled()),
            "region": cfg.get("region"),
            "profile": os.getenv("OCI_PROFILE") or "DEFAULT",
            "tools": [t.name for t in tools],
        }
    except Exception as e:
        return {"server": "oci-mcp-compute", "ok": False, "error": str(e)}

# =============================================================================
# Server Manifest Resource
# =============================================================================

def server_manifest() -> str:
    """Server manifest resource for capability discovery."""
    import json
    manifest = {
        "name": "OCI MCP Compute Server",
        "version": "1.0.0",
        "description": "OCI Compute MCP Server for instance management and monitoring",
        "capabilities": {
            "skills": ["compute-management", "instance-lifecycle", "performance-monitoring"],
            "tools": {
                "tier1_instant": ["healthcheck", "doctor"],
                "tier2_api": [
                    "list_instances", "get_instance_metrics", "get_instance_details_with_ips",
                    "get_instance_cost", "get_comprehensive_instance_details", "list_shapes"
                ],
                "tier3_heavy": [],
                "tier4_admin": [
                    "create_instance", "start_instance", "stop_instance", "restart_instance"
                ]
            }
        },
        "usage_guide": "Use list_instances for discovery, get_comprehensive_instance_details for full info, admin tools require ALLOW_MUTATIONS=true.",
        "environment_variables": ["OCI_PROFILE", "OCI_REGION", "COMPARTMENT_OCID", "ALLOW_MUTATIONS", "MCP_OCI_PRIVACY"]
    }
    return json.dumps(manifest, indent=2)

tools = [
    Tool.from_function(
        fn=healthcheck,
        name="healthcheck",
        description="Lightweight readiness/liveness check for the compute server"
    ),
    Tool.from_function(
        fn=doctor,
        name="doctor",
        description="Return server health, config summary, and masking status"
    ),
    Tool.from_function(
        fn=list_instances,
        name="list_instances",
        description="List compute instances with their configuration, IP addresses, and attached volumes (boot volumes and block volumes). Returns instance name, IPs, shape, and volume information."
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
    Tool.from_function(
        fn=get_instance_cost,
        name="get_instance_cost",
        description="Get cost breakdown for an instance including attached boot volumes and block volumes. Returns compute costs and storage costs separately."
    ),
    Tool.from_function(
        fn=get_comprehensive_instance_details,
        name="get_comprehensive_instance_details",
        description="Get comprehensive instance details including configuration, IPs, volumes, and optionally costs. This is the recommended tool for getting all instance information in one call."
    ),
]

def get_tools():
    return [{"name": t.name, "description": t.description} for t in tools]

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
    if not validate_and_log_tools(tools, "oci-mcp-compute"):
        logging.error("MCP tool validation failed. Server will not start.")
        exit(1)

    mcp = FastMCP(tools=tools, name="oci-mcp-compute")

    # Register the server manifest resource
    @mcp.resource("server://manifest")
    def get_manifest() -> str:
        return server_manifest()

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
