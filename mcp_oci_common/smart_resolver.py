"""
Smart Resolver Module for OCI MCP Servers

Provides compartment name resolution and smart parameter handling that can be used
by individual MCP servers OR the gateway. Works directly with OCI SDK.

Usage in MCP servers:
    from mcp_oci_common.smart_resolver import resolve_compartment, get_resolver

    # Resolve compartment name to OCID
    ocid = resolve_compartment("Adrian_Birzu")

    # Or use the resolver instance for caching
    resolver = get_resolver()
    ocid = resolver.resolve("Adrian_Birzu")
    info = resolver.get_info("adrian")  # case-insensitive
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)

# Global cache with thread safety
_cache_lock = threading.Lock()
_compartment_cache: Dict[str, 'CompartmentInfo'] = {}
_cache_loaded = False
_cache_expiry: Optional[datetime] = None
_CACHE_TTL_SECONDS = 300  # 5 minutes


@dataclass
class CompartmentInfo:
    """Compartment information"""
    ocid: str
    name: str
    parent_id: Optional[str] = None
    description: Optional[str] = None
    lifecycle_state: Optional[str] = None


def _load_compartments_from_oci() -> List[CompartmentInfo]:
    """Load all compartments from OCI using the SDK directly"""
    try:
        import oci
        from oci.pagination import list_call_get_all_results
        from . import get_oci_config, make_client

        config = get_oci_config()
        identity_client = make_client(oci.identity.IdentityClient)
        tenancy_id = config.get("tenancy")

        if not tenancy_id:
            logger.error("Tenancy ID not found in config")
            return []

        # Get all compartments in the tenancy hierarchy
        kwargs = {
            'compartment_id': tenancy_id,
            'lifecycle_state': 'ACTIVE',
            'access_level': 'ANY',
            'compartment_id_in_subtree': True
        }

        response = list_call_get_all_results(identity_client.list_compartments, **kwargs)
        compartments = response.data

        result = []
        for comp in compartments:
            result.append(CompartmentInfo(
                ocid=comp.id,
                name=comp.name,
                parent_id=getattr(comp, 'compartment_id', None),
                description=getattr(comp, 'description', None),
                lifecycle_state=getattr(comp, 'lifecycle_state', None),
            ))

        # Add root compartment (tenancy)
        try:
            root = identity_client.get_compartment(compartment_id=tenancy_id).data
            result.append(CompartmentInfo(
                ocid=root.id,
                name=root.name,
                parent_id=None,
                description=getattr(root, 'description', None),
                lifecycle_state=getattr(root, 'lifecycle_state', None),
            ))
        except Exception as e:
            logger.warning(f"Could not fetch root compartment: {e}")

        logger.info(f"Loaded {len(result)} compartments from OCI")
        return result

    except Exception as e:
        logger.error(f"Error loading compartments from OCI: {e}")
        return []


def _ensure_cache_loaded() -> None:
    """Ensure compartment cache is loaded and not expired"""
    global _compartment_cache, _cache_loaded, _cache_expiry

    with _cache_lock:
        now = datetime.utcnow()

        # Check if cache is valid
        if _cache_loaded and _cache_expiry and now < _cache_expiry:
            return

        # Load fresh data
        compartments = _load_compartments_from_oci()
        _compartment_cache.clear()

        for comp in compartments:
            # Index by lowercase name for case-insensitive lookup
            _compartment_cache[comp.name.lower()] = comp

        _cache_loaded = True
        _cache_expiry = now + timedelta(seconds=_CACHE_TTL_SECONDS)
        logger.debug(f"Compartment cache refreshed with {len(_compartment_cache)} entries")


def resolve_compartment(name_or_ocid: str) -> Optional[str]:
    """
    Resolve compartment name to OCID.

    Supports:
    - OCID passthrough: "ocid1.compartment..." returns as-is
    - Exact name match: "Adrian_Birzu"
    - Case-insensitive: "adrian_birzu"
    - Partial match: "adrian" (finds first match containing this string)

    Args:
        name_or_ocid: Compartment name or OCID

    Returns:
        OCID string or None if not found
    """
    if not name_or_ocid:
        return None

    # If already an OCID, return as-is
    if name_or_ocid.startswith("ocid1."):
        return name_or_ocid

    _ensure_cache_loaded()

    with _cache_lock:
        # Try exact match (case-insensitive)
        lower_name = name_or_ocid.lower()
        if lower_name in _compartment_cache:
            return _compartment_cache[lower_name].ocid

        # Try partial match
        for cached_name, info in _compartment_cache.items():
            if lower_name in cached_name or cached_name in lower_name:
                logger.debug(f"Partial match: '{name_or_ocid}' -> '{info.name}'")
                return info.ocid

    logger.warning(f"Compartment not found: {name_or_ocid}")
    return None


def get_compartment_info(name_or_ocid: str) -> Optional[CompartmentInfo]:
    """Get full compartment information"""
    if not name_or_ocid:
        return None

    _ensure_cache_loaded()

    with _cache_lock:
        # If OCID, find by OCID
        if name_or_ocid.startswith("ocid1."):
            for info in _compartment_cache.values():
                if info.ocid == name_or_ocid:
                    return info
            return None

        # By name (case-insensitive)
        lower_name = name_or_ocid.lower()
        return _compartment_cache.get(lower_name)


def search_compartments(pattern: str) -> List[CompartmentInfo]:
    """Search compartments by name pattern (case-insensitive)"""
    if not pattern:
        return []

    _ensure_cache_loaded()

    pattern_lower = pattern.lower()
    results = []

    with _cache_lock:
        for name, info in _compartment_cache.items():
            if pattern_lower in name:
                results.append(info)

    return results


def list_all_compartments() -> List[CompartmentInfo]:
    """Get all compartments"""
    _ensure_cache_loaded()

    with _cache_lock:
        return list(_compartment_cache.values())


def refresh_cache() -> int:
    """Force refresh of compartment cache. Returns count of compartments loaded."""
    global _cache_loaded, _cache_expiry

    with _cache_lock:
        _cache_loaded = False
        _cache_expiry = None

    _ensure_cache_loaded()

    with _cache_lock:
        return len(_compartment_cache)


class CompartmentResolver:
    """
    Compartment resolver with instance-level options.

    Can be used when you need more control over caching or want to
    use a different OCI config profile.
    """

    def __init__(self, profile: Optional[str] = None, cache_ttl: int = 300):
        """
        Initialize resolver.

        Args:
            profile: OCI config profile name (uses default if None)
            cache_ttl: Cache TTL in seconds
        """
        self._profile = profile
        self._cache_ttl = cache_ttl
        self._local_cache: Dict[str, CompartmentInfo] = {}
        self._cache_loaded = False
        self._cache_expiry: Optional[datetime] = None

    def _load_cache(self) -> None:
        """Load compartments into local cache"""
        now = datetime.utcnow()

        if self._cache_loaded and self._cache_expiry and now < self._cache_expiry:
            return

        try:
            import oci
            from oci.pagination import list_call_get_all_results
            from . import get_oci_config, make_client

            config = get_oci_config(profile_name=self._profile)
            identity_client = make_client(oci.identity.IdentityClient, profile=self._profile)
            tenancy_id = config.get("tenancy")

            if not tenancy_id:
                logger.error("Tenancy ID not found in config")
                return

            kwargs = {
                'compartment_id': tenancy_id,
                'lifecycle_state': 'ACTIVE',
                'access_level': 'ANY',
                'compartment_id_in_subtree': True
            }

            response = list_call_get_all_results(identity_client.list_compartments, **kwargs)

            self._local_cache.clear()
            for comp in response.data:
                info = CompartmentInfo(
                    ocid=comp.id,
                    name=comp.name,
                    parent_id=getattr(comp, 'compartment_id', None),
                    description=getattr(comp, 'description', None),
                )
                self._local_cache[comp.name.lower()] = info

            # Add root
            try:
                root = identity_client.get_compartment(compartment_id=tenancy_id).data
                self._local_cache[root.name.lower()] = CompartmentInfo(
                    ocid=root.id,
                    name=root.name,
                )
            except Exception:
                pass

            self._cache_loaded = True
            self._cache_expiry = now + timedelta(seconds=self._cache_ttl)

        except Exception as e:
            logger.error(f"Error loading compartments: {e}")

    def resolve(self, name_or_ocid: str) -> Optional[str]:
        """Resolve compartment name to OCID"""
        if not name_or_ocid:
            return None

        if name_or_ocid.startswith("ocid1."):
            return name_or_ocid

        self._load_cache()

        lower_name = name_or_ocid.lower()
        if lower_name in self._local_cache:
            return self._local_cache[lower_name].ocid

        # Partial match
        for cached_name, info in self._local_cache.items():
            if lower_name in cached_name or cached_name in lower_name:
                return info.ocid

        return None

    def get_info(self, name_or_ocid: str) -> Optional[CompartmentInfo]:
        """Get compartment info"""
        if not name_or_ocid:
            return None

        self._load_cache()

        if name_or_ocid.startswith("ocid1."):
            for info in self._local_cache.values():
                if info.ocid == name_or_ocid:
                    return info
            return None

        return self._local_cache.get(name_or_ocid.lower())

    def search(self, pattern: str) -> List[CompartmentInfo]:
        """Search compartments by pattern"""
        self._load_cache()
        pattern_lower = pattern.lower()
        return [
            info for name, info in self._local_cache.items()
            if pattern_lower in name
        ]


# Global resolver instance
_global_resolver: Optional[CompartmentResolver] = None


def get_resolver(profile: Optional[str] = None) -> CompartmentResolver:
    """Get global resolver instance (or create one for specific profile)"""
    global _global_resolver

    if profile:
        return CompartmentResolver(profile=profile)

    if _global_resolver is None:
        _global_resolver = CompartmentResolver()

    return _global_resolver


# Smart parameter handling utilities
def smart_compartment_id(compartment: Optional[str] = None) -> Optional[str]:
    """
    Get compartment OCID with smart resolution.

    1. If compartment is an OCID, return as-is
    2. If compartment is a name, resolve to OCID
    3. If compartment is None, use COMPARTMENT_OCID env var

    Args:
        compartment: Compartment name or OCID (optional)

    Returns:
        OCID or None
    """
    import os

    if compartment:
        return resolve_compartment(compartment)

    # Fall back to environment variable
    return os.getenv("COMPARTMENT_OCID")


def smart_time_range(days: int = 7) -> tuple:
    """
    Get smart time range for queries.

    Args:
        days: Number of days to look back

    Returns:
        Tuple of (start_time, end_time) as datetime objects
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    return start_time, end_time


def smart_time_range_iso(days: int = 7) -> tuple:
    """
    Get smart time range as ISO strings with Z suffix.

    Args:
        days: Number of days to look back

    Returns:
        Tuple of (start_time, end_time) as ISO strings
    """
    start, end = smart_time_range(days)
    return start.isoformat() + "Z", end.isoformat() + "Z"
