# Task 1 — Config & Exception Update

## 1. Judul Task
Tambah konfigurasi `GATEWAY_TOKEN`, `RATE_LIMIT_RPM`, dan dua exception baru ke project

## 2. Deskripsi
Menyiapkan foundation untuk fitur auth: menambahkan field konfigurasi baru di Settings dan dua exception class baru (`AuthenticationError`, `RateLimitExceededError`) ke hierarchy error yang sudah ada.

## 3. Tujuan Teknis
- `settings.GATEWAY_TOKEN` bisa diakses dari seluruh aplikasi (default: `""`)
- `settings.RATE_LIMIT_RPM` bisa diakses (default: `120`)
- `AuthenticationError` dan `RateLimitExceededError` bisa di-raise dan di-catch
- `.env` dan `.env.example` terupdate
- `APP_VERSION` terupdate ke `"0.2.1"`

## 4. Scope
### Yang dikerjakan
- `app/config.py` — tambah 2 field, update version
- `app/core/exceptions.py` — tambah 2 exception class
- `.env` — tambah 2 variabel baru
- `.env.example` — update dengan dokumentasi

### Yang TIDAK dikerjakan
- Implementasi rate limiter (Task 2)
- Implementasi auth logic (Task 3)
- Integrasi ke router/handler (Task 4)

## 5. Langkah Implementasi

### Step 1: Update `app/config.py`
Tambahkan 2 field baru di class `Settings`, setelah section `# --- Logging ---`:
```python
# --- Gateway Auth ---
GATEWAY_TOKEN: str = ""       # Static service token, kosong = auth disabled
RATE_LIMIT_RPM: int = 120     # Max requests per minute, 0 = unlimited
```
Ubah `APP_VERSION` dari `"0.1.9"` menjadi `"0.2.1"`.

### Step 2: Tambah exception di `app/core/exceptions.py`
Tambahkan setelah class `AllKeysExhaustedError`:

```python
class AuthenticationError(AIGatewayError):
    """Request tanpa token atau token tidak valid."""

    def __init__(self, detail: str = ""):
        msg = "Authentication failed"
        if detail:
            msg += f": {detail}"
        super().__init__(message=msg, code="AUTHENTICATION_FAILED")


class RateLimitExceededError(AIGatewayError):
    """Request melebihi batas rate limit per menit."""

    def __init__(self, limit: int, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(
            message=f"Rate limit exceeded: max {limit} requests/minute",
            code="RATE_LIMIT_EXCEEDED",
        )
```

### Step 3: Update `.env`
Tambahkan di akhir file, sebelum section `# --- Logging ---`:
```env
# --- Gateway Auth ---
# Static service token. Frontend harus kirim: Authorization: Bearer <token>
# Kosongkan untuk disable auth (development mode)
GATEWAY_TOKEN=

# Rate limit: max requests per minute (0 = unlimited)
RATE_LIMIT_RPM=120
```

### Step 4: Update `.env.example`
Sama seperti `.env` tapi dengan contoh token:
```env
GATEWAY_TOKEN=my-secret-gateway-token-2026
RATE_LIMIT_RPM=120
```

## 6. Output yang Diharapkan

Setelah task selesai, verifikasi dengan script:
```python
from app.config import settings
from app.core.exceptions import AuthenticationError, RateLimitExceededError

# Config
assert settings.APP_VERSION == "0.2.1"
assert settings.GATEWAY_TOKEN == ""  # default kosong
assert settings.RATE_LIMIT_RPM == 120

# AuthenticationError
try:
    raise AuthenticationError("Invalid token")
except AuthenticationError as e:
    assert e.message == "Authentication failed: Invalid token"
    assert e.code == "AUTHENTICATION_FAILED"

# RateLimitExceededError
try:
    raise RateLimitExceededError(limit=120, retry_after=60)
except RateLimitExceededError as e:
    assert e.message == "Rate limit exceeded: max 120 requests/minute"
    assert e.code == "RATE_LIMIT_EXCEEDED"
    assert e.retry_after == 60

print("All checks passed!")
```

## 7. Dependencies
- Tidak ada (task pertama)

## 8. Acceptance Criteria
- [ ] `settings.GATEWAY_TOKEN` accessible, default `""`
- [ ] `settings.RATE_LIMIT_RPM` accessible, default `120`
- [ ] `APP_VERSION` = `"0.2.1"`
- [ ] `AuthenticationError("detail")` → message `"Authentication failed: detail"`, code `"AUTHENTICATION_FAILED"`
- [ ] `AuthenticationError()` (tanpa detail) → message `"Authentication failed"`
- [ ] `RateLimitExceededError(120)` → message contains `"max 120"`, punya `retry_after=60`
- [ ] `.env` punya `GATEWAY_TOKEN` dan `RATE_LIMIT_RPM`
- [ ] Server bisa start tanpa error: `uvicorn app.main:app --reload --port 8000`
- [ ] Semua 52 existing tests tetap PASS

## 9. Estimasi
Low (~20 menit)
