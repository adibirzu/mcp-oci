import os
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

# Set up logging
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)

# Set up tracing
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-inventory")
init_tracing(service_name="oci-mcp-inventory")
init_metrics()
tracer = trace.get_tracer("oci-mcp-inventory")

CACHE_DIR = "/tmp/mcp-oci-cache/inventory"
os.makedirs(CACHE_DIR, exist_ok=True)

def run_showoci(
    profile: Optional[str] = None,
    regions: Optional[List[str]] = None,
    compartments: Optional[List[str]] = None,
    resource_types: Optional[List[str]] = None,
    output_format: str = "text",
    diff_mode: bool = True,
    limit: Optional[int] = None
) -> Dict:
    with tool_span(tracer, "run_showoci", mcp_server="oci-mcp-inventory") as span:
        # Build command and defaults from env
        from mcp_oci_common.observability import record_token_usage
        cfg_profile = profile or os.getenv("OCI_PROFILE")
        cfg_regions = regions or ([os.getenv("OCI_REGION")] if os.getenv("OCI_REGION") else None)
        cfg_compartments = compartments or ([os.getenv("COMPARTMENT_OCID")] if os.getenv("COMPARTMENT_OCID") else None)
        cmd = ["python", "third_party/oci-python-sdk/examples/showoci/showoci.py"]
        config_path = os.path.expanduser("~/.oci/config")
        # Enrich span attributes for observability
        try:
            add_oci_call_attributes(span, oci_service="ShowOCI", oci_operation="RunReport", region=(cfg_regions[0] if cfg_regions else None), endpoint=None)
        except Exception:
            pass
        
        if cfg_profile:
            cmd.extend(["--config-file", config_path, "--profile", cfg_profile])
        if cfg_regions:
            cmd.extend(["--region", ",".join(cfg_regions)])
        if cfg_compartments:
            cmd.extend(["--compartment-id", ",".join(cfg_compartments)])
        if resource_types:
            cmd.extend(["--query", ",".join(resource_types)])  # Assuming it supports
        if output_format == "csv":
            cmd.append("--generate-full-report")  # From repo, it has CSV options
        
        # Compute cache key
        param_str = json.dumps({
            "profile": profile,
            "regions": regions,
            "compartments": compartments,
            "resource_types": resource_types,
            "output_format": output_format
        }, sort_keys=True)
        cache_key = hashlib.sha256(param_str.encode()).hexdigest()
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.txt")
        prev_cache_file = os.path.join(CACHE_DIR, f"{cache_key}.prev.txt")
        
        try:
            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                return {"error": result.stderr}
            
            output = result.stdout
            if limit:
                output = "\n".join(output.splitlines()[:limit])
            
            # Cache current
            if os.path.exists(cache_file):
                os.rename(cache_file, prev_cache_file)
            with open(cache_file, "w") as f:
                f.write(output)
            
            if diff_mode and os.path.exists(prev_cache_file):
                with open(prev_cache_file, "r") as f:
                    prev_output = f.read()
                diff = list(difflib.unified_diff(
                    prev_output.splitlines(keepends=True),
                    output.splitlines(keepends=True),
                    fromfile="previous",
                    tofile="current"
                ))
                diff_text = "".join(diff)
                try:
                    record_token_usage(int(len(diff_text) / 4), attrs={"source": "showoci", "diff": True})
                except Exception:
                    pass
                return {"diff": diff_text, "changes_detected": bool(diff)}
            else:
                try:
                    record_token_usage(int(len(output) / 4), attrs={"source": "showoci", "diff": False})
                except Exception:
                    pass
                return {"output": output}
        
        except Exception as e:
            logging.error(f"Error running showoci: {e}")
            span.record_exception(e)
            return {"error": str(e)}

def run_showoci_simple(
    profile: Optional[str] = None,
    regions: Optional[str] = None,
    compartments: Optional[str] = None,
    resource_types: Optional[str] = None,
    output_format: str = "text",
    diff_mode: bool = True,
    limit: Optional[int] = None
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
    )

tools = [
    Tool.from_function(
        fn=run_showoci,
        name="run_showoci",
        description="Run ShowOCI inventory report with optional diff for changes"
    ),
    Tool.from_function(
        fn=run_showoci_simple,
        name="run_showoci_simple",
        description="Run ShowOCI using comma-separated regions/compartments/resource_types"
    )
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
