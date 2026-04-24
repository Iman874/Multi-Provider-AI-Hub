# Task 1 — Config & Exception Update

> **Modul**: beta0.1.9 — Multi API Key Management  
> **Estimasi**: Low (20 menit)  
> **Dependencies**: Tidak ada (standalone, paling fundamental)

---

## 1. Judul Task

Menambahkan field konfigurasi multi API key di `Settings` dan exception `AllKeysExhaustedError`.

---

## 2. Deskripsi

Update konfigurasi aplikasi agar mendukung penyimpanan banyak API key di `.env` (comma-separated), dan menambahkan exception baru yang akan digunakan saat semua key di pool telah habis/rate-limited.

---

## 3. Tujuan Teknis

- Field baru `OLLAMA_API_KEYS` dan `GEMINI_API_KEYS` di class `Settings`
- Exception baru `AllKeysExhaustedError` di `app/core/exceptions.py`
- File `.env` diperbarui dengan format multi-key
- File `.env.example` dibuat sebagai template

---

## 4. Scope

### ✅ Yang Dikerjakan
- Edit `app/config.py` — tambah 2 field baru
- Edit `app/core/exceptions.py` — tambah 1 exception
- Edit `.env` — tambah variabel baru
- Buat `.env.example` — template untuk user baru

### ❌ Yang Tidak Dikerjakan
- Parsing key ke list (itu Task 2 / Task 5)
- Koneksi ke provider (itu Task 3 & 4)

---

## 5. Langkah Implementasi

### Step 1: Edit `app/config.py`

Tambahkan 2 field baru di class `Settings`:

```python
# --- Ollama (Local LLM) ---
OLLAMA_BASE_URL: str = "http://localhost:11434"
OLLAMA_TIMEOUT: int = 120
OLLAMA_API_KEYS: str = ""  # ← BARU: Ollama Cloud keys, comma-separated

# --- Google Gemini ---
GEMINI_API_KEY: str = ""           # Single key (backward compatible)
GEMINI_API_KEYS: str = ""          # ← BARU: Multi-key, comma-separated
GEMINI_TIMEOUT: int = 120
```

### Step 2: Edit `app/core/exceptions.py`

Tambahkan exception baru di akhir file:

```python
class AllKeysExhaustedError(AIGatewayError):
    """Raised when all API keys in the pool are rate-limited or blacklisted."""

    def __init__(self, provider: str):
        super().__init__(
            message=f"All API keys for '{provider}' are exhausted or rate-limited",
            code="ALL_KEYS_EXHAUSTED",
        )
```

### Step 3: Update `.env`

Tambahkan variabel baru (tanpa menghapus yang lama):

```env
# --- Ollama (Local LLM) ---
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=120
# Ollama Cloud API keys (comma-separated, opsional)
OLLAMA_API_KEYS=750d793cdb974fb9a33f5a30e43bfed8.mjEnjL1YjTnlA674XgQVuii3

# --- Google Gemini ---
GEMINI_API_KEY=<your-single-key-here>
GEMINI_API_KEYS=<key1>,<key2>,<key3>
GEMINI_TIMEOUT=120
```

### Step 4: Buat `.env.example`

```env
# ============================================
# AI Generative Core — Configuration
# ============================================

# --- App ---
APP_NAME=AI Generative Core
APP_VERSION=0.1.9
DEBUG=true

# --- Ollama (Local LLM) ---
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=120
# Ollama Cloud API keys (comma-separated, opsional)
# Dibutuhkan untuk model cloud (glm-5.1:cloud, qwen3.5:397b-cloud, dsb)
# Jika kosong, hanya model lokal yang bisa dipakai
OLLAMA_API_KEYS=

# --- Google Gemini ---
# Multi-key support (comma-separated, prioritas utama)
GEMINI_API_KEYS=
# Single key (backward compatible, dipakai jika GEMINI_API_KEYS kosong)
GEMINI_API_KEY=
GEMINI_TIMEOUT=120

# --- Logging ---
LOG_LEVEL=DEBUG
LOG_FORMAT=text
```

### Step 5: Verifikasi

```powershell
.\venv\Scripts\python -c "from app.config import settings; print('OLLAMA_API_KEYS:', repr(settings.OLLAMA_API_KEYS)); print('GEMINI_API_KEYS:', repr(settings.GEMINI_API_KEYS))"
```

```powershell
.\venv\Scripts\python -c "from app.core.exceptions import AllKeysExhaustedError; e = AllKeysExhaustedError('gemini'); print(e.message, e.code)"
```

---

## 6. Output yang Diharapkan

### `app/config.py` — field baru

```python
OLLAMA_API_KEYS: str = ""
GEMINI_API_KEYS: str = ""
```

### `app/core/exceptions.py` — exception baru

```python
class AllKeysExhaustedError(AIGatewayError):
    def __init__(self, provider: str):
        super().__init__(
            message=f"All API keys for '{provider}' are exhausted or rate-limited",
            code="ALL_KEYS_EXHAUSTED",
        )
```

### Verifikasi output

```
OLLAMA_API_KEYS: '750d793cdb974fb9a33f5a30e43bfed8.mjEnjL1YjTnlA674XgQVuii3'
GEMINI_API_KEYS: ''
All API keys for 'gemini' are exhausted or rate-limited ALL_KEYS_EXHAUSTED
```

---

## 7. Dependencies

Tidak ada — ini task pertama dan paling fundamental.

---

## 8. Acceptance Criteria

- [ ] `settings.OLLAMA_API_KEYS` bisa diakses tanpa error
- [ ] `settings.GEMINI_API_KEYS` bisa diakses tanpa error
- [ ] `settings.GEMINI_API_KEY` (single, lama) tetap ada dan berfungsi
- [ ] `AllKeysExhaustedError` bisa di-raise dengan provider name
- [ ] `AllKeysExhaustedError` punya `message` dan `code` yang benar
- [ ] `.env.example` ada sebagai template
- [ ] Server bisa startup normal dengan `.env` baru

---

## 9. Estimasi

**Low** — Hanya menambah field dan exception, tidak ada logic rumit.
