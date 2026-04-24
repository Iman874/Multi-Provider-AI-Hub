# Task 2 - Reasoning Capability Resolver

## 1. Judul Task
Buat module resolver untuk menentukan `supports_reasoning` lintas provider

## 2. Deskripsi
Task ini membuat source of truth internal untuk capability reasoning. Resolver dibutuhkan karena cara deteksi reasoning berbeda di tiap provider: Gemini punya metadata resmi, Ollama butuh kombinasi detail endpoint dan heuristic konservatif, sedangkan NVIDIA harus memakai curated exact-ID catalog.

## 3. Tujuan Teknis
- Ada module baru `app/services/reasoning_capability.py`
- Tersedia curated constants untuk Ollama thinking families dan NVIDIA reasoning model IDs
- Ada helper resolver terpisah untuk Ollama, Gemini, dan NVIDIA
- Resolver bersifat deterministic dan konservatif
- Unknown model default ke `False`

## 4. Scope

### Yang dikerjakan
- `app/services/reasoning_capability.py` - module baru untuk resolver dan curated catalog

### Yang TIDAK dikerjakan
- Panggilan network ke provider
- Integrasi ke `fetch_models()` provider
- Endpoint `/api/v1/models`
- Dokumentasi dan unit tests

## 5. Langkah Implementasi

### Step 1: Buat file `app/services/reasoning_capability.py`
Struktur minimum file:

```python
OLLAMA_THINKING_FAMILIES = {...}
NVIDIA_REASONING_MODEL_IDS = {...}

def detect_ollama_reasoning(...) -> bool:
    ...

def detect_gemini_reasoning(model_payload: object) -> bool:
    ...

def detect_nvidia_reasoning(model_id: str) -> bool:
    ...
```

### Step 2: Tambah curated constants untuk Ollama
Tambahkan family/model tokens yang memang disebut di dokumentasi Ollama Thinking, misalnya:

- `qwen3`
- `gpt-oss`
- `deepseek-v3.1`
- `deepseek-r1`

Resolver Ollama boleh mengecek:

- `details.family`
- `details.families`
- `capabilities[]`
- `name`

Tetapi heuristic harus konservatif. Jangan menandai reasoning hanya dari kata umum seperti `large`, `pro`, atau `instruct`.

### Step 3: Tambah curated exact-ID catalog untuk NVIDIA
`NVIDIA_REASONING_MODEL_IDS` harus berisi exact model IDs yang sudah diverifikasi dari referensi resmi/model card, bukan wildcard longgar.

Contoh pendekatan:

```python
NVIDIA_REASONING_MODEL_IDS = {
    "nvidia/nvidia-nemotron-nano-9b-v2",
    "nvidia/nemotron-3-nano-30b-a3b",
    "qwen/qwen3-next-80b-a3b-thinking",
}
```

Jika ada model ID yang belum diverifikasi, jangan dimasukkan.

### Step 4: Implement `detect_ollama_reasoning()`
Aturan urutan evaluasi:

1. Jika `capabilities[]` memberi sinyal eksplisit reasoning/thinking -> return `True`
2. Jika family/families cocok dengan curated thinking families -> return `True`
3. Jika name cocok exact/prefix yang sudah diizinkan secara konservatif -> return `True`
4. Selain itu -> `False`

### Step 5: Implement `detect_gemini_reasoning()`
Resolver Gemini membaca field metadata resmi `thinking`.

Aturan:

- Jika field `thinking` ada dan boolean true -> `True`
- Jika field `thinking` ada dan false -> `False`
- Jika field tidak tersedia -> `False`

Task ini tidak memutuskan jalur SDK vs REST; itu milik task integrasi provider.

### Step 6: Implement `detect_nvidia_reasoning()`
Aturan sederhana:

```python
return model_id in NVIDIA_REASONING_MODEL_IDS
```

Jangan pakai substring longgar seperti `"reason"` atau `"thinking"` sebagai source of truth utama.

## 6. Output yang Diharapkan

Contoh penggunaan:

```python
assert detect_ollama_reasoning(
    name="qwen3:8b",
    family="qwen3",
    families=["qwen3"],
    capabilities=["completion"],
) is True

assert detect_gemini_reasoning({"thinking": True}) is True
assert detect_nvidia_reasoning("unknown/model") is False
```

## 7. Dependencies
- Task 1 (Registry & Response Schema Update)

## 8. Acceptance Criteria
- [x] File `app/services/reasoning_capability.py` ada
- [x] Ada curated constants untuk Ollama dan NVIDIA
- [x] Ada resolver `detect_ollama_reasoning()`
- [x] Ada resolver `detect_gemini_reasoning()`
- [x] Ada resolver `detect_nvidia_reasoning()`
- [x] Unknown model/provider metadata default ke `False`
- [x] Resolver tidak memakai heuristic longgar untuk NVIDIA

## 9. Estimasi
Medium (~45 menit)
