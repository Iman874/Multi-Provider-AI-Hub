# Task 4 — Background Monitor & Startup Integration

## 1. Judul Task
Inisialisasi `HealthChecker` di startup, jalankan initial check, dan start background health monitor loop

## 2. Deskripsi
Menghubungkan `HealthChecker` service ke application lifecycle: inisialisasi di `initialize_services()`, jalankan initial health check saat startup (menggantikan ad-hoc Ollama check yang ada), dan start background asyncio task yang memprobe semua provider secara periodik.

## 3. Tujuan Teknis
- `HealthChecker` diinisialisasi di `initialize_services()` dengan config values
- Initial `check_all()` saat startup (menggantikan ad-hoc Ollama check di `lifespan`)
- Background `_health_monitor_loop()` berjalan setiap `HEALTH_CHECK_INTERVAL` detik
- Task di-cancel cleanly saat shutdown
- Ad-hoc Ollama connectivity check dihapus (diganti health checker)

## 4. Scope
### Yang dikerjakan
- `app/api/dependencies.py` — init `HealthChecker` di `initialize_services()`
- `app/main.py` — hapus ad-hoc Ollama check, tambah `_health_monitor_loop()`, integrasikan ke `lifespan()`

### Yang TIDAK dikerjakan
- HealthChecker logic (sudah Task 2)
- Endpoints (sudah Task 3)
- Unit tests — Task 5

## 5. Langkah Implementasi

### Step 1: Update `app/api/dependencies.py` — init HealthChecker
Di `initialize_services()`, tambahkan inisialisasi HealthChecker setelah pembuatan GeneratorService.

**Update global declaration:**
```python
global _model_registry, _generator_service, _providers, _health_checker
```

**Tambahkan section baru di akhir `initialize_services()`:**
```python
    # --- 4. Create Health Checker ---
    _health_checker = HealthChecker(
        providers=_providers,
        timeout=settings.HEALTH_CHECK_TIMEOUT,
        threshold=settings.HEALTH_CHECK_THRESHOLD,
    )
```

> **Note**: Pastikan import `HealthChecker` sudah ada dari Task 3.

### Step 2: Tambah `_health_monitor_loop()` di `app/main.py`
Tambah import `asyncio` (jika belum ada) dan definisikan function SEBELUM `lifespan()`:

```python
import asyncio
```

```python
async def _health_monitor_loop(interval: int = 30):
    """
    Background task — periodically probe all providers for health status.

    Runs every `interval` seconds. Logs warnings for DOWN providers.

    Args:
        interval: Seconds between health check runs.
    """
    while True:
        await asyncio.sleep(interval)
        try:
            health_checker = get_health_checker()
            if health_checker is None:
                continue
            statuses = await health_checker.check_all()
            for name, status in statuses.items():
                if status.status == "down":
                    logger.warning(
                        "Provider '{name}' is DOWN: {err}",
                        name=name,
                        err=status.error_message,
                    )
        except Exception as e:
            logger.error("Health monitor error: {err}", err=str(e))
```

### Step 3: Update `lifespan()` — HAPUS ad-hoc Ollama check
Hapus blok berikut dari `lifespan()`:
```python
    # HAPUS SELURUH BLOK INI:
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
```

### Step 4: Update `lifespan()` — tambah initial check + monitor task
**SETELAH `initialize_services(settings)`, SEBELUM `yield`, tambahkan:**

```python
    # Initial health check (replaces ad-hoc Ollama check)
    health_checker = get_health_checker()
    if health_checker:
        initial_statuses = await health_checker.check_all()
        for name, status in initial_statuses.items():
            if status.status == "up":
                logger.info(
                    "Provider '{name}': UP (latency: {latency:.1f}ms)",
                    name=name,
                    latency=status.latency_ms or 0,
                )
            elif status.status == "degraded":
                logger.warning(
                    "Provider '{name}': DEGRADED — {err}",
                    name=name,
                    err=status.error_message,
                )
            else:
                logger.warning(
                    "Provider '{name}': DOWN — {err}",
                    name=name,
                    err=status.error_message,
                )

    # Start background health monitor
    health_monitor_task = asyncio.create_task(
        _health_monitor_loop(interval=settings.HEALTH_CHECK_INTERVAL),
        name="health-monitor",
    )
    logger.info(
        "Health monitor started (interval: {interval}s)",
        interval=settings.HEALTH_CHECK_INTERVAL,
    )
```

### Step 5: Update `lifespan()` — shutdown cleanup
**SEBELUM providers close loop, tambahkan:**

```python
    # Cancel background health monitor
    health_monitor_task.cancel()
    try:
        await health_monitor_task
    except asyncio.CancelledError:
        pass
    logger.info("Health monitor stopped")
```

### Step 6: Cleanup unused import
Setelah menghapus ad-hoc Ollama check, cek apakah `httpx` masih dibutuhkan di `app/main.py`. Jika tidak ada penggunaan lain, hapus:
```python
# Hapus jika tidak diperlukan lagi:
import httpx
```

### Step 7: Hasil akhir `lifespan()` function
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

    # Initialize services (providers, registry, generator, health checker)
    initialize_services(settings)

    # Initial health check (replaces ad-hoc Ollama check)
    health_checker = get_health_checker()
    if health_checker:
        initial_statuses = await health_checker.check_all()
        for name, status in initial_statuses.items():
            if status.status == "up":
                logger.info(
                    "Provider '{name}': UP (latency: {latency:.1f}ms)",
                    name=name,
                    latency=status.latency_ms or 0,
                )
            elif status.status == "degraded":
                logger.warning(
                    "Provider '{name}': DEGRADED — {err}",
                    name=name,
                    err=status.error_message,
                )
            else:
                logger.warning(
                    "Provider '{name}': DOWN — {err}",
                    name=name,
                    err=status.error_message,
                )

    # Start background health monitor
    health_monitor_task = asyncio.create_task(
        _health_monitor_loop(interval=settings.HEALTH_CHECK_INTERVAL),
        name="health-monitor",
    )
    logger.info(
        "Health monitor started (interval: {interval}s)",
        interval=settings.HEALTH_CHECK_INTERVAL,
    )

    yield

    # === SHUTDOWN ===
    # Cancel background health monitor
    health_monitor_task.cancel()
    try:
        await health_monitor_task
    except asyncio.CancelledError:
        pass
    logger.info("Health monitor stopped")

    providers = get_providers()
    for name, provider in providers.items():
        await provider.close()
        logger.debug(f"Closed provider: {name}")

    logger.info("Shutting down AI Generative Core...")
```

## 6. Output yang Diharapkan

**Startup log (Ollama running, Gemini key configured):**
```
==================================================
AI Generative Core v0.2.3
==================================================
HealthChecker initialized: providers=['ollama', 'gemini'], timeout=5s, threshold=3
Provider 'ollama': UP (latency: 12.3ms)
Provider 'gemini': UP (latency: 450.1ms)
Health monitor started (interval: 30s)
```

**Startup log (Ollama running, Gemini no key):**
```
Provider 'ollama': UP (latency: 8.5ms)
Health monitor started (interval: 30s)
```

**Background monitor log (saat Ollama mati):**
```
Provider 'ollama' is DOWN: Connection refused
```

**Shutdown log:**
```
Health monitor stopped
Closed provider: ollama
Shutting down AI Generative Core...
```

## 7. Dependencies
- **Task 1** — Config fields (`HEALTH_CHECK_INTERVAL`, `HEALTH_CHECK_TIMEOUT`, `HEALTH_CHECK_THRESHOLD`)
- **Task 2** — `HealthChecker` service
- **Task 3** — `get_health_checker()` dependency

## 8. Acceptance Criteria
- [ ] `HealthChecker` initialized in `initialize_services()` with config values
- [ ] `get_health_checker()` returns initialized instance (not None after startup)
- [ ] Initial `check_all()` runs at startup — replaces ad-hoc Ollama check
- [ ] Ad-hoc Ollama connectivity check (`httpx.AsyncClient` di lifespan) dihapus
- [ ] Startup logs show status per provider (UP/DEGRADED/DOWN)
- [ ] `_health_monitor_loop()` runs as background asyncio task
- [ ] Monitor runs every `HEALTH_CHECK_INTERVAL` seconds
- [ ] DOWN providers logged with warning level
- [ ] Monitor errors caught (try-catch, no crash)
- [ ] Task cancelled cleanly at shutdown (no unfinished task warnings)
- [ ] `GET /health/providers` returns real data after startup
- [ ] Server bisa start tanpa error
- [ ] Semua existing tests tetap PASS

## 9. Estimasi
Low (~25 menit)
