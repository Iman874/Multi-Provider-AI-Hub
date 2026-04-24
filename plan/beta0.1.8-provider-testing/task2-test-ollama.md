# Task 2 — OllamaProvider Unit Tests

> **Modul**: beta0.1.8 — Provider Testing  
> **Estimasi**: Medium (60–90 menit)  
> **Dependencies**: Task 1 (Setup Testing Environment)

---

## 1. Judul Task

Implementasi `tests/providers/test_ollama_provider.py` — Unit test lengkap untuk semua method OllamaProvider.

---

## 2. Deskripsi

Membuat test suite menggunakan `respx` untuk mock HTTP. Mencover `generate()`, `stream()`, `embedding()`, error handling, dan image support.

---

## 3. Tujuan Teknis

- Test `generate()`: payload, response parsing, image stripping, errors
- Test `stream()`: NDJSON parsing, malformed JSON, empty lines, errors
- Test `embedding()`: stub `NotImplementedError`
- Test helpers: `supports_image()`, `name`, `close()`

---

## 4. Scope

### ✅ Yang Dikerjakan
- Semua test di `tests/providers/test_ollama_provider.py`
- Fully mocked — tidak perlu Ollama running

### ❌ Yang Tidak Dikerjakan
- Integration test dengan Ollama asli
- Test endpoint/service layer

---

## 5. Langkah Implementasi

### Step 1: Buat test file dengan test cases berikut

**Test Classes:**
1. `TestOllamaGenerate` — 6 tests: success, payload format, with images, HTTP error, timeout, connection error
2. `TestOllamaStream` — 6 tests: success NDJSON, malformed JSON skip, empty lines skip, HTTP error, timeout, connection error
3. `TestOllamaEmbedding` — 1 test: NotImplementedError
4. `TestOllamaHelpers` — 3 tests: supports_image, name, close

**Pola Mock (respx):**
```python
@respx.mock
@pytest.mark.asyncio
async def test_generate_success(self, provider):
    respx.post("http://test-ollama:11434/api/generate").mock(
        return_value=httpx.Response(200, json={
            "model": "gemma4:e2b", "response": "Hello!", "done": True,
            "prompt_eval_count": 5, "eval_count": 8,
        })
    )
    result = await provider.generate(model="gemma4:e2b", prompt="Hi")
    assert result["output"] == "Hello!"
    assert result["provider"] == "ollama"
    assert result["usage"]["total_tokens"] == 13
```

**Pola Error Mock:**
```python
respx.post(...).mock(side_effect=httpx.TimeoutException("timed out"))
# → pytest.raises(ProviderTimeoutError)

respx.post(...).mock(side_effect=httpx.ConnectError("refused"))
# → pytest.raises(ProviderConnectionError)

respx.post(...).mock(return_value=httpx.Response(404, text="not found"))
# → pytest.raises(ProviderAPIError)
```

### Step 2: Jalankan test
```powershell
.\venv\Scripts\pytest tests/providers/test_ollama_provider.py -v
```

---

## 6. Output yang Diharapkan

16 test cases, semua PASS. Tidak perlu Ollama service berjalan.

---

## 7. Dependencies
- **Task 1** — pytest, respx installed dan struktur tests/ ada.

---

## 8. Acceptance Criteria

- [ ] Minimal 16 test cases
- [ ] Semua PASS tanpa Ollama running
- [ ] generate() success path validated
- [ ] generate() image data URI stripping verified
- [ ] stream() NDJSON parsing correct
- [ ] Malformed JSON skipped gracefully
- [ ] Error exceptions mapped correctly (Timeout, Connection, API)
- [ ] supports_image() returns True
- [ ] close() closes httpx client

---

## 9. Estimasi

**Medium** — Banyak test case tapi polanya repetitif.
