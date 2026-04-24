# Task 4 - Gemini & NVIDIA Reasoning Mapping

## 1. Judul Task
Update `fetch_models()` Gemini dan NVIDIA agar mengisi `supports_reasoning` dengan source of truth yang tepat

## 2. Deskripsi
Task ini menyelesaikan reasoning mapping untuk dua provider cloud. Gemini harus memakai metadata resmi `thinking`, sedangkan NVIDIA harus memakai curated exact-ID catalog karena endpoint `/models` tidak menyediakan reasoning flag yang stabil.

## 3. Tujuan Teknis
- `GeminiProvider.fetch_models()` membaca metadata reasoning resmi
- `GeminiProvider.fetch_models()` tidak lagi menebak reasoning dari nama model
- `NvidiaProvider.fetch_models()` mengisi `supports_reasoning` via curated catalog
- Unknown NVIDIA model default ke `False`
- Task ini tidak melakukan scraping runtime ke halaman dinamis NVIDIA

## 4. Scope

### Yang dikerjakan
- `app/providers/gemini.py` - update `fetch_models()`
- `app/providers/nvidia.py` - update `fetch_models()`
- Integrasi dengan `app/services/reasoning_capability.py`

### Yang TIDAK dikerjakan
- Runtime request control untuk thinking/reasoning
- Perubahan endpoint `/api/v1/models`
- Unit tests
- Dokumentasi

## 5. Langkah Implementasi

### Step 1: Update Gemini fetch source
Import resolver:

```python
from app.services.reasoning_capability import detect_gemini_reasoning
```

`GeminiProvider.fetch_models()` harus berhenti memakai heuristic nama untuk reasoning.

### Step 2: Pakai metadata model resmi Gemini
Jalur yang diizinkan:

1. `client.models.list()` jika SDK mengekspos field `thinking`
2. fallback ke REST metadata resmi Gemini jika SDK tidak memberi field tersebut secara konsisten

Provider harus tetap mengambil capability lain seperti:

- embedding vs text
- image capability
- streaming capability

tetapi reasoning tetap dibaca dari metadata resmi.

### Step 3: Map `thinking` -> `supports_reasoning`
Aturan:

- `thinking=true` -> `supports_reasoning=True`
- `thinking=false` -> `supports_reasoning=False`
- field missing -> `False`

Jangan infer dari nama model seperti `gemini-2.5-pro`.

### Step 4: Update NVIDIA mapping
Import resolver:

```python
from app.services.reasoning_capability import detect_nvidia_reasoning
```

`NvidiaProvider.fetch_models()` tetap memakai `/models` untuk daftar model, tetapi reasoning ditentukan lewat:

```python
supports_reasoning = detect_nvidia_reasoning(name)
```

### Step 5: Tetap konservatif untuk NVIDIA
Aturan wajib:

- jangan scrape `build.nvidia.com`
- jangan infer reasoning dari substring umum
- model yang tidak ada di curated catalog -> `False`

### Step 6: Jangan ubah capability existing yang sudah berjalan
Task ini hanya menambahkan reasoning mapping. Capability lama tetap dihitung seperti sebelumnya:

- `supports_text`
- `supports_image`
- `supports_embedding`
- `supports_streaming`

## 6. Output yang Diharapkan

Contoh Gemini:

```python
ModelCapability(
    name="gemini-2.5-pro",
    provider="gemini",
    supports_reasoning=True,
)
```

Contoh NVIDIA:

```python
ModelCapability(
    name="qwen/qwen3-next-80b-a3b-thinking",
    provider="nvidia",
    supports_reasoning=True,
)
```

Model NVIDIA unknown:

```python
ModelCapability(
    name="unknown/new-model",
    provider="nvidia",
    supports_reasoning=False,
)
```

## 7. Dependencies
- Task 1 (Registry & Response Schema Update)
- Task 2 (Reasoning Capability Resolver)

## 8. Acceptance Criteria
- [x] `GeminiProvider.fetch_models()` memakai metadata resmi untuk reasoning
- [x] Gemini tidak lagi menebak reasoning dari nama model
- [x] `NvidiaProvider.fetch_models()` memakai curated exact-ID catalog
- [x] Unknown model NVIDIA default ke `supports_reasoning=False`
- [x] Tidak ada scraping runtime ke halaman dinamis NVIDIA
- [x] Capability lama tetap tidak berubah

## 9. Estimasi
Medium (~45 menit)
