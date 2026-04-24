# Task 2 — SessionManager Service (Data Models + Core Logic)

## 1. Judul Task
Implementasi `SessionManager` service dengan data models `ChatMessage`/`ChatSession` dan semua operasi CRUD + trimming

## 2. Deskripsi
Membangun service inti yang mengelola in-memory session storage untuk percakapan multi-turn. Ini termasuk dataclass models, operasi CRUD session, logic auto-trim history FIFO (dengan system prompt preserved), dan prompt builder.

## 3. Tujuan Teknis
- `ChatMessage` dan `ChatSession` dataclass tersedia
- `SessionManager` menyediakan: create, get, add_message, get_history, delete, cleanup_expired, build_prompt, active_count
- History auto-trim saat melebihi `max_history` (FIFO, system prompt di index 0 tetap)
- `cleanup_expired()` menghapus session yang melewati TTL
- `build_prompt()` menghasilkan formatted string `[Role] Content`

## 4. Scope
### Yang dikerjakan
- `app/services/session_manager.py` — file baru, berisi:
  - `ChatMessage` dataclass
  - `ChatSession` dataclass
  - `SessionManager` class (full implementation)

### Yang TIDAK dikerjakan
- Endpoint / Router — Task 3
- Background async loop — Task 4
- Dependency injection wiring — Task 3
- Unit tests — Task 5

## 5. Langkah Implementasi

### Step 1: Buat file `app/services/session_manager.py`
Buat file baru dengan imports:
```python
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
```

### Step 2: Definisikan `ChatMessage` dataclass
```python
@dataclass
class ChatMessage:
    """A single message in a chat session."""

    role: str           # "user" | "assistant" | "system"
    content: str        # Message text
    timestamp: float    # time.time() saat message dibuat
    model: str | None = None  # Model yang dipakai (hanya untuk assistant)
```

### Step 3: Definisikan `ChatSession` dataclass
```python
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
```

### Step 4: Implementasi `SessionManager.__init__()`
```python
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
```

### Step 5: Implementasi `create_session()`
```python
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
```

### Step 6: Implementasi `get_session()` dan `get_history()`
```python
    def get_session(self, session_id: str) -> ChatSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    def get_history(self, session_id: str) -> list[ChatMessage]:
        session = self.get_session(session_id)
        return session.messages
```

### Step 7: Implementasi `add_message()` — KRITIS: trimming logic
Ini adalah method paling penting. Pastikan logic trim benar:
```python
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
```

**Detail trimming logic:**
- Jika ada system prompt → pertahankan `messages[0]` (system), ambil `max_history - 1` pesan terbaru
- Jika tidak ada system prompt → ambil `max_history` pesan terbaru
- Contoh: max=5, 6 pesan [sys, u1, a1, u2, a2, u3] → [sys, a1, u2, a2, u3] (sys tetap, u1 hilang)

### Step 8: Implementasi `delete_session()`
```python
    def delete_session(self, session_id: str) -> bool:
        if session_id not in self._sessions:
            raise SessionNotFoundError(session_id)
        del self._sessions[session_id]
        logger.info("Session deleted: {id}", id=session_id)
        return True
```

### Step 9: Implementasi `cleanup_expired()`
```python
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
```

### Step 10: Implementasi `build_prompt()` dan `active_count`
```python
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
```

## 6. Output yang Diharapkan

Setelah implementasi, verifikasi manual:
```python
from app.services.session_manager import SessionManager

mgr = SessionManager(max_history=5, ttl_minutes=1)

# Create session with system prompt
session = mgr.create_session("ollama", "llama3.2", system_prompt="You are helpful")
assert len(session.messages) == 1
assert session.messages[0].role == "system"

# Add messages
mgr.add_message(session.session_id, "user", "Hello")
mgr.add_message(session.session_id, "assistant", "Hi!", model="llama3.2")
assert len(mgr.get_history(session.session_id)) == 3

# Build prompt
prompt = mgr.build_prompt(session.session_id)
assert "[System] You are helpful" in prompt
assert "[User] Hello" in prompt
assert "[Assistant] Hi!" in prompt

# Trim test (max=5, already 3, add 3 more = 6 → trim to 5)
mgr.add_message(session.session_id, "user", "Q2")
mgr.add_message(session.session_id, "assistant", "A2", model="llama3.2")
mgr.add_message(session.session_id, "user", "Q3")
history = mgr.get_history(session.session_id)
assert len(history) == 5
assert history[0].role == "system"  # System prompt preserved!

# Delete
mgr.delete_session(session.session_id)
assert mgr.active_count == 0

print("All checks passed!")
```

## 7. Dependencies
- **Task 1** — `SessionNotFoundError` dari `app/core/exceptions.py`

## 8. Acceptance Criteria
- [ ] `ChatMessage` dataclass: role, content, timestamp, model (optional)
- [ ] `ChatSession` dataclass: session_id, provider, model, messages, created_at, last_active, system_prompt (optional)
- [ ] `create_session()` → UUID session, system prompt sebagai message pertama jika ada
- [ ] `get_session()` → session object, raise `SessionNotFoundError` jika tidak ada
- [ ] `add_message()` → message tersimpan, timestamp auto-set, `last_active` di-update
- [ ] Trim FIFO: saat messages > `max_history`, oldest ditrim, system prompt di index 0 selalu dipertahankan
- [ ] `get_history()` → list messages chronological order
- [ ] `delete_session()` → session dihapus, raise `SessionNotFoundError` jika tidak ada
- [ ] `cleanup_expired()` → hapus session yang `last_active` > TTL, return count
- [ ] `build_prompt()` → string format `[Role] Content` dipisah `\n\n`
- [ ] `active_count` → return jumlah session aktif
- [ ] Semua logging menggunakan session ID saja (TIDAK log content message)
- [ ] Server bisa start tanpa error

## 9. Estimasi
Medium (~45 menit)
