# Building OCI Agents - Reference Guide

**Version:** 1.0.0
**Last Updated:** 2025-12-31

This guide provides patterns and best practices for building AI agents that interact with OCI MCP servers.

---

## 1. Overview

OCI Agents are AI-powered assistants that use the OCI MCP Server to manage Oracle Cloud Infrastructure. They can:

- Discover and execute OCI tools
- Perform multi-step workflows using skills
- Share findings with other agents
- Provide intelligent analysis and recommendations

---

## 2. Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         OCI Agent                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Tool Discovery │  │  Skill Executor │  │ Shared Memory   │ │
│  │  oci_search_*   │  │  Multi-step     │  │ Inter-agent     │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
│           └────────────────────┼────────────────────┘          │
│                                │                                │
│  ┌─────────────────────────────▼─────────────────────────────┐ │
│  │                    Agent Context                          │ │
│  │   LLM Sampling │ Conversation Memory │ Progress Tracking  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────┬─────────────────────────────┘
                                    │ MCP Protocol
┌───────────────────────────────────▼─────────────────────────────┐
│                      OCI MCP Server                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Agent Components

### 3.1 Agent Context

```python
# skills/agent.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

@dataclass
class Message:
    role: MessageRole
    content: str
    metadata: dict = field(default_factory=dict)

@dataclass
class ConversationMemory:
    """Maintains conversation history for context."""
    messages: List[Message] = field(default_factory=list)
    max_messages: int = 50

    def add(self, role: MessageRole, content: str, **metadata):
        self.messages.append(Message(role, content, metadata))
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get_context(self, last_n: int = 10) -> List[Message]:
        return self.messages[-last_n:]

@dataclass
class AgentContext:
    """Context for agent execution."""
    agent_id: str
    memory: ConversationMemory = field(default_factory=ConversationMemory)
    sampling_client: Optional[Any] = None  # MCP sampling client
    tool_registry: Dict[str, Any] = field(default_factory=dict)

    async def analyze(self, data: dict, prompt: str) -> str:
        """Use LLM to analyze data and generate insights."""
        if not self.sampling_client:
            return self._basic_analysis(data)

        messages = [
            {"role": "system", "content": "You are an OCI infrastructure analyst."},
            {"role": "user", "content": f"{prompt}\n\nData:\n{data}"}
        ]

        response = await self.sampling_client.create_message(
            messages=messages,
            max_tokens=2000
        )
        return response.content
```

### 3.2 Sampling Client

```python
class SamplingClient:
    """Client for MCP LLM sampling capability."""

    def __init__(self, mcp_context):
        self._ctx = mcp_context

    async def create_message(
        self,
        messages: List[dict],
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Any:
        """Create a message using LLM sampling."""
        # Uses MCP's sampling capability
        return await self._ctx.sample(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
```

---

## 4. Tool Discovery Pattern

Agents should use progressive disclosure to find tools:

```python
class OCIAgentToolDiscovery:
    """Helper for discovering OCI tools."""

    def __init__(self, executor):
        self._executor = executor
        self._tool_cache = {}

    async def discover_tools(self, query: str = None) -> dict:
        """Discover available tools."""

        # Step 1: List available domains
        domains = await self._executor.call_tool("oci_list_domains", {})

        # Step 2: Search for specific tools if query provided
        if query:
            tools = await self._executor.call_tool("oci_search_tools", {
                "query": query,
                "detail_level": "summary"
            })
            return {"domains": domains, "matching_tools": tools}

        return {"domains": domains}

    async def get_tool_schema(self, tool_name: str) -> dict:
        """Get input schema for a specific tool."""
        tools = await self._executor.call_tool("oci_search_tools", {
            "query": tool_name,
            "detail_level": "full"
        })
        return tools
```

### Tool Name Mapping

Agents may use either canonical or alias names:

| Canonical Name | Alias |
|----------------|-------|
| `oci_compute_list_instances` | `list_instances` |
| `oci_compute_start_instance` | `start_instance` |
| `oci_compute_stop_instance` | `stop_instance` |
| `oci_compute_restart_instance` | `restart_instance` |
| `oci_observability_get_instance_metrics` | `get_instance_metrics` |

---

## 5. Skill Execution

### 5.1 Using the Skill Executor

```python
from mcp_server_oci.skills import SkillExecutor, ToolCallResult

class MyOCIAgent:
    """Example OCI agent implementation."""

    def __init__(self, mcp_context):
        self.context = AgentContext(agent_id="my-agent")
        self.executor = SkillExecutor(mcp_context, "my-agent")

    async def troubleshoot_instance(self, instance_id: str) -> str:
        """Run instance troubleshooting workflow."""

        # Step 1: Get instance details
        await self.executor.report_progress(0.1, "Fetching instance...")
        instance = await self.executor.call_tool(
            "oci_compute_get_instance",
            {"instance_id": instance_id, "response_format": "json"}
        )

        # Step 2: Get metrics
        await self.executor.report_progress(0.3, "Fetching metrics...")
        metrics = await self.executor.call_tool(
            "get_instance_metrics",  # Using alias
            {"instance_id": instance_id, "response_format": "json"}
        )

        # Step 3: Analyze with LLM
        await self.executor.report_progress(0.6, "Analyzing...")
        analysis = await self.context.analyze(
            data={"instance": instance, "metrics": metrics},
            prompt="Analyze this instance and identify any issues"
        )

        # Step 4: Generate recommendations
        await self.executor.report_progress(0.9, "Generating report...")
        return self._format_report(instance, metrics, analysis)

    async def perform_security_audit(self, compartment_id: str) -> str:
        """Run security audit workflow."""

        await self.executor.report_progress(0.1, "Starting security audit...")

        # Use the skill tool directly
        result = await self.executor.call_tool(
            "oci_security_audit",
            {"compartment_id": compartment_id}
        )

        return result
```

### 5.2 Chaining Skills

```python
async def comprehensive_health_check(self, compartment_id: str) -> str:
    """Chain multiple skills for comprehensive health check."""

    results = {}

    # Run multiple skills in sequence
    skills = [
        ("security_audit", {"compartment_id": compartment_id}),
        ("cost_analysis", {"compartment_id": compartment_id}),
    ]

    for skill_name, params in skills:
        await self.executor.report_progress(
            0.2 + (skills.index((skill_name, params)) * 0.3),
            f"Running {skill_name}..."
        )

        try:
            result = await self.executor.call_tool(
                f"oci_skill_{skill_name}",
                params
            )
            results[skill_name] = {"success": True, "result": result}
        except Exception as e:
            results[skill_name] = {"success": False, "error": str(e)}

    return self._format_comprehensive_report(results)
```

---

## 6. Inter-Agent Communication

### 6.1 Sharing Findings

```python
from mcp_server_oci.core import (
    share_finding,
    share_recommendation,
    get_shared_findings,
    get_shared_recommendations
)

class CollaborativeAgent:
    """Agent that shares findings with other agents."""

    async def analyze_and_share(self, resource_id: str):
        """Analyze resource and share findings."""

        # Perform analysis
        findings = await self._analyze_resource(resource_id)

        # Share each finding
        for finding in findings:
            await share_finding(
                agent_id=self.agent_id,
                category=finding["category"],
                severity=finding["severity"],
                message=finding["message"],
                resource_id=resource_id
            )

        # Share recommendations
        recommendations = await self._generate_recommendations(findings)
        for rec in recommendations:
            await share_recommendation(
                agent_id=self.agent_id,
                category=rec["category"],
                priority=rec["priority"],
                message=rec["recommendation"]
            )

    async def get_peer_findings(self, category: str = None) -> list:
        """Get findings from other agents."""
        return await get_shared_findings(category=category)
```

### 6.2 Agent Coordination

```python
class CoordinatedAgentTeam:
    """Coordinates multiple specialized agents."""

    def __init__(self):
        self.agents = {
            "security": SecurityAgent(),
            "performance": PerformanceAgent(),
            "cost": CostAgent(),
        }

    async def comprehensive_audit(self, compartment_id: str) -> dict:
        """Run coordinated audit with multiple agents."""

        results = {}

        # Each agent performs its specialty
        for name, agent in self.agents.items():
            result = await agent.audit(compartment_id)
            results[name] = result

            # Agent shares findings to shared memory
            # Other agents can access these findings

        # Collect shared findings for final report
        all_findings = await get_shared_findings()

        return self._synthesize_report(results, all_findings)
```

---

## 7. Caching Integration

Agents should leverage the server's caching:

```python
from mcp_server_oci.core import get_cache, cached

class CacheAwareAgent:
    """Agent that uses caching for efficiency."""

    async def get_compartments(self, tenancy_id: str) -> list:
        """Get compartments with caching."""

        # Check cache first
        cache = get_cache("config")  # 5-minute TTL
        cache_key = f"compartments:{tenancy_id}"

        cached_value = await cache.get(cache_key)
        if cached_value:
            return cached_value

        # Fetch from API
        compartments = await self._fetch_compartments(tenancy_id)

        # Store in cache
        await cache.set(cache_key, compartments)

        return compartments

    @cached(tier="operational", ttl=60)
    async def get_instance_status(self, instance_id: str) -> dict:
        """Get instance status with automatic caching."""
        return await self.executor.call_tool(
            "oci_compute_get_instance",
            {"instance_id": instance_id}
        )
```

---

## 8. Error Handling in Agents

```python
from mcp_server_oci.core import OCIError, ErrorCategory

class RobustAgent:
    """Agent with robust error handling."""

    async def safe_tool_call(self, tool_name: str, params: dict) -> dict:
        """Call tool with error handling."""

        try:
            result = await self.executor.call_tool(tool_name, params)
            return {"success": True, "result": result}

        except Exception as e:
            # Categorize and handle error
            if "authentication" in str(e).lower():
                return {
                    "success": False,
                    "error": "Authentication failed",
                    "suggestion": "Check OCI credentials",
                    "retry": False
                }
            elif "rate limit" in str(e).lower():
                return {
                    "success": False,
                    "error": "Rate limited",
                    "suggestion": "Wait and retry",
                    "retry": True,
                    "retry_after": 30
                }
            else:
                return {
                    "success": False,
                    "error": str(e),
                    "retry": True
                }

    async def call_with_retry(
        self,
        tool_name: str,
        params: dict,
        max_retries: int = 3
    ) -> dict:
        """Call tool with automatic retry."""

        for attempt in range(max_retries):
            result = await self.safe_tool_call(tool_name, params)

            if result["success"]:
                return result

            if not result.get("retry", False):
                return result

            # Wait before retry
            wait_time = result.get("retry_after", 2 ** attempt)
            await asyncio.sleep(wait_time)

        return result  # Return last failure
```

---

## 9. Analysis Patterns

### 9.1 Diagnostic Analysis

```python
from mcp_server_oci.skills import create_diagnostic_request

class DiagnosticAgent:
    """Agent for infrastructure diagnostics."""

    async def diagnose_instance_issue(self, instance_id: str) -> str:
        """Diagnose issues with an instance."""

        # Gather data
        data = {
            "instance": await self._get_instance(instance_id),
            "metrics": await self._get_metrics(instance_id),
            "logs": await self._get_recent_logs(instance_id),
            "network": await self._get_network_status(instance_id),
        }

        # Create diagnostic request
        request = create_diagnostic_request(
            symptoms=["high latency", "connection timeouts"],
            resource_type="compute_instance",
            data=data
        )

        # Analyze with LLM
        diagnosis = await self.context.analyze(
            data=request.to_dict(),
            prompt="""
            Analyze this compute instance diagnostic data.
            Identify:
            1. Root cause of the symptoms
            2. Contributing factors
            3. Recommended remediation steps
            """
        )

        return diagnosis
```

### 9.2 Recommendation Generation

```python
from mcp_server_oci.skills import create_recommendation_request

class AdvisorAgent:
    """Agent for generating optimization recommendations."""

    async def generate_cost_recommendations(
        self,
        compartment_id: str
    ) -> list:
        """Generate cost optimization recommendations."""

        # Get cost data
        cost_data = await self.executor.call_tool(
            "oci_cost_by_service",
            {"compartment_id": compartment_id}
        )

        # Get resource utilization
        utilization = await self._get_resource_utilization(compartment_id)

        # Generate recommendations
        request = create_recommendation_request(
            category="cost_optimization",
            context={
                "costs": cost_data,
                "utilization": utilization
            }
        )

        recommendations = await self.context.analyze(
            data=request.to_dict(),
            prompt="""
            Analyze cost and utilization data.
            Generate specific, actionable recommendations for:
            1. Right-sizing opportunities
            2. Reserved capacity candidates
            3. Unused resource cleanup
            """
        )

        return self._parse_recommendations(recommendations)
```

---

## 10. Best Practices

### 10.1 Tool Selection

| Scenario | Recommended Approach |
|----------|---------------------|
| Quick status check | Use alias (`list_instances`) |
| Detailed analysis | Use canonical name with JSON format |
| Multi-step workflow | Use SkillExecutor |
| Frequent queries | Enable caching |

### 10.2 Performance

1. **Use appropriate cache tiers** based on data volatility
2. **Report progress** for operations >1 second
3. **Batch operations** when possible
4. **Use pagination** for large result sets

### 10.3 Reliability

1. **Implement retry logic** for transient failures
2. **Handle rate limits** gracefully
3. **Validate inputs** before tool calls
4. **Log important operations** for debugging

### 10.4 Security

1. **Never hardcode credentials** - use environment variables
2. **Guard mutations** - require explicit confirmation
3. **Audit sensitive operations** - log who, what, when
4. **Validate OCIDs** before operations

---

## 11. Example: Complete Agent Implementation

```python
# agents/infrastructure_agent.py
from mcp_server_oci.skills import (
    SkillExecutor,
    AgentContext,
    SamplingClient,
)
from mcp_server_oci.core import (
    get_cache,
    share_finding,
    get_shared_store,
)

class InfrastructureAgent:
    """Complete OCI infrastructure management agent."""

    def __init__(self, mcp_context):
        self.context = AgentContext(
            agent_id="infra-agent",
            sampling_client=SamplingClient(mcp_context)
        )
        self.executor = SkillExecutor(mcp_context, "infra-agent")
        self._store = get_shared_store()

    async def run(self, task: str, params: dict) -> str:
        """Execute a task."""

        # Map tasks to handlers
        handlers = {
            "troubleshoot": self._troubleshoot,
            "audit": self._security_audit,
            "optimize": self._cost_optimize,
            "monitor": self._health_monitor,
        }

        handler = handlers.get(task)
        if not handler:
            return f"Unknown task: {task}"

        return await handler(params)

    async def _troubleshoot(self, params: dict) -> str:
        instance_id = params["instance_id"]

        # Discover what tools are available
        tools = await self.executor.call_tool(
            "oci_search_tools",
            {"query": "instance", "detail_level": "name_only"}
        )

        # Execute troubleshooting workflow
        instance = await self.executor.call_tool(
            "oci_compute_get_instance",
            {"instance_id": instance_id}
        )

        metrics = await self.executor.call_tool(
            "get_instance_metrics",
            {"instance_id": instance_id}
        )

        # Analyze
        analysis = await self.context.analyze(
            data={"instance": instance, "metrics": metrics},
            prompt="Identify any issues and recommendations"
        )

        # Share findings
        await share_finding(
            agent_id=self.context.agent_id,
            category="troubleshooting",
            severity="info",
            message=f"Analyzed instance {instance_id}"
        )

        return analysis

    async def _security_audit(self, params: dict) -> str:
        return await self.executor.call_tool(
            "oci_security_audit",
            params
        )

    async def _cost_optimize(self, params: dict) -> str:
        # Get cost breakdown
        costs = await self.executor.call_tool(
            "oci_cost_by_service",
            params
        )

        # Analyze and recommend
        return await self.context.analyze(
            data={"costs": costs},
            prompt="Generate cost optimization recommendations"
        )

    async def _health_monitor(self, params: dict) -> str:
        # Check instance health
        instances = await self.executor.call_tool(
            "list_instances",
            {"compartment_id": params["compartment_id"]}
        )

        # Check for unhealthy instances
        return self._format_health_report(instances)
```

---

## 12. Related Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Overall architecture
- [SKILL.md](../SKILL.md) - Skill definitions
- [BUILD_MCP_SERVER.md](./BUILD_MCP_SERVER.md) - Building MCP servers
