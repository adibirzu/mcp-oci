import os
import sys
import logging
import subprocess
import json
import hashlib
import difflib
from typing import Dict, Optional, List
from fastmcp import FastMCP
from fastmcp.tools import Tool
from opentelemetry import trace
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span, add_oci_call_attributes
from mcp_oci_common.cache import get_cache
from mcp_oci_common.config import get_oci_config

# Set up logging
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)

# Set up tracing
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-inventory")
init_tracing(service_name="oci-mcp-inventory")
init_metrics()
tracer = trace.get_tracer("oci-mcp-inventory")

CACHE_DIR = "/tmp/mcp-oci-cache/inventory"
os.makedirs(CACHE_DIR, exist_ok=True)

# Shared cache instance (disk + memory)
cache = get_cache()

def healthcheck() -> Dict:
    """
    Lightweight readiness/liveness probe.
    Returns static metadata without touching OCI or network.
    """
    return {"status": "ok", "server": "oci-mcp-inventory", "pid": os.getpid()}

def run_showoci(
    profile: Optional[str] = None,
    regions: Optional[List[str]] = None,
    compartments: Optional[List[str]] = None,
    resource_types: Optional[List[str]] = None,
    output_format: str = "text",
    diff_mode: bool = True,
    limit: Optional[int] = None,
    force_refresh: bool = False
) -> Dict:
    with tool_span(tracer, "run_showoci", mcp_server="oci-mcp-inventory") as span:
        # Build command and defaults from env
        from mcp_oci_common.observability import record_token_usage
        cfg_profile = profile or os.getenv("OCI_PROFILE")
        cfg_regions = regions or ([os.getenv("OCI_REGION")] if os.getenv("OCI_REGION") else None)
        cfg_compartments = compartments or ([os.getenv("COMPARTMENT_OCID")] if os.getenv("COMPARTMENT_OCID") else None)
        # Resolve showoci script path robustly relative to repo root
        here = os.path.abspath(__file__)
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(here)))
        showoci_py = os.path.join(repo_root, "third_party", "oci-python-sdk", "examples", "showoci", "showoci.py")
        if not os.path.exists(showoci_py):
            showoci_py = os.path.join(os.getcwd(), "third_party", "oci-python-sdk", "examples", "showoci", "showoci.py")
        cmd_base = [sys.executable or "python", showoci_py]
        config_path = os.path.expanduser("~/.oci/config")
        # Enrich span attributes for observability
        try:
            add_oci_call_attributes(span, oci_service="ShowOCI", oci_operation="RunReport", region=(cfg_regions[0] if cfg_regions else None), endpoint=None)
        except Exception:
            pass

        # Params used for caching key
        cache_params = {
            "profile": cfg_profile,
            "regions": cfg_regions,
            "compartments": cfg_compartments,
            "resource_types": resource_types,
            "output_format": output_format,
        }

        # Local disk files for human-readable diff preservation
        param_str = json.dumps(cache_params, sort_keys=True)
        cache_hash = hashlib.sha256(param_str.encode()).hexdigest()
        cache_file = os.path.join(CACHE_DIR, f"{cache_hash}.txt")
        prev_cache_file = os.path.join(CACHE_DIR, f"{cache_hash}.prev.txt")

        def fetch_func():
            # Build command dynamically at fetch time
            py = sys.executable or os.getenv("PY") or "python"
            cmd = [py] + cmd_base[1:]
            if cfg_profile:
                cmd.extend(["--config-file", config_path, "--profile", cfg_profile])
            if cfg_regions:
                cmd.extend(["--region", ",".join(cfg_regions)])
            if cfg_compartments:
                cmd.extend(["--compartment-id", ",".join(cfg_compartments)])
            if resource_types:
                cmd.extend(["--query", ",".join(resource_types)])  # Assuming showoci supports this
            if output_format == "csv":
                cmd.append("--generate-full-report")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "showoci failed")

            full_output = result.stdout

            # Maintain simple on-disk previous/current files to compute diffs
            try:
                if os.path.exists(cache_file):
                    # rotate current -> prev
                    try:
                        if os.path.exists(prev_cache_file):
                            os.remove(prev_cache_file)
                    except Exception:
                        pass
                    os.rename(cache_file, prev_cache_file)
                with open(cache_file, "w") as f:
                    f.write(full_output)
            except Exception as _e:
                # Do not fail the call if we cannot persist files
                logging.debug(f"Failed writing cache files for diff: {_e}")

            diff_text = None
            changes_detected = None
            if diff_mode and os.path.exists(prev_cache_file):
                try:
                    with open(prev_cache_file, "r") as f:
                        prev_output = f.read()
                    diff = list(difflib.unified_diff(
                        prev_output.splitlines(keepends=True),
                        full_output.splitlines(keepends=True),
                        fromfile="previous",
                        tofile="current"
                    ))
                    diff_text = "".join(diff)
                    changes_detected = bool(diff)
                except Exception as _e:
                    logging.debug(f"Failed computing diff: {_e}")

            payload = {"output": full_output}
            if diff_mode:
                payload["diff"] = diff_text
                payload["changes_detected"] = changes_detected
            return payload

        try:
            data = cache.get_or_refresh(
                server_name="inventory",
                operation="run_showoci",
                params=cache_params,
                fetch_func=fetch_func,
                force_refresh=force_refresh,
                ttl_seconds=900
            )
            if data is None:
                return {"error": "No data available for ShowOCI (cache refresh failed)"}

            # Truncate output for response only (keep full output in cache)
            resp_output = data.get("output", "")
            if limit:
                resp_output = "\n".join(resp_output.splitlines()[:limit])

            if diff_mode:
                diff_text = data.get("diff")
                changes_detected = data.get("changes_detected")
                # Token accounting
                try:
                    token_len = len(diff_text or resp_output)
                    record_token_usage(int(token_len / 4), attrs={"source": "showoci", "diff": diff_text is not None})
                except Exception:
                    pass
                if diff_text is not None:
                    return {"diff": diff_text, "changes_detected": bool(changes_detected)}
                else:
                    return {"output": resp_output}
            else:
                try:
                    record_token_usage(int(len(resp_output) / 4), attrs={"source": "showoci", "diff": False})
                except Exception:
                    pass
                return {"output": resp_output}

        except Exception as e:
            logging.error(f"Error running showoci: {e}", exc_info=False)
            span.record_exception(e)
            return {"error": str(e)}

def run_showoci_simple(
    profile: Optional[str] = None,
    regions: Optional[str] = None,
    compartments: Optional[str] = None,
    resource_types: Optional[str] = None,
    output_format: str = "text",
    diff_mode: bool = True,
    limit: Optional[int] = None,
    force_refresh: bool = False
) -> Dict:
    """
    Convenience wrapper that accepts comma-separated strings to minimize schema friction.
    """
    reg_list = [r.strip() for r in regions.split(",")] if regions else None
    comp_list = [c.strip() for c in compartments.split(",")] if compartments else None
    res_list = [t.strip() for t in resource_types.split(",")] if resource_types else None
    return run_showoci(
        profile=profile,
        regions=reg_list,
        compartments=comp_list,
        resource_types=res_list,
        output_format=output_format,
        diff_mode=diff_mode,
        limit=limit,
        force_refresh=force_refresh,
    )

def generate_compute_capacity_report(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None,
    profile: Optional[str] = None,
    include_metrics: bool = True,
    output_format: str = "json"
) -> Dict:
    """
    Generate a comprehensive compute capacity report showing utilization, costs, and recommendations.
    Based on patterns from OCI_ComputeCapacityReport repository.
    """
    with tool_span(tracer, "generate_compute_capacity_report", mcp_server="oci-mcp-inventory") as span:
        try:
            from mcp_oci_common import get_oci_config
            import oci
            from datetime import datetime, timedelta

            config = get_oci_config()
            if profile:
                # This is a simplified approach - in production you'd handle multiple profiles
                config['profile'] = profile
            if region:
                config['region'] = region

            # Initialize OCI clients
            compute_client = oci.core.ComputeClient(config)
            monitoring_client = oci.monitoring.MonitoringClient(config)
            tenancy_client = oci.identity.IdentityClient(config)
            network_client = oci.core.VirtualNetworkClient(config)

            # Get compartment details (fall back to tenancy OCID)
            target_compartment = compartment_id or os.getenv('COMPARTMENT_OCID') or config.get('tenancy')

            # Fetch compute instances
            instances = []
            try:
                response = compute_client.list_instances(compartment_id=target_compartment)
                instances = response.data
                span.set_attribute("instances.found", len(instances))
            except Exception as e:
                span.record_exception(e)
                return {"error": f"Failed to fetch compute instances: {str(e)}"}

            # Generate capacity report
            capacity_report = {
                "timestamp": datetime.utcnow().isoformat(),
                "compartment_id": target_compartment,
                "region": config.get('region'),
                "total_instances": len(instances),
                "instances_by_shape": {},
                "instances_by_state": {},
                "instances_by_ad": {},
                "capacity_analysis": {},
                "recommendations": []
            }

            # Analyze instances
            for instance in instances:
                shape = instance.shape
                state = instance.lifecycle_state
                ad = getattr(instance, 'availability_domain', 'N/A')

                # Count by shape
                if shape not in capacity_report["instances_by_shape"]:
                    capacity_report["instances_by_shape"][shape] = 0
                capacity_report["instances_by_shape"][shape] += 1

                # Count by state
                if state not in capacity_report["instances_by_state"]:
                    capacity_report["instances_by_state"][state] = 0
                capacity_report["instances_by_state"][state] += 1

                # Count by availability domain
                if ad not in capacity_report["instances_by_ad"]:
                    capacity_report["instances_by_ad"][ad] = 0
                capacity_report["instances_by_ad"][ad] += 1

            # Generate recommendations based on analysis
            running_instances = capacity_report["instances_by_state"].get("RUNNING", 0)
            stopped_instances = capacity_report["instances_by_state"].get("STOPPED", 0)

            if stopped_instances > running_instances * 0.3:
                capacity_report["recommendations"].append({
                    "type": "cost_optimization",
                    "priority": "high",
                    "message": f"Consider terminating {stopped_instances} stopped instances to reduce costs",
                    "potential_savings": f"~${stopped_instances * 50}/month (estimated)"
                })

            # Check for shape diversity
            if len(capacity_report["instances_by_shape"]) > 5:
                capacity_report["recommendations"].append({
                    "type": "simplification",
                    "priority": "medium",
                    "message": "Consider consolidating instance shapes for better management",
                    "details": f"Currently using {len(capacity_report['instances_by_shape'])} different shapes"
                })

            # Single availability domain risk
            if len(capacity_report["instances_by_ad"]) == 1 and running_instances > 2:
                capacity_report["recommendations"].append({
                    "type": "high_availability",
                    "priority": "high",
                    "message": "Consider distributing instances across multiple availability domains",
                    "details": "All instances are in a single AD, increasing failure risk"
                })

            capacity_report["capacity_analysis"] = {
                "utilization_score": "medium",  # Would be calculated from actual metrics
                "cost_efficiency": "good" if stopped_instances < running_instances * 0.2 else "needs_attention",
                "high_availability_score": "good" if len(capacity_report["instances_by_ad"]) > 1 else "needs_attention"
            }

            # Fetch all VNIC attachments in the compartment
            vnic_attachments = []
            try:
                vnic_attachments = compute_client.list_vnic_attachments(compartment_id=target_compartment).data
            except Exception as e:
                logging.warning(f"Failed to fetch VNIC attachments: {str(e)}")

            # Create a map of instance_id to list of IPs
            instance_ips = {}
            for attachment in vnic_attachments:
                if attachment.lifecycle_state != "ATTACHED":
                    continue
                try:
                    vnic = network_client.get_vnic(attachment.vnic_id).data
                    ips = {
                        "private_ip": vnic.private_ip,
                        "public_ip": vnic.public_ip if hasattr(vnic, 'public_ip') and vnic.public_ip else None,  # Public IP may be None for private subnets or stopped instances
                        "hostname_label": vnic.hostname_label,
                        "subnet_id": vnic.subnet_id
                    }
                    inst_id = attachment.instance_id
                    if inst_id not in instance_ips:
                        instance_ips[inst_id] = []
                    instance_ips[inst_id].append(ips)
                except Exception as e:
                    logging.warning(f"Failed to get VNIC {attachment.vnic_id}: {str(e)}")

            # Add to instance details
            capacity_report["instance_details"] = []
            for instance in instances[:50]:  # Limit to first 50 for performance
                inst_id = instance.id
                ips = instance_ips.get(inst_id, [])
                if instance.lifecycle_state == "STOPPED" and ips:
                    for ip in ips:
                        if ip["public_ip"] is None:
                            ip["note"] = "Public IP released due to instance stop"
                instance_detail = {
                    "id": inst_id,
                    "display_name": instance.display_name,
                    "shape": instance.shape,
                    "lifecycle_state": instance.lifecycle_state,
                    "availability_domain": getattr(instance, 'availability_domain', 'N/A'),
                    "time_created": getattr(instance, 'time_created', '').isoformat() if hasattr(instance, 'time_created') and instance.time_created else None,
                    "ips": ips  # List of dicts with private_ip, public_ip, hostname_label, subnet_id
                }
                capacity_report["instance_details"].append(instance_detail)

            if output_format == "summary":
                return {
                    "summary": {
                        "total_instances": capacity_report["total_instances"],
                        "running_instances": capacity_report["instances_by_state"].get("RUNNING", 0),
                        "stopped_instances": capacity_report["instances_by_state"].get("STOPPED", 0),
                        "shapes_used": len(capacity_report["instances_by_shape"]),
                        "recommendations_count": len(capacity_report["recommendations"])
                    }
                }

            return capacity_report

        except Exception as e:
            span.record_exception(e)
            return {"error": f"Failed to generate capacity report: {str(e)}"}

def list_streams_inventory(compartment_id: Optional[str] = None, limit: int = 50,
                           profile: Optional[str] = None, region: Optional[str] = None) -> Dict:
    """List Streaming streams (discovery helper). Wraps per-service tool with sane defaults."""
    with tool_span(tracer, "list_streams_inventory", mcp_server="oci-mcp-inventory") as span:
        try:
            # Resolve default compartment from config
            if not compartment_id:
                cfg = get_oci_config(profile_name=profile)
                if region:
                    cfg["region"] = region
                compartment_id = cfg.get("tenancy")
            from mcp_oci_streaming.server import list_streams as _lst
            import json as _json
            out = _lst(compartment_id=compartment_id, limit=limit, profile=profile, region=region)
            data = _json.loads(out) if isinstance(out, str) else out
            return {"items": data.get("items", []), "count": len(data.get("items", []))}
        except Exception as e:
            return {"error": str(e)}

def list_functions_applications_inventory(compartment_id: Optional[str] = None, limit: int = 50,
                                          profile: Optional[str] = None, region: Optional[str] = None) -> Dict:
    """List Functions applications (discovery helper). Wraps per-service tool with sane defaults."""
    with tool_span(tracer, "list_functions_applications_inventory", mcp_server="oci-mcp-inventory") as span:
        try:
            if not compartment_id:
                cfg = get_oci_config(profile_name=profile)
                if region:
                    cfg["region"] = region
                compartment_id = cfg.get("tenancy")
            from mcp_oci_functions.server import list_applications as _lapp
            import json as _json
            out = _lapp(compartment_id=compartment_id, limit=limit, profile=profile, region=region)
            data = _json.loads(out) if isinstance(out, str) else out
            return {"items": data.get("items", []), "count": len(data.get("items", []))}
        except Exception as e:
            return {"error": str(e)}

def list_security_lists_inventory(compartment_id: Optional[str] = None, vcn_id: Optional[str] = None, limit: int = 50,
                                  profile: Optional[str] = None, region: Optional[str] = None) -> Dict:
    """List Networking security lists (NSGs) in a compartment; optionally filter by VCN."""
    with tool_span(tracer, "list_security_lists_inventory", mcp_server="oci-mcp-inventory") as span:
        try:
            if not compartment_id:
                cfg = get_oci_config(profile_name=profile)
                if region:
                    cfg["region"] = region
                compartment_id = cfg.get("tenancy")
            from mcp_oci_networking.server import list_security_lists as _lsl
            import json as _json
            out = _lsl(compartment_id=compartment_id, vcn_id=vcn_id, limit=limit, profile=profile, region=region)
            data = _json.loads(out) if isinstance(out, str) else out
            return {"items": data.get("items", []), "count": len(data.get("items", []))}
        except Exception as e:
            return {"error": str(e)}

def list_load_balancers_inventory(compartment_id: Optional[str] = None, limit: int = 50,
                                  profile: Optional[str] = None, region: Optional[str] = None) -> Dict:
    """List Load Balancers in a compartment."""
    with tool_span(tracer, "list_load_balancers_inventory", mcp_server="oci-mcp-inventory") as span:
        try:
            if not compartment_id:
                cfg = get_oci_config(profile_name=profile)
                if region:
                    cfg["region"] = region
                compartment_id = cfg.get("tenancy")
            from mcp_oci_loadbalancer.server import list_load_balancers as _llb
            import json as _json
            out = _llb(compartment_id=compartment_id, limit=limit, profile=profile, region=region)
            data = _json.loads(out) if isinstance(out, str) else out
            return {"items": data.get("items", []), "count": len(data.get("items", []))}
        except Exception as e:
            return {"error": str(e)}

def list_all_discovery(compartment_id: Optional[str] = None, profile: Optional[str] = None, region: Optional[str] = None,
                       limit_per_type: int = 25) -> Dict:
    """Aggregate discovery for common resources: VCNs, subnets, NSGs, instances, LBs, Functions apps, Streams.
    Returns counts per type and small samples (up to limit_per_type).
    """
    with tool_span(tracer, "list_all_discovery", mcp_server="oci-mcp-inventory"):
        import json as _json
        if not compartment_id:
            cfg = get_oci_config(profile_name=profile)
            if region:
                cfg["region"] = region
            compartment_id = cfg.get("tenancy")
        result: Dict[str, Dict] = {}
        # Helper to load possibly-JSON-returning functions
        def _load(x):
            try:
                return _json.loads(x) if isinstance(x, str) else x
            except Exception:
                return x
        # Networking
        try:
            from mcp_oci_networking.server import list_vcns as _lv, list_subnets as _ls, list_security_lists as _lsl
            lv = _load(_lv(compartment_id=compartment_id, limit=limit_per_type, profile=profile, region=region))
            ls = _load(_ls(compartment_id=compartment_id, limit=limit_per_type, profile=profile, region=region))
            lsl = _load(_lsl(compartment_id=compartment_id, limit=limit_per_type, profile=profile, region=region))
            result["vcns"] = {"count": len(lv.get("items", [])), "items": lv.get("items", [])}
            result["subnets"] = {"count": len(ls.get("items", [])), "items": ls.get("items", [])}
            result["security_lists"] = {"count": len(lsl.get("items", [])), "items": lsl.get("items", [])}
        except Exception as e:
            result["networking_error"] = {"error": str(e)}
        # Compute
        try:
            from mcp_oci_compute.server import list_instances as _li
            li = _li(compartment_id=compartment_id, include_subtree=False, max_items=limit_per_type, profile=profile, region=region)
            result["instances"] = {"count": len(li.get("items", [])), "items": li.get("items", [])}
        except Exception as e:
            result["compute_error"] = {"error": str(e)}
        # Load balancers
        try:
            from mcp_oci_loadbalancer.server import list_load_balancers as _llb
            lb = _load(_llb(compartment_id=compartment_id, limit=limit_per_type, profile=profile, region=region))
            result["load_balancers"] = {"count": len(lb.get("items", [])), "items": lb.get("items", [])}
        except Exception as e:
            result["loadbalancer_error"] = {"error": str(e)}
        # Functions
        try:
            from mcp_oci_functions.server import list_applications as _lapp
            fa = _load(_lapp(compartment_id=compartment_id, limit=limit_per_type, profile=profile, region=region))
            result["functions_apps"] = {"count": len(fa.get("items", [])), "items": fa.get("items", [])}
        except Exception as e:
            result["functions_error"] = {"error": str(e)}
        # Streaming
        try:
            from mcp_oci_streaming.server import list_streams as _lst
            st = _load(_lst(compartment_id=compartment_id, limit=limit_per_type, profile=profile, region=region))
            result["streams"] = {"count": len(st.get("items", [])), "items": st.get("items", [])}
        except Exception as e:
            result["streaming_error"] = {"error": str(e)}
        return result

tools = [
    Tool.from_function(
        fn=healthcheck,
        name="healthcheck",
        description="Lightweight readiness/liveness check for the inventory server"
    ),
    Tool.from_function(
        fn=run_showoci,
        name="run_showoci",
        description="Run ShowOCI inventory report with optional diff for changes"
    ),
    Tool.from_function(
        fn=run_showoci_simple,
        name="run_showoci_simple",
        description="Run ShowOCI using comma-separated regions/compartments/resource_types"
    ),
    Tool.from_function(
        fn=generate_compute_capacity_report,
        name="generate_compute_capacity_report",
        description="Generate comprehensive compute capacity report with utilization analysis and recommendations"
    ),
    Tool.from_function(
        fn=list_streams_inventory,
        name="list_streams_inventory",
        description="List OCI Streaming streams (discovery shortcut for inventory)"
    ),
    Tool.from_function(
        fn=list_functions_applications_inventory,
        name="list_functions_applications_inventory",
        description="List OCI Functions applications (discovery shortcut for inventory)"
    ),
    Tool.from_function(
        fn=list_security_lists_inventory,
        name="list_security_lists_inventory",
        description="List OCI Networking security lists (discovery shortcut for inventory)"
    ),
    Tool.from_function(
        fn=list_load_balancers_inventory,
        name="list_load_balancers_inventory",
        description="List OCI Load Balancers (discovery shortcut for inventory)"
    ),
    Tool.from_function(
        fn=list_all_discovery,
        name="list_all_discovery",
        description="Aggregate discovery of core resources in a compartment"
    ),
]

if __name__ == "__main__":
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
            _start_http_server(int(os.getenv("METRICS_PORT", "8010")))
        except Exception:
            pass
    mcp = FastMCP(tools=tools, name="oci-mcp-inventory")
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
                application_name=os.getenv("PYROSCOPE_APP_NAME", "oci-mcp-inventory"),
                server_address=os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040"),
                sample_rate=int(os.getenv("PYROSCOPE_SAMPLE_RATE", "100")),
                detect_subprocesses=True,
                enable_logging=True,
            )
    except Exception:
        # Never break server if profiler not available
        pass

    mcp.run()
