# Task 2 — Config, Enum & Provider Skeleton

## 1. Judul Task
Tambah konfigurasi NVIDIA, update ProviderEnum, dan buat skeleton NvidiaProvider

## 2. Deskripsi
Menyiapkan fondasi infrastruktur untuk NVIDIA NIM provider: environment config (`NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, `NVIDIA_TIMEOUT`), menambahkan `"nvidia"` ke ProviderEnum agar request schema menerima provider baru, dan membuat file `nvidia.py` yang mengimport `BaseProvider`.

## 3. Tujuan Teknis
- `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, `NVIDIA_TIMEOUT` bisa di-configure via `.env`
- `ProviderEnum` menerima value `"nvidia"` di semua request schema
- File `app/providers/nvidia.py` ada dengan class skeleton

## 4. Scope

### Termasuk
- `app/config.py` — tambah 3 field baru (NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_TIMEOUT)
- `.env` dan `.env.example` — tambah NVIDIA environment variables
- `app/schemas/common.py` — tambah `NVIDIA = "nvidia"` ke ProviderEnum

### Tidak Termasuk
- NvidiaProvider logic (Task 3)
- Factory & registry integration (Task 4)
- Unit tests (Task 5)

## 5. Langkah Implementasi

### Step 1: Tambah config fields di `app/config.py`
Tambahkan setelah section `# --- Google Gemini ---`:

```python
# --- NVIDIA NIM ---
NVIDIA_API_KEY: str = ""          # nvapi-... key from build.nvidia.com
NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
NVIDIA_TIMEOUT: int = 120
```

### Step 2: Tambah environment variables
Di `.env`:
```env
# --- NVIDIA NIM ---
NVIDIA_API_KEY=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
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_TIMEOUT=120
```

Di `.env.example`:
```env
# --- NVIDIA NIM ---
# API key from build.nvidia.com (nvapi-... format)
# Kosongkan untuk skip NVIDIA provider
NVIDIA_API_KEY=
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_TIMEOUT=120
```

### Step 3: Tambah `NVIDIA` ke ProviderEnum di `app/schemas/common.py`
```python
class ProviderEnum(str, Enum):
    OLLAMA = "ollama"
    GEMINI = "gemini"
    NVIDIA = "nvidia"   # ← tambah ini
```

## 6. Output yang Diharapkan

```python
from app.config import settings
assert settings.NVIDIA_API_KEY != ""
assert settings.NVIDIA_BASE_URL == "https://integrate.api.nvidia.com/v1"
assert settings.NVIDIA_TIMEOUT == 120

from app.schemas.common import ProviderEnum
assert ProviderEnum("nvidia") == ProviderEnum.NVIDIA
```

## 7. Dependencies
- Task 1 (exploratory findings menentukan config fields)

## 8. Acceptance Criteria
- [x] `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, `NVIDIA_TIMEOUT` ada di `app/config.py`
- [x] `.env` dan `.env.example` berisi NVIDIA config section
- [x] `ProviderEnum.NVIDIA = "nvidia"` ada di `app/schemas/common.py`
- [x] Semua existing request schemas otomatis menerima `"nvidia"` sebagai provider
- [x] Server bisa start tanpa error
- [x] Semua existing tests tetap PASS

## 9. Estimasi
Low (~15 menit)
