# Task 5 — Unit Tests

## 1. Judul Task
Buat comprehensive unit tests untuk `NvidiaProvider` menggunakan `respx` mocking

## 2. Deskripsi
Menulis unit test suite yang mencakup semua method di `NvidiaProvider`: generate, stream, embedding, auth header, error handling, dan helper methods. Semua HTTP calls di-mock menggunakan `respx` — tidak butuh NVIDIA API key atau koneksi internet.

## 3. Tujuan Teknis
- 17 test cases yang cover seluruh NvidiaProvider behavior
- Zero dependency pada external API (fully mocked)
- Test both success path dan error paths
- Verify NVIDIA-specific quirks (SSE format, `input_type` untuk embedding)

## 4. Scope

### Termasuk
- `tests/providers/test_nvidia_provider.py` — full test suite
  - **TestNvidiaGenerate** (6 tests): success, payload format, auth header, HTTP error, timeout, connection error
  - **TestNvidiaStream** (4 tests): success, skip empty deltas, HTTP error, timeout
  - **TestNvidiaEmbedding** (4 tests): success, input_type verification, empty error, HTTP error
  - **TestNvidiaHelpers** (3 tests): supports_image, name property, close

### Tidak Termasuk
- Integration tests (real API calls)
- Performance/load tests
- Health checker tests for NVIDIA

## 5. Langkah Implementasi

### Step 1: Buat fixture
```python
@pytest.fixture
def nvidia_provider():
    return NvidiaProvider(
        api_key="nvapi-test-key-123",
        base_url="https://test-nvidia.api.com/v1",
        timeout=30,
    )
```

### Step 2: Test generate — success path
Mock `POST /chat/completions` return OpenAI format response.
Verify normalized output: `output`, `provider`, `model`, `usage`, `metadata`.

### Step 3: Test generate — payload format
Verify request body is OpenAI chat format:
```json
{
    "model": "...",
    "messages": [{"role": "user", "content": "..."}],
    "max_tokens": 4096
}
```

### Step 4: Test generate — auth header
Verify `Authorization: Bearer nvapi-test-key-123` is sent.

### Step 5: Test generate — error cases
- HTTP 401 → `ProviderAPIError` with "HTTP 401"
- `httpx.TimeoutException` → `ProviderTimeoutError`
- `httpx.ConnectError` → `ProviderConnectionError`

### Step 6: Test stream — success path
Mock SSE response:
```
data: {"choices":[{"delta":{"content":"Hello"}}]}
data: {"choices":[{"delta":{"content":" world"}}]}
data: [DONE]
```
Verify tokens: `["Hello", " world", "!"]`

### Step 7: Test stream — edge cases
- Empty `delta.content` → skipped
- Role-only delta (no content key) → skipped

### Step 8: Test embedding — success + input_type
Verify `input_type: "query"` is in request body.
Verify `data[0].embedding` is extracted correctly.

### Step 9: Test embedding — empty data
Empty `data` array → `ProviderAPIError` with "Empty embedding returned"

### Step 10: Test helpers
- `name` → `"nvidia"`
- `supports_image()` → `False`
- `close()` → `_client.is_closed` is True

## 6. Output yang Diharapkan

```
tests/providers/test_nvidia_provider.py::TestNvidiaGenerate::test_generate_success PASSED
tests/providers/test_nvidia_provider.py::TestNvidiaGenerate::test_generate_payload_format PASSED
tests/providers/test_nvidia_provider.py::TestNvidiaGenerate::test_generate_sends_auth_header PASSED
tests/providers/test_nvidia_provider.py::TestNvidiaGenerate::test_generate_http_error PASSED
tests/providers/test_nvidia_provider.py::TestNvidiaGenerate::test_generate_timeout PASSED
tests/providers/test_nvidia_provider.py::TestNvidiaGenerate::test_generate_connection_error PASSED
tests/providers/test_nvidia_provider.py::TestNvidiaStream::test_stream_success PASSED
tests/providers/test_nvidia_provider.py::TestNvidiaStream::test_stream_skips_empty_deltas PASSED
tests/providers/test_nvidia_provider.py::TestNvidiaStream::test_stream_http_error PASSED
tests/providers/test_nvidia_provider.py::TestNvidiaStream::test_stream_timeout PASSED
tests/providers/test_nvidia_provider.py::TestNvidiaEmbedding::test_embedding_success PASSED
tests/providers/test_nvidia_provider.py::TestNvidiaEmbedding::test_embedding_sends_input_type PASSED
tests/providers/test_nvidia_provider.py::TestNvidiaEmbedding::test_embedding_empty_error PASSED
tests/providers/test_nvidia_provider.py::TestNvidiaEmbedding::test_embedding_http_error PASSED
tests/providers/test_nvidia_provider.py::TestNvidiaHelpers::test_supports_image_returns_false PASSED
tests/providers/test_nvidia_provider.py::TestNvidiaHelpers::test_name_property PASSED
tests/providers/test_nvidia_provider.py::TestNvidiaHelpers::test_close PASSED

17 passed in 0.28s
```

Full regression: **131 passed** (114 existing + 17 new)

## 7. Dependencies
- Task 3 (NvidiaProvider class)

## 8. Acceptance Criteria
- [x] 17 test cases semua PASS
- [x] Generate: success, payload, auth, HTTP error, timeout, connection error
- [x] Stream: success, skip empty deltas, HTTP error, timeout
- [x] Embedding: success, input_type verified, empty error, HTTP error
- [x] Helpers: name, supports_image, close
- [x] Full test suite 131 passed — zero regressions
- [x] No real API calls (fully mocked via respx)

## 9. Estimasi
Low (~45 menit)
