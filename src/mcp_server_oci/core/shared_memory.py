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
- ATP_WALLET_LOCATION / ATP_WALLET_DIR: Path to wallet directory
- ATP_WALLET_PASSWORD: Wallet password (if different)
- AGENT_ID: Unique identifier for this agent instance
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
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
            wallet_location = os.getenv("ATP_WALLET_LOCATION") or os.getenv("ATP_WALLET_DIR")
            wallet_password = os.getenv("ATP_WALLET_PASSWORD") or password

            if wallet_location:
                # Use wallet authentication
                self._pool = oracledb.create_pool(
                    user=user,
                    password=password,
                    dsn=self._connection_string,
                    config_dir=wallet_location,
                    wallet_location=wallet_location,
                    wallet_password=wallet_password,
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
        ddl_statements = [
            """
            CREATE TABLE mcp_agents (
                agent_id VARCHAR2(100) PRIMARY KEY,
                agent_type VARCHAR2(50) NOT NULL,
                state VARCHAR2(20) NOT NULL,
                last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                capabilities CLOB,
                metadata CLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE mcp_contexts (
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
            )
            """,
            """
            CREATE TABLE mcp_events (
                event_id VARCHAR2(100) PRIMARY KEY,
                event_type VARCHAR2(50) NOT NULL,
                source_agent VARCHAR2(100) NOT NULL,
                target_agent VARCHAR2(100),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                payload CLOB,
                ttl_seconds NUMBER DEFAULT 3600,
                acknowledged NUMBER(1) DEFAULT 0
            )
            """,
            """
            CREATE TABLE mcp_conversations (
                entry_id VARCHAR2(100) PRIMARY KEY,
                session_id VARCHAR2(100) NOT NULL,
                agent_id VARCHAR2(100) NOT NULL,
                role VARCHAR2(20) NOT NULL,
                content CLOB,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata CLOB
            )
            """,
            "CREATE INDEX idx_ctx_sess ON mcp_contexts(session_id)",
            "CREATE INDEX idx_ctx_res ON mcp_contexts(resource_id)",
            "CREATE INDEX idx_evt_type ON mcp_events(event_type)",
            "CREATE INDEX idx_evt_src ON mcp_events(source_agent)",
            "CREATE INDEX ix_conv ON mcp_conversations(session_id)",
        ]

        try:
            import oracledb

            async with self._get_connection() as conn:
                cursor = conn.cursor()
                for statement in ddl_statements:
                    stmt = statement.strip()
                    if not stmt:
                        continue
                    try:
                        await asyncio.to_thread(cursor.execute, stmt)
                    except oracledb.DatabaseError as e:
                        error, = e.args
                        if error.code not in (955, 1408):
                            raise
                await asyncio.to_thread(conn.commit)
            logger.info("ATP schema initialized")
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")

    @asynccontextmanager
    async def _get_connection(self) -> AsyncGenerator[Any, None]:
        """Get a connection from the pool."""
        if not self._atp_available or not self._pool:
            raise RuntimeError("ATP not available")

        conn = await asyncio.to_thread(self._pool.acquire)
        try:
            yield conn
        finally:
            await asyncio.to_thread(self._pool.release, conn)

    async def _save_agent_to_atp(self, agent: AgentInfo) -> None:
        """Upsert agent metadata in ATP."""
        if not self._atp_available:
            return

        try:
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                await asyncio.to_thread(
                    cursor.execute,
                    """
                    MERGE INTO mcp_agents a
                    USING (SELECT :agent_id AS agent_id FROM dual) s
                    ON (a.agent_id = s.agent_id)
                    WHEN MATCHED THEN
                        UPDATE SET
                            agent_type = :agent_type,
                            state = :state,
                            last_heartbeat = :last_heartbeat,
                            capabilities = :capabilities,
                            metadata = :metadata
                    WHEN NOT MATCHED THEN
                        INSERT (agent_id, agent_type, state, last_heartbeat, capabilities, metadata)
                        VALUES (:agent_id, :agent_type, :state, :last_heartbeat, :capabilities, :metadata)
                    """,
                    {
                        "agent_id": agent.agent_id,
                        "agent_type": agent.agent_type,
                        "state": agent.state.value,
                        "last_heartbeat": agent.last_heartbeat,
                        "capabilities": json.dumps(agent.capabilities),
                        "metadata": json.dumps(agent.metadata),
                    },
                )
                await asyncio.to_thread(conn.commit)
        except Exception as e:
            logger.error(f"ATP save_agent failed: {e}")

    async def _save_context_to_atp(self, context: SharedContext) -> None:
        """Persist shared context to ATP."""
        if not self._atp_available:
            return

        try:
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                await asyncio.to_thread(
                    cursor.execute,
                    """
                    MERGE INTO mcp_contexts c
                    USING (SELECT :context_id AS context_id FROM dual) s
                    ON (c.context_id = s.context_id)
                    WHEN MATCHED THEN
                        UPDATE SET
                            findings = :findings,
                            recommendations = :recommendations,
                            metadata = :metadata,
                            updated_at = CURRENT_TIMESTAMP,
                            version = version + 1
                        WHERE version = :expected_version
                    WHEN NOT MATCHED THEN
                        INSERT (context_id, session_id, resource_id, resource_type,
                               findings, recommendations, metadata)
                        VALUES (:context_id, :session_id, :resource_id, :resource_type,
                               :findings, :recommendations, :metadata)
                    """,
                    {
                        "context_id": context.context_id,
                        "findings": json.dumps(context.findings),
                        "recommendations": json.dumps(context.recommendations),
                        "metadata": json.dumps(context.metadata),
                        "expected_version": context.version - 1,
                        "session_id": context.session_id,
                        "resource_id": context.resource_id,
                        "resource_type": context.resource_type,
                    },
                )
                await asyncio.to_thread(conn.commit)
        except Exception as e:
            logger.error(f"ATP save_context failed: {e}")

    async def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> AgentInfo:
        agent = await super().register_agent(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities,
            metadata=metadata,
        )
        await self._save_agent_to_atp(agent)
        return agent

    async def update_agent_state(self, agent_id: str, state: AgentState) -> None:
        await super().update_agent_state(agent_id, state)
        agent = self._agents.get(agent_id)
        if agent:
            await self._save_agent_to_atp(agent)

    async def heartbeat(self, agent_id: str) -> None:
        await super().heartbeat(agent_id)
        agent = self._agents.get(agent_id)
        if agent:
            await self._save_agent_to_atp(agent)

    async def list_agents(
        self,
        agent_type: str | None = None,
        state: AgentState | None = None,
    ) -> list[AgentInfo]:
        if not self._atp_available:
            return await super().list_agents(agent_type, state)

        try:
            query = """
                SELECT agent_id, agent_type, state, last_heartbeat, capabilities, metadata
                FROM mcp_agents
                WHERE (:agent_type IS NULL OR agent_type = :agent_type)
                  AND (:state IS NULL OR state = :state)
            """
            params = {
                "agent_type": agent_type,
                "state": state.value if state else None,
            }
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                await asyncio.to_thread(cursor.execute, query, params)
                rows = await asyncio.to_thread(cursor.fetchall)

            agents = []
            for row in rows:
                # Handle LOB types
                caps_val = row[4].read() if hasattr(row[4], 'read') else row[4]
                meta_val = row[5].read() if hasattr(row[5], 'read') else row[5]
                capabilities = json.loads(caps_val) if caps_val else []
                metadata = json.loads(meta_val) if meta_val else {}
                agents.append(
                    AgentInfo(
                        agent_id=row[0],
                        agent_type=row[1],
                        state=AgentState(row[2]),
                        last_heartbeat=row[3],
                        capabilities=capabilities,
                        metadata=metadata,
                    )
                )
            return agents
        except Exception as e:
            logger.error(f"ATP list_agents failed: {e}")
            return await super().list_agents(agent_type, state)

    async def save_context(self, context: SharedContext) -> SharedContext:
        """Save context to ATP (with in-memory fallback)."""
        # Always update in-memory for fast reads
        await super().save_context(context)
        await self._save_context_to_atp(context)

        return context

    async def get_context(self, context_id: str) -> SharedContext | None:
        """Get shared context by ID (ATP-backed)."""
        context = await super().get_context(context_id)
        if context or not self._atp_available:
            return context

        try:
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                await asyncio.to_thread(
                    cursor.execute,
                    """
                    SELECT context_id, session_id, resource_id, resource_type,
                           findings, recommendations, metadata,
                           created_at, updated_at, version
                    FROM mcp_contexts
                    WHERE context_id = :1
                    """,
                    [context_id],
                )
                row = await asyncio.to_thread(cursor.fetchone)
                if not row:
                    return None

            context = SharedContext(
                context_id=row[0],
                session_id=row[1],
                resource_id=row[2],
                resource_type=row[3],
                findings=json.loads(row[4]) if row[4] else [],
                recommendations=json.loads(row[5]) if row[5] else [],
                metadata=json.loads(row[6]) if row[6] else {},
                created_at=row[7],
                updated_at=row[8],
                version=int(row[9]),
            )
            self._contexts[context.context_id] = context
            return context
        except Exception as e:
            logger.error(f"ATP get_context failed: {e}")
            return None

    async def find_contexts(
        self,
        session_id: str | None = None,
        resource_id: str | None = None,
        resource_type: str | None = None,
    ) -> list[SharedContext]:
        """Find contexts matching criteria (ATP-backed)."""
        if not self._atp_available:
            return await super().find_contexts(session_id, resource_id, resource_type)

        try:
            query = """
                SELECT context_id, session_id, resource_id, resource_type,
                       findings, recommendations, metadata,
                       created_at, updated_at, version
                FROM mcp_contexts
                WHERE (:1 IS NULL OR session_id = :1)
                  AND (:2 IS NULL OR resource_id = :2)
                  AND (:3 IS NULL OR resource_type = :3)
                ORDER BY updated_at DESC
            """
            params = [session_id, resource_id, resource_type]
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                await asyncio.to_thread(cursor.execute, query, params)
                rows = await asyncio.to_thread(cursor.fetchall)

            contexts = []
            for row in rows:
                context = SharedContext(
                    context_id=row[0],
                    session_id=row[1],
                    resource_id=row[2],
                    resource_type=row[3],
                    findings=json.loads(row[4]) if row[4] else [],
                    recommendations=json.loads(row[5]) if row[5] else [],
                    metadata=json.loads(row[6]) if row[6] else {},
                    created_at=row[7],
                    updated_at=row[8],
                    version=int(row[9]),
                )
                contexts.append(context)
                self._contexts[context.context_id] = context

            return contexts
        except Exception as e:
            logger.error(f"ATP find_contexts failed: {e}")
            return await super().find_contexts(session_id, resource_id, resource_type)

    async def add_finding(
        self,
        context_id: str,
        finding: dict[str, Any],
    ) -> SharedContext:
        """Add a finding to existing context (ATP-backed)."""
        context = await super().add_finding(context_id, finding)
        await self._save_context_to_atp(context)
        return context

    async def add_recommendation(
        self,
        context_id: str,
        recommendation: str,
    ) -> SharedContext:
        """Add a recommendation to existing context (ATP-backed)."""
        context = await super().add_recommendation(context_id, recommendation)
        await self._save_context_to_atp(context)
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

    async def get_recent_events(
        self,
        event_type: EventType | None = None,
        source_agent: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[SharedEvent]:
        """Get recent events matching criteria (ATP-backed)."""
        if not self._atp_available:
            return await super().get_recent_events(event_type, source_agent, since, limit)

        try:
            query = """
                SELECT event_id, event_type, source_agent, target_agent,
                       timestamp, payload, ttl_seconds, acknowledged
                FROM mcp_events
                WHERE (:event_type IS NULL OR event_type = :event_type)
                  AND (:source_agent IS NULL OR source_agent = :source_agent)
                  AND (:since IS NULL OR timestamp > :since)
                ORDER BY timestamp DESC
            """
            params = {
                "event_type": event_type.value if event_type else None,
                "source_agent": source_agent,
                "since": since,
            }
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                await asyncio.to_thread(cursor.execute, query, params)
                rows = await asyncio.to_thread(cursor.fetchmany, limit)

            events = []
            now = datetime.now(UTC)
            for row in rows:
                timestamp = row[4]
                ttl_seconds = int(row[6]) if row[6] is not None else 3600
                if (now - timestamp).total_seconds() > ttl_seconds:
                    continue
                # Handle LOB types
                payload_val = row[5].read() if hasattr(row[5], 'read') else row[5]
                events.append(
                    SharedEvent(
                        event_id=row[0],
                        event_type=EventType(row[1]),
                        source_agent=row[2],
                        target_agent=row[3],
                        timestamp=timestamp,
                        payload=json.loads(payload_val) if payload_val else {},
                        ttl_seconds=ttl_seconds,
                        requires_ack=bool(row[7]),
                    )
                )
            return events[:limit]
        except Exception as e:
            logger.error(f"ATP get_recent_events failed: {e}")
            return await super().get_recent_events(event_type, source_agent, since, limit)

    async def save_conversation_entry(self, entry: ConversationEntry) -> None:
        """Save a conversation entry (ATP-backed)."""
        await super().save_conversation_entry(entry)
        if not self._atp_available:
            return

        try:
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                await asyncio.to_thread(
                    cursor.execute,
                    """
                    INSERT INTO mcp_conversations
                    (entry_id, session_id, agent_id, role, content, timestamp, metadata)
                    VALUES (:1, :2, :3, :4, :5, :6, :7)
                    """,
                    [
                        entry.entry_id,
                        entry.session_id,
                        entry.agent_id,
                        entry.role,
                        entry.content,
                        entry.timestamp,
                        json.dumps(entry.metadata),
                    ],
                )
                await asyncio.to_thread(conn.commit)
        except Exception as e:
            logger.error(f"ATP save_conversation_entry failed: {e}")

    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[ConversationEntry]:
        """Get conversation history for a session (ATP-backed)."""
        if not self._atp_available:
            return await super().get_conversation_history(session_id, limit)

        try:
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                await asyncio.to_thread(
                    cursor.execute,
                    """
                    SELECT entry_id, session_id, agent_id, role, content,
                           timestamp, metadata
                    FROM mcp_conversations
                    WHERE session_id = :1
                    ORDER BY timestamp ASC
                    """,
                    [session_id],
                )
                rows = await asyncio.to_thread(cursor.fetchall)

            entries = [
                ConversationEntry(
                    entry_id=row[0],
                    session_id=row[1],
                    agent_id=row[2],
                    role=row[3],
                    content=row[4],
                    timestamp=row[5],
                    metadata=json.loads(row[6]) if row[6] else {},
                )
                for row in rows
            ]
            return entries[-limit:]
        except Exception as e:
            logger.error(f"ATP get_conversation_history failed: {e}")
            return await super().get_conversation_history(session_id, limit)

    async def cleanup_expired(self) -> int:
        """Clean up expired events in memory and ATP."""
        expired_count = await super().cleanup_expired()
        if not self._atp_available:
            return expired_count

        try:
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                await asyncio.to_thread(
                    cursor.execute,
                    """
                    DELETE FROM mcp_events
                    WHERE timestamp < (SYSTIMESTAMP - NUMTODSINTERVAL(ttl_seconds, 'SECOND'))
                    """,
                )
                count = cursor.rowcount or 0
                await asyncio.to_thread(conn.commit)
                return expired_count + count
        except Exception as e:
            logger.error(f"ATP cleanup_expired failed: {e}")
            return expired_count


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
