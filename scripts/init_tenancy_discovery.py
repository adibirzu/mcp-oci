#!/usr/bin/env python3
"""
Tenancy Discovery Initialization Script

Runs at server startup to discover and cache tenancy information.
This ensures all MCP servers have access to tenancy details without
requiring individual API calls.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Load .env.local before any imports
try:
    from dotenv import load_dotenv
    _repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(_repo_root / ".env.local", override=False)
except Exception:
    pass

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import oci
    from mcp_oci_common import get_oci_config
    from mcp_oci_common.local_cache import get_local_cache
except ImportError as e:
    print(f"ERROR: Required dependencies not available: {e}")
    print("Install with: pip install -e .[oci]")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def discover_tenancy_info(profile: Optional[str] = None) -> Dict[str, Any]:
    """
    Discover tenancy information and return structured data.
    
    Args:
        profile: OCI profile name (defaults to DEFAULT or OCI_PROFILE env var)
        
    Returns:
        Dictionary with tenancy details including:
        - id: Tenancy OCID
        - name: Tenancy name
        - home_region: Home region name
        - subscribed_regions: List of subscribed regions
        - compartments: Basic compartment hierarchy
    """
    try:
        config = get_oci_config()
        if profile:
            config['profile'] = profile
        
        tenancy_id = config.get('tenancy')
        if not tenancy_id:
            logger.error("Tenancy OCID not found in OCI configuration")
            return {}
        
        identity_client = oci.identity.IdentityClient(config)
        
        # Get tenancy details
        tenancy = identity_client.get_tenancy(tenancy_id).data
        
        # Get subscribed regions
        regions = identity_client.list_region_subscriptions(tenancy_id).data
        
        # Find home region
        home_region = None
        subscribed_regions = []
        for region in regions:
            subscribed_regions.append({
                'name': region.region_name,
                'key': region.region_key,
                'is_home': region.is_home_region,
                'status': region.status
            })
            if region.is_home_region:
                home_region = region.region_name
        
        # Get root compartment (tenancy itself)
        root_compartment = identity_client.get_compartment(tenancy_id).data
        
        # Get top-level compartments (limit to first 50 for performance)
        try:
            compartments = oci.pagination.list_call_get_all_results(
                identity_client.list_compartments,
                compartment_id=tenancy_id,
                compartment_id_in_subtree=False,
                limit=50
            ).data
            
            compartment_list = [{
                'id': root_compartment.id,
                'name': root_compartment.name,
                'description': root_compartment.description,
                'lifecycle_state': root_compartment.lifecycle_state,
                'is_root': True
            }]
            
            for comp in compartments:
                if comp.lifecycle_state == 'ACTIVE':
                    compartment_list.append({
                        'id': comp.id,
                        'name': comp.name,
                        'description': comp.description or '',
                        'lifecycle_state': comp.lifecycle_state,
                        'is_root': False
                    })
        except Exception as e:
            logger.warning(f"Error fetching compartments: {e}")
            compartment_list = [{
                'id': root_compartment.id,
                'name': root_compartment.name,
                'description': root_compartment.description,
                'lifecycle_state': root_compartment.lifecycle_state,
                'is_root': True
            }]
        
        tenancy_info = {
            'id': tenancy.id,
            'name': tenancy.name,
            'description': tenancy.description or '',
            'home_region': home_region,
            'subscribed_regions': subscribed_regions,
            'compartments': compartment_list,
            'discovered_at': str(oci.util.datetime_to_string(oci.util.datetime.now()))
        }
        
        logger.info(f"Discovered tenancy: {tenancy.name} (Home: {home_region})")
        logger.info(f"Found {len(subscribed_regions)} subscribed regions")
        logger.info(f"Found {len(compartment_list)} compartments")
        
        return tenancy_info
        
    except Exception as e:
        logger.error(f"Error discovering tenancy information: {e}", exc_info=True)
        return {}


def save_tenancy_cache(tenancy_info: Dict[str, Any], cache_dir: Optional[str] = None) -> str:
    """
    Save tenancy information to local cache.
    
    Args:
        tenancy_info: Tenancy information dictionary
        cache_dir: Cache directory path (defaults to ~/.mcp-oci/cache)
        
    Returns:
        Path to the cache file
    """
    if not tenancy_info:
        logger.warning("No tenancy information to cache")
        return ""
    
    if cache_dir is None:
        cache_dir = os.path.expanduser("~/.mcp-oci/cache")
    
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    
    cache_file = cache_path / "tenancy_discovery.json"
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(tenancy_info, f, indent=2)
        logger.info(f"Tenancy cache saved to: {cache_file}")
        return str(cache_file)
    except Exception as e:
        logger.error(f"Error saving tenancy cache: {e}")
        return ""


def main():
    """Main entry point for tenancy discovery initialization."""
    profile = os.getenv('OCI_PROFILE', 'DEFAULT')
    cache_dir = os.getenv('MCP_CACHE_DIR') or os.getenv('OCI_MCP_CACHE_DIR') or os.getenv('MCP_OCI_CACHE_DIR')
    
    logger.info("Starting tenancy discovery...")
    logger.info(f"Using OCI profile: {profile}")
    
    tenancy_info = discover_tenancy_info(profile=profile)
    
    if tenancy_info:
        cache_file = save_tenancy_cache(tenancy_info, cache_dir)
        if cache_file:
            logger.info("Tenancy discovery completed successfully")
            print(json.dumps(tenancy_info, indent=2))
            return 0
        else:
            logger.warning("Tenancy discovery completed but cache save failed")
            return 1
    else:
        logger.error("Tenancy discovery failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
