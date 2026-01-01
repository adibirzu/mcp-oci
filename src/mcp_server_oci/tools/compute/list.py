from typing import Any

import oci

from mcp_server_oci.auth import get_client, get_compartment_id, get_oci_config


def _format_markdown(instances: list[dict[str, Any]]) -> str:
    if not instances:
        return "No instances found."

    md = "| Name | State | Shape | IP Address | OCID |\n"
    md += "|---|---|---|---|---|\n"
    for inst in instances:
        ips = []
        if inst.get('public_ip'):
            ips.append(inst['public_ip'])
        if inst.get('private_ip'):
            ips.append(inst['private_ip'])
        ip_str = ", ".join(ips)

        short_id = f"`{inst['id'][-6:]}...`"
        md += (
            f"| {inst['display_name']} | {inst['lifecycle_state']} "
            f"| {inst['shape']} | {ip_str} | {short_id} |\n"
        )
    return md

def list_instances(
    compartment_id: str | None = None,
    lifecycle_state: str | None = None,
    limit: int = 20,
    format: str = "markdown"  # "json" or "markdown"
) -> str | list[dict]:
    """
    List compute instances in a compartment.

    Args:
        compartment_id: OCID of the compartment (defaults to env var)
        lifecycle_state: Filter by state (RUNNING, STOPPED, etc.)
        limit: Max number of results (default 20)
        format: Output format "markdown" (for reading) or "json" (for processing)
    """
    comp_id = compartment_id or get_compartment_id()
    if not comp_id:
        return "Error: Compartment OCID not provided and COMPARTMENT_OCID env var not set."

    config = get_oci_config()
    client = get_client(oci.core.ComputeClient, region=config.get("region"))

    kwargs = {"compartment_id": comp_id, "limit": limit}
    if lifecycle_state:
        kwargs["lifecycle_state"] = lifecycle_state.upper()

    try:
        # Note: list_instances returns paginated response. We take the first page for now
        # or iterate until limit is reached.
        response = client.list_instances(**kwargs)
        items = response.data

        # Simple enhancement (simulating the complex logic from original for now)
        results = []
        for inst in items:
            # We would fetch IPs here ideally, but for MVP keeping it fast
            results.append({
                "id": inst.id,
                "display_name": inst.display_name,
                "lifecycle_state": inst.lifecycle_state,
                "shape": inst.shape,
                "time_created": inst.time_created.isoformat(),
                # Placeholders until deep fetch implemented
                "public_ip": None,
                "private_ip": None
            })

        if format == "markdown":
            return _format_markdown(results)
        return results

    except Exception as e:
        return f"Error listing instances: {str(e)}"
