# Task 4 — Unit Tests

## 1. Judul Task
Implementasi unit tests untuk `BatchService` — 10 test cases

## 2. Deskripsi
Membuat test suite komprehensif untuk `BatchService` yang memvalidasi: batch success, partial failure, size validation, cache integration, concurrency limit, dan provider/model validation. Semua provider calls di-mock.

## 3. Tujuan Teknis
- 10 test cases di `tests/services/test_batch_service.py`
- Semua provider interactions di-mock (tidak ada real API calls)
- Cover: happy path, error path, edge cases, validation

## 4. Scope
### Yang dikerjakan
- `tests/services/test_batch_service.py` — file baru, 10 test cases

### Yang TIDAK dikerjakan
- Integration / E2E tests
- Test terhadap real providers

## 5. Langkah Implementasi

### Step 1: Buat file `tests/services/test_batch_service.py`

**Fixtures yang dibutuhkan:**
- `mock_generator` — `GeneratorService` dengan mocked providers dan registry
- `batch_service` — `BatchService(generator=mock_generator, max_size=5, concurrency=2)`

**Mock strategy:**
- Mock `GeneratorService.generate()` → return `GenerateResponse(output="...", provider="...", model="...", metadata={"cached": False})`
- Mock `GeneratorService.embedding()` → return `EmbeddingResponse(embedding=[0.1, 0.2], provider="...", model="...")`
- Mock `GeneratorService._get_provider()` → return mock provider
- Mock `GeneratorService._registry.get_model()` → return `ModelCapability`

### Step 2: Implementasi 10 Test Cases

**1. `test_batch_generate_success`** — 3 items, mock generate returns output → all succeed, `succeeded=3`, `failed=0`

**2. `test_batch_embedding_success`** — 3 texts, mock embedding returns vector → all succeed, `succeeded=3`, `failed=0`

**3. `test_batch_partial_failure`** — 3 items, mock generate raises exception on item index 1 → `succeeded=2`, `failed=1`, item 1 has `status="error"`

**4. `test_batch_too_large`** — 10 items with `max_size=5` → `BatchTooLargeError` raised

**5. `test_batch_single_item`** — 1 item batch → works same as individual, `total=1`, `succeeded=1`

**6. `test_batch_cache_integration`** — mock generate returns response with `metadata={"cached": True}` → result has `cached=True`

**7. `test_batch_concurrency_limit`** — verify semaphore limits concurrent calls. Use `asyncio.Event` to track max concurrent tasks

**8. `test_batch_provider_validation`** — mock `_get_provider()` to raise `ProviderNotFoundError` → error raised before any item processing

**9. `test_batch_model_validation`** — mock `_registry.get_model()` to raise `ModelNotFoundError` → error raised before any item processing

**10. `test_batch_empty_rejected`** — verify `BatchGenerateRequest(items=[])` raises Pydantic `ValidationError` (min_length=1)

### Step 3: Run tests dan verifikasi

```bash
.\venv\Scripts\pytest tests/services/test_batch_service.py -v
```

Semua 10 tests harus PASS.

Juga jalankan full suite:
```bash
.\venv\Scripts\pytest tests/ -v
```

Semua 104 + 10 = 114 tests harus PASS.

## 6. Output yang Diharapkan

```
tests/services/test_batch_service.py::test_batch_generate_success PASSED
tests/services/test_batch_service.py::test_batch_embedding_success PASSED
tests/services/test_batch_service.py::test_batch_partial_failure PASSED
tests/services/test_batch_service.py::test_batch_too_large PASSED
tests/services/test_batch_service.py::test_batch_single_item PASSED
tests/services/test_batch_service.py::test_batch_cache_integration PASSED
tests/services/test_batch_service.py::test_batch_concurrency_limit PASSED
tests/services/test_batch_service.py::test_batch_provider_validation PASSED
tests/services/test_batch_service.py::test_batch_model_validation PASSED
tests/services/test_batch_service.py::test_batch_empty_rejected PASSED

========== 10 passed ==========
```

## 7. Dependencies
- **Task 1** — Schemas dan exception
- **Task 2** — `BatchService` class
- **Task 3** — Integration (optional, tests mock everything)

## 8. Acceptance Criteria
- [ ] File `tests/services/test_batch_service.py` ada
- [ ] 10 test cases diimplementasi
- [ ] Semua 10 tests PASS
- [ ] Semua existing 104 tests tetap PASS
- [ ] Test coverage: success, failure, partial failure, validation, cache, concurrency
- [ ] Tidak ada real provider calls (fully mocked)

## 9. Estimasi
Medium (~45 menit)
