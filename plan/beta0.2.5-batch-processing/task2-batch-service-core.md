# Task 2 — BatchService Core

## 1. Judul Task
Implementasi `BatchService` — orchestrator untuk concurrent batch generation dan embedding

## 2. Deskripsi
Membuat service utama yang memproses batch request secara concurrent menggunakan `asyncio.Semaphore`. Mendelegasikan setiap item ke `GeneratorService` yang sudah ada sehingga caching dan validasi otomatis.

## 3. Tujuan Teknis
- Class `BatchService` di `app/services/batch_service.py`
- Concurrency control via `asyncio.Semaphore`
- `generate_batch()` dan `embedding_batch()` — proses N items concurrent
- Partial failure handling per item

## 4. Scope
### Yang dikerjakan
- `app/services/batch_service.py` — file baru

### Yang TIDAK dikerjakan
- Endpoints / router (Task 3)
- Unit tests (Task 4)

## 5. Langkah Implementasi

### Step 1: Buat file `app/services/batch_service.py`

Buat file baru dengan struktur berikut:

**Imports:**
```python
import asyncio
from loguru import logger
from app.core.exceptions import BatchTooLargeError, ModelCapabilityError
from app.schemas.requests import (
    BatchGenerateRequest, BatchGenerateItem, BatchEmbeddingRequest,
    GenerateRequest, EmbeddingRequest,
)
from app.schemas.responses import (
    BatchGenerateResult, BatchGenerateResponse,
    BatchEmbeddingResult, BatchEmbeddingResponse,
)
from app.services.generator import GeneratorService
```

**Class `BatchService`:**
- `__init__(self, generator: GeneratorService, max_size: int = 20, concurrency: int = 5)` — simpan generator, max_size, buat `asyncio.Semaphore(concurrency)`
- `generate_batch(request)` — validate size → validate provider/model sekali → `asyncio.gather` semua items → build response
- `_process_generate_item(index, item, provider, model)` — acquire semaphore → `GeneratorService.generate()` → return `BatchGenerateResult` (success/error)
- `embedding_batch(request)` — validate size → validate provider/model/capability → `asyncio.gather` → build response
- `_process_embedding_item(index, text, provider, model)` — acquire semaphore → `GeneratorService.embedding()` → return `BatchEmbeddingResult`

**Key logic di `generate_batch()`:**
1. `len(request.items) > self._max_size` → raise `BatchTooLargeError`
2. `self._generator._get_provider(request.provider.value)` — fail fast
3. `self._generator._registry.get_model(...)` — fail fast
4. `asyncio.gather(*tasks)` — semua items concurrent
5. `succeeded = sum(1 for r in results if r.status == "success")`
6. Results sorted by `index`

**Key logic di `_process_generate_item()`:**
1. `async with self._semaphore:` — limit concurrency
2. Build `GenerateRequest` dari item
3. `response = await self._generator.generate(request)`
4. Return `BatchGenerateResult(status="success", output=..., usage=..., cached=...)`
5. `except Exception as e:` → Return `BatchGenerateResult(status="error", error=str(e))`

**Key logic di `embedding_batch()`:**
Same as generate but juga check `supports_embedding` sebelum processing.

## 6. Output yang Diharapkan

File `app/services/batch_service.py` dengan class `BatchService` dan 4 methods. Bisa di-import tanpa error:
```python
from app.services.batch_service import BatchService
```

## 7. Dependencies
- **Task 1** — `BatchTooLargeError`, request/response schemas

## 8. Acceptance Criteria
- [ ] File `app/services/batch_service.py` ada dan importable
- [ ] `asyncio.Semaphore` diinisialisasi dengan concurrency value
- [ ] `generate_batch()` — validate → gather → sorted results
- [ ] `embedding_batch()` — validate + capability check → gather → sorted results
- [ ] Batch size > max → `BatchTooLargeError`
- [ ] Invalid provider/model → error sebelum item processing
- [ ] Item success → `status="success"` + output/embedding
- [ ] Item failure → `status="error"` + error message
- [ ] `succeeded` dan `failed` counts akurat

## 9. Estimasi
Medium (~45 menit)
