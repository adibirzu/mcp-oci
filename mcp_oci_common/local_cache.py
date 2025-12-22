"""
Local Cache Loader for OCI Resources
=====================================
Provides utilities to load and query the local OCI resource cache
built by scripts/build-local-cache.py

This reduces token usage by providing local lookups for:
- Compartment names/IDs
- VM/instance names/IDs
- Database names/IDs
- User names/IDs
- Network resource names/IDs
- Tenancy details
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def _get_shared_cache_dir() -> str:
    """Resolve shared cache directory across MCP servers and agents."""
    raw = os.getenv("MCP_CACHE_DIR") or os.getenv("OCI_MCP_CACHE_DIR")
    if raw:
        return os.path.expanduser(raw)
    return os.path.expanduser("~/.mcp-oci/cache")


DEFAULT_CACHE_DIR = _get_shared_cache_dir()


class OCILocalCache:
    """Provides access to locally cached OCI resource metadata"""

    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR):
        """
        Initialize the local cache loader

        Args:
            cache_dir: Directory containing cache files
        """
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, 'oci_resources_cache.json')
        self.metadata_file = os.path.join(cache_dir, 'cache_metadata.json')

        self._cache_data = None
        self._metadata = None
        self._load_cache()

    def _load_cache(self):
        """Load cache from disk"""
        try:
            if self._load_cache_from_redis():
                return
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    self._cache_data = json.load(f)
                logger.debug(f"Loaded cache from {self.cache_file}")
            else:
                logger.warning(f"Cache file not found: {self.cache_file}")
                self._cache_data = self._empty_cache()

            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r') as f:
                    self._metadata = json.load(f)
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            self._cache_data = self._empty_cache()

    def _load_cache_from_redis(self) -> bool:
        """Load cache from Redis when configured."""
        backend = os.getenv("MCP_CACHE_BACKEND", "file").lower()
        redis_url = os.getenv("MCP_REDIS_URL") or os.getenv("REDIS_URL")
        if backend != "redis" or not redis_url:
            return False
        try:
            import redis  # type: ignore
        except Exception:
            logger.warning("Redis cache backend requested but redis library not installed; falling back to file cache")
            return False

        try:
            prefix = os.getenv("MCP_CACHE_KEY_PREFIX", "mcp:cache")
            cache_key = f"{prefix}:oci_resources_cache"
            meta_key = f"{prefix}:oci_cache_metadata"
            client = redis.Redis.from_url(redis_url)
            raw = client.get(cache_key)
            if raw:
                self._cache_data = json.loads(raw)
                meta_raw = client.get(meta_key)
                if meta_raw:
                    self._metadata = json.loads(meta_raw)
                return True
        except Exception as e:
            logger.warning(f"Failed to load cache from Redis: {e}")
        return False

    def _empty_cache(self) -> Dict[str, Any]:
        """Return empty cache structure"""
        return {
            'metadata': {},
            'tenancy': {},
            'compartments': {'list': [], 'by_id': {}, 'by_name': {}, 'count': 0},
            'compute': {'instances': [], 'by_id': {}, 'by_name': {}, 'count': 0},
            'database': {'db_systems': [], 'autonomous_databases': [], 'by_id': {}, 'by_name': {}, 'count': 0},
            'users': {'users': [], 'by_id': {}, 'by_name': {}, 'count': 0},
            'groups': {'groups': [], 'by_id': {}, 'by_name': {}, 'count': 0},
            'network': {'vcns': [], 'subnets': [], 'by_id': {}, 'by_name': {}, 'count': 0},
        }

    def is_available(self) -> bool:
        """Check if cache is available and loaded"""
        return self._cache_data is not None and bool(self._cache_data.get('metadata'))

    def get_cache_age_minutes(self) -> Optional[float]:
        """Get cache age in minutes"""
        if not self.is_available():
            return None

        try:
            generated_at = self._cache_data['metadata'].get('generated_at')
            if generated_at:
                cache_time = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                delta = now - cache_time
                return delta.total_seconds() / 60
        except Exception as e:
            logger.debug(f"Error calculating cache age: {e}")

        return None

    def needs_refresh(self, max_age_minutes: int = 1440) -> bool:
        """
        Check if cache needs refresh

        Args:
            max_age_minutes: Maximum acceptable age in minutes (default 24 hours)

        Returns:
            True if cache needs refresh, False otherwise
        """
        if not self.is_available():
            return True

        age = self.get_cache_age_minutes()
        if age is None:
            return True

        return age > max_age_minutes

    # === Tenancy Methods ===

    def get_tenancy_details(self) -> Dict[str, Any]:
        """Get complete tenancy details"""
        if not self.is_available():
            return {}
        return self._cache_data.get('tenancy', {})

    def get_tenancy_name(self) -> Optional[str]:
        """Get tenancy name"""
        tenancy = self.get_tenancy_details()
        return tenancy.get('name')

    def get_home_region(self) -> Optional[str]:
        """Get tenancy home region"""
        tenancy = self.get_tenancy_details()
        return tenancy.get('home_region')

    def get_subscribed_regions(self) -> List[Dict[str, Any]]:
        """Get list of subscribed regions"""
        tenancy = self.get_tenancy_details()
        return tenancy.get('subscribed_regions', [])

    # === Compartment Methods ===

    def get_compartment_by_id(self, compartment_id: str) -> Optional[Dict[str, Any]]:
        """Get compartment details by OCID"""
        if not self.is_available():
            return None
        return self._cache_data['compartments']['by_id'].get(compartment_id)

    def get_compartment_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get compartment details by name"""
        if not self.is_available():
            return None
        return self._cache_data['compartments']['by_name'].get(name)

    def get_compartment_name(self, compartment_id: str) -> Optional[str]:
        """Get compartment name from OCID"""
        comp = self.get_compartment_by_id(compartment_id)
        return comp.get('name') if comp else None

    def get_all_compartments(self) -> List[Dict[str, Any]]:
        """Get all compartments"""
        if not self.is_available():
            return []
        return self._cache_data['compartments'].get('list', [])

    # === Compute Methods ===

    def get_instance_by_id(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get compute instance details by OCID"""
        if not self.is_available():
            return None
        return self._cache_data['compute']['by_id'].get(instance_id)

    def get_instance_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get compute instance details by name"""
        if not self.is_available():
            return None
        return self._cache_data['compute']['by_name'].get(name)

    def get_instance_name(self, instance_id: str) -> Optional[str]:
        """Get instance display name from OCID"""
        instance = self.get_instance_by_id(instance_id)
        return instance.get('display_name') if instance else None

    def get_all_instances(self) -> List[Dict[str, Any]]:
        """Get all compute instances"""
        if not self.is_available():
            return []
        return self._cache_data['compute'].get('instances', [])

    # === Database Methods ===

    def get_database_by_id(self, db_id: str) -> Optional[Dict[str, Any]]:
        """Get database details by OCID"""
        if not self.is_available():
            return None
        return self._cache_data['database']['by_id'].get(db_id)

    def get_database_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get database details by name"""
        if not self.is_available():
            return None
        return self._cache_data['database']['by_name'].get(name)

    def get_database_name(self, db_id: str) -> Optional[str]:
        """Get database name from OCID"""
        db = self.get_database_by_id(db_id)
        return db.get('display_name') if db else None

    def get_all_databases(self) -> List[Dict[str, Any]]:
        """Get all databases (DB systems + autonomous)"""
        if not self.is_available():
            return []
        db_data = self._cache_data.get('database', {})
        return db_data.get('db_systems', []) + db_data.get('autonomous_databases', [])

    # === User/Group Methods ===

    def get_user_by_id(self, user_id: str) -> Optional[str]:
        """Get user name from OCID"""
        if not self.is_available():
            return None
        return self._cache_data['users']['by_id'].get(user_id)

    def get_user_by_name(self, name: str) -> Optional[str]:
        """Get user OCID from name"""
        if not self.is_available():
            return None
        return self._cache_data['users']['by_name'].get(name)

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        if not self.is_available():
            return []
        return self._cache_data['users'].get('users', [])

    def get_group_by_id(self, group_id: str) -> Optional[str]:
        """Get group name from OCID"""
        if not self.is_available():
            return None
        return self._cache_data['groups']['by_id'].get(group_id)

    def get_all_groups(self) -> List[Dict[str, Any]]:
        """Get all groups"""
        if not self.is_available():
            return []
        return self._cache_data['groups'].get('groups', [])

    # === Network Methods ===

    def get_vcn_by_id(self, vcn_id: str) -> Optional[Dict[str, Any]]:
        """Get VCN details by OCID"""
        if not self.is_available():
            return None
        return self._cache_data['network']['by_id'].get(vcn_id)

    def get_vcn_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get VCN details by name"""
        if not self.is_available():
            return None
        return self._cache_data['network']['by_name'].get(name)

    def get_all_vcns(self) -> List[Dict[str, Any]]:
        """Get all VCNs"""
        if not self.is_available():
            return []
        return self._cache_data['network'].get('vcns', [])

    def get_all_subnets(self) -> List[Dict[str, Any]]:
        """Get all subnets"""
        if not self.is_available():
            return []
        return self._cache_data['network'].get('subnets', [])

    # === Enrichment Methods ===

    def enrich_with_names(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich data dictionary with human-readable names from cache

        Args:
            data: Dictionary potentially containing OCIDs

        Returns:
            Enriched dictionary with _name fields added
        """
        if not self.is_available():
            return data

        enriched = data.copy()

        # Enrich compartment IDs
        if 'compartment_id' in enriched:
            comp_name = self.get_compartment_name(enriched['compartment_id'])
            if comp_name:
                enriched['compartment_name'] = comp_name

        # Enrich instance IDs
        if 'instance_id' in enriched:
            inst_name = self.get_instance_name(enriched['instance_id'])
            if inst_name:
                enriched['instance_name'] = inst_name

        # Enrich database IDs
        if 'database_id' in enriched:
            db_name = self.get_database_name(enriched['database_id'])
            if db_name:
                enriched['database_name'] = db_name

        # Enrich user IDs
        if 'user_id' in enriched:
            user_name = self.get_user_by_id(enriched['user_id'])
            if user_name:
                enriched['user_name'] = user_name

        return enriched

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.is_available():
            return {'available': False}

        age_minutes = self.get_cache_age_minutes()

        return {
            'available': True,
            'generated_at': self._cache_data['metadata'].get('generated_at'),
            'age_minutes': age_minutes,
            'needs_refresh': self.needs_refresh(),
            'tenancy_name': self.get_tenancy_name(),
            'home_region': self.get_home_region(),
            'resources': {
                'compartments': self._cache_data['compartments']['count'],
                'compute_instances': self._cache_data['compute']['count'],
                'databases': self._cache_data['database']['count'],
                'users': self._cache_data['users']['count'],
                'groups': self._cache_data['groups']['count'],
                'network_resources': self._cache_data['network']['count']
            }
        }


# Global instance for easy access
_global_cache: Optional[OCILocalCache] = None


def get_local_cache(cache_dir: str = DEFAULT_CACHE_DIR) -> OCILocalCache:
    """
    Get global local cache instance

    Args:
        cache_dir: Directory containing cache files

    Returns:
        OCILocalCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = OCILocalCache(cache_dir)
    return _global_cache


def reload_cache():
    """Force reload of global cache instance"""
    global _global_cache
    _global_cache = None
