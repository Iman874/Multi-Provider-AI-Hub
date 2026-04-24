# Task 3 - Ollama Reasoning Discovery

## 1. Judul Task
Perkaya `OllamaProvider.fetch_models()` agar bisa mendeteksi `supports_reasoning`

## 2. Deskripsi
Task ini mengimplementasikan reasoning discovery untuk Ollama local dan cloud. Karena `GET /api/tags` tidak cukup untuk mengetahui capability reasoning, provider perlu melakukan enrichment best-effort ke `POST /api/show`, lalu memadukan hasil detail model dengan resolver reasoning yang sudah dibuat sebelumnya.

## 3. Tujuan Teknis
- `OllamaProvider.fetch_models()` tetap mulai dari `GET /api/tags`
- Untuk model text, provider melakukan enrichment best-effort ke `POST /api/show`
- Metadata `family`, `families`, dan `capabilities[]` dipakai untuk resolver reasoning
- `supports_reasoning` terisi pada `ModelCapability`
- Failure pada satu model tidak menggagalkan seluruh `fetch_models()`
- Flow ini berlaku untuk Ollama local dan Ollama cloud karena API-nya sama

## 4. Scope

### Yang dikerjakan
- `app/providers/ollama.py` - update `fetch_models()`
- Integrasi dengan `app/services/reasoning_capability.py`

### Yang TIDAK dikerjakan
- Perubahan `generate()`, `stream()`, atau `embedding()`
- Endpoint `/api/v1/models`
- Unit tests
- Dokumentasi

## 5. Langkah Implementasi

### Step 1: Import resolver reasoning
Di `app/providers/ollama.py`, import helper dari module baru:

```python
from app.services.reasoning_capability import detect_ollama_reasoning
```

### Step 2: Pertahankan flow dasar `GET /api/tags`
Jangan ubah source daftar model utama. `GET /api/tags` tetap dipakai untuk:

- enumerasi model
- deteksi dasar `supports_embedding`
- deteksi dasar `supports_image`
- deteksi dasar `supports_streaming`

### Step 3: Tambah helper internal untuk `POST /api/show`
Tambahkan helper private, misalnya:

```python
async def _fetch_model_details(self, name: str) -> dict | None:
    ...
```

Endpoint:

```python
POST /api/show
{"model": name}
```

Helper ini bersifat best-effort:

- return dict detail jika sukses
- return `None` jika gagal
- jangan raise yang memutus seluruh `fetch_models()`

### Step 4: Enrichment hanya untuk model text
Jangan panggil `POST /api/show` untuk model embedding murni. Enrichment reasoning hanya relevan untuk model yang `supports_text=True`.

### Step 5: Ambil field detail yang relevan
Minimal ekstraksi:

- `details.family`
- `details.families`
- `capabilities`

Jika struktur response berbeda, mapping harus tetap defensif:

- missing key -> `None` / `[]`
- response aneh -> fallback ke heuristic nama

### Step 6: Hitung `supports_reasoning`
Gunakan resolver:

```python
supports_reasoning = detect_ollama_reasoning(
    name=name,
    family=family,
    families=families,
    capabilities=capabilities,
)
```

Untuk model embedding:

- set `supports_reasoning=False`

### Step 7: Jangan gagal total bila enrichment error
Jika `POST /api/show` timeout, 404, atau malformed:

- log warning singkat
- lanjutkan pakai heuristic minimum berbasis nama/family jika ada
- default `supports_reasoning=False` jika tetap tidak yakin

## 6. Output yang Diharapkan

Contoh object model:

```python
ModelCapability(
    name="qwen3:8b",
    provider="ollama",
    supports_text=True,
    supports_image=False,
    supports_embedding=False,
    supports_streaming=True,
    supports_reasoning=True,
)
```

Contoh failure handling:

```text
POST /api/show gagal
model tetap direturn dari fetch_models()
supports_reasoning fallback ke False jika data tidak cukup
```

## 7. Dependencies
- Task 1 (Registry & Response Schema Update)
- Task 2 (Reasoning Capability Resolver)

## 8. Acceptance Criteria
- [x] `OllamaProvider.fetch_models()` tetap memakai `GET /api/tags` sebagai source daftar model
- [x] Ada enrichment best-effort ke `POST /api/show`
- [x] `supports_reasoning` dihitung via resolver khusus Ollama
- [x] Model embedding selalu `supports_reasoning=False`
- [x] Gagal `POST /api/show` untuk satu model tidak memutus seluruh `fetch_models()`
- [x] Flow yang sama berlaku untuk Ollama local dan cloud

## 9. Estimasi
Medium (~1 jam)
