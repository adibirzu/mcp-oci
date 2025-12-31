"""
High-Performance Caching Layer for OCI MCP Server.

Provides TTL-based caching with:
- Async-safe operations
- Automatic key generation
- LRU eviction policy
- Cache statistics
- Decorator-based caching

This significantly reduces API calls and improves response times
for frequently accessed data like compartments, instances, and metrics.
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from .observability import get_logger

logger = get_logger("oci-mcp.cache")

P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class CacheEntry:
    """A single cache entry with TTL tracking."""
    value: Any
    created_at: float
    ttl_seconds: float
    hits: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() - self.created_at > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        """Get age of entry in seconds."""
        return time.time() - self.created_at

    @property
    def remaining_ttl(self) -> float:
        """Get remaining TTL in seconds."""
        return max(0, self.ttl_seconds - self.age_seconds)


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "expirations": self.expirations,
            "size": self.size,
            "hit_rate": f"{self.hit_rate:.2%}",
        }


class TTLCache:
    """
    Thread-safe TTL cache with LRU eviction.

    Features:
    - Configurable TTL per entry
    - Maximum size with LRU eviction
    - Automatic cleanup of expired entries
    - Performance statistics

    Example:
        cache = TTLCache(max_size=1000, default_ttl=300)

        # Set with default TTL
        cache.set("key", value)

        # Set with custom TTL
        cache.set("key", value, ttl=60)

        # Get (returns None if expired or missing)
        value = cache.get("key")
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float = 300,  # 5 minutes default
        cleanup_interval: float = 60,  # Cleanup every minute
    ):
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._stats = CacheStats()
        self._last_cleanup = time.time()

    async def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                return None

            if entry.is_expired:
                del self._cache[key]
                self._stats.expirations += 1
                self._stats.misses += 1
                self._stats.size = len(self._cache)
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.hits += 1
            self._stats.hits += 1

            return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: float | None = None,
    ) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override (uses default if not specified)
        """
        async with self._lock:
            # Remove if exists (to update order)
            if key in self._cache:
                del self._cache[key]

            # Evict if at capacity
            while len(self._cache) >= self._max_size:
                evicted_key = next(iter(self._cache))
                del self._cache[evicted_key]
                self._stats.evictions += 1

            # Add new entry
            self._cache[key] = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl_seconds=ttl or self._default_ttl,
            )
            self._stats.size = len(self._cache)

            # Periodic cleanup
            await self._maybe_cleanup()

    async def delete(self, key: str) -> bool:
        """Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.size = len(self._cache)
                return True
            return False

    async def clear(self) -> None:
        """Clear all entries from cache."""
        async with self._lock:
            self._cache.clear()
            self._stats.size = 0

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: float | None = None,
    ) -> Any:
        """Get from cache or compute and cache value.

        Args:
            key: Cache key
            factory: Function to compute value if not cached
            ttl: Optional TTL override

        Returns:
            Cached or computed value
        """
        value = await self.get(key)
        if value is not None:
            return value

        # Compute value (outside lock to avoid blocking)
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()

        await self.set(key, value, ttl)
        return value

    async def _maybe_cleanup(self) -> None:
        """Perform cleanup if interval has passed."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired
        ]

        for key in expired_keys:
            del self._cache[key]
            self._stats.expirations += 1

        self._stats.size = len(self._cache)

        if expired_keys:
            logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")

    @property
    def stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats

    def __len__(self) -> int:
        return len(self._cache)


# =============================================================================
# Cache Key Generation
# =============================================================================

def generate_cache_key(*args: Any, prefix: str = "", **kwargs: Any) -> str:
    """Generate a deterministic cache key from arguments.

    Args:
        *args: Positional arguments to include in key
        prefix: Optional prefix for key namespacing
        **kwargs: Keyword arguments to include in key

    Returns:
        Deterministic cache key string
    """
    # Build key components
    components = []

    if prefix:
        components.append(prefix)

    for arg in args:
        if arg is not None:
            components.append(str(arg))

    # Sort kwargs for deterministic ordering
    for key in sorted(kwargs.keys()):
        value = kwargs[key]
        if value is not None:
            components.append(f"{key}={value}")

    # Create hash for long keys
    key_str = ":".join(components)
    if len(key_str) > 200:
        hash_suffix = hashlib.md5(key_str.encode()).hexdigest()[:12]
        key_str = f"{prefix}:{hash_suffix}" if prefix else hash_suffix

    return key_str


# =============================================================================
# Cache Decorator
# =============================================================================

def cached(
    cache: TTLCache,
    ttl: float | None = None,
    key_prefix: str = "",
    key_builder: Callable[..., str] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to cache function results.

    Args:
        cache: TTLCache instance to use
        ttl: Optional TTL override
        key_prefix: Prefix for cache keys
        key_builder: Optional custom key builder function

    Example:
        @cached(api_cache, ttl=60, key_prefix="instances")
        async def list_instances(compartment_id: str) -> list:
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Generate cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = generate_cache_key(
                    *args,
                    prefix=key_prefix or func.__name__,
                    **kwargs
                )

            # Try cache first
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # Call function
            logger.debug(f"Cache miss: {cache_key}")
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Cache result
            await cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


# =============================================================================
# Tiered Cache Configuration
# =============================================================================

@dataclass
class CacheTier:
    """Configuration for a cache tier."""
    name: str
    ttl_seconds: float
    max_size: int = 500
    description: str = ""


# Pre-configured cache tiers for different data types
CACHE_TIERS = {
    # Tier 1: Highly cacheable, rarely changes
    "static": CacheTier(
        name="static",
        ttl_seconds=3600,  # 1 hour
        max_size=200,
        description="Static data (shapes, regions, ADs)",
    ),

    # Tier 2: Moderately cacheable
    "config": CacheTier(
        name="config",
        ttl_seconds=300,  # 5 minutes
        max_size=500,
        description="Configuration data (compartments, VCNs)",
    ),

    # Tier 3: Short-lived cache
    "operational": CacheTier(
        name="operational",
        ttl_seconds=60,  # 1 minute
        max_size=1000,
        description="Operational data (instances, alarms)",
    ),

    # Tier 4: Very short cache for metrics
    "metrics": CacheTier(
        name="metrics",
        ttl_seconds=30,  # 30 seconds
        max_size=500,
        description="Metrics and monitoring data",
    ),

    # Tier 5: No cache (pass-through)
    "realtime": CacheTier(
        name="realtime",
        ttl_seconds=0,
        max_size=0,
        description="Real-time data (no caching)",
    ),
}


# =============================================================================
# Global Cache Instances
# =============================================================================

# Main caches for different data tiers
_static_cache: TTLCache | None = None
_config_cache: TTLCache | None = None
_operational_cache: TTLCache | None = None
_metrics_cache: TTLCache | None = None


def get_cache(tier: str = "operational") -> TTLCache:
    """Get cache instance for specified tier.

    Args:
        tier: Cache tier name (static, config, operational, metrics)

    Returns:
        TTLCache instance for the tier
    """
    global _static_cache, _config_cache, _operational_cache, _metrics_cache

    tier_config = CACHE_TIERS.get(tier, CACHE_TIERS["operational"])

    if tier == "static":
        if _static_cache is None:
            _static_cache = TTLCache(
                max_size=tier_config.max_size,
                default_ttl=tier_config.ttl_seconds,
            )
        return _static_cache

    elif tier == "config":
        if _config_cache is None:
            _config_cache = TTLCache(
                max_size=tier_config.max_size,
                default_ttl=tier_config.ttl_seconds,
            )
        return _config_cache

    elif tier == "metrics":
        if _metrics_cache is None:
            _metrics_cache = TTLCache(
                max_size=tier_config.max_size,
                default_ttl=tier_config.ttl_seconds,
            )
        return _metrics_cache

    else:  # operational (default)
        if _operational_cache is None:
            _operational_cache = TTLCache(
                max_size=tier_config.max_size,
                default_ttl=tier_config.ttl_seconds,
            )
        return _operational_cache


async def get_all_cache_stats() -> dict[str, Any]:
    """Get statistics for all cache tiers.

    Returns:
        Dictionary with stats for each cache tier
    """
    return {
        "static": get_cache("static").stats.to_dict(),
        "config": get_cache("config").stats.to_dict(),
        "operational": get_cache("operational").stats.to_dict(),
        "metrics": get_cache("metrics").stats.to_dict(),
    }


async def clear_all_caches() -> None:
    """Clear all cache tiers."""
    await get_cache("static").clear()
    await get_cache("config").clear()
    await get_cache("operational").clear()
    await get_cache("metrics").clear()
    logger.info("All caches cleared")
