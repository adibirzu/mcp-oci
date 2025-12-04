#!/usr/bin/env python3
"""
OCI Local Cache Builder
=======================
Builds a comprehensive local cache of OCI resources to reduce token usage
and improve response times for MCP servers.

This script collects:
- Tenancy details
- Compartment hierarchy
- Compute instances (VMs) with names and OCIDs
- Database systems and names
- Autonomous databases
- Users and groups
- Network resources (VCNs, subnets)
- And more...

Usage:
    python scripts/build-local-cache.py --profile DEFAULT --region us-ashburn-1
    python scripts/build-local-cache.py --all-regions
    python scripts/build-local-cache.py --refresh-interval 3600
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import oci

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mcp_oci_common import get_oci_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default cache directory
DEFAULT_CACHE_DIR = os.path.expanduser("~/.mcp-oci/cache")


class OCILocalCacheBuilder:
    """Builds and maintains a local cache of OCI resources"""

    def __init__(self, config: Dict[str, Any], cache_dir: str = DEFAULT_CACHE_DIR):
        """
        Initialize the cache builder

        Args:
            config: OCI configuration dictionary
            cache_dir: Directory to store cache files
        """
        self.config = config
        self.cache_dir = cache_dir
        self.tenancy_id = config.get('tenancy')

        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)

        # Initialize clients lazily
        self._identity_client = None
        self._compute_client = None
        self._database_client = None
        self._network_client = None

        # Cache data structures
        self.cache_data = {
            'metadata': {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'tenancy_id': self.tenancy_id,
                'region': config.get('region'),
                'profile': os.getenv('OCI_PROFILE', 'DEFAULT')
            },
            'tenancy': {},
            'compartments': {},
            'compute': {},
            'database': {},
            'users': {},
            'groups': {},
            'network': {},
        }

    @property
    def identity_client(self):
        """Lazy initialization of identity client"""
        if self._identity_client is None:
            self._identity_client = oci.identity.IdentityClient(self.config)
        return self._identity_client

    @property
    def compute_client(self):
        """Lazy initialization of compute client"""
        if self._compute_client is None:
            self._compute_client = oci.core.ComputeClient(self.config)
        return self._compute_client

    @property
    def database_client(self):
        """Lazy initialization of database client"""
        if self._database_client is None:
            self._database_client = oci.database.DatabaseClient(self.config)
        return self._database_client

    @property
    def network_client(self):
        """Lazy initialization of network client"""
        if self._network_client is None:
            self._network_client = oci.core.VirtualNetworkClient(self.config)
        return self._network_client

    def collect_tenancy_details(self):
        """Collect comprehensive tenancy information"""
        logger.info("Collecting tenancy details...")

        try:
            # Get tenancy object
            tenancy = self.identity_client.get_tenancy(self.tenancy_id).data

            # Get subscribed regions
            regions = self.identity_client.list_region_subscriptions(self.tenancy_id).data

            # Determine home region
            home_region = None
            for region in regions:
                if region.is_home_region:
                    home_region = region.region_name
                    break

            self.cache_data['tenancy'] = {
                'id': tenancy.id,
                'name': tenancy.name,
                'description': tenancy.description,
                'home_region': home_region,
                'subscribed_regions': [
                    {
                        'name': r.region_name,
                        'key': r.region_key,
                        'is_home': r.is_home_region,
                        'status': r.status
                    } for r in regions
                ]
            }

            logger.info(f"Tenancy: {tenancy.name} (Home: {home_region})")

        except Exception as e:
            logger.error(f"Error collecting tenancy details: {e}")

    def collect_compartments(self):
        """Collect compartment hierarchy"""
        logger.info("Collecting compartment hierarchy...")

        try:
            compartments_list = []

            # Use pagination to get all compartments
            compartments = oci.pagination.list_call_get_all_results(
                self.identity_client.list_compartments,
                self.tenancy_id,
                compartment_id_in_subtree=True
            ).data

            # Add root compartment (tenancy)
            root_tenancy = self.identity_client.get_compartment(self.tenancy_id).data
            compartments_list.append({
                'id': root_tenancy.id,
                'name': root_tenancy.name,
                'description': root_tenancy.description,
                'lifecycle_state': root_tenancy.lifecycle_state,
                'is_root': True
            })

            # Add all sub-compartments
            for comp in compartments:
                if comp.lifecycle_state == 'ACTIVE':
                    compartments_list.append({
                        'id': comp.id,
                        'name': comp.name,
                        'description': comp.description,
                        'lifecycle_state': comp.lifecycle_state,
                        'is_root': False
                    })

            # Build hierarchy map (OCID -> name, and name -> OCID)
            self.cache_data['compartments'] = {
                'list': compartments_list,
                'by_id': {c['id']: c for c in compartments_list},
                'by_name': {c['name']: c for c in compartments_list},
                'count': len(compartments_list)
            }

            logger.info(f"Collected {len(compartments_list)} compartments")

        except Exception as e:
            logger.error(f"Error collecting compartments: {e}")

    def collect_compute_resources(self, compartment_id: str = None):
        """Collect compute instances across all compartments"""
        logger.info("Collecting compute resources...")

        if compartment_id is None:
            compartment_id = self.tenancy_id

        instances_data = {
            'instances': [],
            'by_id': {},
            'by_name': {},
            'count': 0
        }

        try:
            # Iterate through all compartments
            compartments = self.cache_data['compartments']['list']

            for comp in compartments:
                try:
                    instances = oci.pagination.list_call_get_all_results(
                        self.compute_client.list_instances,
                        comp['id']
                    ).data

                    for instance in instances:
                        instance_info = {
                            'id': instance.id,
                            'display_name': instance.display_name,
                            'compartment_id': comp['id'],
                            'compartment_name': comp['name'],
                            'shape': instance.shape,
                            'lifecycle_state': instance.lifecycle_state,
                            'availability_domain': instance.availability_domain,
                            'region': instance.region
                        }

                        instances_data['instances'].append(instance_info)
                        instances_data['by_id'][instance.id] = instance_info
                        instances_data['by_name'][instance.display_name] = instance_info

                except Exception as e:
                    logger.debug(f"Error listing instances in compartment {comp['name']}: {e}")

            instances_data['count'] = len(instances_data['instances'])
            self.cache_data['compute'] = instances_data

            logger.info(f"Collected {instances_data['count']} compute instances")

        except Exception as e:
            logger.error(f"Error collecting compute resources: {e}")

    def collect_database_resources(self):
        """Collect database systems and autonomous databases"""
        logger.info("Collecting database resources...")

        db_data = {
            'db_systems': [],
            'autonomous_databases': [],
            'by_id': {},
            'by_name': {},
            'count': 0
        }

        try:
            compartments = self.cache_data['compartments']['list']

            for comp in compartments:
                # Collect DB Systems
                try:
                    db_systems = oci.pagination.list_call_get_all_results(
                        self.database_client.list_db_systems,
                        comp['id']
                    ).data

                    for db_system in db_systems:
                        db_info = {
                            'id': db_system.id,
                            'display_name': db_system.display_name,
                            'compartment_id': comp['id'],
                            'compartment_name': comp['name'],
                            'shape': db_system.shape,
                            'lifecycle_state': db_system.lifecycle_state,
                            'type': 'db_system',
                            'database_edition': db_system.database_edition
                        }

                        db_data['db_systems'].append(db_info)
                        db_data['by_id'][db_system.id] = db_info
                        db_data['by_name'][db_system.display_name] = db_info

                except Exception as e:
                    logger.debug(f"Error listing DB systems in compartment {comp['name']}: {e}")

                # Collect Autonomous Databases
                try:
                    adb_list = oci.pagination.list_call_get_all_results(
                        self.database_client.list_autonomous_databases,
                        comp['id']
                    ).data

                    for adb in adb_list:
                        adb_info = {
                            'id': adb.id,
                            'display_name': adb.display_name or adb.db_name,
                            'db_name': adb.db_name,
                            'compartment_id': comp['id'],
                            'compartment_name': comp['name'],
                            'lifecycle_state': adb.lifecycle_state,
                            'type': 'autonomous_database',
                            'db_workload': adb.db_workload
                        }

                        db_data['autonomous_databases'].append(adb_info)
                        db_data['by_id'][adb.id] = adb_info
                        db_data['by_name'][adb.display_name or adb.db_name] = adb_info

                except Exception as e:
                    logger.debug(f"Error listing autonomous databases in compartment {comp['name']}: {e}")

            db_data['count'] = len(db_data['db_systems']) + len(db_data['autonomous_databases'])
            self.cache_data['database'] = db_data

            logger.info(f"Collected {len(db_data['db_systems'])} DB systems and {len(db_data['autonomous_databases'])} autonomous databases")

        except Exception as e:
            logger.error(f"Error collecting database resources: {e}")

    def collect_users_and_groups(self):
        """Collect IAM users and groups"""
        logger.info("Collecting users and groups...")

        try:
            # Collect users
            users = oci.pagination.list_call_get_all_results(
                self.identity_client.list_users,
                self.tenancy_id
            ).data

            users_data = {
                'users': [
                    {
                        'id': u.id,
                        'name': u.name,
                        'description': u.description,
                        'email': u.email,
                        'lifecycle_state': u.lifecycle_state
                    } for u in users
                ],
                'by_id': {u.id: u.name for u in users},
                'by_name': {u.name: u.id for u in users},
                'count': len(users)
            }

            # Collect groups
            groups = oci.pagination.list_call_get_all_results(
                self.identity_client.list_groups,
                self.tenancy_id
            ).data

            groups_data = {
                'groups': [
                    {
                        'id': g.id,
                        'name': g.name,
                        'description': g.description,
                        'lifecycle_state': g.lifecycle_state
                    } for g in groups
                ],
                'by_id': {g.id: g.name for g in groups},
                'by_name': {g.name: g.id for g in groups},
                'count': len(groups)
            }

            self.cache_data['users'] = users_data
            self.cache_data['groups'] = groups_data

            logger.info(f"Collected {len(users)} users and {len(groups)} groups")

        except Exception as e:
            logger.error(f"Error collecting users and groups: {e}")

    def collect_network_resources(self):
        """Collect VCNs and subnets"""
        logger.info("Collecting network resources...")

        network_data = {
            'vcns': [],
            'subnets': [],
            'by_id': {},
            'by_name': {},
            'count': 0
        }

        try:
            compartments = self.cache_data['compartments']['list']

            for comp in compartments:
                try:
                    # Collect VCNs
                    vcns = oci.pagination.list_call_get_all_results(
                        self.network_client.list_vcns,
                        comp['id']
                    ).data

                    for vcn in vcns:
                        vcn_info = {
                            'id': vcn.id,
                            'display_name': vcn.display_name,
                            'compartment_id': comp['id'],
                            'compartment_name': comp['name'],
                            'cidr_block': vcn.cidr_block,
                            'lifecycle_state': vcn.lifecycle_state,
                            'type': 'vcn'
                        }

                        network_data['vcns'].append(vcn_info)
                        network_data['by_id'][vcn.id] = vcn_info
                        network_data['by_name'][vcn.display_name] = vcn_info

                        # Collect subnets for this VCN
                        try:
                            subnets = oci.pagination.list_call_get_all_results(
                                self.network_client.list_subnets,
                                comp['id'],
                                vcn_id=vcn.id
                            ).data

                            for subnet in subnets:
                                subnet_info = {
                                    'id': subnet.id,
                                    'display_name': subnet.display_name,
                                    'vcn_id': vcn.id,
                                    'vcn_name': vcn.display_name,
                                    'compartment_id': comp['id'],
                                    'compartment_name': comp['name'],
                                    'cidr_block': subnet.cidr_block,
                                    'lifecycle_state': subnet.lifecycle_state,
                                    'type': 'subnet'
                                }

                                network_data['subnets'].append(subnet_info)
                                network_data['by_id'][subnet.id] = subnet_info
                                network_data['by_name'][subnet.display_name] = subnet_info

                        except Exception as e:
                            logger.debug(f"Error listing subnets for VCN {vcn.display_name}: {e}")

                except Exception as e:
                    logger.debug(f"Error listing VCNs in compartment {comp['name']}: {e}")

            network_data['count'] = len(network_data['vcns']) + len(network_data['subnets'])
            self.cache_data['network'] = network_data

            logger.info(f"Collected {len(network_data['vcns'])} VCNs and {len(network_data['subnets'])} subnets")

        except Exception as e:
            logger.error(f"Error collecting network resources: {e}")

    def build_cache(self):
        """Build the complete cache"""
        logger.info("Building OCI local cache...")

        self.collect_tenancy_details()
        self.collect_compartments()
        self.collect_compute_resources()
        self.collect_database_resources()
        self.collect_users_and_groups()
        self.collect_network_resources()

        logger.info("Cache building complete!")

    def save_cache(self):
        """Save cache to disk"""
        cache_file = os.path.join(self.cache_dir, 'oci_resources_cache.json')

        try:
            with open(cache_file, 'w') as f:
                json.dump(self.cache_data, f, indent=2, default=str)

            logger.info(f"Cache saved to {cache_file}")

            # Also save a metadata-only file for quick lookups
            metadata_file = os.path.join(self.cache_dir, 'cache_metadata.json')
            metadata = {
                'generated_at': self.cache_data['metadata']['generated_at'],
                'tenancy_id': self.cache_data['metadata']['tenancy_id'],
                'tenancy_name': self.cache_data['tenancy'].get('name'),
                'region': self.cache_data['metadata']['region'],
                'resources': {
                    'compartments': self.cache_data['compartments']['count'],
                    'compute_instances': self.cache_data['compute']['count'],
                    'databases': self.cache_data['database']['count'],
                    'users': self.cache_data['users']['count'],
                    'groups': self.cache_data['groups']['count'],
                    'network_resources': self.cache_data['network']['count']
                }
            }

            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Metadata saved to {metadata_file}")

        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def print_summary(self):
        """Print cache summary"""
        print("\n" + "="*60)
        print("OCI LOCAL CACHE SUMMARY")
        print("="*60)
        print(f"Generated at: {self.cache_data['metadata']['generated_at']}")
        print(f"Tenancy: {self.cache_data['tenancy'].get('name', 'N/A')}")
        print(f"Home Region: {self.cache_data['tenancy'].get('home_region', 'N/A')}")
        print(f"Compartments: {self.cache_data['compartments']['count']}")
        print(f"Compute Instances: {self.cache_data['compute']['count']}")
        print(f"Databases: {self.cache_data['database']['count']}")
        print(f"Users: {self.cache_data['users']['count']}")
        print(f"Groups: {self.cache_data['groups']['count']}")
        print(f"Network Resources: {self.cache_data['network']['count']}")
        print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Build OCI local cache for MCP servers'
    )
    parser.add_argument(
        '--profile',
        default=os.getenv('OCI_PROFILE', 'DEFAULT'),
        help='OCI config profile to use'
    )
    parser.add_argument(
        '--region',
        default=os.getenv('OCI_REGION'),
        help='OCI region'
    )
    parser.add_argument(
        '--cache-dir',
        default=DEFAULT_CACHE_DIR,
        help='Directory to store cache files'
    )
    parser.add_argument(
        '--all-regions',
        action='store_true',
        help='Collect data from all subscribed regions'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Set environment variables for OCI config
    if args.profile:
        os.environ['OCI_PROFILE'] = args.profile
    if args.region:
        os.environ['OCI_REGION'] = args.region

    try:
        # Get OCI configuration
        config = get_oci_config()

        # Build cache
        builder = OCILocalCacheBuilder(config, args.cache_dir)
        builder.build_cache()
        builder.save_cache()
        builder.print_summary()

        logger.info("Cache building completed successfully!")

    except Exception as e:
        logger.error(f"Error building cache: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
