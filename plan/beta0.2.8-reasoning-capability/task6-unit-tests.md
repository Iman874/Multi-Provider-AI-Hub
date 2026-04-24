# Task 6 - Unit Tests

## 1. Judul Task
Tambah test untuk resolver reasoning, provider mapping, dan contract endpoint models

## 2. Deskripsi
Task ini menambahkan coverage untuk fondasi reasoning capability. Fokus test ada pada tiga area: resolver logic, provider `fetch_models()` mapping, dan API contract `GET /api/v1/models` yang sekarang harus mengembalikan `supports_reasoning`.

## 3. Tujuan Teknis
- Ada test terpisah untuk resolver reasoning
- Ada test provider mapping untuk Ollama, Gemini, dan NVIDIA
- Ada test response schema / endpoint models untuk `supports_reasoning`
- Capability lama tetap terlindungi dari regresi
- Unknown model/provider metadata tetap menghasilkan `supports_reasoning=False`

## 4. Scope

### Yang dikerjakan
- `tests/services/test_reasoning_capability.py` - file baru untuk resolver
- `tests/providers/test_ollama_provider.py` - tambah test fetch_models reasoning
- `tests/providers/test_gemini_provider.py` - tambah test fetch_models reasoning
- `tests/providers/test_nvidia_provider.py` - tambah test fetch_models reasoning
- `tests/test_api/test_models_endpoint.py` atau file test API sejenis - test contract endpoint models

### Yang TIDAK dikerjakan
- End-to-end provider integration ke layanan eksternal nyata
- Perubahan dokumentasi
- Runtime reasoning control

## 5. Langkah Implementasi

### Step 1: Buat test resolver baru
File baru:

- `tests/services/test_reasoning_capability.py`

Skenario minimum:

1. Ollama family reasoning -> `True`
2. Ollama non-reasoning -> `False`
3. Gemini payload `thinking=true` -> `True`
4. Gemini payload missing field -> `False`
5. NVIDIA curated ID -> `True`
6. NVIDIA unknown ID -> `False`

### Step 2: Tambah test Ollama provider
Di `tests/providers/test_ollama_provider.py`, tambah test `fetch_models()` dengan mock:

- `GET /api/tags`
- `POST /api/show`

Skenario minimum:

1. `POST /api/show` memberi data family/capabilities yang menandai reasoning
2. `POST /api/show` gagal untuk satu model, tetapi `fetch_models()` tetap return model dan default false bila tidak yakin

### Step 3: Tambah test Gemini provider
Di `tests/providers/test_gemini_provider.py`, mock metadata model resmi dengan field `thinking`.

Skenario minimum:

1. `thinking=true` -> `supports_reasoning=True`
2. `thinking=false` -> `supports_reasoning=False`

### Step 4: Tambah test NVIDIA provider
Di `tests/providers/test_nvidia_provider.py`, mock `/models`.

Skenario minimum:

1. Model ID ada di curated catalog -> `True`
2. Model ID unknown -> `False`

### Step 5: Tambah test endpoint models
Buat file test API untuk `/api/v1/models` jika belum ada, atau extend file test endpoint models yang sudah ada.

Skenario minimum:

1. Response item memiliki `supports_reasoning`
2. Field existing (`supports_text`, `supports_image`, `supports_embedding`, `available`) tetap ada
3. Filtering provider dan availability tetap bekerja

### Step 6: Tambah regression assert
Pastikan test tidak hanya memeriksa field reasoning, tetapi juga memastikan capability lama tidak berubah akibat mapping baru.

## 6. Output yang Diharapkan

Contoh struktur test:

```python
def test_detect_nvidia_reasoning_unknown_defaults_false():
    assert detect_nvidia_reasoning("unknown/model") is False

def test_gemini_fetch_models_maps_thinking_flag(...):
    ...
```

Contoh assert endpoint:

```python
assert "supports_reasoning" in response.json()[0]
assert "available" in response.json()[0]
```

## 7. Dependencies
- Task 1 (Registry & Response Schema Update)
- Task 2 (Reasoning Capability Resolver)
- Task 3 (Ollama Reasoning Discovery)
- Task 4 (Gemini & NVIDIA Reasoning Mapping)
- Task 5 (Models Endpoint & Documentation)

## 8. Acceptance Criteria
- [x] Ada file test baru `tests/services/test_reasoning_capability.py`
- [x] Ada test provider reasoning mapping untuk Ollama
- [x] Ada test provider reasoning mapping untuk Gemini
- [x] Ada test provider reasoning mapping untuk NVIDIA
- [x] Ada test contract endpoint `/api/v1/models`
- [x] Unknown model / missing metadata default ke `supports_reasoning=False`
- [x] Capability lama tetap terlindungi dari regresi

## 9. Estimasi
Medium (~1 jam)
