# Task 3 — Chat Endpoints, Router & Dependency Wiring

## 1. Judul Task
Implementasi 3 chat endpoints (`POST /chat`, `GET /chat/{id}/history`, `DELETE /chat/{id}`), register di router, dan wiring `SessionManager` di dependencies

## 2. Deskripsi
Membangun endpoint layer lengkap untuk fitur Conversation History: endpoint chat utama yang mengelola session lifecycle dan memanggil `GeneratorService`, endpoint history, endpoint delete, serta integrasi ke dependency injection dan router.

## 3. Tujuan Teknis
- `POST /api/v1/chat` — create/continue session, panggil generator, simpan response
- `GET /api/v1/chat/{session_id}/history` — return semua messages
- `DELETE /api/v1/chat/{session_id}` — hapus session
- `SessionManager` tersedia sebagai FastAPI dependency via `get_session_manager()`
- `SessionNotFoundError` di-map ke HTTP 404 di exception handler
- Router include chat endpoint

## 4. Scope
### Yang dikerjakan
- `app/api/endpoints/chat.py` — file baru (3 endpoints)
- `app/api/dependencies.py` — tambah `_session_manager` singleton + `get_session_manager()` + update `initialize_services()`
- `app/api/router.py` — register chat router
- `app/main.py` — tambah `SESSION_NOT_FOUND` ke `status_map` di exception handler

### Yang TIDAK dikerjakan
- Background cleanup loop — Task 4
- Unit tests — Task 5
- Streaming di chat endpoint (gunakan `/stream` terpisah)

## 5. Langkah Implementasi

### Step 1: Update `app/api/dependencies.py`
Tambah import `SessionManager` dan singleton:

```python
# Di bagian imports, tambahkan:
from app.services.session_manager import SessionManager

# Di bagian singleton instances, tambahkan:
_session_manager: SessionManager | None = None
```

Tambahkan getter function setelah `get_generator_service()`:
```python
def get_session_manager() -> SessionManager:
    """FastAPI dependency: provides SessionManager instance."""
    if _session_manager is None:
        raise RuntimeError("SessionManager not initialized. Call initialize_services() first.")
    return _session_manager
```

Update `initialize_services()` — di akhir function, sebelum penutup, tambahkan:
```python
    # Tambah ke global declaration:
    global _model_registry, _generator_service, _providers, _session_manager

    # --- 4. Create Session Manager ---
    _session_manager = SessionManager(
        max_history=settings.CHAT_MAX_HISTORY,
        ttl_minutes=settings.CHAT_SESSION_TTL,
    )
```

### Step 2: Buat `app/api/endpoints/chat.py`

```python
"""
Chat endpoints — Multi-turn conversation with server-side history.

Provides session management for stateful AI conversations.
Sessions are stored in-memory and auto-expire after TTL.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_generator_service, get_session_manager
from app.schemas.requests import ChatRequest, GenerateRequest
from app.schemas.responses import (
    ChatResponse,
    ChatHistoryResponse,
    ChatMessageSchema,
    ErrorResponse,
    UsageInfo,
)
from app.services.generator import GeneratorService
from app.services.session_manager import SessionManager

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Multi-turn chat conversation",
    description="Send a message in a conversation. "
    "If session_id is null, a new session is created. "
    "If session_id is provided, the existing session is continued.",
    responses={
        404: {"model": ErrorResponse, "description": "Session not found or expired"},
        502: {"model": ErrorResponse, "description": "Provider connection error"},
        504: {"model": ErrorResponse, "description": "Provider timeout"},
    },
)
async def chat(
    request: ChatRequest,
    generator: GeneratorService = Depends(get_generator_service),
    session_mgr: SessionManager = Depends(get_session_manager),
) -> ChatResponse:
    """
    Handle a chat turn: create/continue session, generate AI response.

    Flow:
    1. Create new session or get existing session
    2. Add user message to session history
    3. Build prompt from full history
    4. Call GeneratorService with full context prompt
    5. Add assistant response to session history
    6. Return ChatResponse with session metadata
    """
    # 1. Create or continue session
    if request.session_id is None:
        # New session
        session = session_mgr.create_session(
            provider=request.provider.value,
            model=request.model,
            system_prompt=request.system_prompt,
        )
    else:
        # Continue existing session
        session = session_mgr.get_session(request.session_id)

    session_id = session.session_id

    # 2. Add user message to history
    session_mgr.add_message(session_id, "user", request.message)

    # 3. Build prompt from full history
    prompt = session_mgr.build_prompt(session_id)

    # 4. Call generator with full context
    generate_request = GenerateRequest(
        provider=request.provider,
        model=request.model,
        input=prompt,
    )
    result = await generator.generate(generate_request)

    # 5. Add assistant response to history
    session_mgr.add_message(
        session_id, "assistant", result.output, model=result.model
    )

    # 6. Return response
    return ChatResponse(
        session_id=session_id,
        output=result.output,
        provider=result.provider,
        model=result.model,
        usage=result.usage,
        turn_count=len(session_mgr.get_history(session_id)),
        metadata=result.metadata,
    )


@router.get(
    "/chat/{session_id}/history",
    response_model=ChatHistoryResponse,
    summary="Get chat session history",
    description="Retrieve the full conversation history for a session.",
    responses={
        404: {"model": ErrorResponse, "description": "Session not found or expired"},
    },
)
async def get_chat_history(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
) -> ChatHistoryResponse:
    """Return full conversation history for a session."""
    session = session_mgr.get_session(session_id)
    messages = [
        ChatMessageSchema(
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp,
            model=msg.model,
        )
        for msg in session.messages
    ]
    return ChatHistoryResponse(
        session_id=session.session_id,
        provider=session.provider,
        model=session.model,
        messages=messages,
        created_at=session.created_at,
        last_active=session.last_active,
        turn_count=len(session.messages),
    )


@router.delete(
    "/chat/{session_id}",
    summary="Delete chat session",
    description="Delete a chat session and its history.",
    responses={
        404: {"model": ErrorResponse, "description": "Session not found or expired"},
    },
)
async def delete_chat_session(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
) -> dict:
    """Delete a chat session."""
    session_mgr.delete_session(session_id)
    return {
        "status": "deleted",
        "session_id": session_id,
    }
```

### Step 3: Update `app/api/router.py`
Tambah import dan register chat router:

```python
# Di imports, tambahkan:
from app.api.endpoints import models, generate, stream, embedding, chat

# Register router, tambahkan baris baru:
api_router.include_router(chat.router, tags=["Chat"])
```

### Step 4: Update exception handler di `app/main.py`
Tambahkan `SESSION_NOT_FOUND` ke `status_map` di `gateway_error_handler()`:

```python
status_map = {
    "PROVIDER_NOT_FOUND": 404,
    "MODEL_NOT_FOUND": 404,
    "SESSION_NOT_FOUND": 404,        # ← TAMBAH INI
    "CAPABILITY_NOT_SUPPORTED": 400,
    "PROVIDER_CONNECTION_ERROR": 502,
    "PROVIDER_TIMEOUT": 504,
    "PROVIDER_API_ERROR": 502,
}
```

### Step 5: Update `app/api/endpoints/__init__.py`
Pastikan `chat` module ter-expose (jika menggunakan explicit imports). Jika file `__init__.py` kosong atau auto-discover, step ini bisa di-skip. Cek konten saat ini:
```python
# Jika ada explicit imports, tambahkan:
# from app.api.endpoints import chat
```

## 6. Output yang Diharapkan

Setelah task selesai, tes manual via curl/httpie:

**Create new session:**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"llama3.2","message":"Hello, who are you?"}'
```
Expected response:
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "output": "I am a helpful AI assistant...",
    "provider": "ollama",
    "model": "llama3.2",
    "usage": null,
    "turn_count": 2,
    "metadata": null
}
```

**Continue session:**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"llama3.2","message":"What was my first question?","session_id":"<id dari response sebelumnya>"}'
```
Expected: Response yang aware terhadap context dari pesan sebelumnya. `turn_count` naik.

**Get history:**
```bash
curl http://localhost:8000/api/v1/chat/<session_id>/history
```
Expected: JSON dengan semua messages ordered chronologically.

**Delete session:**
```bash
curl -X DELETE http://localhost:8000/api/v1/chat/<session_id>
```
Expected: `{"status": "deleted", "session_id": "..."}`

**Invalid session_id:**
```bash
curl http://localhost:8000/api/v1/chat/invalid-uuid/history
```
Expected: `{"error": "Chat session 'invalid-uuid' not found or expired", "code": "SESSION_NOT_FOUND"}` (HTTP 404)

## 7. Dependencies
- **Task 1** — Config fields, exception, Pydantic schemas
- **Task 2** — `SessionManager` service

## 8. Acceptance Criteria
- [ ] `POST /api/v1/chat` — new session (session_id=null) → 200 + session_id + output
- [ ] `POST /api/v1/chat` — continue session (session_id=valid) → 200 + accumulated history
- [ ] `POST /api/v1/chat` — invalid session_id → 404 `SESSION_NOT_FOUND`
- [ ] `GET /api/v1/chat/{session_id}/history` → 200 + ordered messages
- [ ] `GET /api/v1/chat/{session_id}/history` — invalid id → 404
- [ ] `DELETE /api/v1/chat/{session_id}` → 200 + confirmation
- [ ] `DELETE /api/v1/chat/{session_id}` — invalid id → 404
- [ ] `SessionManager` diinisialisasi di `initialize_services()` dengan config values
- [ ] `get_session_manager()` tersedia sebagai FastAPI dependency
- [ ] Chat router terdaftar di `api_router` dengan tag "Chat"
- [ ] `turn_count` di response = jumlah total messages di session (termasuk system prompt)
- [ ] Prompt yang dikirim ke generator berisi full history context
- [ ] Server start tanpa error
- [ ] Endpoint muncul di Swagger UI (`/docs`)
- [ ] Semua existing tests tetap PASS

## 9. Estimasi
Medium (~45 menit)
