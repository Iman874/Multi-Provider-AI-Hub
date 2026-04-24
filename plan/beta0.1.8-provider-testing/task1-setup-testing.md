# Task 1 — Setup Testing Environment

> **Modul**: beta0.1.8 — Provider Testing  
> **Estimasi**: Low (30 menit)  
> **Dependencies**: Tidak ada (standalone setup)

---

## 1. Judul Task

Konfigurasi `pytest`, `pytest-asyncio`, `respx`, dan `pytest-mock` — plus buat `tests/conftest.py` dengan fixture global.

---

## 2. Deskripsi

Menambahkan semua dependency testing ke `requirements.txt`, membuat struktur direktori `tests/providers/`, dan menyiapkan `conftest.py` dengan fixture yang akan digunakan oleh test Ollama dan Gemini. Fixture mencakup inisialisasi provider dengan mock client.

---

## 3. Tujuan Teknis

- Tambah `pytest`, `pytest-asyncio`, `pytest-mock`, dan `respx` ke `requirements.txt`
- Buat `tests/__init__.py` dan `tests/providers/__init__.py`
- Buat `tests/conftest.py` dengan:
  - Konfigurasi `pytest-asyncio` mode `auto`
  - Fixture `ollama_provider` yang return `OllamaProvider` instance (pointing ke dummy URL)
  - Fixture `gemini_provider` yang return `GeminiProvider` instance (dengan mock API key)
- Pastikan `pytest` bisa dieksekusi tanpa error dari root directory

---

## 4. Scope

### ✅ Yang Dikerjakan

- Update `requirements.txt` dengan testing dependencies
- Buat struktur direktori `tests/`
- Buat `conftest.py` dengan fixture provider

### ❌ Yang Tidak Dikerjakan

- Test case (dilakukan di Task 2 dan Task 3)
- CI/CD integration
- Coverage configuration

---

## 5. Langkah Implementasi

### Step 1: Update `requirements.txt`

Tambahkan baris berikut di akhir file:

```text
# --- Testing ---
pytest>=8.0
pytest-asyncio>=0.24
pytest-mock>=3.14
respx>=0.22
```

### Step 2: Install dependencies

```powershell
.\venv\Scripts\pip install -r requirements.txt
```

### Step 3: Buat struktur direktori

```
tests/
├── __init__.py
├── conftest.py
└── providers/
    ├── __init__.py
    ├── test_ollama_provider.py   ← (kosong dulu, Task 2)
    └── test_gemini_provider.py   ← (kosong dulu, Task 3)
```

### Step 4: Buat `tests/__init__.py`

```python
"""AI Generative Core — Test Suite."""
```

### Step 5: Buat `tests/providers/__init__.py`

```python
"""Provider unit tests."""
```

### Step 6: Buat `tests/conftest.py`

```python
"""
Global test fixtures for AI Generative Core.

Provides pre-configured provider instances with mocked external dependencies.
All fixtures are designed so tests run WITHOUT any external services
(no Ollama, no Gemini API key, no internet connection required).
"""

import pytest
from unittest.mock import MagicMock, patch

from app.providers.ollama import OllamaProvider


# --- OllamaProvider Fixture ---

@pytest.fixture
def ollama_provider():
    """
    Create an OllamaProvider instance pointed at a dummy URL.

    The httpx client inside will be intercepted by `respx` in individual
    tests, so no real HTTP calls are made.
    """
    provider = OllamaProvider(
        base_url="http://localhost:11434",
        timeout=30,
    )
    return provider


# --- GeminiProvider Fixture ---

@pytest.fixture
def gemini_provider():
    """
    Create a GeminiProvider with a mocked genai.Client.

    We patch `genai.Client` so the SDK never makes real API calls.
    The mock client is accessible via `provider._client`.
    """
    with patch("app.providers.gemini.genai.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client

        from app.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="test-fake-api-key",
            timeout=30,
        )
        # Ensure the provider uses the mock client
        provider._client = mock_client
        yield provider
```

### Step 7: Buat placeholder test files

`tests/providers/test_ollama_provider.py`:
```python
"""OllamaProvider unit tests — implemented in Task 2."""
```

`tests/providers/test_gemini_provider.py`:
```python
"""GeminiProvider unit tests — implemented in Task 3."""
```

### Step 8: Verifikasi pytest berjalan

```powershell
.\venv\Scripts\pytest tests/ -v --co
```

Output yang diharapkan (no tests collected yet, tapi no errors):

```
============================== no tests ran ===============================
```

---

## 6. Output yang Diharapkan

### Struktur File Akhir

```
tests/
├── __init__.py
├── conftest.py
└── providers/
    ├── __init__.py
    ├── test_ollama_provider.py
    └── test_gemini_provider.py
```

### `requirements.txt` (bagian baru)

```text
# --- Testing ---
pytest>=8.0
pytest-asyncio>=0.24
pytest-mock>=3.14
respx>=0.22
```

---

## 7. Dependencies

- Tidak ada dependency ke task lain (standalone)

---

## 8. Acceptance Criteria

- [ ] `pytest`, `pytest-asyncio`, `pytest-mock`, `respx` ada di `requirements.txt`
- [ ] Semua testing packages terinstall di venv
- [ ] `tests/__init__.py` ada
- [ ] `tests/providers/__init__.py` ada
- [ ] `tests/conftest.py` ada dengan fixture `ollama_provider` dan `gemini_provider`
- [ ] `.\venv\Scripts\pytest tests/ -v` berjalan tanpa error (0 test collected OK)
- [ ] Fixture `gemini_provider` mem-patch `genai.Client` agar tidak memanggil API asli

---

## 9. Estimasi

**Low** — Setup konfigurasi dan boilerplate, tidak ada logic testing.
