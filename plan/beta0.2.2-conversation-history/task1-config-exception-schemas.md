# Task 1 — Config, Exception & Pydantic Schemas

## 1. Judul Task
Tambah konfigurasi Conversation History, exception `SessionNotFoundError`, dan semua Pydantic schemas baru

## 2. Deskripsi
Menyiapkan foundation data layer untuk fitur Conversation History: config fields baru di Settings, exception class baru, dan semua Pydantic request/response schemas yang dibutuhkan oleh endpoint chat.

## 3. Tujuan Teknis
- `settings.CHAT_MAX_HISTORY` dan `settings.CHAT_SESSION_TTL` bisa diakses dari seluruh aplikasi
- `SessionNotFoundError` bisa di-raise dan di-catch sebagai subclass `AIGatewayError`
- `ChatRequest`, `ChatResponse`, `ChatMessageSchema`, `ChatHistoryResponse` tersedia sebagai Pydantic models
- `APP_VERSION` terupdate ke `"0.2.2"`
- `.env` dan `.env.example` terupdate

## 4. Scope
### Yang dikerjakan
- `app/config.py` — tambah 2 field config baru, update version
- `app/core/exceptions.py` — tambah `SessionNotFoundError`
- `app/schemas/requests.py` — tambah `ChatRequest`
- `app/schemas/responses.py` — tambah `ChatResponse`, `ChatMessageSchema`, `ChatHistoryResponse`
- `.env` — tambah 2 variabel baru
- `.env.example` — update dengan dokumentasi

### Yang TIDAK dikerjakan
- Data models internal (`ChatMessage`, `ChatSession`) — itu di Task 2 (SessionManager)
- Implementasi SessionManager — Task 2
- Endpoint / Router — Task 3
- Background cleanup — Task 4

## 5. Langkah Implementasi

### Step 1: Update `app/config.py`
Tambahkan 2 field baru di class `Settings`, setelah section `# --- Logging ---`:
```python
# --- Conversation History ---
CHAT_MAX_HISTORY: int = 50    # Max messages per session (trim FIFO, system prompt preserved)
CHAT_SESSION_TTL: int = 30    # Session TTL in minutes (auto-expire inactive sessions)
```
Ubah `APP_VERSION` dari `"0.1.9"` menjadi `"0.2.2"`.

### Step 2: Tambah exception di `app/core/exceptions.py`
Tambahkan setelah class `AllKeysExhaustedError`:

```python
class SessionNotFoundError(AIGatewayError):
    """Session ID tidak ditemukan atau sudah expired."""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"Chat session '{session_id}' not found or expired",
            code="SESSION_NOT_FOUND",
        )
```

### Step 3: Tambah `ChatRequest` di `app/schemas/requests.py`
Tambahkan di akhir file, setelah class `EmbeddingRequest`:

```python
class ChatRequest(BaseModel):
    """
    Request body for POST /chat.

    Supports multi-turn conversation with server-side history.
    If session_id is null, a new session is created.
    If session_id is provided, the existing session is continued.
    """

    provider: ProviderEnum = Field(
        ...,
        description="AI provider to use",
        examples=["ollama", "gemini"],
    )
    model: str = Field(
        ...,
        description="Model name",
        examples=["llama3.2", "gemini-2.5-pro"],
    )
    message: str = Field(
        ...,
        min_length=1,
        description="User message for this turn",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Existing session ID to continue. Null = create new session",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="System prompt (only used when creating a new session)",
    )
```

### Step 4: Tambah response schemas di `app/schemas/responses.py`
Tambahkan di akhir file, setelah class `ErrorResponse`:

```python
class ChatResponse(BaseModel):
    """
    Response for POST /chat endpoint.

    Contains the AI-generated response and session metadata.
    """

    session_id: str = Field(
        ..., description="Session UUID (new or existing)"
    )
    output: str = Field(
        ..., description="Generated AI response text"
    )
    provider: str = Field(
        ..., description="Provider that generated the response"
    )
    model: str = Field(
        ..., description="Model that generated the response"
    )
    usage: Optional[UsageInfo] = Field(
        default=None, description="Token usage statistics"
    )
    turn_count: int = Field(
        ..., description="Total messages in this session"
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Additional provider-specific metadata"
    )


class ChatMessageSchema(BaseModel):
    """
    Schema for a single chat message in history.
    """

    role: str = Field(
        ..., description="Message role: user, assistant, or system"
    )
    content: str = Field(
        ..., description="Message text content"
    )
    timestamp: float = Field(
        ..., description="Unix timestamp when message was created"
    )
    model: Optional[str] = Field(
        default=None, description="Model used (only for assistant messages)"
    )


class ChatHistoryResponse(BaseModel):
    """
    Response for GET /chat/{session_id}/history endpoint.

    Contains full conversation history and session metadata.
    """

    session_id: str = Field(
        ..., description="Session UUID"
    )
    provider: str = Field(
        ..., description="Provider used for this session"
    )
    model: str = Field(
        ..., description="Model used for this session"
    )
    messages: list[ChatMessageSchema] = Field(
        ..., description="Ordered list of all messages in the session"
    )
    created_at: float = Field(
        ..., description="Unix timestamp when session was created"
    )
    last_active: float = Field(
        ..., description="Unix timestamp of last activity"
    )
    turn_count: int = Field(
        ..., description="Total messages in this session"
    )
```

### Step 5: Update `.env`
Tambahkan di akhir file:
```env
# --- Conversation History ---
# Max messages per session (trim FIFO, system prompt preserved)
CHAT_MAX_HISTORY=50
# Session TTL in minutes (auto-expire inactive sessions)
CHAT_SESSION_TTL=30
```

### Step 6: Update `.env.example`
Sama seperti `.env`:
```env
# --- Conversation History ---
CHAT_MAX_HISTORY=50
CHAT_SESSION_TTL=30
```

## 6. Output yang Diharapkan

Setelah task selesai, verifikasi dengan script:
```python
from app.config import settings
from app.core.exceptions import SessionNotFoundError
from app.schemas.requests import ChatRequest
from app.schemas.responses import ChatResponse, ChatMessageSchema, ChatHistoryResponse

# Config
assert settings.APP_VERSION == "0.2.2"
assert settings.CHAT_MAX_HISTORY == 50
assert settings.CHAT_SESSION_TTL == 30

# SessionNotFoundError
try:
    raise SessionNotFoundError("abc-123")
except SessionNotFoundError as e:
    assert e.message == "Chat session 'abc-123' not found or expired"
    assert e.code == "SESSION_NOT_FOUND"

# ChatRequest — new session
req = ChatRequest(provider="ollama", model="llama3.2", message="Hello")
assert req.session_id is None
assert req.system_prompt is None

# ChatRequest — continue session
req2 = ChatRequest(
    provider="ollama", model="llama3.2",
    message="Follow up", session_id="abc-123"
)
assert req2.session_id == "abc-123"

# ChatResponse
resp = ChatResponse(
    session_id="abc", output="Hello!", provider="ollama",
    model="llama3.2", turn_count=2
)
assert resp.turn_count == 2

# ChatHistoryResponse
hist = ChatHistoryResponse(
    session_id="abc", provider="ollama", model="llama3.2",
    messages=[], created_at=0.0, last_active=0.0, turn_count=0
)
assert hist.messages == []

print("All checks passed!")
```

## 7. Dependencies
- Tidak ada (task pertama, foundation layer)

## 8. Acceptance Criteria
- [ ] `settings.CHAT_MAX_HISTORY` accessible, default `50`
- [ ] `settings.CHAT_SESSION_TTL` accessible, default `30`
- [ ] `APP_VERSION` = `"0.2.2"`
- [ ] `SessionNotFoundError("id")` → message `"Chat session 'id' not found or expired"`, code `"SESSION_NOT_FOUND"`
- [ ] `ChatRequest` validates: provider (enum), model (str), message (min_length=1), session_id (optional), system_prompt (optional)
- [ ] `ChatResponse` has: session_id, output, provider, model, usage (optional), turn_count, metadata (optional)
- [ ] `ChatMessageSchema` has: role, content, timestamp, model (optional)
- [ ] `ChatHistoryResponse` has: session_id, provider, model, messages, created_at, last_active, turn_count
- [ ] `.env` punya `CHAT_MAX_HISTORY` dan `CHAT_SESSION_TTL`
- [ ] Server bisa start tanpa error: `uvicorn app.main:app --reload --port 8000`
- [ ] Semua existing tests tetap PASS

## 9. Estimasi
Low (~25 menit)
