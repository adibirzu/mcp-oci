"""
Shared ATP Memory for Inter-Agent Communication.

Provides a shared state store using Oracle Autonomous Transaction Processing (ATP)
for communication between multiple agents and MCP servers.

Features:
- Agent context sharing (findings, recommendations)
- Conversation memory persistence
- Pub/sub event system for inter-agent coordination
- Session state management
- Optimistic locking for concurrent updates

Environment Variables:
- ATP_CONNECTION_STRING: Oracle ATP connection string
- ATP_USER: Database user
- ATP_PASSWORD: Database password (or use wallet)
- ATP_WALLET_LOCATION: Path to wallet directory
- AGENT_ID: Unique identifier for this agent instance
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .observability import get_logger

logger = get_logger("oci-mcp.shared-memory")


# =============================================================================
# Data Models
# =============================================================================

class EventType(str, Enum):
    """Types of inter-agent events."""
    FINDING = "finding"
    RECOMMENDATION = "recommendation"
    ALERT = "alert"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    CONTEXT_UPDATE = "context_update"
    QUERY = "query"
    RESPONSE = "response"


class AgentState(str, Enum):
    """Agent lifecycle states."""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    PAUSED = "paused"
    SHUTDOWN = "shutdown"


@dataclass
class AgentInfo:
    """Information about a connected agent."""
    agent_id: str
    agent_type: str
    state: AgentState
    last_heartbeat: datetime
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SharedEvent(BaseModel):
    """Event for inter-agent communication."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    source_agent: str
    target_agent: str | None = None  # None = broadcast
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)
    ttl_seconds: int = 3600  # 1 hour default
    requires_ack: bool = False


class SharedContext(BaseModel):
    """Shared context between agents."""
    context_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    resource_id: str | None = None  # e.g., instance OCID
    resource_type: str | None = None  # e.g., "compute_instance"
    findings: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: int = 1  # For optimistic locking


class ConversationEntry(BaseModel):
    """A single entry in conversation memory."""
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    agent_id: str
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# In-Memory Implementation (Fallback when ATP not available)
# =============================================================================

class InMemorySharedStore:
    """
    In-memory implementation of shared store.

    Used as fallback when ATP is not configured, or for testing.
    Supports all shared memory operations in-process.
    """

    def __init__(self):
        self._contexts: dict[str, SharedContext] = {}
        self._events: dict[str, SharedEvent] = {}
        self._agents: dict[str, AgentInfo] = {}
        self._conversations: dict[str, list[ConversationEntry]] = {}
        self._event_subscribers: dict[str, list[Callable[[SharedEvent], Awaitable[None]]]] = {}
        self._lock = asyncio.Lock()
        logger.info("Using in-memory shared store (ATP not configured)")

    async def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> AgentInfo:
        """Register an agent in the shared store."""
        async with self._lock:
            agent = AgentInfo(
                agent_id=agent_id,
                agent_type=agent_type,
                state=AgentState.READY,
                last_heartbeat=datetime.now(UTC),
                capabilities=capabilities,
                metadata=metadata or {},
            )
            self._agents[agent_id] = agent
            logger.info(f"Agent registered: {agent_id} ({agent_type})")
            return agent

    async def update_agent_state(self, agent_id: str, state: AgentState) -> None:
        """Update agent state."""
        async with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].state = state
                self._agents[agent_id].last_heartbeat = datetime.now(UTC)

    async def heartbeat(self, agent_id: str) -> None:
        """Update agent heartbeat."""
        async with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].last_heartbeat = datetime.now(UTC)

    async def list_agents(
        self,
        agent_type: str | None = None,
        state: AgentState | None = None,
    ) -> list[AgentInfo]:
        """List registered agents with optional filtering."""
        async with self._lock:
            agents = list(self._agents.values())

            if agent_type:
                agents = [a for a in agents if a.agent_type == agent_type]

            if state:
                agents = [a for a in agents if a.state == state]

            return agents

    # Context operations

    async def save_context(self, context: SharedContext) -> SharedContext:
        """Save or update shared context."""
        async with self._lock:
            existing = self._contexts.get(context.context_id)

            if existing and existing.version != context.version:
                raise ValueError(
                    f"Optimistic lock failed: context version mismatch "
                    f"(expected {context.version}, got {existing.version})"
                )

            context.updated_at = datetime.now(UTC)
            context.version += 1
            self._contexts[context.context_id] = context

            logger.debug(f"Context saved: {context.context_id}")
            return context

    async def get_context(self, context_id: str) -> SharedContext | None:
        """Get shared context by ID."""
        return self._contexts.get(context_id)

    async def find_contexts(
        self,
        session_id: str | None = None,
        resource_id: str | None = None,
        resource_type: str | None = None,
    ) -> list[SharedContext]:
        """Find contexts matching criteria."""
        contexts = list(self._contexts.values())

        if session_id:
            contexts = [c for c in contexts if c.session_id == session_id]

        if resource_id:
            contexts = [c for c in contexts if c.resource_id == resource_id]

        if resource_type:
            contexts = [c for c in contexts if c.resource_type == resource_type]

        return sorted(contexts, key=lambda c: c.updated_at, reverse=True)

    async def add_finding(
        self,
        context_id: str,
        finding: dict[str, Any],
    ) -> SharedContext:
        """Add a finding to existing context."""
        async with self._lock:
            context = self._contexts.get(context_id)
            if not context:
                raise ValueError(f"Context not found: {context_id}")

            context.findings.append(finding)
            context.updated_at = datetime.now(UTC)
            context.version += 1

            return context

    async def add_recommendation(
        self,
        context_id: str,
        recommendation: str,
    ) -> SharedContext:
        """Add a recommendation to existing context."""
        async with self._lock:
            context = self._contexts.get(context_id)
            if not context:
                raise ValueError(f"Context not found: {context_id}")

            if recommendation not in context.recommendations:
                context.recommendations.append(recommendation)
                context.updated_at = datetime.now(UTC)
                context.version += 1

            return context

    # Event operations

    async def publish_event(self, event: SharedEvent) -> SharedEvent:
        """Publish an event to the shared store."""
        async with self._lock:
            self._events[event.event_id] = event
            logger.debug(f"Event published: {event.event_type} from {event.source_agent}")

        # Notify subscribers
        await self._notify_subscribers(event)

        return event

    async def _notify_subscribers(self, event: SharedEvent) -> None:
        """Notify event subscribers."""
        # Broadcast subscribers
        for callback in self._event_subscribers.get("*", []):
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Event subscriber error: {e}")

        # Type-specific subscribers
        for callback in self._event_subscribers.get(event.event_type, []):
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Event subscriber error: {e}")

        # Target-specific subscribers
        if event.target_agent:
            for callback in self._event_subscribers.get(f"agent:{event.target_agent}", []):
                try:
                    await callback(event)
                except Exception as e:
                    logger.error(f"Event subscriber error: {e}")

    async def subscribe(
        self,
        event_type: EventType | None = None,
        agent_id: str | None = None,
        callback: Callable[[SharedEvent], Awaitable[None]] = None,
    ) -> str:
        """Subscribe to events.

        Args:
            event_type: Subscribe to specific event type (None = all)
            agent_id: Subscribe to events targeting this agent
            callback: Async callback function

        Returns:
            Subscription ID for later unsubscribe
        """
        subscription_id = str(uuid.uuid4())

        if agent_id:
            key = f"agent:{agent_id}"
        elif event_type:
            key = event_type.value
        else:
            key = "*"

        if key not in self._event_subscribers:
            self._event_subscribers[key] = []

        self._event_subscribers[key].append(callback)
        logger.debug(f"Subscribed to {key}: {subscription_id}")

        return subscription_id

    async def get_recent_events(
        self,
        event_type: EventType | None = None,
        source_agent: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[SharedEvent]:
        """Get recent events matching criteria."""
        events = list(self._events.values())

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if source_agent:
            events = [e for e in events if e.source_agent == source_agent]

        if since:
            events = [e for e in events if e.timestamp > since]

        # Filter expired events
        now = datetime.now(UTC)
        events = [
            e for e in events
            if (now - e.timestamp).total_seconds() < e.ttl_seconds
        ]

        # Sort by timestamp descending
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)

        return events[:limit]

    # Conversation operations

    async def save_conversation_entry(self, entry: ConversationEntry) -> None:
        """Save a conversation entry."""
        async with self._lock:
            if entry.session_id not in self._conversations:
                self._conversations[entry.session_id] = []
            self._conversations[entry.session_id].append(entry)

    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[ConversationEntry]:
        """Get conversation history for a session."""
        entries = self._conversations.get(session_id, [])
        return sorted(entries, key=lambda e: e.timestamp)[-limit:]

    async def cleanup_expired(self) -> int:
        """Clean up expired events."""
        now = datetime.now(UTC)
        expired_count = 0

        async with self._lock:
            expired_ids = [
                eid for eid, event in self._events.items()
                if (now - event.timestamp).total_seconds() > event.ttl_seconds
            ]

            for eid in expired_ids:
                del self._events[eid]
                expired_count += 1

        if expired_count:
            logger.debug(f"Cleaned up {expired_count} expired events")

        return expired_count


# =============================================================================
# ATP-Backed Implementation
# =============================================================================

class ATPSharedStore(InMemorySharedStore):
    """
    ATP-backed shared store for production use.

    Uses Oracle ATP as the backing store for:
    - Persistence across restarts
    - Multi-node coordination
    - ACID guarantees

    Falls back to in-memory when ATP is not available.
    """

    def __init__(self, connection_string: str | None = None):
        super().__init__()

        self._connection_string = connection_string or os.getenv("ATP_CONNECTION_STRING")
        self._atp_available = False
        self._pool = None

        if self._connection_string:
            self._init_atp()

    def _init_atp(self) -> None:
        """Initialize ATP connection pool."""
        try:
            import oracledb

            # Get credentials
            user = os.getenv("ATP_USER", "ADMIN")
            password = os.getenv("ATP_PASSWORD")
            wallet_location = os.getenv("ATP_WALLET_LOCATION")

            if wallet_location:
                # Use wallet authentication
                self._pool = oracledb.create_pool(
                    user=user,
                    password=password,
                    dsn=self._connection_string,
                    config_dir=wallet_location,
                    wallet_location=wallet_location,
                    wallet_password=password,
                    min=2,
                    max=10,
                    increment=1,
                )
            else:
                # Direct connection
                self._pool = oracledb.create_pool(
                    user=user,
                    password=password,
                    dsn=self._connection_string,
                    min=2,
                    max=10,
                    increment=1,
                )

            self._atp_available = True
            logger.info("ATP shared store initialized")

            # Initialize schema
            asyncio.create_task(self._init_schema())

        except ImportError:
            logger.warning("oracledb not installed, using in-memory store")
        except Exception as e:
            logger.warning(f"ATP connection failed: {e}, using in-memory store")

    async def _init_schema(self) -> None:
        """Initialize database schema if not exists."""
        if not self._atp_available:
            return

        schema_sql = """
        BEGIN
            -- Agent registry table
            EXECUTE IMMEDIATE '
                CREATE TABLE IF NOT EXISTS mcp_agents (
                    agent_id VARCHAR2(100) PRIMARY KEY,
                    agent_type VARCHAR2(50) NOT NULL,
                    state VARCHAR2(20) NOT NULL,
                    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    capabilities CLOB,
                    metadata CLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )';

            -- Shared context table
            EXECUTE IMMEDIATE '
                CREATE TABLE IF NOT EXISTS mcp_contexts (
                    context_id VARCHAR2(100) PRIMARY KEY,
                    session_id VARCHAR2(100) NOT NULL,
                    resource_id VARCHAR2(200),
                    resource_type VARCHAR2(50),
                    findings CLOB,
                    recommendations CLOB,
                    metadata CLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version NUMBER DEFAULT 1
                )';

            -- Events table
            EXECUTE IMMEDIATE '
                CREATE TABLE IF NOT EXISTS mcp_events (
                    event_id VARCHAR2(100) PRIMARY KEY,
                    event_type VARCHAR2(50) NOT NULL,
                    source_agent VARCHAR2(100) NOT NULL,
                    target_agent VARCHAR2(100),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    payload CLOB,
                    ttl_seconds NUMBER DEFAULT 3600,
                    acknowledged NUMBER(1) DEFAULT 0
                )';

            -- Conversation history table
            EXECUTE IMMEDIATE '
                CREATE TABLE IF NOT EXISTS mcp_conversations (
                    entry_id VARCHAR2(100) PRIMARY KEY,
                    session_id VARCHAR2(100) NOT NULL,
                    agent_id VARCHAR2(100) NOT NULL,
                    role VARCHAR2(20) NOT NULL,
                    content CLOB,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata CLOB
                )';

            -- Indexes
            EXECUTE IMMEDIATE 'CREATE INDEX IF NOT EXISTS idx_ctx_session ON mcp_contexts(session_id)';
            EXECUTE IMMEDIATE 'CREATE INDEX IF NOT EXISTS idx_ctx_resource ON mcp_contexts(resource_id)';
            EXECUTE IMMEDIATE 'CREATE INDEX IF NOT EXISTS idx_evt_type ON mcp_events(event_type)';
            EXECUTE IMMEDIATE 'CREATE INDEX IF NOT EXISTS idx_evt_source ON mcp_events(source_agent)';
            EXECUTE IMMEDIATE 'CREATE INDEX IF NOT EXISTS idx_conv_session ON mcp_conversations(session_id)';
        EXCEPTION
            WHEN OTHERS THEN
                -- Tables may already exist
                NULL;
        END;
        """

        try:
            async with self._get_connection() as conn:
                await conn.execute(schema_sql)
                await conn.commit()
            logger.info("ATP schema initialized")
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")

    @asynccontextmanager
    async def _get_connection(self):
        """Get a connection from the pool."""
        if not self._atp_available or not self._pool:
            raise RuntimeError("ATP not available")

        conn = await asyncio.to_thread(self._pool.acquire)
        try:
            yield conn
        finally:
            await asyncio.to_thread(self._pool.release, conn)

    async def save_context(self, context: SharedContext) -> SharedContext:
        """Save context to ATP (with in-memory fallback)."""
        # Always update in-memory for fast reads
        await super().save_context(context)

        if self._atp_available:
            try:
                async with self._get_connection() as conn:
                    cursor = conn.cursor()
                    await asyncio.to_thread(
                        cursor.execute,
                        """
                        MERGE INTO mcp_contexts c
                        USING (SELECT :1 AS context_id FROM dual) s
                        ON (c.context_id = s.context_id)
                        WHEN MATCHED THEN
                            UPDATE SET
                                findings = :2,
                                recommendations = :3,
                                metadata = :4,
                                updated_at = CURRENT_TIMESTAMP,
                                version = version + 1
                            WHERE version = :5
                        WHEN NOT MATCHED THEN
                            INSERT (context_id, session_id, resource_id, resource_type,
                                   findings, recommendations, metadata)
                            VALUES (:1, :6, :7, :8, :2, :3, :4)
                        """,
                        [
                            context.context_id,
                            json.dumps(context.findings),
                            json.dumps(context.recommendations),
                            json.dumps(context.metadata),
                            context.version - 1,  # Expected version
                            context.session_id,
                            context.resource_id,
                            context.resource_type,
                        ]
                    )
                    await asyncio.to_thread(conn.commit)
            except Exception as e:
                logger.error(f"ATP save_context failed: {e}")

        return context

    async def publish_event(self, event: SharedEvent) -> SharedEvent:
        """Publish event to ATP and notify subscribers."""
        # In-memory for immediate subscriber notification
        await super().publish_event(event)

        if self._atp_available:
            try:
                async with self._get_connection() as conn:
                    cursor = conn.cursor()
                    await asyncio.to_thread(
                        cursor.execute,
                        """
                        INSERT INTO mcp_events
                        (event_id, event_type, source_agent, target_agent, payload, ttl_seconds)
                        VALUES (:1, :2, :3, :4, :5, :6)
                        """,
                        [
                            event.event_id,
                            event.event_type.value,
                            event.source_agent,
                            event.target_agent,
                            json.dumps(event.payload),
                            event.ttl_seconds,
                        ]
                    )
                    await asyncio.to_thread(conn.commit)
            except Exception as e:
                logger.error(f"ATP publish_event failed: {e}")

        return event


# =============================================================================
# Global Instance and Helper Functions
# =============================================================================

_shared_store: InMemorySharedStore | None = None


def get_shared_store() -> InMemorySharedStore:
    """Get the global shared store instance.

    Returns ATPSharedStore if ATP is configured, otherwise InMemorySharedStore.
    """
    global _shared_store

    if _shared_store is None:
        if os.getenv("ATP_CONNECTION_STRING"):
            _shared_store = ATPSharedStore()
        else:
            _shared_store = InMemorySharedStore()

    return _shared_store


# Convenience functions

async def share_finding(
    session_id: str,
    resource_id: str,
    finding: dict[str, Any],
    source_agent: str,
) -> SharedContext:
    """Share a finding with other agents.

    Creates or updates shared context and publishes event.
    """
    store = get_shared_store()

    # Find or create context
    contexts = await store.find_contexts(
        session_id=session_id,
        resource_id=resource_id,
    )

    if contexts:
        context = contexts[0]
        await store.add_finding(context.context_id, finding)
    else:
        context = SharedContext(
            session_id=session_id,
            resource_id=resource_id,
            findings=[finding],
        )
        await store.save_context(context)

    # Publish event
    await store.publish_event(SharedEvent(
        event_type=EventType.FINDING,
        source_agent=source_agent,
        payload={
            "context_id": context.context_id,
            "finding": finding,
        },
    ))

    return context


async def share_recommendation(
    session_id: str,
    resource_id: str,
    recommendation: str,
    source_agent: str,
) -> SharedContext:
    """Share a recommendation with other agents."""
    store = get_shared_store()

    # Find or create context
    contexts = await store.find_contexts(
        session_id=session_id,
        resource_id=resource_id,
    )

    if contexts:
        context = contexts[0]
        await store.add_recommendation(context.context_id, recommendation)
    else:
        context = SharedContext(
            session_id=session_id,
            resource_id=resource_id,
            recommendations=[recommendation],
        )
        await store.save_context(context)

    # Publish event
    await store.publish_event(SharedEvent(
        event_type=EventType.RECOMMENDATION,
        source_agent=source_agent,
        payload={
            "context_id": context.context_id,
            "recommendation": recommendation,
        },
    ))

    return context


async def get_shared_findings(
    session_id: str,
    resource_id: str | None = None,
) -> list[dict[str, Any]]:
    """Get all shared findings for a session/resource."""
    store = get_shared_store()

    contexts = await store.find_contexts(
        session_id=session_id,
        resource_id=resource_id,
    )

    findings = []
    for ctx in contexts:
        findings.extend(ctx.findings)

    return findings


async def get_shared_recommendations(
    session_id: str,
    resource_id: str | None = None,
) -> list[str]:
    """Get all shared recommendations for a session/resource."""
    store = get_shared_store()

    contexts = await store.find_contexts(
        session_id=session_id,
        resource_id=resource_id,
    )

    recommendations = []
    for ctx in contexts:
        recommendations.extend(ctx.recommendations)

    return list(set(recommendations))  # Deduplicate
