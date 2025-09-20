import os
import json
import time
import threading
import hashlib
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CacheEntry:
    def __init__(self, data: Any, ttl_seconds: int = 3600):  # Default 1 hour TTL
        self.data = data
        self.timestamp = time.time()
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl_seconds

    def refresh_needed(self) -> bool:
        # Refresh if expired or older than 80% of TTL
        return self.is_expired() or (time.time() - self.timestamp > self.ttl_seconds * 0.8)

class MCPCache:
    def __init__(self, cache_dir: str = "/tmp/mcp-oci-cache", default_ttl: int = 3600):
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.lock = threading.Lock()

        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)

        # Start background refresh thread
        self.refresh_thread = threading.Thread(target=self._background_refresh, daemon=True)
        self.refresh_thread.start()

    def _get_cache_key(self, server_name: str, operation: str, params: Dict[str, Any]) -> str:
        """Generate a unique cache key for the operation"""
        key_data = {
            'server': server_name,
            'operation': operation,
            'params': params
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cache_file(self, cache_key: str) -> str:
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    def _load_from_disk(self, cache_key: str) -> Optional[CacheEntry]:
        """Load cached data from disk"""
        cache_file = self._get_cache_file(cache_key)
        if not os.path.exists(cache_file):
            return None

        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                entry = CacheEntry(
                    data=data['data'],
                    ttl_seconds=data.get('ttl_seconds', self.default_ttl)
                )
                entry.timestamp = data['timestamp']
                return entry if not entry.is_expired() else None
        except Exception as e:
            logger.warning(f"Failed to load cache from disk: {e}")
            return None

    def _save_to_disk(self, cache_key: str, entry: CacheEntry):
        """Save cached data to disk"""
        try:
            cache_file = self._get_cache_file(cache_key)
            data = {
                'data': entry.data,
                'timestamp': entry.timestamp,
                'ttl_seconds': entry.ttl_seconds
            }
            with open(cache_file, 'w') as f:
                try:
                    json.dump(data, f, default=str)
                except TypeError:
                    # Fallback: stringify non-serializable payloads
                    safe = dict(data)
                    safe['data'] = str(entry.data)
                    json.dump(safe, f)
        except Exception as e:
            logger.warning(f"Failed to save cache to disk: {e}")

    def get(self, server_name: str, operation: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached data if available and not expired"""
        cache_key = self._get_cache_key(server_name, operation, params)

        with self.lock:
            # Check memory cache first
            if cache_key in self.cache and not self.cache[cache_key].is_expired():
                return self.cache[cache_key].data

            # Check disk cache
            disk_entry = self._load_from_disk(cache_key)
            if disk_entry:
                self.cache[cache_key] = disk_entry
                return disk_entry.data

        return None

    def set(self, server_name: str, operation: str, params: Dict[str, Any], data: Any, ttl_seconds: Optional[int] = None):
        """Cache data with optional TTL"""
        cache_key = self._get_cache_key(server_name, operation, params)
        ttl = ttl_seconds or self.default_ttl

        entry = CacheEntry(data, ttl)

        with self.lock:
            self.cache[cache_key] = entry
            self._save_to_disk(cache_key, entry)

    def invalidate(self, server_name: str, operation: str, params: Dict[str, Any]):
        """Invalidate specific cache entry"""
        cache_key = self._get_cache_key(server_name, operation, params)

        with self.lock:
            if cache_key in self.cache:
                del self.cache[cache_key]

            cache_file = self._get_cache_file(cache_key)
            if os.path.exists(cache_file):
                os.remove(cache_file)

    def refresh_operation(self, server_name: str, operation: str, params: Dict[str, Any], fetch_func: Callable[[], Any], ttl_seconds: Optional[int] = None):
        """Refresh cached data by calling the fetch function"""
        try:
            logger.info(f"Refreshing cache for {server_name}.{operation}")
            data = fetch_func()
            self.set(server_name, operation, params, data, ttl_seconds=ttl_seconds)
            return data
        except Exception as e:
            logger.error(f"Failed to refresh cache for {server_name}.{operation}: {e}")
            return None

    def get_or_refresh(self, server_name: str, operation: str, params: Dict[str, Any], fetch_func: Callable[[], Any], force_refresh: bool = False, ttl_seconds: Optional[int] = None) -> Any:
        """Get cached data or refresh if needed"""
        cache_key = self._get_cache_key(server_name, operation, params)

        # Check if we need to refresh
        needs_refresh = force_refresh
        if not needs_refresh:
            with self.lock:
                if cache_key in self.cache:
                    needs_refresh = self.cache[cache_key].refresh_needed()
                else:
                    disk_entry = self._load_from_disk(cache_key)
                    if disk_entry:
                        needs_refresh = disk_entry.refresh_needed()
                    else:
                        needs_refresh = True  # No cache exists

        if needs_refresh:
            return self.refresh_operation(server_name, operation, params, fetch_func, ttl_seconds=ttl_seconds)
        else:
            return self.get(server_name, operation, params)

    def _background_refresh(self):
        """Background thread to periodically refresh expiring cache entries"""
        while True:
            try:
                time.sleep(300)  # Check every 5 minutes

                with self.lock:
                    to_refresh = []
                    for cache_key, entry in self.cache.items():
                        if entry.refresh_needed():
                            # We can't refresh here without knowing the fetch function
                            # Just mark for potential cleanup if expired
                            if entry.is_expired():
                                logger.debug(f"Removing expired cache entry: {cache_key}")
                                # Remove from memory (disk will be checked on next access)
                                del self.cache[cache_key]

            except Exception as e:
                logger.error(f"Background refresh error: {e}")
                time.sleep(60)  # Wait a minute before retrying

# Global cache instance
_cache_instance = None

def get_cache() -> MCPCache:
    """Get the global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        cache_dir = os.getenv("MCP_CACHE_DIR", "/tmp/mcp-oci-cache")
        default_ttl = int(os.getenv("MCP_CACHE_TTL", "3600"))  # 1 hour default
        _cache_instance = MCPCache(cache_dir, default_ttl)
    return _cache_instance
