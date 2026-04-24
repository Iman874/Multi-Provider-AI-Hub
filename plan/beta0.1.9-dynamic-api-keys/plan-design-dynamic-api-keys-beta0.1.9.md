# Blueprint: AI Generative Core — Multi API Key Management (beta0.1.9)

## 1. Visi & Tujuan

Saat ini, backend memiliki dua kelemahan kritis terkait API key:

1. **Gemini**: Hanya satu API key hardcoded di `.env` → rentan rate limit, single point of failure
2. **Ollama Cloud**: Model cloud di Ollama (seperti `glm-5.1:cloud`, `qwen3.5:397b-cloud`, `gpt-oss:120b-cloud`) membutuhkan API key, tapi saat ini `OllamaProvider` tidak mengirimkan header autentikasi apapun → cloud model pasti gagal

Modul **beta0.1.9** membangun sistem **Multi API Key Pool** yang:
- Mengelola **banyak key** secara **server-side** untuk **kedua provider** (Gemini + Ollama Cloud)
- Frontend **tidak tahu dan tidak perlu tahu** tentang key apapun
- Key dirotasi **otomatis** saat satu key kena rate limit
- **Backward compatible** dengan format `.env` lama

---

## 2. Scope Development

### ✅ Yang Dikerjakan
- **`KeyManager` Service**: Class generik `app/services/key_manager.py` yang bisa dipakai oleh provider manapun
- **Config Update**: Variabel `.env` baru: `GEMINI_API_KEYS` (multi) + `OLLAMA_API_KEYS` (multi)
- **Ollama Cloud Auth**: `OllamaProvider` mengirim header `Authorization: Bearer <key>` saat ada key tersedia
- **Gemini Multi-Key**: `GeminiProvider` menginstansiasi `genai.Client` per-key saat request
- **Key Rotation**: Round-robin + auto-blacklist sementara saat rate limit (429)
- **Exception Baru**: `AllKeysExhaustedError` → HTTP 503

### ❌ Yang Tidak Dikerjakan
- Frontend tidak diubah sama sekali
- Tidak ada database/admin UI untuk manage key
- Per-user key isolation (scope Auth beta0.2.1)
- Ollama Cloud health check (scope beta0.2.3)

---

## 3. Arsitektur & Desain

### 3.1. Key Storage Format (`.env`)

```env
# ============================================
# AI Generative Core — Configuration
# ============================================

# --- App ---
APP_NAME=AI Generative Core
APP_VERSION=0.1.9
DEBUG=true

# --- Ollama ---
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=120

# Ollama Cloud API keys (comma-separated, opsional)
# Dibutuhkan untuk model dengan suffix :cloud (glm-5.1:cloud, dsb)
# Jika kosong, hanya model lokal yang bisa dipakai
OLLAMA_API_KEYS=750d793cdb974fb9a33f5a30e43bfed8.mjEnjL1YjTnlA674XgQVuii3

# --- Google Gemini ---
# Multi-key (comma-separated, prioritas utama)
GEMINI_API_KEYS=key-alpha-123,key-beta-456,key-gamma-789

# Single key (fallback backward compatible)
GEMINI_API_KEY=key-alpha-123

GEMINI_TIMEOUT=120

# --- Logging ---
LOG_LEVEL=DEBUG
LOG_FORMAT=text
```

**Aturan Loading**:
1. Jika `GEMINI_API_KEYS` ada → parse sebagai list (split by comma)
2. Jika hanya `GEMINI_API_KEY` ada → wrap jadi list `[key]`
3. Jika keduanya kosong → Gemini provider di-disable
4. Jika `OLLAMA_API_KEYS` ada → parse sebagai list
5. Jika `OLLAMA_API_KEYS` kosong → Ollama tetap jalan (local models saja, cloud model akan gagal)

### 3.2. KeyManager Service — Class Generik

```
app/services/key_manager.py
```

`KeyManager` adalah class **generik** (bukan provider-specific). Satu instance per provider:
- `gemini_keys = KeyManager(name="gemini", keys=[...])` 
- `ollama_keys = KeyManager(name="ollama_cloud", keys=[...])`

```
┌─────────────────────────────────────────────────┐
│                  KeyManager                     │
├─────────────────────────────────────────────────┤
│ name: str                    # Provider label   │
│ _keys: list[str]             # Semua key        │
│ _index: int                  # Round-robin pos  │
│ _blacklist: dict[str, float] # key → expire_at  │
│ _cooldown: int               # Blacklist (sec)  │
├─────────────────────────────────────────────────┤
│ get_key() → str              # Ambil key aktif  │
│ report_failure(key: str)     # Blacklist key    │
│ report_success(key: str)     # Un-blacklist     │
│ has_keys → bool              # Ada key?         │
│ available_count → int        # Key tersedia     │
│ total_count → int            # Total key        │
│ mask_key(key: str) → str     # "***abc" (log)   │
└─────────────────────────────────────────────────┘
```

**Alur `get_key()`**:
```
START → cek _keys kosong? → True → raise AllKeysExhaustedError
                          → False ↓
Iterasi round-robin dari _index:
  ├── key di _blacklist dan BELUM expire → skip
  ├── key di _blacklist dan SUDAH expire → hapus dari blacklist, return key
  └── key TIDAK di blacklist → return key, geser _index
  
Semua key ter-blacklist → raise AllKeysExhaustedError
```

### 3.3. Ollama Cloud — Header Authentication

Ollama Cloud API menggunakan header `Authorization: Bearer <key>`.

Saat ini `OllamaProvider` membuat satu `httpx.AsyncClient` tanpa header auth. Perubahannya:
- `OllamaProvider.__init__()` menerima `key_manager: Optional[KeyManager]`
- Sebelum setiap HTTP request, jika `key_manager.has_keys`:
  - Ambil key via `key_manager.get_key()`
  - Kirim request dengan header `Authorization: Bearer <key>`
- Jika `key_manager` kosong (tidak ada `OLLAMA_API_KEYS`):
  - Request dikirim TANPA header auth (model lokal tetap berjalan normal)

```
POST /api/generate HTTP/1.1
Host: localhost:11434
Authorization: Bearer 750d793c...XgQVuii3    ← HANYA jika ada key
Content-Type: application/json

{"model": "glm-5.1:cloud", "prompt": "Hello", "stream": false}
```

### 3.4. Gemini — Multi-Key Client Instantiation

`GeminiProvider` saat ini membuat satu `genai.Client(api_key=...)` di `__init__`. Perubahannya:
- `__init__()` menerima `key_manager: KeyManager` alih-alih `api_key: str`
- Setiap `generate()` / `stream()` / `embedding()`:
  1. `key = self._key_manager.get_key()`
  2. `client = genai.Client(api_key=key)`
  3. Call API menggunakan `client` lokal
  4. Sukses → `report_success(key)`
  5. Error 429 → `report_failure(key)` → retry 1x dengan key baru
  6. Error lain → raise seperti biasa

### 3.5. Integration Flow

```
Frontend POST /api/v1/generate
  │  (TANPA key apapun — frontend buta total)
  ▼
Router (generate.py) → GeneratorService.generate()
  │
  ├── provider == "ollama"
  │     ▼
  │   OllamaProvider._key_manager.get_key()  ← ambil dari pool
  │     │                                       (atau None jika lokal)
  │     ▼
  │   httpx POST /api/generate
  │     Headers: Authorization: Bearer ***xyz  ← jika cloud
  │
  └── provider == "gemini"
        ▼
      GeminiProvider._key_manager.get_key()  ← ambil dari pool
        ▼
      genai.Client(api_key=key).models.generate_content(...)
```

### 3.6. Error Hierarchy

```python
class AllKeysExhaustedError(AIGatewayError):
    """Semua API key telah rate-limited / blacklisted."""
    code = "ALL_KEYS_EXHAUSTED"
    # HTTP 503 Service Unavailable
```

### 3.7. Key Masking (Logging Safety)

Key **TIDAK BOLEH** muncul di log/response. Fungsi `mask_key()`:
```
Input:  "750d793cdb974fb9a33f5a30e43bfed8.mjEnjL1YjTnlA674XgQVuii3"
Output: "***uii3"   (tampilkan hanya 4 karakter terakhir)
```

---

## 4. Breakdowns (Daftar Task)

### Task 1 — Config & Exception Update (`task1-config-update.md`)

**File yang diubah**: `app/config.py`, `app/core/exceptions.py`, `.env`

**Langkah spesifik:**
1. Tambah field di `Settings`:
   - `OLLAMA_API_KEYS: str = ""` — Ollama Cloud API keys, comma-separated
   - `GEMINI_API_KEYS: str = ""` — Gemini API keys, comma-separated
2. Tambah `AllKeysExhaustedError` di `app/core/exceptions.py`
3. Update `.env` dengan format multi-key baru
4. Buat `.env.example` agar user baru tahu formatnya

**Acceptance Criteria:**
- `settings.OLLAMA_API_KEYS` bisa diakses
- `settings.GEMINI_API_KEYS` bisa diakses
- `AllKeysExhaustedError` bisa di-raise dan di-catch
- Backward compatible: `GEMINI_API_KEY` (single) tetap ada

**Estimasi:** Low (20 menit)

---

### Task 2 — KeyManager Service (`task2-key-manager.md`)

**File yang dibuat**: `app/services/key_manager.py`

**Langkah spesifik:**
1. Buat class `KeyManager` dengan:
   - `__init__(name: str, keys: list[str], cooldown: int = 60)`
   - `get_key() → str` — round-robin dengan blacklist check
   - `report_failure(key: str)` — blacklist key selama `cooldown` detik
   - `report_success(key: str)` — hapus key dari blacklist
   - `has_keys → bool` — cek apakah pool punya key
   - `available_count → int` — jumlah key yang tidak di-blacklist
   - `total_count → int` — total key di pool
   - `mask_key(key: str) → str` — return `***xxxx` (4 char terakhir)
2. Jika `keys` kosong, `has_keys` return `False`, `get_key()` raise `AllKeysExhaustedError`
3. Jika semua key di-blacklist dan belum expire, raise `AllKeysExhaustedError`
4. Log setiap rotasi dan blacklist menggunakan `mask_key()` (JANGAN log key asli)

**Acceptance Criteria:**
- Round-robin: 3 key → request 1 dapat key[0], request 2 dapat key[1], request 3 dapat key[2], request 4 kembali ke key[0]
- Blacklist: key di-blacklist → skip sampai cooldown expire
- Cooldown expire: key otomatis un-blacklist
- All exhausted: raise `AllKeysExhaustedError`
- `mask_key("abc123xyz")` → `"***xyz"`
- Key asli TIDAK PERNAH muncul di log output

**Estimasi:** Medium (45 menit)

---

### Task 3 — OllamaProvider Cloud Auth (`task3-ollama-cloud-auth.md`)

**File yang diubah**: `app/providers/ollama.py`

**Langkah spesifik:**
1. Update `__init__()` signature: tambah `key_manager: Optional[KeyManager] = None`
2. Simpan sebagai `self._key_manager`
3. Buat helper method `_get_auth_headers() → dict`:
   - Jika `self._key_manager` ada dan `has_keys`:
     - `key = self._key_manager.get_key()`
     - Return `{"Authorization": f"Bearer {key}"}`
   - Jika tidak: return `{}` (kosong — model lokal)
4. Update `generate()`:
   - Ambil headers via `_get_auth_headers()`
   - Kirim request dengan `headers=headers`
   - Jika response 401/429: `report_failure(key)`, raise error
   - Jika sukses: `report_success(key)` (jika key dipakai)
5. Update `stream()` — sama seperti generate
6. Update `embedding()` — sama seperti generate

**Acceptance Criteria:**
- Model lokal (`gemma4:e2b`) tetap berjalan tanpa header auth
- Model cloud (`glm-5.1:cloud`) mengirim header `Authorization: Bearer <key>`
- 429 error → key di-blacklist, error diteruskan
- Tanpa `OLLAMA_API_KEYS` → behavior 100% sama seperti sebelumnya (zero-regression)

**Estimasi:** Medium (45 menit)

---

### Task 4 — GeminiProvider Multi-Key (`task4-gemini-multi-key.md`)

**File yang diubah**: `app/providers/gemini.py`

**Langkah spesifik:**
1. Update `__init__()` signature: ganti `api_key: str` menjadi `key_manager: KeyManager`
2. Hapus `self._client = genai.Client(api_key=...)` di init
3. Simpan `self._key_manager = key_manager`
4. Buat helper `_get_client() → genai.Client`:
   - `key = self._key_manager.get_key()`
   - Return `genai.Client(api_key=key)`, simpan key sementara untuk report
5. Update `generate()`:
   - `client = self._get_client()`
   - Ganti `self._client.models.generate_content(...)` → `client.models.generate_content(...)`
   - Sukses → `report_success(key)`
   - Error 429 → `report_failure(key)`, retry 1x dengan key baru
6. Update `stream()` — sama
7. Update `embedding()` — sama

**Acceptance Criteria:**
- Dengan 3 key → request dirotasi round-robin
- Key pertama kena 429 → otomatis retry dengan key kedua (1x retry max)
- Semua key kena rate limit → HTTP 503 `ALL_KEYS_EXHAUSTED`
- Key TIDAK muncul di log (hanya masked)

**Estimasi:** Medium (60 menit)

---

### Task 5 — Provider Factory & Dependency Integration (`task5-factory-integration.md`)

**File yang diubah**: `app/providers/__init__.py`, `app/api/dependencies.py`, `app/main.py`

**Langkah spesifik:**
1. Update `create_provider()` di `app/providers/__init__.py`:
   - Ollama: parse `settings.OLLAMA_API_KEYS` → buat `KeyManager`, pass ke `OllamaProvider`
   - Gemini: parse `settings.GEMINI_API_KEYS` (fallback ke `settings.GEMINI_API_KEY`) → buat `KeyManager`, pass ke `GeminiProvider`
2. Update error handler di `app/main.py`:
   - `AllKeysExhaustedError` → HTTP 503
3. Log saat startup:
   - "Ollama Cloud: {n} API keys loaded"
   - "Gemini: {n} API keys loaded"
   - (jumlah saja, BUKAN key-nya)

**Acceptance Criteria:**
- Server startup berhasil dengan format `.env` baru
- Server startup berhasil dengan format `.env` lama (backward compatible)
- Error 503 + `ALL_KEYS_EXHAUSTED` di-handle di global error handler
- Log startup menunjukkan jumlah key yang dimuat (tanpa expose key)

**Estimasi:** Medium (30 menit)

---

### Task 6 — Unit Tests (`task6-testing.md`)

**File yang dibuat/diubah**: `tests/services/test_key_manager.py`, update `tests/providers/test_*.py`

**Langkah spesifik:**
1. Buat `tests/services/__init__.py`
2. Buat `tests/services/test_key_manager.py`:
   - `test_round_robin` — 3 key dirotasi urut
   - `test_blacklist_skip` — key di-blacklist di-skip
   - `test_cooldown_expire` — key kembali available setelah cooldown
   - `test_all_exhausted` — semua key blacklisted → `AllKeysExhaustedError`
   - `test_empty_pool` — pool kosong → `AllKeysExhaustedError`
   - `test_has_keys` — True jika ada key, False jika kosong
   - `test_mask_key` — output format `***xxxx`
   - `test_report_success_clears_blacklist` — un-blacklist setelah success
3. Update `tests/providers/test_ollama_provider.py`:
   - Test request dengan cloud key → header `Authorization` terkirim
   - Test request tanpa key → header kosong (lokal mode)
4. Update `tests/providers/test_gemini_provider.py`:
   - Update fixture: provider sekarang pakai `KeyManager` bukan `api_key`
   - Test retry 429 → key kedua dipakai

**Acceptance Criteria:**
- Minimal 8 test baru untuk `KeyManager`
- Minimal 2 test baru untuk Ollama Cloud auth
- Minimal 2 test baru untuk Gemini multi-key
- Semua 35 existing test tetap PASS (zero-regression)
- Total test suite: ~47+ tests, semua PASS

**Estimasi:** Medium (60 menit)

---

## 5. Timeline & Estimasi Total

| Task | Scope | Estimasi |
|---|---|---|
| Task 1 | Config & Exception Update | 20 menit |
| Task 2 | KeyManager Service | 45 menit |
| Task 3 | OllamaProvider Cloud Auth | 45 menit |
| Task 4 | GeminiProvider Multi-Key | 60 menit |
| Task 5 | Factory & Dependency Integration | 30 menit |
| Task 6 | Unit Tests | 60 menit |
| **Total** | | **~4 jam** |

---

## 6. Acceptance Criteria Global

- [ ] Gemini mendukung banyak API key dari `.env` (comma-separated)
- [ ] Ollama Cloud mendukung banyak API key dari `.env` (comma-separated)
- [ ] Key dirotasi otomatis (round-robin) untuk setiap request
- [ ] Key yang kena rate limit (429) otomatis di-blacklist sementara
- [ ] Jika semua key habis → HTTP 503 `ALL_KEYS_EXHAUSTED`
- [ ] Frontend **TIDAK BERUBAH** dan **TIDAK MENGIRIM key apapun**
- [ ] API key **TIDAK PERNAH** muncul di response, error message, atau log
- [ ] Backward compatible: `GEMINI_API_KEY` tunggal tetap bekerja
- [ ] Backward compatible: tanpa `OLLAMA_API_KEYS` → Ollama lokal tetap normal
- [ ] Semua 35 existing tests tetap PASS
- [ ] Minimal 12 test baru ditambahkan
