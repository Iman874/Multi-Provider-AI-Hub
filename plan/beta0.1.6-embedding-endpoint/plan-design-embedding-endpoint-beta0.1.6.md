# Embedding Endpoint — beta0.1.6

> **Versi**: beta0.1.6  
> **Modul**: Embedding Support (Ollama & Gemini), POST /embedding Endpoint  
> **Status**: 📋 Planned  
> **Dependency**: beta0.1.4 (Gemini Provider)  
> **Referensi Blueprint**: `02-provider-layer.md`, `04-api-layer.md`, `05-schemas.md`

---

## 1. Latar Belakang

Embedding adalah fitur krusial untuk SaaS berbasis AI — digunakan untuk semantic search, RAG (Retrieval-Augmented Generation), similarity matching, dan clustering. Tanpa embedding endpoint, project ini hanya bisa generate text tapi tidak bisa "memahami" konten.

Ollama dan Gemini keduanya menyediakan embedding model, tapi dengan API yang berbeda:
- **Ollama**: `POST /api/embed` → `{ embeddings: [[...]] }`
- **Gemini**: `client.models.embed_content()` → `result.embeddings[0].values`

### Masalah yang Diselesaikan

- Belum bisa generate embedding vector → SaaS yang butuh semantic search tidak bisa dibangun
- Dua provider punya API embedding berbeda → perlu normalisasi
- Belum ada validasi capability embedding → model text bisa dipanggil untuk embedding

### Kaitan dengan Sistem

- Menggunakan `BaseProvider.embedding()` yang masih stub
- `ModelRegistry` sudah track `supports_embedding` flag (beta0.1.2)
- `GeneratorService` akan validasi capability sebelum call provider
- `EmbeddingRequest` dan `EmbeddingResponse` schema sudah didefinisikan (beta0.1.2)

---

## 2. Tujuan

| # | Outcome | Measurable |
|---|---|---|
| 1 | Ollama embedding berfungsi | Return float vector dari `nomic-embed-text` |
| 2 | Gemini embedding berfungsi | Return float vector dari `text-embedding-004` |
| 3 | Output format seragam | Kedua provider return `list[float]` identik |
| 4 | POST /embedding endpoint live | Kirim text, terima vector |
| 5 | Capability validation | Model non-embedding → error 400 |

---

## 3. Scope

### ✅ Yang Dikerjakan

- Implementasi `OllamaProvider.embedding()` — `/api/embed` call
- Implementasi `GeminiProvider.embedding()` — SDK `embed_content` call
- Implementasi `GeneratorService.embedding()` — routing + capability validation
- Implementasi `app/api/endpoints/embedding.py` — POST /embedding
- Update router untuk include embedding endpoint

### ❌ Yang Tidak Dikerjakan

- Batch embedding (multiple texts) → future version
- Embedding caching → future version
- Dimensionality metadata → future version
- Custom embedding model selection logic → future version

---

## 4. Breakdown Task

### Task 1: OllamaProvider.embedding()

- [ ] Implementasi di `app/providers/ollama.py`
  - Build payload: `{ model, input: text }`
  - POST ke `{base_url}/api/embed`
  - Parse response: `response["embeddings"][0]`
  - Return `list[float]`
  - Error handling: model not found, timeout

### Task 2: GeminiProvider.embedding()

- [ ] Implementasi di `app/providers/gemini.py`
  - Call `client.models.embed_content(model=model, contents=text)`
  - Parse: `result.embeddings[0].values`
  - Return `list[float]`
  - Error handling: API error, invalid model

### Task 3: GeneratorService.embedding()

- [ ] Implementasi di `app/services/generator.py`
  - Method `embedding(request: EmbeddingRequest) -> EmbeddingResponse`
  - Flow:
    1. Resolve provider
    2. Lookup model di registry
    3. Validate `model_info.supports_embedding == True`
    4. Jika tidak → raise `ModelCapabilityError(model, "embedding")`
    5. Call `provider.embedding(model, input_text)`
    6. Wrap dalam `EmbeddingResponse(embedding=vector, provider, model)`

### Task 4: POST /embedding Endpoint

- [ ] Implementasi `app/api/endpoints/embedding.py`
  - Route: `POST /embedding`
  - Accept: `EmbeddingRequest` body
  - Inject: `GeneratorService` via Depends
  - Call: `service.embedding(request)`
  - Return: `EmbeddingResponse`

### Task 5: Router Update

- [ ] Update `app/api/router.py`
  - Include embedding router dengan tag "Embedding"

---

## 5. Design Teknis

### File Baru

| File | Layer | Fungsi |
|---|---|---|
| `app/api/endpoints/embedding.py` | API | POST /embedding endpoint |

### File yang Dimodifikasi

| File | Perubahan |
|---|---|
| `app/providers/ollama.py` | Implement `embedding()` (replace stub) |
| `app/providers/gemini.py` | Implement `embedding()` (replace stub) |
| `app/services/generator.py` | Add `embedding()` method |
| `app/api/router.py` | Include embedding router |

### Flow: POST /embedding

```
Client → POST /api/v1/embedding
  Body: { provider: "ollama", model: "nomic-embed-text", input: "Hello world" }

→ service.embedding(request)
  → registry.get_model("ollama", "nomic-embed-text")
    → supports_embedding: true ✓
  → provider.embedding("nomic-embed-text", "Hello world")
    → POST http://localhost:11434/api/embed
      Body: { model: "nomic-embed-text", input: "Hello world" }
    ← { embeddings: [[0.0123, -0.0456, 0.0789, ...]] }
  ← [0.0123, -0.0456, 0.0789, ...]

→ JSON Response 200:
  { embedding: [0.0123, -0.0456, ...], provider: "ollama", model: "nomic-embed-text" }
```

### Flow: Capability Error

```
Client → POST /api/v1/embedding
  Body: { provider: "ollama", model: "llama3.2", input: "Hello" }

→ service.embedding(request)
  → registry.get_model("ollama", "llama3.2")
    → supports_embedding: false ✗
  → raise ModelCapabilityError("llama3.2", "embedding")

→ JSON Response 400:
  { error: "Model 'llama3.2' does not support 'embedding'", code: "CAPABILITY_NOT_SUPPORTED" }
```

---

## 6. Dampak ke Sistem

### Bagian yang Berubah

- Kedua provider: stub `embedding()` diganti implementasi real
- Service layer: method baru ditambahkan
- API layer: 1 endpoint baru

### Risiko

| Risiko | Mitigasi |
|---|---|
| Embedding dimension berbeda antar model | Tidak masalah — client harus konsisten pakai 1 model |
| Ollama embedding model belum di-pull | Error jelas dari Ollama API → ProviderAPIError |
| Gemini embedding quota limit | 429 error → ProviderAPIError |

### Dependency

| Depends On | Depended By |
|---|---|
| beta0.1.3 (OllamaProvider base) | Future: RAG pipeline |
| beta0.1.4 (GeminiProvider base) | Future: Semantic search SaaS |
| beta0.1.2 (EmbeddingRequest schema) | — |

---

## 7. Definition of Done

- [ ] `POST /embedding` dengan Ollama `nomic-embed-text` → return float vector
- [ ] `POST /embedding` dengan Gemini `text-embedding-004` → return float vector
- [ ] Kedua provider return format `list[float]` yang konsisten
- [ ] Model non-embedding (e.g. llama3.2) → 400 error dengan code `CAPABILITY_NOT_SUPPORTED`
- [ ] Vector length > 0 (bukan array kosong)
- [ ] Swagger UI menampilkan POST /embedding dengan schema benar

---

## Referensi Blueprint

- [02-provider-layer.md](../bluprint/02-provider-layer.md) — embedding() method spec
- [04-api-layer.md](../bluprint/04-api-layer.md) — POST /embedding spec
- [05-schemas.md](../bluprint/05-schemas.md) — EmbeddingRequest/Response
