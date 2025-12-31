# Building OCI MCP Servers - Reference Guide

**Version:** 1.0.0
**Last Updated:** 2025-12-31

This guide provides patterns and best practices for building MCP servers that integrate with Oracle Cloud Infrastructure.

---

## 1. Project Structure

```
my-oci-mcp-server/
├── pyproject.toml            # UV/pip dependencies
├── src/
│   └── mcp_server_myservice/
│       ├── __init__.py
│       ├── server.py         # FastMCP entry point
│       ├── config.py         # Pydantic settings
│       ├── core/             # Core infrastructure
│       │   ├── __init__.py   # Unified exports
│       │   ├── client.py     # OCI client manager
│       │   ├── errors.py     # Error handling
│       │   ├── formatters.py # Response formatters
│       │   ├── models.py     # Shared Pydantic models
│       │   ├── cache.py      # Caching layer
│       │   └── observability.py
│       ├── tools/            # Domain tools
│       │   └── myservice/
│       │       ├── __init__.py
│       │       ├── models.py
│       │       ├── tools.py
│       │       ├── formatters.py
│       │       └── SKILL.md
│       └── skills/           # High-level workflows
│           ├── __init__.py
│           ├── executor.py
│           └── my_skill.py
├── tests/
└── docs/
```

---

## 2. Server Setup

### 2.1 Dependencies (pyproject.toml)

```toml
[project]
name = "mcp-server-myservice"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.0.0",
    "oci>=2.100.0",
    "pydantic>=2.0.0",
    "structlog>=24.0.0",
]

[project.scripts]
mcp-server-myservice = "mcp_server_myservice.server:main"
```

### 2.2 Server Entry Point

```python
# server.py
from contextlib import asynccontextmanager
from fastmcp import FastMCP, Context

from .config import get_config
from .core import get_client_manager, get_logger, get_cache

config = get_config()
logger = get_logger("my-mcp")

@asynccontextmanager
async def app_lifespan(server: FastMCP):
    """Initialize resources on startup."""
    logger.info("Starting MCP Server")

    # Initialize OCI client
    client_manager = get_client_manager()
    await client_manager.initialize()

    # Initialize caches
    _ = get_cache("operational")

    yield {"oci_client": client_manager}

    # Cleanup
    logger.info("Shutting down")

mcp = FastMCP(
    name=config.server.name,
    instructions="Use oci_ping to check health, oci_search_tools to find tools.",
    lifespan=app_lifespan,
)

# Register tools
from .tools.myservice import register_myservice_tools
register_myservice_tools(mcp)

def main():
    mcp.run()
```

---

## 3. Tool Implementation

### 3.1 Input Models

```python
# tools/myservice/models.py
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"

class ListResourcesInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    compartment_id: str = Field(
        ...,
        description="Compartment OCID"
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum results to return"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN
    )
```

### 3.2 Tool Registration

```python
# tools/myservice/tools.py
from fastmcp import FastMCP, Context
from .models import ListResourcesInput, ResponseFormat
from .formatters import MyServiceFormatter

def register_myservice_tools(mcp: FastMCP) -> None:

    @mcp.tool(
        name="oci_myservice_list_resources",
        annotations={
            "title": "List My Resources",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def list_resources(params: ListResourcesInput, ctx: Context) -> str:
        """
        List resources in a compartment.

        Returns resources with their current state.

        Args:
            params: ListResourcesInput with compartment_id and limit

        Returns:
            Resource list in requested format
        """
        await ctx.report_progress(0.1, "Connecting...")

        try:
            from mcp_server_myservice.core import get_client_manager
            client = await get_client_manager()

            await ctx.report_progress(0.3, "Fetching resources...")
            # Call OCI API
            response = await client.list_resources(params.compartment_id)

            await ctx.report_progress(0.9, "Formatting...")

            if params.response_format == ResponseFormat.JSON:
                return MyServiceFormatter.to_json(response)
            return MyServiceFormatter.to_markdown(response)

        except Exception as e:
            from mcp_server_myservice.core import handle_oci_error
            error = handle_oci_error(e, "listing resources")
            return error.format(params.response_format)
```

### 3.3 Tool Naming Convention

Follow this pattern: `oci_{domain}_{action}_{resource}`

| Pattern | Example | Description |
|---------|---------|-------------|
| `oci_{domain}_list_{resource}` | `oci_compute_list_instances` | List resources |
| `oci_{domain}_get_{resource}` | `oci_compute_get_instance` | Get single resource |
| `oci_{domain}_{action}_{resource}` | `oci_compute_start_instance` | Perform action |

---

## 4. Tool Aliases (Backward Compatibility)

When adding aliases for agents using shorter names:

```python
# server.py - Add after tool registration

# Import models early for type hints
from .tools.myservice.models import ListResourcesInput

@mcp.tool(
    name="list_resources",  # Short alias
    annotations={"title": "List Resources (Alias)", ...}
)
async def list_resources_alias(params: ListResourcesInput, ctx: Context) -> str:
    """Alias for oci_myservice_list_resources."""
    # Implementation (same as canonical tool)
    ...
```

**Important:** Import Pydantic models at module top-level for type hint resolution.

---

## 5. Caching Layer

### 5.1 Cache Tiers

```python
# core/cache.py
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional
import time
import asyncio

class CacheTier(str, Enum):
    STATIC = "static"       # TTL: 1 hour (shapes, regions)
    CONFIG = "config"       # TTL: 5 min (compartments)
    OPERATIONAL = "operational"  # TTL: 1 min (instances)
    METRICS = "metrics"     # TTL: 30 sec (real-time)

CACHE_TIERS = {
    CacheTier.STATIC: {"ttl": 3600, "max_size": 500},
    CacheTier.CONFIG: {"ttl": 300, "max_size": 500},
    CacheTier.OPERATIONAL: {"ttl": 60, "max_size": 1000},
    CacheTier.METRICS: {"ttl": 30, "max_size": 2000},
}

@dataclass
class CacheEntry:
    value: Any
    expires_at: float

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

class TTLCache:
    def __init__(self, tier: CacheTier):
        config = CACHE_TIERS[tier]
        self._ttl = config["ttl"]
        self._max_size = config["max_size"]
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired:
                return entry.value
            return None

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._cache[key] = CacheEntry(
                value=value,
                expires_at=time.time() + self._ttl
            )
```

### 5.2 Cache Decorator

```python
def cached(tier: str = "operational", ttl: Optional[int] = None):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache(tier)
            key = generate_cache_key(func.__name__, args, kwargs)

            cached_value = await cache.get(key)
            if cached_value is not None:
                return cached_value

            result = await func(*args, **kwargs)
            await cache.set(key, result)
            return result
        return wrapper
    return decorator

# Usage
@cached(tier="config", ttl=300)
async def get_compartments(tenancy_id: str):
    return await fetch_compartments(tenancy_id)
```

---

## 6. Shared Memory (Inter-Agent Communication)

For multi-agent scenarios:

```python
# core/shared_memory.py
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
import asyncio

class EventType(str, Enum):
    FINDING = "finding"
    RECOMMENDATION = "recommendation"
    STATUS = "status"

@dataclass
class SharedEvent:
    agent_id: str
    event_type: EventType
    category: str
    message: str
    timestamp: float
    metadata: dict = field(default_factory=dict)

class InMemorySharedStore:
    """In-process shared memory for single-server deployments."""

    def __init__(self):
        self._events: List[SharedEvent] = []
        self._lock = asyncio.Lock()

    async def publish_event(self, event: SharedEvent) -> None:
        async with self._lock:
            self._events.append(event)

    async def get_events(
        self,
        event_type: Optional[EventType] = None,
        category: Optional[str] = None
    ) -> List[SharedEvent]:
        async with self._lock:
            events = self._events
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            if category:
                events = [e for e in events if e.category == category]
            return events

# Convenience functions
async def share_finding(agent_id: str, category: str, message: str, **metadata):
    store = get_shared_store()
    await store.publish_event(SharedEvent(
        agent_id=agent_id,
        event_type=EventType.FINDING,
        category=category,
        message=message,
        timestamp=time.time(),
        metadata=metadata
    ))
```

---

## 7. Skills Framework

### 7.1 Skill Executor

```python
# skills/executor.py
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

@dataclass
class ToolCallResult:
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None

class SkillExecutor:
    """Orchestrates multi-tool skill execution."""

    def __init__(self, mcp_context, agent_id: str):
        self._ctx = mcp_context
        self._agent_id = agent_id
        self._tool_calls: List[ToolCallResult] = []

    async def report_progress(self, progress: float, message: str) -> None:
        await self._ctx.report_progress(progress, message)

    async def call_tool(self, tool_name: str, params: dict) -> Any:
        """Call another registered tool."""
        try:
            # Get tool from registry and call it
            result = await self._execute_tool(tool_name, params)
            self._tool_calls.append(ToolCallResult(
                tool_name=tool_name,
                success=True,
                result=result
            ))
            return result
        except Exception as e:
            self._tool_calls.append(ToolCallResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=str(e)
            ))
            raise

    async def analyze(self, data: dict, prompt: str) -> str:
        """Use LLM sampling for analysis (if available)."""
        # Uses MCP sampling capability
        pass
```

### 7.2 Skill Registration

```python
# skills/__init__.py
from typing import Dict, Type

_skill_registry: Dict[str, Type] = {}

def register_skill(name: str):
    """Decorator to register a skill class."""
    def decorator(cls):
        _skill_registry[name] = cls
        return cls
    return decorator

def get_skill_registry():
    return _skill_registry

def list_skills():
    return list(_skill_registry.keys())
```

### 7.3 Skill Implementation

```python
# skills/troubleshoot.py
from . import register_skill
from .executor import SkillExecutor

@register_skill("troubleshoot_instance")
class TroubleshootInstanceSkill:
    """Multi-step instance troubleshooting."""

    async def execute(self, executor: SkillExecutor, params: dict) -> str:
        await executor.report_progress(0.1, "Fetching instance...")

        instance = await executor.call_tool(
            "oci_compute_get_instance",
            {"instance_id": params["instance_id"]}
        )

        await executor.report_progress(0.4, "Fetching metrics...")
        metrics = await executor.call_tool(
            "oci_observability_get_instance_metrics",
            {"instance_id": params["instance_id"]}
        )

        await executor.report_progress(0.7, "Analyzing...")
        analysis = await executor.analyze(
            data={"instance": instance, "metrics": metrics},
            prompt="Analyze health and provide recommendations"
        )

        return self.format_report(instance, metrics, analysis)
```

---

## 8. Error Handling

```python
# core/errors.py
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class ErrorCategory(str, Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"
    VALIDATION = "validation"
    SERVICE = "service"
    TIMEOUT = "timeout"

@dataclass
class OCIError:
    category: ErrorCategory
    message: str
    suggestion: str
    details: dict

def handle_oci_error(exception: Exception, context: str) -> OCIError:
    """Convert OCI exceptions to structured errors."""

    if hasattr(exception, 'status'):
        status = exception.status
        if status == 401:
            return OCIError(
                category=ErrorCategory.AUTHENTICATION,
                message=f"Authentication failed: {context}",
                suggestion="Check OCI credentials and config file",
                details={"status": status}
            )
        elif status == 403:
            return OCIError(
                category=ErrorCategory.AUTHORIZATION,
                message=f"Access denied: {context}",
                suggestion="Verify IAM policies grant required permissions",
                details={"status": status}
            )
        elif status == 404:
            return OCIError(
                category=ErrorCategory.NOT_FOUND,
                message=f"Resource not found: {context}",
                suggestion="Verify the OCID is correct and resource exists",
                details={"status": status}
            )

    return OCIError(
        category=ErrorCategory.SERVICE,
        message=f"Error during {context}: {str(exception)}",
        suggestion="Check OCI service status and retry",
        details={}
    )
```

---

## 9. Testing

```bash
# Install dependencies
uv sync

# Run server locally
uv run python -m mcp_server_myservice.server

# Test imports
uv run python -c "from mcp_server_myservice.server import mcp; print('OK')"

# Run tests
uv run pytest tests/

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/
```

---

## 10. Best Practices

1. **Progressive Disclosure**: Start with discovery tools (`ping`, `list_domains`, `search_tools`)
2. **Dual Formats**: Support both markdown (context-efficient) and JSON (machine-readable)
3. **Report Progress**: Use `ctx.report_progress()` for operations >1s
4. **Handle Errors**: Return structured errors with actionable suggestions
5. **Cache Appropriately**: Use tiered caching based on data volatility
6. **Document Tools**: Each domain should have a SKILL.md file
7. **Type Everything**: Use Pydantic models for all inputs/outputs
8. **Guard Mutations**: Require `ALLOW_MUTATIONS=true` for write operations

---

## 11. Related Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Overall architecture
- [SKILL.md](../SKILL.md) - Skill definitions for AI agents
- [BUILD_OCI_AGENTS.md](./BUILD_OCI_AGENTS.md) - Building OCI agents
