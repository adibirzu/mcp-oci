import oci

from mcp_server_oci.auth import allow_mutations, get_client, get_oci_config


def start_instance(instance_id: str) -> dict:
    """Start a compute instance."""
    if not allow_mutations():
        return {"error": "Mutations are not allowed. Set ALLOW_MUTATIONS=true."}

    try:
        config = get_oci_config()
        client = get_client(oci.core.ComputeClient, region=config.get("region"))
        client.instance_action(instance_id, "START")
        return {"status": "STARTING", "instance_id": instance_id}
    except Exception as e:
        return {"error": str(e)}

def stop_instance(instance_id: str) -> dict:
    """Stop a compute instance."""
    if not allow_mutations():
        return {"error": "Mutations are not allowed. Set ALLOW_MUTATIONS=true."}

    try:
        config = get_oci_config()
        client = get_client(oci.core.ComputeClient, region=config.get("region"))
        client.instance_action(instance_id, "STOP")
        return {"status": "STOPPING", "instance_id": instance_id}
    except Exception as e:
        return {"error": str(e)}

def restart_instance(instance_id: str) -> dict:
    """Restart (soft reset) a compute instance."""
    if not allow_mutations():
        return {"error": "Mutations are not allowed. Set ALLOW_MUTATIONS=true."}

    try:
        config = get_oci_config()
        client = get_client(oci.core.ComputeClient, region=config.get("region"))
        client.instance_action(instance_id, "SOFTRESET")
        return {"status": "RESTARTING", "instance_id": instance_id}
    except Exception as e:
        return {"error": str(e)}
