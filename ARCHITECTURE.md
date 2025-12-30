# OCI MCP Server Architecture Analysis & Modernization Plan

## 1. Executive Summary
This document outlines the architectural transformation of the OCI MCP server from a monolithic, server-per-domain model to a modern, unified, skill-centric FastMCP implementation. The goal is to align with "Anthropic's code execution with MCP best practices," emphasizing progressive disclosure, context efficiency, and high-level agent skills.

## 2. Current State Analysis

### 2.1 Tool Inventory & Organization
The existing implementation (`../mcp-oci`) follows a **Domain-Siloed Pattern**:
- **Structure:** Multiple independent servers (`compute`, `network`, `db`, etc.), each running as a separate process.
- **Inventory:**
    - **Compute:** `list_instances`, `create_instance`, `start/stop/restart`, `get_metrics`, `get_cost`.
    - **Observability:** `get_metrics`, `get_logs`.
    - **Others:** `network`, `security`, `cost`, `inventory`, `blockstorage`, `loadbalancer`.
- **Definition:** Tools are defined inline within monolithic `server.py` files using `FastMCP`.

### 2.2 Authentication & Transport
- **Authentication:**
    - Relies on standard OCI SDK config (`~/.oci/config`) or Instance Principals.
    - Managed via `mcp_oci_common.session.get_client`.
    - Context (Profile/Region) is injected via Environment Variables (`OCI_PROFILE`, `OCI_REGION`).
- **Transport:**
    - Standard Input/Output (`stdio`) configured in `mcp.json`.
    - No SSE (Server-Sent Events) support visible in the main configuration.

### 2.3 Response Patterns
- **Format:** JSON dictionaries.
- **Serialization:** Custom `_safe_serialize` function to handle OCI SDK objects.
- **Context Risk:** `list_` tools (e.g., `list_instances`) can return unbounded lists, potentially overflowing LLM context windows.

### 2.4 Error Handling
- **Approach:** `try-except` blocks catching `oci.exceptions.ServiceError`.
- **Output:** Returns `{ "error": "message" }` dicts rather than raising MCP protocol errors in some cases.

## 3. Modern MCP Architecture Design

### 3.1 Core Principles
1.  **Progressive Disclosure:** Agents should "pull" information as needed rather than being "pushed" huge dumps.
2.  **Context Efficiency:** Tools must support filtering, pagination, and summarized Markdown outputs.
3.  **Skill-Centricity:** Elevate from "atomic API calls" to "Workflow Skills" (e.g., "Troubleshoot Instance" vs "Get Metrics").

### 3.2 Directory Structure
We will adopt a modular, filesystem-based routing structure:

```text
src/
  mcp_server_oci/
    ├── server.py            # Main FastMCP entrypoint
    ├── auth.py              # Centralized OCI Auth
    ├── tools/               # Atomic Tools (API Wrappers)
    │   ├── compute/
    │   │   ├── __init__.py
    │   │   ├── list.py
    │   │   └── actions.py
    │   └── network/
    ├── resources/           # Read-only Resources (Logs, Configs)
    │   ├── logs.py
    │   └── limits.py
    └── skills/              # High-Level Skills (Workflows)
        ├── troubleshoot.py
        └── cost_analysis.py
```

### 3.3 Progressive Disclosure Pattern
Instead of registering 50+ tools at startup, we will implement:

1.  **`search_capabilities(query: str, domain: Optional[str])`**:
    - Returns a lightweight list of available tools/skills matching the intent.
2.  **Dynamic Tool Registration:**
    - Tools are loaded lazily or grouped by functionality.

### 3.4 Context-Efficient Tool Design
All "List" and "Get" tools will implement the following standard parameters:

- **`limit` (int, default=20):** Hard cap on items returned.
- **`offset` (int, default=0):** For pagination.
- **`format` (enum: "json" | "markdown"):**
    - `json`: Full structural data for programmatic use.
    - `markdown`: LLM-optimized summary (tables, bullet points) to save tokens.

**Example Interface:**
```python
def list_instances(
    compartment_id: str, 
    limit: int = 20, 
    format: str = "markdown"
) -> str | dict:
    ...
```

### 3.5 Skills Architecture
Skills are composite functions that orchestrate multiple atomic tools or perform complex logic *before* returning to the model.

**Example: `troubleshoot_instance` Skill**
1.  Checks instance state (Compute).
2.  Fetches recent alarms (Monitoring).
3.  Checks VCN security lists (Network).
4.  Returns a *Root Cause Analysis* report, not just raw data.

## 4. Implementation Plan

### Phase 1: Foundation
- [ ] Initialize Python project structure (`pyproject.toml`, `uv` or `poetry`).
- [ ] Port `mcp_oci_common` authentication and session management.
- [ ] Setup unified `FastMCP` server instance.

### Phase 2: Compute Domain Migration
- [ ] Refactor `list_instances` with pagination and Markdown support.
- [ ] Refactor `instance_actions` (start/stop) with safety checks.
- [ ] Implement `search_tools` capability.

### Phase 3: Observability & Skills
- [ ] Port metrics and logs tools.
- [ ] Implement `analyze_high_cpu` skill.

### Phase 4: Verification
- [ ] Integration tests with recorded OCI responses.
- [ ] Context usage benchmarks.
