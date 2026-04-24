# Plan-Design: Reasoning Capability Detection - beta0.2.8

> **Version**: beta0.2.8  
> **Module**: Reasoning Capability Discovery & Model Exposure  
> **Status**: Plan  
> **Depends On**: beta0.2.7  
> **Created**: 2026-04-24

---

## 1. Latar Belakang

Saat ini gateway sudah mendukung multi-provider, streaming, health-aware routing, dan auto fallback. Masalah berikutnya adalah **reasoning capability** belum dikenali secara eksplisit di level gateway.

Akibatnya:

1. Client tidak tahu apakah model tertentu memang mendukung reasoning / thinking mode.
2. Endpoint `GET /api/v1/models` belum mengembalikan metadata reasoning.
3. Provider local dan cloud memiliki cara deteksi yang berbeda-beda, bahkan tidak semuanya menyediakan metadata reasoning yang eksplisit.

### Masalah Praktis yang Ingin Diselesaikan

Pada endpoint streaming dan generation, ada model yang bisa menghasilkan reasoning trace atau thinking behavior, dan ada model yang tidak. Karena registry model belum menyimpan capability ini, frontend atau consumer API tidak punya sumber kebenaran yang konsisten untuk memutuskan:

- model mana yang layak diberi opsi reasoning
- model mana yang hanya text generation biasa
- provider mana yang punya metadata resmi vs provider mana yang perlu fallback strategy

### Fokus Version Ini

Version `beta0.2.8` fokus pada **foundation reasoning capability**, bukan pada unified runtime reasoning control lintas provider.

Goal:
1. Menentukan bagaimana tiap provider mendeteksi support reasoning secara realistis dan stabil.
2. Menambahkan field `supports_reasoning` ke `ModelRegistry`.
3. Mengekspos `supports_reasoning` di `GET /api/v1/models`.
4. Menyiapkan pondasi untuk versi selanjutnya yang akan mengaktifkan request-time reasoning control (`think`, `thinkingBudget`, reasoning trace, dll).

---

## 2. Riset Provider Metadata - Cara Mengetahui Model Support Reasoning

### 2.1 Ollama (Local dan Cloud)

Temuan dari dokumentasi resmi:

- API lokal dan cloud memakai API yang sama, hanya base URL berbeda:
  - local: `http://localhost:11434/api`
  - cloud: `https://ollama.com/api`
- `GET /api/tags` hanya mengembalikan daftar model dan detail dasar seperti family, parameter size, dan quantization.
- `POST /api/show` mengembalikan `capabilities[]` sebagai daftar fitur model.
- Dokumentasi Thinking menjelaskan bahwa thinking-capable models mendukung field `thinking` dan parameter request `think`, serta menyebut keluarga model yang didukung seperti `Qwen 3`, `GPT-OSS`, `DeepSeek-v3.1`, dan `DeepSeek R1`.

Implikasi desain:

- `GET /api/tags` **tidak cukup** untuk mendeteksi reasoning.
- `POST /api/show` bisa dipakai sebagai sinyal tambahan karena ada `capabilities[]`, tetapi dokumentasi tidak menjamin nilai reasoning tertentu secara eksplisit.
- Karena itu, deteksi Ollama harus memakai **dua lapis**:
  1. best-effort probe ke `POST /api/show`
  2. fallback heuristic berbasis nama/family untuk model yang secara resmi masuk daftar thinking-capable dari dokumentasi Ollama

Keputusan untuk `0.2.8`:

- Gunakan API yang sama untuk Ollama local dan Ollama cloud.
- Untuk setiap model hasil `GET /api/tags`, lakukan enrichment best-effort via `POST /api/show`.
- Jika `capabilities[]` atau detail model tidak memberi sinyal reasoning yang jelas, gunakan heuristic konservatif berbasis family/name yang cocok dengan daftar model thinking resmi.
- Jika tetap tidak yakin, default ke `supports_reasoning=False`.

### 2.2 Gemini

Temuan dari dokumentasi resmi:

- Resource `Model` pada Gemini API menyediakan field `thinking: boolean`.
- Dokumentasi model overview Gemini juga menampilkan capability "Thinking Supported" pada model-model yang mendukungnya.
- Dokumentasi Thinking menyatakan seri Gemini 2.5 dan 3 mendukung thinking.

Implikasi desain:

- Gemini adalah provider dengan metadata reasoning paling jelas dan paling stabil.
- Deteksi reasoning **tidak perlu heuristic** jika data diambil dari metadata resmi model.

Keputusan untuk `0.2.8`:

- Jadikan metadata resmi Gemini sebagai source of truth untuk `supports_reasoning`.
- `GeminiProvider.fetch_models()` harus membaca field `thinking` dari metadata model resmi, bukan menebaknya dari nama model.
- Jika SDK tidak mengekspose field ini dengan konsisten, provider boleh memakai REST `models.list`/`models.get` resmi Gemini sebagai jalur metadata.

### 2.3 NVIDIA NIM

Temuan dari dokumentasi resmi:

- Endpoint OpenAI-compatible `POST /v1/chat/completions` dan `GET /v1/models` tidak mendokumentasikan field reasoning khusus pada response list model.
- Model card / API reference resmi NVIDIA menandai beberapa model dengan kata kunci seperti `reasoning`, `thinking`, atau `thinking budget`.
- Contoh resmi NVIDIA menunjukkan ada model yang memang reasoning-capable, misalnya model keluarga Nemotron dan beberapa model dengan suffix `-thinking`.

Implikasi desain:

- `GET /v1/models` **tidak cukup** untuk mendeteksi reasoning secara machine-readable.
- Model card NVIDIA memang memuat informasi reasoning, tetapi bukan API runtime yang stabil untuk di-scrape pada startup gateway.

Keputusan untuk `0.2.8`:

- Jangan scrape `build.nvidia.com` atau halaman dinamis NVIDIA saat runtime.
- Gunakan **curated exact-ID catalog** di dalam repo untuk model NVIDIA yang reasoning-capable.
- Catalog ini harus seeded dari model ID yang sudah diverifikasi dari dokumentasi resmi/model card.
- Model NVIDIA yang tidak ada di catalog reasoning dianggap `supports_reasoning=False` secara default.

### 2.4 Aturan Global yang Dipilih

Urutan sumber kebenaran capability reasoning:

1. **Metadata resmi provider** jika ada field eksplisit
2. **Provider detail endpoint** jika mendokumentasikan capability list
3. **Curated provider catalog** berbasis dokumentasi resmi
4. **Default false** jika tidak ada bukti yang cukup

Prinsip utama:

- lebih baik false negative daripada false positive
- gateway tidak boleh mengklaim model support reasoning kalau metadata-nya tidak cukup kuat
- reasoning capability harus bersifat deterministic, bukan hasil tebakan longgar

---

## 3. Arsitektur & Perubahan Kode

### 3.1 Model Registry

File utama:

- `app/services/model_registry.py`

Perubahan:

```python
@dataclass
class ModelCapability:
    name: str
    provider: str
    supports_text: bool = True
    supports_image: bool = False
    supports_embedding: bool = False
    supports_streaming: bool = True
    supports_reasoning: bool = False
```

`supports_reasoning` akan menjadi capability baru yang disimpan di registry dan dipakai untuk API exposure.

### 3.2 Response Schema untuk Endpoint Models

File utama:

- `app/schemas/responses.py`
- `app/api/endpoints/models.py`

Perubahan:

- Tambah field `supports_reasoning: bool` ke `ModelInfo`
- `ModelInfoWithAvailability` akan mewarisi field tersebut otomatis
- `GET /api/v1/models` mengembalikan field reasoning di setiap item

Contoh response baru:

```json
{
  "name": "gemini-2.5-pro",
  "provider": "gemini",
  "supports_text": true,
  "supports_image": true,
  "supports_embedding": false,
  "supports_reasoning": true,
  "available": true
}
```

### 3.3 Reasoning Capability Resolver

Tambah module baru:

- `app/services/reasoning_capability.py`

Isi module:

1. Resolver untuk Ollama
2. Resolver untuk Gemini
3. Curated catalog untuk NVIDIA

Struktur yang diusulkan:

```python
OLLAMA_THINKING_FAMILIES = {
    "qwen3",
    "gpt-oss",
    "deepseek-v3.1",
    "deepseek-r1",
}

NVIDIA_REASONING_MODEL_IDS = {
    "...",
}

def detect_ollama_reasoning(
    name: str,
    family: str | None,
    families: list[str] | None,
    capabilities: list[str] | None,
) -> bool:
    ...

def detect_gemini_reasoning(model_payload: dict) -> bool:
    ...

def detect_nvidia_reasoning(model_id: str) -> bool:
    ...
```

Catatan:

- untuk Ollama, heuristic berbasis family/name hanya dipakai jika metadata resmi tidak cukup
- untuk NVIDIA, catalog exact-ID adalah source of truth

### 3.4 Provider Fetch Models

#### OllamaProvider

File:

- `app/providers/ollama.py`

Perubahan:

1. `fetch_models()` tetap mulai dari `GET /api/tags`
2. untuk setiap model text, lakukan best-effort `POST /api/show`
3. ambil:
   - `details.family`
   - `details.families`
   - `capabilities[]`
4. hitung `supports_reasoning` via resolver Ollama

Aturan failure:

- jika `POST /api/show` gagal untuk model tertentu, jangan gagal total
- fallback ke heuristic family/name
- jika tetap tidak yakin, set false

#### GeminiProvider

File:

- `app/providers/gemini.py`

Perubahan:

1. ganti fetch metadata model dari heuristic nama ke metadata resmi Gemini
2. baca field `thinking`
3. map field tersebut ke `supports_reasoning`

Keputusan implementasi:

- metadata reasoning Gemini harus diambil dari response resmi `models.list` / `models.get`
- jangan infer reasoning hanya dari nama seperti `gemini-2.5-pro`

#### NvidiaProvider

File:

- `app/providers/nvidia.py`

Perubahan:

1. `fetch_models()` tetap ambil model ID dari `/models`
2. tentukan `supports_reasoning` via curated catalog `NVIDIA_REASONING_MODEL_IDS`
3. unknown model IDs default ke false

### 3.5 API Contract Boundary

Version ini **tidak** menambahkan request-time reasoning control lintas provider.

Artinya:

- belum ada field request universal seperti `reasoning`, `think`, `thinking_budget`, atau `thinking_level`
- belum ada perubahan pada `GenerateResponse`, `ChatResponse`, atau stream payload untuk membawa reasoning trace
- belum ada reasoning-aware auto routing

Version ini hanya menyelesaikan **capability discovery + exposure**.

---

## 4. Scope

### Yang Dikerjakan

1. **Provider research integration** - tentukan jalur deteksi reasoning per provider
2. **Registry update** - tambah `supports_reasoning` ke `ModelCapability`
3. **Provider fetch enrichment** - update Ollama, Gemini, dan NVIDIA agar mengisi capability reasoning
4. **Models endpoint exposure** - tampilkan `supports_reasoning` di `GET /api/v1/models`
5. **Unit tests** - test resolver, provider fetch mapping, dan response schema models
6. **Documentation** - update `how_to_run.md` / docs models response untuk field baru

### Yang TIDAK Dikerjakan

- Unified request parameter untuk mengaktifkan reasoning
- Streaming reasoning trace di response gateway
- Standarisasi output `thinking` / `reasoning_content` lintas provider
- Reasoning-aware auto routing
- Mengubah contract generate/chat/stream request
- Scraping runtime ke halaman dinamis NVIDIA catalog

---

## 5. Rencana Pengujian

### Test Case 1: Ollama - /api/tags Saja Tidak Cukup

- Mock `GET /api/tags` dengan model text biasa
- Mock `POST /api/show` dengan `capabilities=["completion"]`
- Assert `supports_reasoning=False`

### Test Case 2: Ollama - Thinking Family

- Mock model family `qwen3` atau `deepseek-r1`
- Mock `POST /api/show` tanpa flag reasoning eksplisit
- Assert heuristic resmi menandai `supports_reasoning=True`

### Test Case 3: Gemini - Metadata Resmi

- Mock response model Gemini dengan `thinking=true`
- Assert `supports_reasoning=True`

### Test Case 4: Gemini - Non-Thinking Model

- Mock response model Gemini dengan `thinking=false`
- Assert `supports_reasoning=False`

### Test Case 5: NVIDIA - Curated Catalog

- Mock `/models` mengembalikan model ID reasoning dan non-reasoning
- Assert exact-ID yang ada di catalog -> true
- Assert unknown model -> false

### Test Case 6: Models Endpoint Contract

- Call `GET /api/v1/models`
- Assert setiap item response memiliki field `supports_reasoning`
- Assert field existing (`supports_text`, `supports_image`, `supports_embedding`, `available`) tetap tidak berubah

---

## 6. Task Breakdown (Estimasi)

| # | Task | Scope | Estimasi |
|---|------|-------|----------|
| 1 | Registry & Response Schema Update | `ModelCapability`, `ModelInfo`, `ModelInfoWithAvailability` | 20 min |
| 2 | Reasoning Capability Resolver | module resolver + curated catalogs | 45 min |
| 3 | Ollama Reasoning Discovery | `/api/show` enrichment + fallback heuristic | 1 hr |
| 4 | Gemini & NVIDIA Mapping | Gemini official metadata + NVIDIA catalog lookup | 45 min |
| 5 | Models Endpoint & Documentation | `/api/v1/models` response + docs update | 20 min |
| 6 | Unit Tests | resolver, provider fetch, endpoint response | 1 hr |

**Total estimasi: ~4 jam 10 menit**

---

## 7. Risiko & Mitigasi

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| Ollama tidak punya reasoning flag yang terdokumentasi jelas di list API | False positive/false negative pada model lokal | Gunakan `POST /api/show` sebagai best-effort enrichment, fallback ke daftar thinking family resmi, dan default false jika tidak yakin |
| `POST /api/show` per model menambah latency startup | Dynamic model loading jadi lebih lambat | Batasi enrichment ke model text saja, lakukan best-effort, dan fallback ke heuristic bila probe gagal |
| Gemini SDK tidak memetakan field `thinking` dengan stabil | Metadata reasoning hilang walau provider mendukung | Gunakan REST metadata resmi Gemini sebagai fallback/source of truth |
| NVIDIA model catalog berubah lebih cepat dari curated catalog lokal | Beberapa model reasoning baru tidak terdeteksi | Gunakan exact-ID catalog konservatif, default false untuk unknown, dan update catalog secara berkala dari model card resmi |
| User mengira `supports_reasoning=true` berarti trace reasoning pasti tersedia di response saat ini | Ekspektasi API salah | Dokumentasi harus eksplisit bahwa `0.2.8` hanya capability discovery, belum reasoning runtime control |

---

## 8. Success Criteria

- [ ] `ModelCapability` memiliki field `supports_reasoning`
- [ ] `GET /api/v1/models` mengembalikan `supports_reasoning` untuk semua model
- [ ] Ollama local dan cloud memakai flow deteksi yang sama karena API-nya sama
- [ ] Gemini memakai metadata resmi provider untuk mendeteksi reasoning
- [ ] NVIDIA tidak memakai heuristic longgar; hanya catalog resmi berbasis model ID
- [ ] Unknown model default ke `supports_reasoning=False`
- [ ] Field capability lama tetap bekerja tanpa regresi
- [ ] Dokumentasi menjelaskan bahwa version ini belum menambahkan reasoning request controls

---

## Referensi Resmi

- Ollama API intro: https://docs.ollama.com/api
- Ollama list models: https://docs.ollama.com/api/tags
- Ollama show model details: https://docs.ollama.com/api-reference/show-model-details
- Ollama thinking capability: https://docs.ollama.com/capabilities/thinking
- Gemini model metadata API: https://ai.google.dev/api/rest/generativelanguage/models
- Gemini model overview: https://ai.google.dev/gemini-api/docs/models
- Gemini thinking guide: https://ai.google.dev/gemini-api/docs/thinking
- NVIDIA NIM overview: https://docs.api.nvidia.com/nim/docs/overview
- NVIDIA LLM APIs: https://docs.api.nvidia.com/nim/reference/llm-apis
- NVIDIA reasoning-capable model references:
  - https://docs.api.nvidia.com/nim/reference/nvidia-nvidia-nemotron-nano-9b-v2
  - https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-nano-30b-a3b
  - https://build.nvidia.com/qwen/qwen3-next-80b-a3b-thinking/modelcard
