#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict

# Ensure repo src path is available if not executed via poetry
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from mcp_oci_common.config import get_oci_config  # noqa: E402
from mcp_oci_common.observability import init_tracing, tool_span
from opentelemetry import trace

def utc_now():
    return datetime.now(timezone.utc)

def utc_midnight_today():
    now = utc_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)

def summarize_cpu_for_instance(monitoring_client, compartment_id: str, instance_id: str, start_time: datetime, end_time: datetime):
    import oci
    query = f'CpuUtilization[1m]{{resourceId="{instance_id}"}}.mean()'
    resp = monitoring_client.summarize_metrics_data(
        compartment_id=compartment_id,
        summarize_metrics_data_details=oci.monitoring.models.SummarizeMetricsDataDetails(
            namespace="oci_computeagent",
            query=query,
            start_time=start_time,
            end_time=end_time,
        ),
    )
    datapoints = []
    if resp.data:
        # resp.data is a list of MetricData
        datapoints = resp.data[0].aggregated_datapoints or []

    values = [float(dp.value) for dp in datapoints if getattr(dp, "value", None) is not None]

    if not values:
        return {"average": 0.0, "max": 0.0, "min": 0.0, "count": 0}

    avg = sum(values) / len(values)
    return {"average": avg, "max": max(values), "min": min(values), "count": len(values)}

# Initialize tracing
os.environ.setdefault("OTEL_SERVICE_NAME", "mcp-oci-cpu-table")
init_tracing(service_name="mcp-oci-cpu-table")
tracer = trace.get_tracer("mcp-oci-cpu-table")

def main():
    with tool_span(tracer, "run-cpu-table", mcp_server="mcp-oci-ops"):
        try:
            import oci
            from oci.pagination import list_call_get_all_results
        except Exception:
            print("ERROR: OCI SDK not installed. Please install 'oci' (pip install oci).", file=sys.stderr)
            sys.exit(2)

        cfg = get_oci_config()

        tenancy_id = cfg.get("tenancy") or os.getenv("COMPARTMENT_OCID")
        if not tenancy_id:
            print("ERROR: Could not determine tenancy OCID (missing 'tenancy' in config).", file=sys.stderr)
            sys.exit(2)

        region = cfg.get("region")
        compute = oci.core.ComputeClient(cfg)
        monitoring = oci.monitoring.MonitoringClient(cfg)
        identity = oci.identity.IdentityClient(cfg)

        # Time window: today (UTC midnight -> now)
        start_time = utc_midnight_today()
        end_time = utc_now()

    # Enumerate all ACTIVE compartments in tenancy and list RUNNING instances
    with tool_span(tracer, "list_compartments", mcp_server="mcp-oci-ops"):
        try:
            comps_resp = list_call_get_all_results(
                identity.list_compartments,
                compartment_id=tenancy_id,
                compartment_id_in_subtree=True,
                access_level="ANY",
            )
            compartments = [c.id for c in comps_resp.data if getattr(c, "lifecycle_state", "ACTIVE") == "ACTIVE"]
            # include root tenancy itself
            if tenancy_id not in compartments:
                compartments.append(tenancy_id)
        except oci.exceptions.ServiceError as e:
            print(f"ERROR: Failed to list compartments: {e}", file=sys.stderr)
            sys.exit(2)

    rows: List[Dict] = []
    for comp_id in compartments:
        with tool_span(tracer, "list_instances", mcp_server="mcp-oci-ops", compartment_id=comp_id):
            try:
                resp = list_call_get_all_results(
                    compute.list_instances,
                    compartment_id=comp_id,
                    lifecycle_state="RUNNING",
                )
                instances = resp.data
            except oci.exceptions.ServiceError:
                # Skip compartments with permissions issues
                continue

        for inst in instances:
            with tool_span(tracer, "summarize_cpu", mcp_server="mcp-oci-ops", instance_id=inst.id):
                metrics = summarize_cpu_for_instance(monitoring, comp_id, inst.id, start_time, end_time)
            rows.append({
                "id": inst.id,
                "name": getattr(inst, "display_name", ""),
                "shape": getattr(inst, "shape", ""),
                "average": metrics["average"],
                "max": metrics["max"],
                "min": metrics["min"],
                "datapoints": metrics["count"],
            })

    # Sort by average descending
    rows.sort(key=lambda r: r["average"], reverse=True)

    # Output Markdown table
    print(f"CPU Utilization (today, UTC {start_time.isoformat()} -> {end_time.isoformat()}) - Region: {region}")
    print()
    print("| Instance Name | Shape | Instance OCID | Avg CPU % | Max CPU % | Min CPU % | Points |")
    print("|---------------|-------|---------------|-----------:|----------:|----------:|-------:|")
    for r in rows:
        print(f"| {r['name'] or '-'} | {r['shape'] or '-'} | {r['id']} | {r['average']:.2f} | {r['max']:.2f} | {r['min']:.2f} | {r['datapoints']} |")

    if not rows:
        print()
        print("_No RUNNING instances found in the compartment for today._")

if __name__ == "__main__":
    main()
