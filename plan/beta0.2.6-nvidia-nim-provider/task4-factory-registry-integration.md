# Task 4 — Factory, Registry, Health Checker & Integration

## 1. Judul Task
Register NvidiaProvider di factory, tambah model defaults ke registry, tambah health probe, dan update dependency injection

## 2. Deskripsi
Mengintegrasikan `NvidiaProvider` ke dalam seluruh gateway infrastructure: provider factory (`create_provider()`), model registry (default NVIDIA models), health checker (probe via `GET /models`), dan dependency injection layer.

## 3. Tujuan Teknis
- `create_provider("nvidia", settings)` → `NvidiaProvider` instance (atau `None` jika key kosong)
- Model registry mempunyai 3 NVIDIA default models
- Health checker bisa probe NVIDIA via `GET /v1/models`
- Startup flow otomatis initialize NVIDIA provider

## 4. Scope

### Termasuk
- `app/providers/__init__.py` — tambah `case "nvidia"` di factory
- `app/services/model_registry.py` — register 3 NVIDIA default models
- `app/services/health_checker.py` — tambah `_probe_nvidia()` method
- `app/api/dependencies.py` — tambah `"nvidia"` ke `provider_names` list

### Tidak Termasuk
- NvidiaProvider class (Task 3 — sudah selesai)
- Unit tests (Task 5)
- Multimodal/vision support

## 5. Langkah Implementasi

### Step 1: Tambah factory case di `app/providers/__init__.py`

Import `NvidiaProvider`:
```python
from app.providers.nvidia import NvidiaProvider
```

Tambah case di `create_provider()`:
```python
case "nvidia":
    if not settings.NVIDIA_API_KEY:
        logger.warning("NVIDIA NIM provider skipped: no API key configured")
        return None

    logger.info("NVIDIA NIM: API key loaded")

    return NvidiaProvider(
        api_key=settings.NVIDIA_API_KEY,
        base_url=settings.NVIDIA_BASE_URL,
        timeout=settings.NVIDIA_TIMEOUT,
    )
```

### Step 2: Register NVIDIA default models di `app/services/model_registry.py`

Tambahkan setelah section Gemini models di `register_defaults()`:

```python
# --- NVIDIA NIM models ---
nvidia_defaults = [
    ModelCapability(
        name="meta/llama-3.3-70b-instruct",
        provider="nvidia",
        supports_text=True,
        supports_image=False,
        supports_streaming=True,
        supports_embedding=False,
    ),
    ModelCapability(
        name="deepseek-ai/deepseek-r1",
        provider="nvidia",
        supports_text=True,
        supports_image=False,
        supports_streaming=True,
        supports_embedding=False,
    ),
    ModelCapability(
        name="nvidia/nv-embedqa-e5-v5",
        provider="nvidia",
        supports_text=False,
        supports_image=False,
        supports_streaming=False,
        supports_embedding=True,
    ),
]

for model in nvidia_defaults:
    self.register(model)
```

### Step 3: Tambah health probe di `app/services/health_checker.py`

Tambah method `_probe_nvidia()`:
```python
async def _probe_nvidia(self) -> tuple[bool, float, str | None]:
    """Probe NVIDIA NIM via HTTP GET /models."""
    provider = self._providers.get("nvidia")
    if provider is None:
        return False, 0.0, "Provider not configured"

    base_url = getattr(provider, "_base_url", "https://integrate.api.nvidia.com/v1")
    api_key = getattr(provider, "_api_key", "")
    start = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            latency = (time.perf_counter() - start) * 1000

            if resp.status_code == 200:
                return True, latency, None
            elif resp.status_code in (401, 403):
                return True, latency, "Auth issue (reachable)"
            else:
                return False, latency, f"HTTP {resp.status_code}"
    except httpx.TimeoutException:
        latency = (time.perf_counter() - start) * 1000
        return False, latency, "Timeout"
    except httpx.ConnectError:
        latency = (time.perf_counter() - start) * 1000
        return False, latency, "Connection refused"
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return False, latency, str(e)[:100]
```

Tambah case di `_probe()` dispatcher:
```python
case "nvidia":
    return await self._probe_nvidia()
```

### Step 4: Update dependency injection di `app/api/dependencies.py`
Ubah provider_names list:
```python
provider_names = ["ollama", "gemini", "nvidia"]  # ← tambah "nvidia"
```

## 6. Output yang Diharapkan

Server startup log:
```
INFO: NvidiaProvider initialized: https://integrate.api.nvidia.com/v1 (timeout=120s)
INFO: NVIDIA NIM: API key loaded
INFO: Active providers: ['ollama', 'gemini', 'nvidia']
INFO: Registered 9 default models
```

API verification:
```bash
curl http://localhost:8000/api/v1/models?provider=nvidia
# Returns 3 NVIDIA models

curl http://localhost:8000/health/providers
# Shows nvidia: { status: "up", latency_ms: ... }
```

## 7. Dependencies
- Task 2 (config fields)
- Task 3 (NvidiaProvider class)

## 8. Acceptance Criteria
- [x] `create_provider("nvidia", settings)` returns `NvidiaProvider` instance
- [x] `create_provider("nvidia", settings)` returns `None` jika `NVIDIA_API_KEY` kosong
- [x] 3 NVIDIA models ter-register di ModelRegistry defaults
- [x] `_probe_nvidia()` probe via `GET /models` (lightweight, no tokens)
- [x] Health probe handle 401/403 sebagai "reachable" (degraded)
- [x] `"nvidia"` ada di `provider_names` list di startup
- [x] `GET /api/v1/models?provider=nvidia` menampilkan NVIDIA models
- [x] Server start tanpa error saat `NVIDIA_API_KEY` kosong (graceful skip)
- [x] Semua existing tests tetap PASS

## 9. Estimasi
Low (~30 menit)
