"""
Session Manager — In-memory conversation history store.

Manages chat sessions with CRUD operations, automatic FIFO trimming,
and TTL-based expiration. Each session stores ordered messages and
metadata for multi-turn AI conversations.
"""

import time
import uuid
from dataclasses import dataclass, field

from loguru import logger

from app.core.exceptions import SessionNotFoundError


@dataclass
class ChatMessage:
    """A single message in a chat session."""

    role: str           # "user" | "assistant" | "system"
    content: str        # Message text
    timestamp: float    # time.time() saat message dibuat
    model: str | None = None  # Model yang dipakai (hanya untuk assistant)


@dataclass
class ChatSession:
    """A chat session containing ordered messages and metadata."""

    session_id: str               # UUID v4
    provider: str                 # "ollama" | "gemini"
    model: str                    # Active model name
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: float = 0.0
    last_active: float = 0.0
    system_prompt: str | None = None


class SessionManager:
    """
    In-memory session store for multi-turn chat conversations.

    Provides CRUD operations, automatic FIFO history trimming,
    TTL-based session expiration, and prompt building.
    """

    def __init__(self, max_history: int = 50, ttl_minutes: int = 30):
        self._sessions: dict[str, ChatSession] = {}
        self._max_history = max_history
        self._ttl_minutes = ttl_minutes
        logger.info(
            "SessionManager initialized: max_history={max}, ttl={ttl}min",
            max=max_history,
            ttl=ttl_minutes,
        )

    def create_session(
        self,
        provider: str,
        model: str,
        system_prompt: str | None = None,
    ) -> ChatSession:
        session_id = str(uuid.uuid4())
        now = time.time()
        messages: list[ChatMessage] = []

        if system_prompt:
            messages.append(ChatMessage(
                role="system",
                content=system_prompt,
                timestamp=now,
            ))

        session = ChatSession(
            session_id=session_id,
            provider=provider,
            model=model,
            messages=messages,
            created_at=now,
            last_active=now,
            system_prompt=system_prompt,
        )
        self._sessions[session_id] = session
        logger.info("Session created: {id}", id=session_id)
        return session

    def get_session(self, session_id: str) -> ChatSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    def get_history(self, session_id: str) -> list[ChatMessage]:
        session = self.get_session(session_id)
        return session.messages

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        model: str | None = None,
    ) -> ChatMessage:
        session = self.get_session(session_id)
        msg = ChatMessage(
            role=role,
            content=content,
            timestamp=time.time(),
            model=model,
        )
        session.messages.append(msg)
        session.last_active = time.time()

        # Trim jika melebihi max_history (FIFO, system prompt preserved)
        if len(session.messages) > self._max_history:
            if session.system_prompt and session.messages[0].role == "system":
                system_msg = session.messages[0]
                session.messages = [system_msg] + session.messages[-(self._max_history - 1):]
            else:
                session.messages = session.messages[-self._max_history:]

        return msg

    def delete_session(self, session_id: str) -> bool:
        if session_id not in self._sessions:
            raise SessionNotFoundError(session_id)
        del self._sessions[session_id]
        logger.info("Session deleted: {id}", id=session_id)
        return True

    def cleanup_expired(self) -> int:
        now = time.time()
        ttl_seconds = self._ttl_minutes * 60
        expired_ids = [
            sid for sid, session in self._sessions.items()
            if (now - session.last_active) > ttl_seconds
        ]
        for sid in expired_ids:
            del self._sessions[sid]
        if expired_ids:
            logger.info(
                "Cleaned up {n} expired sessions",
                n=len(expired_ids),
            )
        return len(expired_ids)

    def build_prompt(self, session_id: str) -> str:
        session = self.get_session(session_id)
        prefix_map = {
            "system": "[System]",
            "user": "[User]",
            "assistant": "[Assistant]",
        }
        parts = []
        for msg in session.messages:
            prefix = prefix_map.get(msg.role, f"[{msg.role}]")
            parts.append(f"{prefix} {msg.content}")
        return "\n\n".join(parts)

    @property
    def active_count(self) -> int:
        """Return number of active (non-expired) sessions."""
        return len(self._sessions)
