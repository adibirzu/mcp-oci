"""
Core infrastructure modules for OCI MCP Server.

This package contains:
- client: OCI SDK wrapper with async support
- errors: Structured error handling
- formatters: Response formatting utilities
- models: Base Pydantic models
- observability: OCI APM and Logging integration
- pagination: Pagination utilities
- cache: High-performance TTL-based caching
- shared_memory: Inter-agent communication (ATP or in-memory)
"""

# Cache module
from .cache import (
    CACHE_TIERS,
    CacheEntry,
    CacheStats,
    CacheTier,
    RedisTTLCache,
    TTLCache,
    batch_get,
    batch_set,
    cached,
    clear_all_caches,
    generate_cache_key,
    get_all_cache_stats,
    get_cache,
    prefetch_compartments,
)
from .client import OCIClientManager, get_client_manager, get_oci_client, get_oci_config
from .errors import (
    ErrorCategory,
    OCIError,
    create_not_found_error,
    create_validation_error,
    format_error_response,
    handle_oci_error,
)
from .formatters import (
    Formatter,
    JSONFormatter,
    MarkdownFormatter,
    ResponseFormat,
    format_response,
    format_success_response,
)
from .models import (
    BaseSkillInput,
    BaseToolInput,
    Granularity,
    HealthStatus,
    OCIContextInput,
    OCIPaginatedInput,
    PaginatedInput,
    PaginatedOutput,
    ServerManifest,
    SkillMetadata,
    SkillProgress,
    SkillResult,
    # Skill Framework
    SkillStep,
    SortOrder,
    TenancyInput,
    TimeRangeInput,
    ToolMetadata,
)
from .observability import (
    check_observability_health,
    get_logger,
    init_observability,
)

# Shared memory module
from .shared_memory import (
    AgentInfo,
    AgentState,
    ATPSharedStore,
    ConversationEntry,
    EventType,
    InMemorySharedStore,
    SharedContext,
    SharedEvent,
    get_shared_findings,
    get_shared_recommendations,
    get_shared_store,
    share_finding,
    share_recommendation,
)

__all__ = [
    # Errors
    "ErrorCategory",
    "OCIError",
    "handle_oci_error",
    "format_error_response",
    # Formatters
    "ResponseFormat",
    "Formatter",
    "MarkdownFormatter",
    "JSONFormatter",
    "format_response",
    "format_success_response",
    "create_validation_error",
    "create_not_found_error",
    # Models
    "Granularity",
    "SortOrder",
    "BaseToolInput",
    "OCIContextInput",
    "TenancyInput",
    "TimeRangeInput",
    "PaginatedInput",
    "OCIPaginatedInput",
    "PaginatedOutput",
    "ToolMetadata",
    "HealthStatus",
    "ServerManifest",
    # Skill Framework
    "SkillStep",
    "SkillProgress",
    "BaseSkillInput",
    "SkillMetadata",
    "SkillResult",
    # Client
    "OCIClientManager",
    "get_client_manager",
    "get_oci_client",
    "get_oci_config",
    # Observability
    "get_logger",
    "init_observability",
    "check_observability_health",
    # Cache
    "TTLCache",
    "RedisTTLCache",
    "CacheEntry",
    "CacheStats",
    "CacheTier",
    "CACHE_TIERS",
    "get_cache",
    "get_all_cache_stats",
    "clear_all_caches",
    "generate_cache_key",
    "cached",
    "batch_get",
    "batch_set",
    "prefetch_compartments",
    # Shared Memory
    "EventType",
    "AgentState",
    "AgentInfo",
    "SharedEvent",
    "SharedContext",
    "ConversationEntry",
    "InMemorySharedStore",
    "ATPSharedStore",
    "get_shared_store",
    "share_finding",
    "share_recommendation",
    "get_shared_findings",
    "get_shared_recommendations",
]
