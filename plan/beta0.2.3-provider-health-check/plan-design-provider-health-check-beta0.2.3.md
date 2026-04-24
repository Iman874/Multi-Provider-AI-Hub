# Blueprint: AI Generative Core — Provider Health Check (beta0.2.3)

## 1. Visi & Tujuan

Saat ini, Gateway **tidak tahu** apakah provider aktif atau mati sampai request pertama gagal. Masalah:

1. **UX Buruk**: User menunggu timeout 120 detik hanya untuk tahu Ollama belum di-start
2. **Model Registry Tidak Akurat**: `GET /models` tampilkan model dari provider offline
3. **Tidak Ada Monitoring**: Operator tidak bisa lihat kesehatan sistem dari satu endpoint
4. **Ad-hoc Check**: Hanya ada pengecekan Ollama manual di `lifespan`, tidak ada untuk Gemini

Modul **beta0.2.3** membangun **Provider Health Check**:
- Periodik probe ke setiap provider (Ollama: HTTP GET, Gemini: lightweight API call)
- Status `UP` / `DOWN` / `DEGRADED` per provider
- `GET /models` otomatis menyaring model dari provider DOWN
- Endpoint baru: `GET /health/providers` — detail status semua provider
- Background monitor + startup check
- Menggantikan ad-hoc Ollama check di `lifespan`

---

## 2. Scope Development

### ✅ Yang Dikerjakan
- **ProviderStatus Model**: Status, latency, error tracking per provider
- **HealthChecker Service**: Probe logic, status management, threshold tracking
- **Ollama Probe**: `GET /api/tags` → parse response
- **Gemini Probe**: Lightweight `models.list()` call via SDK
- **Smart Model Listing**: `GET /models` filter provider DOWN
- **Health Detail Endpoint**: `GET /health/providers` — status detail
- **Background Monitor**: asyncio task periodik
- **Startup Health Check**: Check semua provider saat boot
- **Unit Tests**

### ❌ Yang Tidak Dikerjakan
- Per-model health check (hanya per-provider level)
- Auto failover antar provider
- External alerting (Prometheus/Grafana)
- Persistent health history (hanya current status)

---

## 3. Arsitektur & Desain

### 3.1. Konfigurasi (`.env`)

```env
# --- Health Check ---
HEALTH_CHECK_INTERVAL=30    # Seconds between checks
HEALTH_CHECK_TIMEOUT=5      # Probe timeout in seconds
HEALTH_CHECK_THRESHOLD=3    # Consecutive failures before DOWN
```

**Config di `app/config.py`**:
```python
HEALTH_CHECK_INTERVAL: int = 30
HEALTH_CHECK_TIMEOUT: int = 5
HEALTH_CHECK_THRESHOLD: int = 3
```

### 3.2. ProviderStatus Model

```python
@dataclass
class ProviderStatus:
    provider: str                     # "ollama" | "gemini"
    status: str                       # "up" | "down" | "degraded"
    last_check: float                 # Unix timestamp of last probe
    last_success: float | None        # Last successful probe timestamp
    consecutive_failures: int         # Failure streak count
    latency_ms: float | None          # Last probe latency in ms
    error_message: str | None         # Last error detail (if any)
```

**Status Definitions:**
- **`up`**: Provider merespon dalam < timeout, no errors
- **`down`**: Provider gagal >= `threshold` kali berturut-turut
- **`degraded`**: Provider merespon tapi lambat (latency > timeout * 500ms) atau partial error (e.g. Gemini 401 = reachable but key issue)

### 3.3. HealthChecker Service (`app/services/health_checker.py`)

```
┌─────────────────────────────────────────────────────────┐
│                  HealthChecker                          │
├─────────────────────────────────────────────────────────┤
│ _providers: dict[str, BaseProvider]                     │
│ _statuses: dict[str, ProviderStatus]                    │
│ _timeout: int                                           │
│ _threshold: int                                         │
├─────────────────────────────────────────────────────────┤
│ async check_provider(name) → ProviderStatus             │
│ async check_all() → dict[str, ProviderStatus]           │
│ get_status(name) → ProviderStatus                       │
│ get_all_statuses() → dict[str, ProviderStatus]          │
│ is_provider_up(name) → bool                             │
│ get_available_providers() → list[str]                    │
│ get_overall_status() → str  ("healthy"|"degraded"|...)  │
└─────────────────────────────────────────────────────────┘
```

### 3.4. Probe Strategies

**Ollama Probe** — HTTP GET ke `/api/tags`:
```python
async def _probe_ollama(self) -> tuple[bool, float, str | None]:
    """
    Returns: (success, latency_ms, error_message)
    """
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{base_url}/api/tags")
            latency = (time.perf_counter() - start) * 1000

            if resp.status_code == 200:
                return True, latency, None
            else:
                return False, latency, f"HTTP {resp.status_code}"
    except httpx.TimeoutException:
        latency = (time.perf_counter() - start) * 1000
        return False, latency, "Timeout"
    except httpx.ConnectError:
        latency = (time.perf_counter() - start) * 1000
        return False, latency, "Connection refused"
```

**Gemini Probe** — Lightweight SDK call:
```python
async def _probe_gemini(self) -> tuple[bool, float, str | None]:
    """
    Uses models.list() — lightweight, no token consumed.
    """
    start = time.perf_counter()
    try:
        # Ambil key dari key_manager (jika ada)
        client, key = provider._get_client()
        # Call models.list() — very lightweight
        models = client.models.list()
        latency = (time.perf_counter() - start) * 1000
        return True, latency, None
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        error_str = str(e)
        # 401/403 = reachable but auth issue → DEGRADED
        if "401" in error_str or "403" in error_str:
            return True, latency, "Auth issue (reachable)"  # Partial success
        return False, latency, error_str[:100]
```

### 3.5. Status Transition Logic

```
                    ┌──────────────────┐
                    │   INITIAL (up)   │
                    └────────┬─────────┘
                             │
              probe success  │  probe fail
              ┌──────────────┤──────────────┐
              ▼              │              ▼
         ┌────────┐          │      consecutive_failures++
         │   UP   │          │              │
         └────┬───┘          │     failures >= threshold?
              │              │       ┌──────┴──────┐
              │              │       NO            YES
              │              │       ▼              ▼
              │              │  (stay current) ┌────────┐
              │              │                 │  DOWN  │
              │              │                 └────┬───┘
              │              │                      │
              │              │              probe success
              │              │                      │
              │              │                      ▼
              │              │                 ┌────────┐
              │              │                 │   UP   │ (recovery)
              │              │                 └────────┘
              │              │
              │    slow response (latency > threshold)?
              │              │
              ▼              ▼
         ┌──────────┐
         │ DEGRADED │
         └──────────┘
```

**Pseudocode `check_provider()`**:
```python
async def check_provider(self, name: str) -> ProviderStatus:
    status = self._statuses.get(name) or ProviderStatus(provider=name, ...)
    success, latency, error = await self._probe(name)

    status.last_check = time.time()
    status.latency_ms = latency
    status.error_message = error

    if success:
        status.consecutive_failures = 0
        status.last_success = time.time()
        # Check for degraded (slow response)
        if latency > self._timeout * 500:  # > 50% of timeout
            status.status = "degraded"
        else:
            status.status = "up"
    else:
        status.consecutive_failures += 1
        if status.consecutive_failures >= self._threshold:
            status.status = "down"
        # else: keep current status (grace period)

    self._statuses[name] = status
    return status
```

### 3.6. Smart Model Listing

Update `GET /api/v1/models`:

```python
# app/api/endpoints/models.py

@router.get("/models")
async def list_models(
    provider: str | None = None,
    include_unavailable: bool = False,  # ← NEW query param
    ...
):
    models = registry.list_models(provider=provider)

    if not include_unavailable and health_checker:
        available = health_checker.get_available_providers()
        models = [m for m in models if m.provider in available]

    # Tambah field "available" di response
    return [
        {
            "name": m.name,
            "provider": m.provider,
            "capabilities": {...},
            "available": health_checker.is_provider_up(m.provider) if health_checker else True,
        }
        for m in models
    ]
```

### 3.7. Health Providers Endpoint

`GET /health/providers` (publik, di luar `/api/v1`):

```json
{
  "status": "degraded",
  "providers": {
    "ollama": {
      "status": "up",
      "last_check": "2026-04-23T10:00:00Z",
      "last_success": "2026-04-23T10:00:00Z",
      "latency_ms": 12.5,
      "consecutive_failures": 0,
      "error": null
    },
    "gemini": {
      "status": "down",
      "last_check": "2026-04-23T10:00:00Z",
      "last_success": "2026-04-23T09:55:00Z",
      "latency_ms": null,
      "consecutive_failures": 5,
      "error": "Connection refused"
    }
  },
  "summary": {
    "total": 2,
    "up": 1,
    "down": 1,
    "degraded": 0
  }
}
```

**Overall status logic:**
- All UP → `"healthy"` | Some UP → `"degraded"` | All DOWN → `"unhealthy"`

### 3.8. Background Monitor

```python
async def _health_monitor_loop(checker: HealthChecker, interval: int):
    """Periodik health check setiap `interval` detik."""
    while True:
        await asyncio.sleep(interval)
        statuses = await checker.check_all()
        for name, s in statuses.items():
            if s.status == "down":
                logger.warning("Provider '{name}' is DOWN: {err}", name=name, err=s.error_message)
```

**Lifecycle:**
- Start: `asyncio.create_task()` di `lifespan` startup (setelah `check_all()` initial)
- Stop: `task.cancel()` di `lifespan` shutdown

---

## 4. Breakdowns (Daftar Task)

### Task 1 — Config & Status Model
**Files**: `app/config.py`, `app/services/health_checker.py` (partial)
- Config fields: `HEALTH_CHECK_INTERVAL`, `HEALTH_CHECK_TIMEOUT`, `HEALTH_CHECK_THRESHOLD`
- Dataclass: `ProviderStatus`
- **Estimasi:** 15 menit

### Task 2 — HealthChecker Service
**Files**: `app/services/health_checker.py`
- Class `HealthChecker` with probe strategies (Ollama HTTP, Gemini SDK)
- Status transition logic with threshold
- `check_provider()`, `check_all()`, `get_status()`, `is_provider_up()`, `get_available_providers()`, `get_overall_status()`
- **Estimasi:** 45 menit

### Task 3 — Smart Model Listing & Health Endpoint
**Files**: `app/api/endpoints/models.py`, `app/main.py`
- Update `GET /models`: `include_unavailable` query param, filter DOWN providers
- New `GET /health/providers`: detail status per provider + summary
- **Estimasi:** 30 menit

### Task 4 — Background Monitor & Startup Integration
**Files**: `app/main.py`, `app/api/dependencies.py`
- Init `HealthChecker` in `initialize_services()`
- Run `check_all()` at startup (replace ad-hoc Ollama check)
- Start `_health_monitor_loop()` background task
- Cancel on shutdown
- **Estimasi:** 25 menit

### Task 5 — Unit Tests
**Files**: `tests/services/test_health_checker.py` (10 tests)
1. `test_ollama_up` — probe success → UP
2. `test_ollama_down` — N failures → DOWN
3. `test_gemini_up` — SDK success → UP
4. `test_gemini_degraded` — auth error but reachable → DEGRADED
5. `test_recovery` — DOWN → success → UP
6. `test_threshold_grace` — 1 failure < threshold → still UP
7. `test_available_providers` — only UP providers returned
8. `test_overall_healthy` — all UP → "healthy"
9. `test_overall_degraded` — mixed → "degraded"
10. `test_models_filtered` — DOWN provider models hidden
- **Estimasi:** 45 menit

---

## 5. Timeline & Estimasi Total

| Task | Scope | Estimasi |
|---|---|---|
| Task 1 | Config & Status Model | 15 menit |
| Task 2 | HealthChecker Service | 45 menit |
| Task 3 | Smart Model Listing & Health Endpoint | 30 menit |
| Task 4 | Background Monitor & Startup | 25 menit |
| Task 5 | Unit Tests | 45 menit |
| **Total** | | **~2.7 jam** |

---

## 6. Acceptance Criteria Global

- [ ] Health check otomatis berjalan saat startup dan periodik
- [ ] Status `up`/`down`/`degraded` per provider
- [ ] Consecutive failure threshold sebelum mark DOWN
- [ ] Recovery otomatis saat provider kembali aktif
- [ ] `GET /models` menyaring model dari provider DOWN (default)
- [ ] `GET /models?include_unavailable=true` tampilkan semua + field `available`
- [ ] `GET /health/providers` menampilkan detail status + summary
- [ ] Overall status: healthy/degraded/unhealthy
- [ ] Latency per-probe diukur dan dilaporkan
- [ ] Ad-hoc Ollama check di startup digantikan health checker
- [ ] Semua existing tests tetap PASS
- [ ] 10 test baru ditambahkan
