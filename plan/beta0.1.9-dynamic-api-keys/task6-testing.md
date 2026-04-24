# Task 6 — Unit Tests

> **Modul**: beta0.1.9 — Multi API Key Management  
> **Estimasi**: Medium (60 menit)  
> **Dependencies**: Task 1–5 (semua task sebelumnya)

---

## 1. Judul Task

Implementasi unit test untuk `KeyManager`, Ollama Cloud auth, dan Gemini multi-key — plus pastikan 35 existing test tetap PASS.

---

## 2. Deskripsi

Membuat test suite baru untuk `KeyManager` service dan update test provider yang ada agar sesuai dengan perubahan constructor (sekarang pakai `KeyManager` alih-alih `api_key`). Semua test harus fully mocked — tidak perlu API key asli atau koneksi internet.

---

## 3. Tujuan Teknis

- Test suite `KeyManager`: round-robin, blacklist, cooldown, masking
- Update fixture `gemini_provider` di `conftest.py` (sekarang pakai `KeyManager`)
- Test Ollama: request dengan/tanpa auth header
- Test Gemini: retry saat 429
- Zero-regression: 35 existing test tetap PASS

---

## 4. Scope

### ✅ Yang Dikerjakan
- Buat `tests/services/__init__.py`
- Buat `tests/services/test_key_manager.py` — 8+ test cases
- Update `tests/conftest.py` — fixture pakai `KeyManager`
- Update `tests/providers/test_ollama_provider.py` — 2+ test baru
- Update `tests/providers/test_gemini_provider.py` — 2+ test baru

### ❌ Yang Tidak Dikerjakan
- Integration test (hit API asli)
- E2E test

---

## 5. Langkah Implementasi

### Step 1: Buat `tests/services/__init__.py`

```python
"""Service unit tests."""
```

### Step 2: Buat `tests/services/test_key_manager.py`

```python
"""
Unit tests for KeyManager service.
"""

import time

import pytest

from app.core.exceptions import AllKeysExhaustedError
from app.services.key_manager import KeyManager


class TestKeyManagerRoundRobin:
    """Tests for round-robin key selection."""

    def test_round_robin_3_keys(self):
        """Keys rotate in order: A → B → C → A."""
        km = KeyManager("test", ["A", "B", "C"])
        assert km.get_key() == "A"
        assert km.get_key() == "B"
        assert km.get_key() == "C"
        assert km.get_key() == "A"  # wraps around

    def test_single_key(self):
        """Single key always returned."""
        km = KeyManager("test", ["only-key"])
        assert km.get_key() == "only-key"
        assert km.get_key() == "only-key"


class TestKeyManagerBlacklist:
    """Tests for blacklist/failure handling."""

    def test_blacklist_skip(self):
        """Blacklisted key is skipped."""
        km = KeyManager("test", ["A", "B", "C"], cooldown=60)
        km.report_failure("A")
        # A is blacklisted, should get B
        assert km.get_key() == "B"

    def test_cooldown_expire(self):
        """Blacklisted key returns after cooldown expires."""
        km = KeyManager("test", ["A", "B"], cooldown=1)
        km.report_failure("A")
        # A is blacklisted
        assert km.get_key() == "B"
        # Wait for cooldown
        time.sleep(1.1)
        # A should be back (index may vary, but A is available)
        keys_gotten = {km.get_key() for _ in range(3)}
        assert "A" in keys_gotten

    def test_all_exhausted(self):
        """All keys blacklisted raises AllKeysExhaustedError."""
        km = KeyManager("test", ["A", "B"], cooldown=60)
        km.report_failure("A")
        km.report_failure("B")
        with pytest.raises(AllKeysExhaustedError):
            km.get_key()

    def test_report_success_clears_blacklist(self):
        """report_success removes key from blacklist."""
        km = KeyManager("test", ["A", "B"], cooldown=60)
        km.report_failure("A")
        assert km.available_count == 1
        km.report_success("A")
        assert km.available_count == 2


class TestKeyManagerProperties:
    """Tests for properties and utilities."""

    def test_empty_pool(self):
        """Empty key pool raises on get_key."""
        km = KeyManager("test", [])
        assert km.has_keys is False
        assert km.total_count == 0
        with pytest.raises(AllKeysExhaustedError):
            km.get_key()

    def test_has_keys(self):
        """has_keys is True when keys exist."""
        km = KeyManager("test", ["A"])
        assert km.has_keys is True

    def test_total_count(self):
        """total_count returns number of keys."""
        km = KeyManager("test", ["A", "B", "C"])
        assert km.total_count == 3

    def test_available_count(self):
        """available_count excludes blacklisted keys."""
        km = KeyManager("test", ["A", "B", "C"], cooldown=60)
        assert km.available_count == 3
        km.report_failure("A")
        assert km.available_count == 2

    def test_mask_key(self):
        """mask_key shows only last 4 chars."""
        assert KeyManager.mask_key("abcdefghijkl") == "***jkl"

    def test_mask_key_short(self):
        """mask_key handles short keys."""
        assert KeyManager.mask_key("ab") == "***ab"

    def test_whitespace_stripped(self):
        """Keys with whitespace are stripped on init."""
        km = KeyManager("test", ["  A  ", " B ", "C"])
        assert km.get_key() == "A"
        assert km.get_key() == "B"

    def test_empty_strings_filtered(self):
        """Empty strings in key list are filtered out."""
        km = KeyManager("test", ["A", "", "  ", "B"])
        assert km.total_count == 2
```

### Step 3: Update `tests/conftest.py`

Update fixture `gemini_provider` agar menggunakan `KeyManager`:

```python
from app.services.key_manager import KeyManager

@pytest.fixture
def gemini_provider():
    """GeminiProvider with mocked client and KeyManager."""
    with patch("app.providers.gemini.genai.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client

        # Buat KeyManager dengan fake keys
        key_manager = KeyManager("gemini_test", ["fake-key-1", "fake-key-2"])

        from app.providers.gemini import GeminiProvider
        provider = GeminiProvider(key_manager=key_manager, timeout=30)

        # Override internal client for tests that mock directly
        provider._client = mock_client
        yield provider
```

Update fixture `ollama_provider` agar menerima opsional `KeyManager`:

```python
@pytest.fixture
def ollama_provider():
    """OllamaProvider without cloud keys (local mode)."""
    return OllamaProvider(base_url="http://test-ollama:11434", timeout=30)

@pytest.fixture
def ollama_provider_cloud():
    """OllamaProvider with cloud key manager."""
    km = KeyManager("ollama_cloud_test", ["test-cloud-key-abc"])
    return OllamaProvider(
        base_url="http://test-ollama:11434",
        timeout=30,
        key_manager=km,
    )
```

### Step 4: Tambah test Ollama Cloud di `test_ollama_provider.py`

```python
class TestOllamaCloudAuth:
    """Tests for Ollama Cloud authentication headers."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_cloud_sends_auth_header(self, ollama_provider_cloud):
        """Cloud provider sends Authorization header."""
        route = respx.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(200, json={
                "response": "cloud reply", "done": True,
            })
        )

        await ollama_provider_cloud.generate(model="glm-5.1:cloud", prompt="Hi")

        request = route.calls[0].request
        assert "Authorization" in request.headers
        assert request.headers["Authorization"].startswith("Bearer ")

    @respx.mock
    @pytest.mark.asyncio
    async def test_local_no_auth_header(self, ollama_provider):
        """Local provider does NOT send Authorization header."""
        route = respx.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(200, json={
                "response": "local reply", "done": True,
            })
        )

        await ollama_provider.generate(model="gemma4:e2b", prompt="Hi")

        request = route.calls[0].request
        assert "Authorization" not in request.headers
```

### Step 5: Update test Gemini di `test_gemini_provider.py`

Existing tests perlu update karena provider sekarang pakai `_get_client()` bukan `self._client` langsung. Pastikan mock masih bekerja — kemungkinan perlu patch `_get_client()` atau update cara mock bekerja.

Tambah test retry:

```python
class TestGeminiKeyRotation:
    """Tests for Gemini multi-key retry."""

    @pytest.mark.asyncio
    async def test_retry_on_429(self, gemini_provider):
        """429 on first key triggers retry with second key."""
        # First call: 429 error
        # Second call: success
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("429 RESOURCE_EXHAUSTED")
            mock_response = MagicMock()
            mock_response.text = "Success on retry"
            mock_response.usage_metadata = None
            return mock_response

        gemini_provider._client.models.generate_content.side_effect = side_effect

        result = await gemini_provider.generate(
            model="gemini-2.5-pro", prompt="Test"
        )
        assert "Success" in result["output"] or call_count == 2
```

### Step 6: Jalankan seluruh test suite

```powershell
.\venv\Scripts\pytest tests/ -v
```

---

## 6. Output yang Diharapkan

```
tests/services/test_key_manager.py::TestKeyManagerRoundRobin::test_round_robin_3_keys PASSED
tests/services/test_key_manager.py::TestKeyManagerRoundRobin::test_single_key PASSED
tests/services/test_key_manager.py::TestKeyManagerBlacklist::test_blacklist_skip PASSED
tests/services/test_key_manager.py::TestKeyManagerBlacklist::test_cooldown_expire PASSED
tests/services/test_key_manager.py::TestKeyManagerBlacklist::test_all_exhausted PASSED
tests/services/test_key_manager.py::TestKeyManagerBlacklist::test_report_success_clears_blacklist PASSED
tests/services/test_key_manager.py::TestKeyManagerProperties::test_empty_pool PASSED
tests/services/test_key_manager.py::TestKeyManagerProperties::test_has_keys PASSED
tests/services/test_key_manager.py::TestKeyManagerProperties::test_total_count PASSED
tests/services/test_key_manager.py::TestKeyManagerProperties::test_available_count PASSED
tests/services/test_key_manager.py::TestKeyManagerProperties::test_mask_key PASSED
tests/services/test_key_manager.py::TestKeyManagerProperties::test_mask_key_short PASSED
tests/services/test_key_manager.py::TestKeyManagerProperties::test_whitespace_stripped PASSED
tests/services/test_key_manager.py::TestKeyManagerProperties::test_empty_strings_filtered PASSED
tests/providers/test_ollama_provider.py::TestOllamaCloudAuth::test_cloud_sends_auth_header PASSED
tests/providers/test_ollama_provider.py::TestOllamaCloudAuth::test_local_no_auth_header PASSED
... (35 existing tests) ...

============================== 51+ passed ===============================
```

---

## 7. Dependencies

- **Task 1–5** — semua kode produksi harus selesai dulu

---

## 8. Acceptance Criteria

- [ ] `tests/services/test_key_manager.py` ada dengan 14 test cases
- [ ] `tests/providers/test_ollama_provider.py` punya 2 test baru (cloud auth)
- [ ] `tests/providers/test_gemini_provider.py` punya test retry 429
- [ ] Semua 35 existing test tetap PASS (zero-regression)
- [ ] Total test suite: 51+ tests, semua PASS
- [ ] `.\venv\Scripts\pytest tests/ -v` exit code 0

---

## 9. Estimasi

**Medium** — Banyak test case tapi banyak yang bisa copy-paste polanya.
