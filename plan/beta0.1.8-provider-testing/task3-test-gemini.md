# Task 3 — GeminiProvider Unit Tests

> **Modul**: beta0.1.8 — Provider Testing  
> **Estimasi**: Medium (60–90 menit)  
> **Dependencies**: Task 1 (Setup Testing Environment)

---

## 1. Judul Task

Implementasi `tests/providers/test_gemini_provider.py` — Unit test lengkap untuk semua method GeminiProvider menggunakan `unittest.mock`.

---

## 2. Deskripsi

Membuat test suite yang mem-mock `genai.Client` internal sehingga SDK tidak pernah memanggil Google API asli. Test mencover `generate()`, `stream()`, `embedding()`, `_build_contents()`, error handling, dan multimodal support.

---

## 3. Tujuan Teknis

- Test `generate()`: mock `client.models.generate_content`, verifikasi output parsing dan usage metadata
- Test `stream()`: mock `client.models.generate_content_stream` sebagai iterable, verifikasi token extraction
- Test `embedding()`: mock `client.models.embed_content`, verifikasi vector extraction
- Test `_build_contents()`: text-only vs multimodal contents building
- Test error handling: string-matching untuk timeout, connection, 429, 403, 404
- Test helpers: `supports_image()`, `name`, `close()`

---

## 4. Scope

### ✅ Yang Dikerjakan
- Semua test di `tests/providers/test_gemini_provider.py`
- Fully mocked — tidak perlu GEMINI_API_KEY atau internet

### ❌ Yang Tidak Dikerjakan
- Integration test dengan Gemini API asli
- Test endpoint/service layer

---

## 5. Langkah Implementasi

### Step 1: Buat test file dengan test cases berikut

**Pola Mock (unittest.mock):**

```python
# Mock generate response
mock_response = MagicMock()
mock_response.text = "Hello from Gemini!"
mock_response.usage_metadata = MagicMock(
    prompt_token_count=5,
    candidates_token_count=8,
    total_token_count=13,
)
provider._client.models.generate_content.return_value = mock_response
```

```python
# Mock stream response (iterable chunks)
chunk1, chunk2 = MagicMock(), MagicMock()
chunk1.text = "Hello"
chunk2.text = " world"
provider._client.models.generate_content_stream.return_value = [chunk1, chunk2]
```

```python
# Mock embedding response
mock_embedding = MagicMock()
mock_embedding.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
provider._client.models.embed_content.return_value = mock_embedding
```

**Test Classes:**
1. `TestGeminiGenerate` — 5 tests: success, usage metadata, timeout error, connection error, API error (429)
2. `TestGeminiStream` — 4 tests: success, chunk extraction, timeout error, API error
3. `TestGeminiEmbedding` — 4 tests: success, empty embedding error, timeout error, API 404 error
4. `TestGeminiBuildContents` — 2 tests: text-only, with images
5. `TestGeminiHelpers` — 3 tests: supports_image, name, close

**Pola Error Mock (exception string matching):**
```python
# Timeout
provider._client.models.generate_content.side_effect = Exception("Deadline exceeded")
# → pytest.raises(ProviderTimeoutError)

# Connection
provider._client.models.generate_content.side_effect = Exception("Network unreachable")
# → pytest.raises(ProviderConnectionError)

# Rate limit
provider._client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED")
# → pytest.raises(ProviderAPIError), status 429
```

### Step 2: Jalankan test
```powershell
.\venv\Scripts\pytest tests/providers/test_gemini_provider.py -v
```

---

## 6. Output yang Diharapkan

18 test cases, semua PASS. Tidak perlu API key atau internet.

---

## 7. Dependencies
- **Task 1** — pytest, pytest-mock installed, `gemini_provider` fixture di conftest.

---

## 8. Acceptance Criteria

- [ ] Minimal 18 test cases
- [ ] Semua PASS tanpa GEMINI_API_KEY atau internet
- [ ] generate() success: output text, usage metadata parsed
- [ ] stream() success: tokens extracted dari mock chunks
- [ ] embedding() success: vector list[float] extracted
- [ ] Empty embedding → ProviderAPIError
- [ ] Timeout keywords → ProviderTimeoutError
- [ ] Connection keywords → ProviderConnectionError
- [ ] HTTP status codes (429, 403, 404) detected dari error string
- [ ] _build_contents() text-only: returns [prompt]
- [ ] _build_contents() with images: returns [prompt, Part, ...]
- [ ] supports_image() returns True
- [ ] close() completes without error

---

## 9. Estimasi

**Medium** — Mock SDK objects lebih complex dari HTTP mock, tapi polanya konsisten.
