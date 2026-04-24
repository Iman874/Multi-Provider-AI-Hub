# Blueprint: AI Generative Core — Conversation History (beta0.2.2)

## 1. Visi & Tujuan

Saat ini, setiap request ke `/api/v1/generate` dan `/api/v1/stream` bersifat **stateless** — Gateway tidak menyimpan riwayat percakapan. Jika frontend ingin multi-turn chat, ia harus mengirim ulang seluruh konteks percakapan di setiap request, yang menyebabkan:

1. **Payload Membengkak**: Frontend harus kirim ulang 10–50 pesan sebelumnya di setiap request
2. **Prompt Token Terbuang**: Provider menghitung token untuk konteks yang sama berulang kali
3. **Kompleksitas Frontend**: Frontend harus mengelola history state sendiri

Modul **beta0.2.2** membangun **Server-Side Conversation History**:
- Session chat disimpan **di server** (in-memory) dengan **UUID** unik
- Frontend cukup kirim `session_id` + pesan terbaru — Gateway otomatis menggabungkan history
- Session memiliki **TTL** (auto-expire) agar memori tidak bocor
- History di-trim otomatis saat melebihi batas (FIFO, system prompt tetap)
- 3 endpoint baru: `POST /chat`, `GET /chat/{id}/history`, `DELETE /chat/{id}`

---

## 2. Scope Development

### ✅ Yang Dikerjakan
- **ChatMessage Model**: Dataclass untuk pesan role-based (user/assistant/system)
- **ChatSession Model**: Dataclass untuk session lengkap
- **SessionManager Service**: In-memory session store, CRUD, auto-cleanup
- **Prompt Builder**: Menggabungkan history → formatted prompt string
- **Chat Endpoint**: `POST /api/v1/chat` — multi-turn conversation
- **History Endpoint**: `GET /api/v1/chat/{session_id}/history`
- **Delete Endpoint**: `DELETE /api/v1/chat/{session_id}`
- **Background Cleanup**: asyncio task untuk expire session
- **Pydantic Request/Response Schemas**
- **Unit Tests**: SessionManager + endpoint integration

### ❌ Yang Tidak Dikerjakan
- Persistent storage (database) — hanya in-memory, restart = hilang
- Cross-server session sharing (single instance only)
- Image/file attachments di chat history (text only)
- Streaming di chat endpoint (gunakan `/stream` terpisah)
- System prompt management via API (dikirim saat create session)

---

## 3. Arsitektur & Desain

### 3.1. Konfigurasi (`.env`)

```env
# --- Conversation History ---
CHAT_MAX_HISTORY=50    # Max messages per session (trim FIFO, system prompt preserved)
CHAT_SESSION_TTL=30    # Session TTL in minutes (auto-expire inactive sessions)
```

**Config di `app/config.py`**:
```python
CHAT_MAX_HISTORY: int = 50
CHAT_SESSION_TTL: int = 30  # minutes
```

### 3.2. Data Models

**`ChatMessage`** (dataclass di `app/services/session_manager.py`):
```python
@dataclass
class ChatMessage:
    role: str           # "user" | "assistant" | "system"
    content: str        # Message text
    timestamp: float    # time.time() saat message dibuat
    model: str | None = None  # Model yang dipakai (hanya untuk assistant)
```

**`ChatSession`** (dataclass):
```python
@dataclass
class ChatSession:
    session_id: str               # UUID v4
    provider: str                 # "ollama" | "gemini"
    model: str                    # Active model name
    messages: list[ChatMessage]   # Riwayat pesan (ordered)
    created_at: float             # time.time()
    last_active: float            # Updated setiap add_message
    system_prompt: str | None = None
```

### 3.3. SessionManager Service (`app/services/session_manager.py`)

```
┌─────────────────────────────────────────────────────────┐
│                  SessionManager                         │
├─────────────────────────────────────────────────────────┤
│ _sessions: dict[str, ChatSession]                       │
│ _max_history: int                                       │
│ _ttl_minutes: int                                       │
├─────────────────────────────────────────────────────────┤
│ create_session(provider, model, system_prompt?)          │
│   → ChatSession (UUID generated)                        │
│ get_session(session_id)                                 │
│   → ChatSession | raise SessionNotFoundError            │
│ add_message(session_id, role, content, model?)          │
│   → ChatMessage (trim if > max_history)                 │
│ get_history(session_id)                                 │
│   → list[ChatMessage]                                   │
│ delete_session(session_id) → bool                       │
│ cleanup_expired() → int  (returns count deleted)        │
│ build_prompt(session_id) → str                          │
│ active_count → int                                      │
└─────────────────────────────────────────────────────────┘
```

**Pseudocode `create_session()`**:
```
def create_session(provider, model, system_prompt=None):
    session_id = str(uuid.uuid4())
    now = time.time()
    messages = []

    # Jika ada system prompt, tambahkan sebagai message pertama
    if system_prompt:
        messages.append(ChatMessage(
            role="system", content=system_prompt, timestamp=now
        ))

    session = ChatSession(
        session_id=session_id,
        provider=provider, model=model,
        messages=messages,
        created_at=now, last_active=now,
        system_prompt=system_prompt,
    )
    _sessions[session_id] = session
    logger.info("Session created: {id}", id=session_id)
    return session
```

**Pseudocode `add_message()` — dengan trimming**:
```
def add_message(session_id, role, content, model=None):
    session = get_session(session_id)
    msg = ChatMessage(role=role, content=content, timestamp=time.time(), model=model)
    session.messages.append(msg)
    session.last_active = time.time()

    # Trim jika melebihi max_history
    if len(session.messages) > _max_history:
        # Pertahankan system prompt (index 0 jika ada)
        if session.system_prompt and session.messages[0].role == "system":
            system_msg = session.messages[0]
            session.messages = [system_msg] + session.messages[-(max_history - 1):]
        else:
            session.messages = session.messages[-max_history:]

    return msg
```

**Pseudocode `build_prompt()`**:
```
def build_prompt(session_id) -> str:
    session = get_session(session_id)
    parts = []
    for msg in session.messages:
        prefix = {"system": "[System]", "user": "[User]", "assistant": "[Assistant]"}
        parts.append(f"{prefix[msg.role]} {msg.content}")
    return "\n\n".join(parts)
```

**Pseudocode `cleanup_expired()`**:
```
def cleanup_expired() -> int:
    now = time.time()
    expired_ids = [
        sid for sid, s in _sessions.items()
        if (now - s.last_active) > (_ttl_minutes * 60)
    ]
    for sid in expired_ids:
        del _sessions[sid]
    if expired_ids:
        logger.info("Cleaned up {n} expired sessions", n=len(expired_ids))
    return len(expired_ids)
```

### 3.4. Exception Baru

```python
class SessionNotFoundError(AIGatewayError):
    """Session ID tidak ditemukan atau sudah expired."""
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Chat session '{session_id}' not found or expired",
            code="SESSION_NOT_FOUND",
        )
        # HTTP 404
```

### 3.5. Pydantic Schemas

**ChatRequest** (`app/schemas/requests.py`):
```python
class ChatRequest(BaseModel):
    provider: ProviderEnum
    model: str
    message: str = Field(..., min_length=1, description="User message")
    session_id: str | None = Field(default=None, description="Existing session ID, null = new")
    system_prompt: str | None = Field(default=None, description="System prompt (only for new session)")
```

**ChatResponse** (`app/schemas/responses.py`):
```python
class ChatResponse(BaseModel):
    session_id: str
    output: str
    provider: str
    model: str
    usage: dict | None = None
    turn_count: int         # Total messages in session
    metadata: dict | None = None
```

**ChatHistoryResponse**:
```python
class ChatMessageSchema(BaseModel):
    role: str
    content: str
    timestamp: float
    model: str | None = None

class ChatHistoryResponse(BaseModel):
    session_id: str
    provider: str
    model: str
    messages: list[ChatMessageSchema]
    created_at: float
    last_active: float
    turn_count: int
```

### 3.6. Chat Endpoint Flow

```
POST /api/v1/chat
  │
  ├── session_id == null?
  │     ├── YES → SessionManager.create_session(provider, model, system_prompt)
  │     └── NO  → SessionManager.get_session(session_id)
  │                ├── NOT FOUND → 404 SESSION_NOT_FOUND
  │                └── FOUND → validate provider/model match
  │
  ├── SessionManager.add_message(session_id, "user", message)
  │
  ├── prompt = SessionManager.build_prompt(session_id)
  │
  ├── result = GeneratorService.generate(prompt_with_history)
  │     (Memanggil provider dengan full context)
  │
  ├── SessionManager.add_message(session_id, "assistant", result.output, model)
  │
  └── Return ChatResponse {
        session_id, output, provider, model, usage,
        turn_count = len(session.messages)
      }
```

### 3.7. Background Cleanup Task

```python
async def _session_cleanup_loop(manager: SessionManager, interval: int = 300):
    """Background task — setiap 5 menit, bersihkan session expired."""
    while True:
        await asyncio.sleep(interval)
        count = manager.cleanup_expired()
        if count > 0:
            logger.info("Session cleanup: removed {n} expired", n=count)
```

Distart di `lifespan` startup, di-cancel di shutdown:
```python
# In lifespan():
cleanup_task = asyncio.create_task(_session_cleanup_loop(session_manager))
yield
cleanup_task.cancel()
```

---

## 4. Breakdowns (Daftar Task)

### Task 1 — Config, Exceptions & Schemas

**File yang diubah**: `app/config.py`, `app/core/exceptions.py`, `app/schemas/requests.py`, `app/schemas/responses.py`

**Langkah:**
1. Config: `CHAT_MAX_HISTORY: int = 50`, `CHAT_SESSION_TTL: int = 30`
2. Exception: `SessionNotFoundError` — code `SESSION_NOT_FOUND`
3. Schema request: `ChatRequest` (provider, model, message, session_id?, system_prompt?)
4. Schema response: `ChatResponse`, `ChatMessageSchema`, `ChatHistoryResponse`

**Acceptance Criteria:**
- Config accessible, schema validates, exception raiseable
- `session_id` optional di ChatRequest

**Estimasi:** Low (25 menit)

---

### Task 2 — SessionManager Service

**File yang dibuat**: `app/services/session_manager.py`

**Langkah:**
1. Dataclass: `ChatMessage`, `ChatSession`
2. Class `SessionManager`: create, get, add_message (with trim), get_history, delete, cleanup_expired, build_prompt, active_count
3. Trimming logic: FIFO, system prompt preserved
4. Logging: session created/deleted/cleaned (ID only, bukan content)

**Acceptance Criteria:**
- Create → UUID session, Get → session, Add → message with trim
- Trim: max 50, system prompt kept at index 0
- Cleanup: sessions > TTL removed
- build_prompt: correct formatted string

**Estimasi:** Medium (45 menit)

---

### Task 3 — Chat Endpoints & Router

**File yang dibuat**: `app/api/endpoints/chat.py`
**File yang diubah**: `app/api/router.py`, `app/api/dependencies.py`

**Langkah:**
1. `POST /chat`: create/continue session, build prompt, call generator, store response
2. `GET /chat/{session_id}/history`: return messages
3. `DELETE /chat/{session_id}`: delete session
4. Register in router, init SessionManager in dependencies
5. Exception handler: `SessionNotFoundError` → 404

**Acceptance Criteria:**
- New session → 200 + session_id, Continue → 200 + accumulated history
- History → ordered messages, Delete → 200 confirmation
- Invalid session_id → 404

**Estimasi:** Medium (45 menit)

---

### Task 4 — Background Cleanup

**File yang diubah**: `app/main.py`

**Langkah:**
1. Create `_session_cleanup_loop()` async function
2. Start in lifespan startup, cancel in shutdown
3. Log cleanup activity

**Acceptance Criteria:**
- Expired sessions removed periodically
- Clean shutdown (task cancelled)

**Estimasi:** Low (15 menit)

---

### Task 5 — Unit Tests

**File yang dibuat**: `tests/services/test_session_manager.py`

**Tests (12 total):**
1. `test_create_session` — UUID generated, messages empty or with system prompt
2. `test_add_message_user` — user message stored
3. `test_add_message_assistant` — assistant message with model
4. `test_history_order` — chronological order
5. `test_max_history_trim` — oldest messages trimmed, system prompt kept
6. `test_system_prompt_preserved` — system prompt always at index 0 after trim
7. `test_delete_session` — session removed
8. `test_session_not_found` — raise SessionNotFoundError
9. `test_cleanup_expired` — expired sessions removed (mock time)
10. `test_build_prompt_format` — correct [User]/[Assistant]/[System] format
11. `test_active_count` — correct count
12. `test_build_prompt_with_system` — system prompt included

**Acceptance Criteria:**
- 12 test baru, semua existing tests PASS

**Estimasi:** Medium (45 menit)

---

## 5. Timeline & Estimasi Total

| Task | Scope | Estimasi |
|---|---|---|
| Task 1 | Config, Exceptions & Schemas | 25 menit |
| Task 2 | SessionManager Service | 45 menit |
| Task 3 | Chat Endpoints & Router | 45 menit |
| Task 4 | Background Cleanup | 15 menit |
| Task 5 | Unit Tests | 45 menit |
| **Total** | | **~3 jam** |

---

## 6. Acceptance Criteria Global

- [ ] Multi-turn chat berfungsi — history terakumulasi per session
- [ ] Session baru dibuat otomatis jika `session_id` null
- [ ] Session lama dilanjutkan dengan `session_id` valid
- [ ] History di-trim FIFO saat melebihi `CHAT_MAX_HISTORY`
- [ ] System prompt TIDAK pernah di-trim (always at index 0)
- [ ] Session expired dihapus otomatis setelah `CHAT_SESSION_TTL` menit
- [ ] `build_prompt()` menghasilkan prompt dengan format `[Role] Content`
- [ ] Provider menerima full context dari history
- [ ] Endpoint history mengembalikan seluruh percakapan
- [ ] Endpoint delete menghapus session
- [ ] Session not found → 404 `SESSION_NOT_FOUND`
- [ ] Background cleanup berjalan periodik
- [ ] Semua existing tests tetap PASS
- [ ] 12 test baru ditambahkan
