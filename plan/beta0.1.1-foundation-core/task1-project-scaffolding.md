# Task 1 — Project Scaffolding & Dependencies

> **Modul**: beta0.1.1 — Foundation Core  
> **Estimasi**: Low (30–60 menit)  
> **Dependencies**: Tidak ada (task pertama)

---

## 1. Judul Task

Membuat project scaffolding: folder structure, `pyproject.toml`, `requirements.txt`, `.gitignore`, `.env.example`, dan semua `__init__.py`.

---

## 2. Deskripsi

Menyiapkan seluruh kerangka project dari nol — folder, file konfigurasi, dan deklarasi package Python — agar developer bisa mulai menulis kode di lokasi yang benar.

---

## 3. Tujuan Teknis

- Folder structure lengkap sesuai clean architecture blueprint
- `pyproject.toml` dengan metadata dan dependencies yang valid
- `requirements.txt` dengan pinned versions
- `.gitignore` standar Python
- `.env.example` sebagai template environment
- Semua `__init__.py` terbuat sehingga Python mengenali packages

---

## 4. Scope

### ✅ Yang Dikerjakan

- Membuat semua folder: `app/`, `app/api/`, `app/api/endpoints/`, `app/schemas/`, `app/services/`, `app/providers/`, `app/core/`, `app/utils/`, `tests/`
- Membuat `pyproject.toml`
- Membuat `requirements.txt`
- Membuat `.gitignore`
- Membuat `.env.example`
- Membuat semua `__init__.py` (11 file)

### ❌ Yang Tidak Dikerjakan

- Implementasi kode apapun (hanya file kosong untuk `__init__.py`)
- Konfigurasi CI/CD
- Docker setup

---

## 5. Langkah Implementasi

### Step 1: Buat folder structure

Buat folder-folder berikut di root project:

```
app/
app/api/
app/api/endpoints/
app/schemas/
app/services/
app/providers/
app/core/
app/utils/
tests/
tests/test_providers/
tests/test_services/
tests/test_api/
```

### Step 2: Buat semua `__init__.py`

Buat file `__init__.py` kosong di setiap package:

```
app/__init__.py
app/api/__init__.py
app/api/endpoints/__init__.py
app/schemas/__init__.py
app/services/__init__.py
app/providers/__init__.py
app/core/__init__.py
app/utils/__init__.py
tests/__init__.py
tests/test_providers/__init__.py
tests/test_services/__init__.py
tests/test_api/__init__.py
```

Semua file ini berisi hanya komentar penanda:

```python
# app/<package_name>
```

### Step 3: Buat `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=75.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "ai-local-api"
version = "0.1.1"
description = "AI Generative Core — Universal AI Gateway for SaaS applications"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "httpx>=0.28",
    "google-genai>=1.0",
    "sse-starlette>=2.0",
    "python-dotenv>=1.0",
    "loguru>=0.7",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "httpx",
]
```

### Step 4: Buat `requirements.txt`

```
fastapi>=0.115
uvicorn[standard]>=0.34
pydantic>=2.0
pydantic-settings>=2.0
httpx>=0.28
google-genai>=1.0
sse-starlette>=2.0
python-dotenv>=1.0
loguru>=0.7
```

### Step 5: Buat `.gitignore`

Gunakan standar Python `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
*.egg

# Virtual environment
.venv/
venv/
env/

# Environment
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/
```

### Step 6: Buat `.env.example`

```env
# ============================================
# AI Generative Core — Configuration
# ============================================

# --- App ---
APP_NAME=AI Generative Core
APP_VERSION=1.0.0
DEBUG=false

# --- Ollama (Local LLM) ---
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=120

# --- Google Gemini ---
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_TIMEOUT=120

# --- Logging ---
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Step 7: Install dependencies

```bash
pip install -r requirements.txt
```

---

## 6. Output yang Diharapkan

Setelah task selesai, struktur project harus terlihat seperti ini:

```
ai-local-api/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints/
│   │       └── __init__.py
│   ├── schemas/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   ├── providers/
│   │   └── __init__.py
│   ├── core/
│   │   └── __init__.py
│   └── utils/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── test_providers/
│   │   └── __init__.py
│   ├── test_services/
│   │   └── __init__.py
│   └── test_api/
│       └── __init__.py
├── pyproject.toml
├── requirements.txt
├── .gitignore
└── .env.example
```

Dan `pip install -r requirements.txt` berhasil tanpa error.

---

## 7. Dependencies

Tidak ada — ini adalah task pertama.

---

## 8. Acceptance Criteria

- [ ] Semua folder dari daftar di atas ada
- [ ] Semua `__init__.py` (12 file) ada
- [ ] `pyproject.toml` valid (bisa di-parse tanpa error)
- [ ] `requirements.txt` valid
- [ ] `.gitignore` ada dan mencakup `.env`, `__pycache__/`, `.venv/`
- [ ] `.env.example` ada dengan semua variabel yang dibutuhkan
- [ ] `pip install -r requirements.txt` berhasil
- [ ] `python -c "import app"` tidak error

---

## 9. Estimasi

**Low** — Tidak ada logic, hanya file creation dan dependency install.
