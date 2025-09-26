"""
OCI Client Adapter for FinOpsAI integration with MCP-OCI architecture
"""
from dataclasses import dataclass
from typing import Optional, List, Dict
import oci
from mcp_oci_common import get_oci_config, get_compartment_id


@dataclass
class OCIClients:
    """
    FinOpsAI-compatible client structure using mcp_oci_common configuration
    """
    usage_api: oci.usage_api.UsageapiClient
    budgets: oci.budget.BudgetClient
    object_storage: oci.object_storage.ObjectStorageClient
    identity: oci.identity.IdentityClient
    config: dict


def make_clients() -> OCIClients:
    """
    Create FinOpsAI-compatible clients using mcp_oci_common configuration
    """
    config = get_oci_config()

    # Create clients using the shared OCI config
    usage_api = oci.usage_api.UsageapiClient(config)
    budgets = oci.budget.BudgetClient(config)
    object_storage = oci.object_storage.ObjectStorageClient(config)
    identity = oci.identity.IdentityClient(config)

    # Add tenancy information to config for FinOpsAI compatibility
    enhanced_config = dict(config)
    if 'tenancy' not in enhanced_config:
        enhanced_config['tenancy'] = config.get('tenancy')

    return OCIClients(
        usage_api=usage_api,
        budgets=budgets,
        object_storage=object_storage,
        identity=identity,
        config=enhanced_config
    )


def list_compartments_recursive(identity_client: oci.identity.IdentityClient,
                               tenancy_id: str,
                               parent_compartment_id: Optional[str] = None) -> List[Dict]:
    """
    List compartments recursively for FinOpsAI compatibility
    """
    compartments = []

    try:
        if parent_compartment_id is None:
            parent_compartment_id = tenancy_id

        response = identity_client.list_compartments(
            compartment_id=parent_compartment_id,
            compartment_id_in_subtree=True,
            lifecycle_state="ACTIVE"
        )

        for comp in response.data:
            compartments.append({
                'id': comp.id,
                'name': comp.name,
                'description': comp.description,
                'lifecycle_state': comp.lifecycle_state
            })

    except Exception as e:
        # Log error but continue - graceful degradation
        print(f"Warning: Could not list compartments: {e}")

    return compartments