"""
OCI Client Adapter for FinOpsAI integration with MCP-OCI architecture
"""
from dataclasses import dataclass
from typing import Optional, List, Dict
import oci
from mcp_oci_common import get_oci_config, get_compartment_id
from mcp_oci_common.session import get_client


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


def _home_region(identity: oci.identity.IdentityClient, tenancy_id: str) -> str:
    """Discover tenancy home region for Usage API calls.

    Strategy:
    1) get_tenancy() -> home_region_key
    2) list_regions() to map key -> region_name
    3) fallback: list_region_subscriptions() and pick is_home_region
    """
    try:
        ten = identity.get_tenancy(tenancy_id).data
        hr_key = getattr(ten, 'home_region_key', None)
        if hr_key:
            regs = identity.list_regions().data or []
            for r in regs:
                if getattr(r, 'key', None) == hr_key:
                    return getattr(r, 'name', None)
    except Exception:
        pass
    # Fallback
    try:
        subs = identity.list_region_subscriptions(tenancy_id)
        for s in getattr(subs, 'data', []) or []:
            if getattr(s, 'is_home_region', False):
                return getattr(s, 'region_name', None) or getattr(s, 'region', None)
    except Exception:
        pass
    return None


def make_clients() -> OCIClients:
    """
    Create FinOpsAI-compatible clients using mcp_oci_common configuration
    """
    config = get_oci_config()

    # Create clients using the shared OCI config
    # Identity first (for home-region discovery)
    identity = get_client(oci.identity.IdentityClient)

    # Usage API must be called in the tenancy's home region; override if needed
    usage_cfg = dict(config)
    try:
        ten = usage_cfg.get('tenancy')
        hr = _home_region(identity, ten) if ten else None
        if hr:
            usage_cfg['region'] = hr
    except Exception:
        pass
    usage_api = get_client(oci.usage_api.UsageapiClient, region=usage_cfg.get('region', config.get('region')))
    budgets = get_client(oci.budget.BudgetClient)
    object_storage = get_client(oci.object_storage.ObjectStorageClient)

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
        # Log to stderr only; never corrupt MCP stdio
        import sys
        print(f"Warning: Could not list compartments: {e}", file=sys.stderr)

    return compartments
