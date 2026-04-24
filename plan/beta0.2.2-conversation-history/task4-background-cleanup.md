# Task 4 — Background Session Cleanup

## 1. Judul Task
Implementasi background asyncio task untuk auto-cleanup expired sessions

## 2. Deskripsi
Menambahkan background async loop yang berjalan periodik (setiap 5 menit) untuk membersihkan chat sessions yang sudah melewati TTL. Task ini distart saat application startup dan di-cancel saat shutdown, terintegrasi dengan FastAPI lifespan.

## 3. Tujuan Teknis
- Background task berjalan periodik setiap 300 detik (5 menit)
- Memanggil `SessionManager.cleanup_expired()` setiap interval
- Di-start di lifespan startup, di-cancel cleanly di lifespan shutdown
- Log cleanup activity (berapa session dihapus)
- Tidak memblokir startup/shutdown

## 4. Scope
### Yang dikerjakan
- `app/main.py` — tambah `_session_cleanup_loop()` async function dan integrasikan ke `lifespan()`

### Yang TIDAK dikerjakan
- Modifikasi SessionManager (sudah selesai di Task 2)
- Endpoint baru — tidak ada
- Unit tests — Task 5

## 5. Langkah Implementasi

### Step 1: Tambah import `asyncio` di `app/main.py`
Di bagian imports (baris atas file), tambahkan:
```python
import asyncio
```

### Step 2: Tambah import `get_session_manager` di `app/main.py`
Update import dari `app.api.dependencies`:
```python
from app.api.dependencies import initialize_services, get_providers, get_session_manager
```

### Step 3: Definisikan `_session_cleanup_loop()` async function
Tambahkan SEBELUM `lifespan()` function (setelah imports, sebelum `@asynccontextmanager`):

```python
async def _session_cleanup_loop(interval: int = 300):
    """
    Background task — periodically cleanup expired chat sessions.

    Runs every `interval` seconds (default 5 minutes).
    Calls SessionManager.cleanup_expired() to remove sessions
    that exceeded their TTL.

    Args:
        interval: Seconds between cleanup runs (default 300 = 5 minutes).
    """
    while True:
        await asyncio.sleep(interval)
        try:
            session_mgr = get_session_manager()
            count = session_mgr.cleanup_expired()
            if count > 0:
                logger.info(
                    "Session cleanup: removed {n} expired sessions",
                    n=count,
                )
        except Exception as e:
            logger.error("Session cleanup error: {err}", err=str(e))
```

### Step 4: Integrasikan ke `lifespan()` — startup
Tambahkan setelah `initialize_services(settings)` dan setelah Ollama connectivity test, SEBELUM `yield`:

```python
    # Start background session cleanup task
    cleanup_task = asyncio.create_task(
        _session_cleanup_loop(),
        name="session-cleanup",
    )
    logger.info("Session cleanup task started (interval: 5min)")
```

### Step 5: Integrasikan ke `lifespan()` — shutdown
Tambahkan SEBELUM providers close loop, SEBELUM shutdown log:

```python
    # Cancel background cleanup task
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("Session cleanup task stopped")
```

### Step 6: Hasil akhir `lifespan()` function
Setelah semua perubahan, `lifespan()` akan terlihat seperti:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # === STARTUP ===
    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
    )

    logger.info("=" * 50)
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 50)
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Ollama URL: {settings.OLLAMA_BASE_URL}")
    logger.info(
        f"Gemini API Key: {'configured' if settings.GEMINI_API_KEY else 'not set'}"
    )

    # Initialize services (providers, registry, generator, session manager)
    initialize_services(settings)

    # Test Ollama connectivity
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                logger.info("Ollama connection: OK")
            else:
                logger.warning(f"Ollama returned status {resp.status_code}")
    except Exception:
        logger.warning(
            "Ollama not reachable at {url} - requests will fail until Ollama is started",
            url=settings.OLLAMA_BASE_URL,
        )

    # Start background session cleanup task
    cleanup_task = asyncio.create_task(
        _session_cleanup_loop(),
        name="session-cleanup",
    )
    logger.info("Session cleanup task started (interval: 5min)")

    yield

    # === SHUTDOWN ===
    # Cancel background cleanup task
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("Session cleanup task stopped")

    providers = get_providers()
    for name, provider in providers.items():
        await provider.close()
        logger.debug(f"Closed provider: {name}")

    logger.info("Shutting down AI Generative Core...")
```

## 6. Output yang Diharapkan

**Startup log:**
```
Session cleanup task started (interval: 5min)
```

**Cleanup log (saat ada expired sessions):**
```
Session cleanup: removed 3 expired sessions
```

**Shutdown log:**
```
Session cleanup task stopped
Shutting down AI Generative Core...
```

**Verifikasi behavior:**
1. Start server → log menunjukkan cleanup task started
2. Buat beberapa session via `POST /chat`
3. Tunggu TTL expired (set `CHAT_SESSION_TTL=1` untuk testing cepat = 1 menit)
4. Setelah cleanup interval → session otomatis dihapus
5. `GET /chat/{session_id}/history` → 404

## 7. Dependencies
- **Task 1** — Config fields (`CHAT_SESSION_TTL`)
- **Task 2** — `SessionManager.cleanup_expired()`
- **Task 3** — `get_session_manager()` dependency

## 8. Acceptance Criteria
- [ ] `_session_cleanup_loop()` berjalan sebagai asyncio background task
- [ ] Cleanup berjalan setiap 5 menit (300 detik)
- [ ] Expired sessions (TTL) berhasil dihapus otomatis
- [ ] Cleanup log muncul hanya jika ada session yang dihapus
- [ ] Error dalam cleanup tidak crash keseluruhan aplikasi (try-catch)
- [ ] Task di-cancel cleanly saat shutdown (no unfinished task warnings)
- [ ] Server start tanpa error
- [ ] Semua existing tests tetap PASS

## 9. Estimasi
Low (~15 menit)
