"""
OCI SDK Client Manager with async support and connection pooling.

Provides a unified interface for OCI SDK clients with:
- Multiple authentication methods (config file, instance/resource principals)
- Client caching and lifecycle management
- Async context manager support
- Convenient properties for common clients

Environment Variables:
- OCI_CONFIG_FILE: Path to OCI config file (default: ~/.oci/config)
- OCI_PROFILE: Config profile name (default: DEFAULT)
- OCI_REGION: Override region
- OCI_CLI_AUTH: Authentication mode (resource_principal, instance_principal)
- COMPARTMENT_OCID: Default compartment for scoping
- ALLOW_MUTATIONS: Enable write operations (default: false)
"""
from __future__ import annotations

import asyncio
import os
import threading
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional, Tuple, Type, TypeVar

import oci
from oci.config import validate_config

from .observability import get_logger

T = TypeVar("T")


class OCIClientManager:
    """Manages OCI SDK clients with proper lifecycle and caching.
    
    This class provides:
    - Lazy client initialization
    - Thread-safe client caching
    - Multiple authentication method support
    - Convenient property access to common clients
    
    Example:
        async with get_oci_client() as client:
            instances = client.compute.list_instances(compartment_id).data
    """
    
    def __init__(
        self,
        profile: Optional[str] = None,
        region: Optional[str] = None,
        config_file: Optional[str] = None
    ):
        """Initialize the client manager.
        
        Args:
            profile: OCI config profile name (default: from env or DEFAULT)
            region: OCI region override
            config_file: Path to OCI config file
        """
        self._profile = profile or os.getenv("OCI_PROFILE", "DEFAULT")
        self._region = region or os.getenv("OCI_REGION")
        self._config_file = config_file or os.getenv(
            "OCI_CONFIG_FILE", 
            os.path.expanduser("~/.oci/config")
        )
        
        self._config: Optional[Dict[str, Any]] = None
        self._signer: Optional[Any] = None
        self._clients: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._initialized = False
        self._auth_method: Optional[str] = None
        
        self._logger = get_logger("oci-mcp.client")
    
    async def initialize(self) -> None:
        """Initialize OCI configuration asynchronously.
        
        This method determines the authentication method and loads
        the appropriate configuration. Safe to call multiple times.
        """
        if self._initialized:
            return
        
        # Run sync initialization in thread pool
        await asyncio.to_thread(self._initialize_sync)
    
    def _initialize_sync(self) -> None:
        """Synchronous initialization logic."""
        with self._lock:
            if self._initialized:
                return
            
            auth_mode = os.getenv("OCI_CLI_AUTH", "").lower()
            
            # 1. Try Resource Principals
            if auth_mode in ("resource_principal", "resource_principals", "resource") \
               or os.getenv("OCI_RESOURCE_PRINCIPAL_VERSION"):
                try:
                    self._init_resource_principal()
                    self._auth_method = "resource_principal"
                    self._initialized = True
                    self._logger.info(
                        "Initialized with Resource Principals",
                        region=self._config.get("region")
                    )
                    return
                except Exception as e:
                    if auth_mode:
                        raise RuntimeError(f"Failed to initialize Resource Principals: {e}") from e
            
            # 2. Try Config File
            try:
                self._init_config_file()
                self._auth_method = "config_file"
                self._initialized = True
                self._logger.info(
                    "Initialized with config file",
                    profile=self._profile,
                    region=self._config.get("region")
                )
                return
            except oci.exceptions.ConfigFileNotFound:
                pass
            except Exception as e:
                self._logger.warning(f"Config file failed: {e}")
            
            # 3. Try Instance Principals
            try:
                self._init_instance_principal()
                self._auth_method = "instance_principal"
                self._initialized = True
                self._logger.info(
                    "Initialized with Instance Principals",
                    region=self._config.get("region")
                )
                return
            except Exception as e:
                self._logger.warning(f"Instance Principals failed: {e}")
            
            raise RuntimeError(
                f"Failed to initialize OCI client. Tried: config file ({self._config_file}), "
                "Resource Principals, Instance Principals. Check OCI configuration."
            )
    
    def _init_config_file(self) -> None:
        """Initialize from OCI config file."""
        self._config = oci.config.from_file(
            file_location=self._config_file,
            profile_name=self._profile
        )
        validate_config(self._config)
        
        # Override region if provided
        if self._region:
            self._config["region"] = self._region
    
    def _init_resource_principal(self) -> None:
        """Initialize with Resource Principals."""
        from oci.auth.signers import get_resource_principals_signer
        
        self._signer = get_resource_principals_signer()
        region = self._region or getattr(self._signer, "region", None)
        
        if not region:
            raise RuntimeError("Resource Principals detected but OCI_REGION not set")
        
        self._config = {"region": region}
    
    def _init_instance_principal(self) -> None:
        """Initialize with Instance Principals."""
        from oci.auth.signers import InstancePrincipalsSecurityTokenSigner
        
        self._signer = InstancePrincipalsSecurityTokenSigner()
        self._config = {"region": self._signer.region}
    
    @property
    def is_initialized(self) -> bool:
        """Check if client manager is initialized."""
        return self._initialized
    
    @property
    def auth_method(self) -> Optional[str]:
        """Get the authentication method being used."""
        return self._auth_method
    
    @property
    def tenancy_id(self) -> str:
        """Get the tenancy OCID.
        
        For config file auth, this comes from the config.
        For principals, this requires additional lookup.
        """
        if not self._initialized:
            raise RuntimeError("Client not initialized. Call initialize() first.")
        
        # Override from environment
        env_tenancy = os.getenv("OCI_TENANCY_OCID")
        if env_tenancy:
            return env_tenancy
        
        # From config file
        if self._config and "tenancy" in self._config:
            return self._config["tenancy"]
        
        # For principals, we need to look it up
        # This is a simplified version - in production you might want to cache this
        raise ValueError(
            "Tenancy OCID not available. Set OCI_TENANCY_OCID environment variable."
        )
    
    @property
    def region(self) -> str:
        """Get the current region."""
        if not self._initialized:
            raise RuntimeError("Client not initialized. Call initialize() first.")
        
        if self._config and "region" in self._config:
            return self._config["region"]
        
        raise ValueError("Region not configured")
    
    @property
    def compartment_id(self) -> Optional[str]:
        """Get the default compartment OCID from environment."""
        return os.getenv("COMPARTMENT_OCID")
    
    @property
    def allow_mutations(self) -> bool:
        """Check if mutation operations are allowed."""
        return os.getenv("ALLOW_MUTATIONS", "false").lower() == "true"
    
    def get_client(
        self,
        client_class: Type[T],
        region: Optional[str] = None
    ) -> T:
        """Get or create a cached OCI client instance.
        
        Args:
            client_class: OCI SDK client class (e.g., oci.core.ComputeClient)
            region: Optional region override for this client
            
        Returns:
            Cached client instance
            
        Example:
            compute = client.get_client(oci.core.ComputeClient)
        """
        if not self._initialized:
            # Sync initialization for convenience
            self._initialize_sync()
        
        cache_key = f"{client_class.__module__}.{client_class.__name__}:{region or 'default'}"
        
        with self._lock:
            if cache_key in self._clients:
                return self._clients[cache_key]
            
            # Build client config
            client_config = dict(self._config) if self._config else {}
            if region:
                client_config["region"] = region
            
            # Build client kwargs
            kwargs: Dict[str, Any] = {}
            
            # Enable retries by default
            if os.getenv("OCI_ENABLE_RETRIES", "true").lower() == "true":
                kwargs["retry_strategy"] = oci.retry.DEFAULT_RETRY_STRATEGY
            
            # Timeout configuration
            timeout = os.getenv("OCI_REQUEST_TIMEOUT")
            if timeout:
                kwargs["timeout"] = float(timeout)
            
            # Create client with appropriate auth
            if self._signer is not None:
                client = client_class(client_config, signer=self._signer, **kwargs)
            else:
                client = client_class(client_config, **kwargs)
            
            self._clients[cache_key] = client
            return client
    
    # Convenience properties for common clients
    
    @property
    def identity(self) -> oci.identity.IdentityClient:
        """Get Identity client for IAM operations."""
        return self.get_client(oci.identity.IdentityClient)
    
    @property
    def compute(self) -> oci.core.ComputeClient:
        """Get Compute client for instance operations."""
        return self.get_client(oci.core.ComputeClient)
    
    @property
    def virtual_network(self) -> oci.core.VirtualNetworkClient:
        """Get VirtualNetwork client for VCN operations."""
        return self.get_client(oci.core.VirtualNetworkClient)
    
    @property
    def block_storage(self) -> oci.core.BlockstorageClient:
        """Get BlockStorage client for volume operations."""
        return self.get_client(oci.core.BlockstorageClient)
    
    @property
    def database(self) -> oci.database.DatabaseClient:
        """Get Database client for DB operations."""
        return self.get_client(oci.database.DatabaseClient)
    
    @property
    def usage_api(self) -> oci.usage_api.UsageapiClient:
        """Get UsageApi client for cost queries."""
        return self.get_client(oci.usage_api.UsageapiClient)
    
    @property
    def monitoring(self) -> oci.monitoring.MonitoringClient:
        """Get Monitoring client for metrics."""
        return self.get_client(oci.monitoring.MonitoringClient)
    
    @property
    def log_analytics(self) -> oci.log_analytics.LogAnalyticsClient:
        """Get LogAnalytics client for log queries."""
        return self.get_client(oci.log_analytics.LogAnalyticsClient)
    
    @property
    def logging(self) -> oci.logging.LoggingManagementClient:
        """Get LoggingManagement client."""
        return self.get_client(oci.logging.LoggingManagementClient)
    
    @property
    def resource_search(self) -> oci.resource_search.ResourceSearchClient:
        """Get ResourceSearch client for cross-resource queries."""
        return self.get_client(oci.resource_search.ResourceSearchClient)
    
    @property
    def budgets(self) -> oci.budget.BudgetClient:
        """Get Budget client for budget operations."""
        return self.get_client(oci.budget.BudgetClient)
    
    @property
    def cloud_guard(self) -> oci.cloud_guard.CloudGuardClient:
        """Get CloudGuard client for security operations."""
        return self.get_client(oci.cloud_guard.CloudGuardClient)
    
    def clear_cache(self) -> None:
        """Clear the client cache."""
        with self._lock:
            self._clients.clear()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the OCI connection.
        
        Returns:
            Health status with connection details
        """
        if not self._initialized:
            return {
                "healthy": False,
                "error": "Client not initialized"
            }
        
        try:
            # Try a simple API call
            identity = self.identity
            # Get tenancy info (if possible)
            try:
                tenancy = self.tenancy_id
            except ValueError:
                tenancy = "unknown"
            
            return {
                "healthy": True,
                "auth_method": self._auth_method,
                "region": self.region,
                "tenancy_id": tenancy[:20] + "..." if len(tenancy) > 25 else tenancy,
                "mutations_allowed": self.allow_mutations
            }
        except Exception as e:
            return {
                "healthy": False,
                "auth_method": self._auth_method,
                "error": str(e)
            }


# Global client instance
_client_manager: Optional[OCIClientManager] = None


def get_client_manager() -> OCIClientManager:
    """Get the global OCI client manager instance.
    
    Creates a new instance if one doesn't exist.
    """
    global _client_manager
    if _client_manager is None:
        _client_manager = OCIClientManager()
    return _client_manager


@asynccontextmanager
async def get_oci_client(
    profile: Optional[str] = None,
    region: Optional[str] = None
) -> AsyncGenerator[OCIClientManager, None]:
    """Async context manager for OCI client access.
    
    Args:
        profile: Optional OCI profile override
        region: Optional region override
        
    Yields:
        Initialized OCIClientManager
        
    Example:
        async with get_oci_client() as client:
            instances = await asyncio.to_thread(
                client.compute.list_instances,
                compartment_id
            )
    """
    if profile or region:
        # Create a new manager for custom config
        manager = OCIClientManager(profile=profile, region=region)
    else:
        # Use global manager
        manager = get_client_manager()
    
    await manager.initialize()
    yield manager


# Alias for direct access (convenience for tools that don't need async context)
oci_client_manager = get_client_manager()


# Convenience function for sync code
def get_oci_config(profile_name: Optional[str] = None) -> Dict[str, Any]:
    """Get OCI configuration dict (sync compatibility).
    
    This function is provided for backward compatibility with
    the original auth.py interface.
    
    Args:
        profile_name: OCI config profile name
        
    Returns:
        OCI config dictionary
    """
    manager = OCIClientManager(profile=profile_name)
    manager._initialize_sync()
    
    config = dict(manager._config) if manager._config else {}
    if manager._signer:
        config["signer"] = manager._signer
    
    return config
