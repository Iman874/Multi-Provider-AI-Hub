# How to Run — Multi-Provider AI Core (v0.2.8)

Backend API gateway yang menyatukan 3 AI provider (Ollama, Gemini, NVIDIA NIM) dalam satu REST API.

---

## ⚡ Quick Start

```cmd
# Terminal 1 — Ollama (skip jika hanya pakai Gemini/NVIDIA)
ollama serve

# Terminal 2 — Backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Swagger UI: **http://localhost:8000/docs**

---

## 1. Setup Pertama Kali

### Prasyarat

| Komponen | Versi | Keterangan |
|----------|-------|------------|
| **Python** | 3.10+ | Backend runtime |
| **Ollama** | 0.4+ | Opsional — skip jika hanya pakai Gemini/NVIDIA |
| **Git** | - | Version control |

### Instalasi

```cmd
# Clone
git clone https://github.com/Iman874/ai-local-api.git
cd ai-local-api

# Virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Konfigurasi
copy .env.example .env
```

### Setup Ollama Models (Opsional)

```cmd
ollama pull gemma4:e2b              # Text generation
ollama pull qwen3-embedding:0.6b    # Embedding
```

### Konfigurasi `.env`

Buka file `.env` dan isi API key yang diperlukan:

```env
# Wajib untuk Gemini provider
GEMINI_API_KEY=your-gemini-api-key

# Wajib untuk NVIDIA provider
NVIDIA_API_KEY=nvapi-your-nvidia-key-here

# Opsional — kosongkan untuk disable auth
GATEWAY_TOKEN=
```

> **Tips**: Provider tanpa API key akan otomatis di-skip saat startup. Tidak perlu isi semua key — isi hanya provider yang ingin dipakai.

---

## 2. Menjalankan Server

### Terminal 1 — Ollama (opsional)

```cmd
ollama serve
```

> Biarkan terbuka. Skip jika hanya pakai Gemini atau NVIDIA.

### Terminal 2 — Backend

```cmd
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Verifikasi:
```cmd
curl http://localhost:8000/health
```

Expected:
```json
{"status": "ok", "version": "0.2.8", "app_name": "Multi-Provider AI Core"}
```

---

## 3. Testing API dengan curl

> **Note**: Semua contoh di bawah tidak menggunakan auth header. Jika `GATEWAY_TOKEN` diisi di `.env`, tambahkan flag: `-H "Authorization: Bearer <token>"` di setiap request.

---

### 3.1 Health Check

**Basic health:**
```cmd
curl http://localhost:8000/health
```

**Provider health (lihat provider mana yang aktif):**
```cmd
curl http://localhost:8000/health/providers
```

Expected response:
```json
{
  "status": "healthy",
  "providers": {
    "ollama": { "status": "up", "latency_ms": 12.5 },
    "gemini": { "status": "up", "latency_ms": 245.3 },
    "nvidia": { "status": "up", "latency_ms": 180.2 }
  },
  "summary": { "total": 3, "up": 3, "down": 0 }
}
```

> Provider yang down atau tidak dikonfigurasi akan tampil dengan `status: "down"`.

---

### 3.2 List Models

> Default menampilkan **3 model teratas per provider**. Gunakan `limit=0` untuk melihat semua.

**Default (3 model per provider):**
```cmd
curl http://localhost:8000/api/v1/models
```

**Semua model (tanpa limit):**
```cmd
curl "http://localhost:8000/api/v1/models?limit=0"
```

**Filter per provider:**
```cmd
# Hanya model Ollama
curl "http://localhost:8000/api/v1/models?provider=ollama"

# Hanya model Gemini
curl "http://localhost:8000/api/v1/models?provider=gemini"

# Hanya model NVIDIA (top 3)
curl "http://localhost:8000/api/v1/models?provider=nvidia"

# Semua model NVIDIA
curl "http://localhost:8000/api/v1/models?provider=nvidia&limit=0"
```

**Termasuk model dari provider yang down:**
```cmd
curl "http://localhost:8000/api/v1/models?include_unavailable=true&limit=0"
```

**Contoh response:**
```json
[
  {
    "name": "gemini-2.5-pro",
    "provider": "gemini",
    "supports_text": true,
    "supports_image": true,
    "supports_embedding": false,
    "supports_reasoning": true,
    "available": true
  },
  {
    "name": "text-embedding-004",
    "provider": "gemini",
    "supports_text": false,
    "supports_image": false,
    "supports_embedding": true,
    "supports_reasoning": false,
    "available": true
  }
]
```

Catatan:
- `supports_reasoning` menunjukkan apakah model diketahui mendukung reasoning/thinking mode.
- Nilai ini bersifat provider-aware: Gemini memakai metadata resmi, Ollama memakai probe `show` + heuristic konservatif, dan NVIDIA memakai curated allowlist.

---

### 3.3 Text Generation (`POST /api/v1/generate`)

#### Dengan Ollama (lokal)
```cmd
curl -X POST http://localhost:8000/api/v1/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\": \"ollama\", \"model\": \"gemma4:e2b\", \"input\": \"Apa itu machine learning? Jelaskan dalam 2 kalimat.\"}"
```

#### Dengan Gemini (cloud)
```cmd
curl -X POST http://localhost:8000/api/v1/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\": \"gemini\", \"model\": \"gemini-2.5-pro\", \"input\": \"Apa itu machine learning? Jelaskan dalam 2 kalimat.\"}"
```

#### Dengan NVIDIA NIM (cloud)
```cmd
curl -X POST http://localhost:8000/api/v1/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\": \"nvidia\", \"model\": \"meta/llama-3.3-70b-instruct\", \"input\": \"Apa itu machine learning? Jelaskan dalam 2 kalimat.\"}"
```

#### Dengan NVIDIA — DeepSeek V3.2 (reasoning model)
```cmd
curl -X POST http://localhost:8000/api/v1/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\": \"nvidia\", \"model\": \"deepseek-ai/deepseek-v3.2\", \"input\": \"Berapa hasil dari 25 x 37? Tunjukkan langkah-langkahnya.\"}"
```

Expected response (semua provider format sama):
```json
{
  "output": "Machine learning adalah cabang dari AI...",
  "provider": "nvidia",
  "model": "meta/llama-3.3-70b-instruct",
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 42,
    "total_tokens": 57
  },
  "metadata": { "cached": false }
}
```

#### Smart Routing & Auto Fallback
Gunakan `provider: "auto"` dan `model: "auto"` agar gateway memilih provider/model terbaik secara otomatis berdasarkan capability request, urutan prioritas provider, dan status health.

```cmd
curl -X POST http://localhost:8000/api/v1/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\": \"auto\", \"model\": \"auto\", \"input\": \"Ringkas logika fallback ini dalam 3 poin.\"}"
```

Contoh response:
```json
{
  "output": "1. Gateway memilih provider prioritas tertinggi yang sehat. 2. Jika provider gagal, gateway mencoba target berikutnya. 3. Response tetap mengembalikan provider dan model aktual yang dipakai.",
  "provider": "gemini",
  "model": "gemini-2.5-pro",
  "usage": {
    "prompt_tokens": 120,
    "completion_tokens": 64,
    "total_tokens": 184
  },
  "metadata": { "cached": false }
}
```

Catatan:
- `POST /api/v1/chat` mengikuti auto mode yang sama karena endpoint chat membangun `GenerateRequest` lalu memanggil `GeneratorService.generate()`.
- `POST /api/v1/embedding` bisa memakai `provider: "auto"` untuk memilih model embedding yang tersedia.
- `POST /api/v1/stream` mendukung auto mode, tetapi fallback hanya bisa terjadi sebelum token pertama dikirim ke client.

---

### 3.4 Streaming / SSE (`POST /api/v1/stream`)

Token dikirim satu per satu via Server-Sent Events.

#### Stream dengan Ollama
```cmd
curl -X POST http://localhost:8000/api/v1/stream ^
  -H "Content-Type: application/json" ^
  -H "Accept: text/event-stream" ^
  -d "{\"provider\": \"ollama\", \"model\": \"gemma4:e2b\", \"input\": \"Tulis haiku tentang coding\"}"
```

#### Stream dengan NVIDIA
```cmd
curl -X POST http://localhost:8000/api/v1/stream ^
  -H "Content-Type: application/json" ^
  -H "Accept: text/event-stream" ^
  -d "{\"provider\": \"nvidia\", \"model\": \"meta/llama-3.3-70b-instruct\", \"input\": \"Hitung dari 1 sampai 10\"}"
```

Expected output (streaming):
```
data: {"token": "1"}
data: {"token": ","}
data: {"token": " 2"}
data: {"token": ","}
data: {"token": " 3"}
...
data: [DONE]
```

---

### 3.5 Embedding (`POST /api/v1/embedding`)

Mengubah teks menjadi vector embedding untuk RAG / semantic search.

#### Dengan Ollama
```cmd
curl -X POST http://localhost:8000/api/v1/embedding ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\": \"ollama\", \"model\": \"qwen3-embedding:0.6b\", \"input\": \"Machine learning sangat menarik\"}"
```

#### Dengan Gemini
```cmd
curl -X POST http://localhost:8000/api/v1/embedding ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\": \"gemini\", \"model\": \"text-embedding-004\", \"input\": \"Machine learning sangat menarik\"}"
```

#### Dengan NVIDIA
```cmd
curl -X POST http://localhost:8000/api/v1/embedding ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\": \"nvidia\", \"model\": \"nvidia/nv-embedqa-e5-v5\", \"input\": \"Machine learning sangat menarik\"}"
```

Expected response:
```json
{
  "embedding": [0.0123, -0.0456, 0.0789, ...],
  "provider": "nvidia",
  "model": "nvidia/nv-embedqa-e5-v5"
}
```

---

### 3.6 Multi-turn Chat (`POST /api/v1/chat`)

Chat dengan memory — server menyimpan histori percakapan.

#### Mulai sesi baru
```cmd
curl -X POST http://localhost:8000/api/v1/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\": \"nvidia\", \"model\": \"meta/llama-3.3-70b-instruct\", \"message\": \"Halo! Siapa namamu?\", \"session_id\": null, \"system_prompt\": \"Kamu adalah asisten yang ramah dan berbicara bahasa Indonesia.\"}"
```

Response (catat `session_id`):
```json
{
  "session_id": "a1b2c3d4-...",
  "output": "Halo! Saya adalah asisten AI...",
  "turn_count": 2
}
```

#### Lanjutkan percakapan (gunakan session_id dari response sebelumnya)
```cmd
curl -X POST http://localhost:8000/api/v1/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\": \"nvidia\", \"model\": \"meta/llama-3.3-70b-instruct\", \"message\": \"Apa yang bisa kamu bantu?\", \"session_id\": \"a1b2c3d4-...\"}"
```

> **Tips**: Ganti `a1b2c3d4-...` dengan `session_id` aktual dari response pertama.

#### Lihat histori chat
```cmd
curl http://localhost:8000/api/v1/chat/a1b2c3d4-.../history
```

#### Hapus sesi
```cmd
curl -X DELETE http://localhost:8000/api/v1/chat/a1b2c3d4-...
```

> Sesi otomatis expired setelah 30 menit tidak aktif (`CHAT_SESSION_TTL`).

---

### 3.7 Batch Processing (`POST /api/v1/batch/...`)

Kirim beberapa prompt sekaligus — diproses secara concurrent.

#### Batch Generate
```cmd
curl -X POST http://localhost:8000/api/v1/batch/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\": \"nvidia\", \"model\": \"meta/llama-3.3-70b-instruct\", \"items\": [{\"input\": \"Apa itu Python?\"}, {\"input\": \"Apa itu JavaScript?\"}, {\"input\": \"Apa itu Rust?\"}]}"
```

Expected response:
```json
{
  "provider": "nvidia",
  "model": "meta/llama-3.3-70b-instruct",
  "total": 3,
  "succeeded": 3,
  "failed": 0,
  "results": [
    {"index": 0, "status": "success", "output": "Python adalah...", "cached": false},
    {"index": 1, "status": "success", "output": "JavaScript adalah...", "cached": false},
    {"index": 2, "status": "success", "output": "Rust adalah...", "cached": false}
  ]
}
```

#### Batch Embedding
```cmd
curl -X POST http://localhost:8000/api/v1/batch/embedding ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\": \"nvidia\", \"model\": \"nvidia/nv-embedqa-e5-v5\", \"inputs\": [\"Machine learning\", \"Deep learning\", \"Natural language processing\"]}"
```

---

### 3.8 Cache Management

**Lihat statistik cache:**
```cmd
curl http://localhost:8000/api/v1/cache/stats
```

Response:
```json
{
  "total_hits": 5,
  "total_misses": 20,
  "hit_rate": 0.2,
  "current_size": 15,
  "max_size": 1000,
  "evictions": 0
}
```

**Clear cache:**
```cmd
curl -X DELETE http://localhost:8000/api/v1/cache
```

> **Tips**: Coba jalankan generate request yang sama 2x — request kedua akan lebih cepat karena dari cache. Cek `metadata.cached: true` di response.

---

## 4. Model Reference

### Default Models (Registered)

| Provider | Model | Tipe | Bisa Generate | Bisa Stream | Bisa Embed | Bisa Reasoning |
|----------|-------|------|:---:|:---:|:---:|:---:|
| `ollama` | `gemma4:e2b` | LLM | ✅ | ✅ | ❌ | ❌ |
| `ollama` | `qwen3-embedding:0.6b` | Embedding | ❌ | ❌ | ✅ | ❌ |
| `gemini` | `gemini-2.5-pro` | LLM + Vision | ✅ | ❌ | ❌ | ❌ |
| `gemini` | `gemini-3.0-pro-preview` | LLM + Vision | ✅ | ❌ | ❌ | ✅ |
| `gemini` | `gemini-3.1-flash-preview` | LLM + Vision | ✅ | ❌ | ❌ | ❌ |
| `gemini` | `text-embedding-004` | Embedding | ❌ | ❌ | ✅ | ❌ |
| `nvidia` | `meta/llama-3.3-70b-instruct` | LLM ⭐ | ✅ | ✅ | ❌ | ❌ |
| `nvidia` | `deepseek-ai/deepseek-v3.2` | Reasoning ⭐ | ✅ | ✅ | ❌ | ✅ |
| `nvidia` | `nvidia/nv-embedqa-e5-v5` | Embedding ⭐ | ❌ | ❌ | ✅ | ❌ |
| `nvidia` | `nvidia/llama-3.1-nemotron-70b-instruct` | LLM | ✅ | ✅ | ❌ | ❌ |
| `nvidia` | `meta/llama-3.1-405b-instruct` | LLM (405B) | ✅ | ✅ | ❌ | ❌ |
| `nvidia` | `mistralai/mistral-large-2-instruct` | LLM | ✅ | ✅ | ❌ | ❌ |
| `nvidia` | `google/gemma-2-27b-it` | LLM | ✅ | ✅ | ❌ | ❌ |
| `nvidia` | `microsoft/phi-3.5-mini-instruct` | LLM (small) | ✅ | ✅ | ❌ | ❌ |
| `nvidia` | `bigcode/starcoder2-15b` | Coding | ✅ | ✅ | ❌ | ❌ |
| `nvidia` | `baai/bge-m3` | Embedding | ❌ | ❌ | ✅ | ❌ |
| `nvidia` | `snowflake/arctic-embed-l` | Embedding | ❌ | ❌ | ✅ | ❌ |

> ⭐ = Top 3 default (tampil saat `limit=3`). Gunakan `limit=0` untuk melihat semua.

---

## 5. Endpoint Summary

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| `GET` | `/health` | Basic health check |
| `GET` | `/health/providers` | Status semua provider |
| `GET` | `/api/v1/models` | List model (filter: `?provider=nvidia`) |
| `POST` | `/api/v1/generate` | Text generation |
| `POST` | `/api/v1/stream` | Streaming via SSE |
| `POST` | `/api/v1/embedding` | Vector embedding |
| `POST` | `/api/v1/chat` | Multi-turn chat |
| `GET` | `/api/v1/chat/{id}/history` | Chat history |
| `DELETE` | `/api/v1/chat/{id}` | Hapus sesi chat |
| `POST` | `/api/v1/batch/generate` | Batch generate |
| `POST` | `/api/v1/batch/embedding` | Batch embedding |
| `GET` | `/api/v1/cache/stats` | Statistik cache |
| `DELETE` | `/api/v1/cache` | Clear cache |

---

## 6. Arsitektur Project

```
ai-local-api/
├── app/
│   ├── api/                    # Endpoints, router, dependencies
│   ├── core/                   # Exceptions, middleware
│   ├── providers/              # Ollama, Gemini, NVIDIA provider
│   ├── schemas/                # Pydantic request/response models
│   ├── services/               # Generator, BatchService, Cache, Health
│   ├── utils/                  # Image helpers
│   └── main.py                 # FastAPI entry point
├── tests/                      # Unit tests (pytest)
├── scripts/                    # Exploratory scripts
├── docs/                       # API documentation
├── plan/                       # Design docs & task breakdowns
├── .env                        # Environment config (JANGAN commit)
├── .env.example                # Template konfigurasi
├── requirements.txt            # Dependencies
└── how_to_run.md               # ← File ini
```

---

## 7. Menjalankan Tests

```cmd
.\venv\Scripts\activate
python -m pytest -v
```

Expected: `131 passed`

---

## 8. Troubleshooting

| Error | Solusi |
|-------|--------|
| `ModuleNotFoundError` | Pastikan `(venv)` aktif: `.\venv\Scripts\activate` |
| `Connection refused port 8000` | Jalankan backend: `uvicorn app.main:app --reload` |
| `Ollama connection refused` | Jalankan `ollama serve` di terminal terpisah |
| `CAPABILITY_NOT_SUPPORTED` | Model tidak mendukung fitur tersebut (cek tabel model di atas) |
| `MODEL_NOT_FOUND` | Cek nama model sesuai tabel — case sensitive |
| `PROVIDER_NOT_FOUND` | Provider value harus: `ollama`, `gemini`, atau `nvidia` |
| `NVIDIA API key invalid` | Pastikan key diawali `nvapi-` dan valid di build.nvidia.com |
| `GEMINI_API_KEY issues` | Pastikan key valid dan tidak dibatasi region |
| `RATE_LIMIT_EXCEEDED` | Tunggu 1 menit atau set `RATE_LIMIT_RPM=0` di `.env` |
| `BATCH_TOO_LARGE` | Kurangi jumlah items (max default: 20) |
