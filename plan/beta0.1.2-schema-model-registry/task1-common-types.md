# Task 1 — Common Types (ProviderEnum)

> **Modul**: beta0.1.2 — Schema & Model Registry  
> **Estimasi**: Low (15–30 menit)  
> **Dependencies**: beta0.1.1 selesai (project scaffolding ada)

---

## 1. Judul Task

Implementasi `app/schemas/common.py` — ProviderEnum dan shared types untuk seluruh schema.

---

## 2. Deskripsi

Membuat enum `ProviderEnum` yang mendefinisikan semua AI provider yang didukung. Enum ini digunakan oleh **semua request schema** untuk validasi field `provider` — memastikan user hanya bisa mengirim value yang valid (`"ollama"` atau `"gemini"`).

---

## 3. Tujuan Teknis

- `ProviderEnum` sebagai `str, Enum` yang compatible dengan Pydantic
- Value: `"ollama"` dan `"gemini"`
- Auto-validation: input selain itu akan menghasilkan Pydantic validation error
- Tampil sebagai dropdown di Swagger UI

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/schemas/common.py`

### ❌ Yang Tidak Dikerjakan

- Request/response schemas → task 2 & 3
- Provider-specific logic

---

## 5. Langkah Implementasi

### Step 1: Buat `app/schemas/common.py`

```python
"""
Shared types and enums used across all schemas.

ProviderEnum defines the supported AI providers and is used
in every request schema for input validation.
"""

from enum import Enum


class ProviderEnum(str, Enum):
    """
    Supported AI providers.

    Used as the `provider` field in all request schemas.
    Pydantic will automatically validate that only these values are accepted.
    """

    OLLAMA = "ollama"
    GEMINI = "gemini"
```

### Step 2: Verifikasi

```bash
python -c "
from app.schemas.common import ProviderEnum

# Valid values
print(ProviderEnum.OLLAMA)        # ollama
print(ProviderEnum.GEMINI)        # gemini
print(ProviderEnum('ollama'))     # ollama
print(ProviderEnum.OLLAMA.value)  # ollama

# String comparison
print(ProviderEnum.OLLAMA == 'ollama')  # True

# List all providers
print([p.value for p in ProviderEnum])  # ['ollama', 'gemini']
"
```

---

## 6. Output yang Diharapkan

### File: `app/schemas/common.py`

Isi seperti Step 1 di atas.

### Behavior

```python
from app.schemas.common import ProviderEnum

ProviderEnum("ollama")    # ✅ ProviderEnum.OLLAMA
ProviderEnum("gemini")    # ✅ ProviderEnum.GEMINI
ProviderEnum("openai")    # ❌ ValueError: 'openai' is not a valid ProviderEnum
```

---

## 7. Dependencies

- **beta0.1.1 Task 1** — folder `app/schemas/` dan `__init__.py` harus ada

---

## 8. Acceptance Criteria

- [ ] File `app/schemas/common.py` ada
- [ ] `from app.schemas.common import ProviderEnum` berhasil
- [ ] `ProviderEnum("ollama")` → `ProviderEnum.OLLAMA`
- [ ] `ProviderEnum("gemini")` → `ProviderEnum.GEMINI`
- [ ] `ProviderEnum("openai")` → raise `ValueError`
- [ ] `ProviderEnum.OLLAMA == "ollama"` → `True` (str compatibility)

---

## 9. Estimasi

**Low** — Satu file, satu class, tidak ada logic.
