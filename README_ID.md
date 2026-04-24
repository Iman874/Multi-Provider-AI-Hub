# 🧠 Multi-Provider AI Core

> **[🇬🇧 English](./README_EN.md)** | **[🇮🇩 Bahasa Indonesia](./README_ID.md)**

**Multi-Provider AI Core** adalah backend API gateway berbasis roadmap yang menyatukan beberapa provider AI (**Ollama**, **Gemini**, **NVIDIA NIM**) ke dalam satu REST API yang seragam.

Sistem ini didesain sebagai AI engine siap produksi dengan smart routing, graceful auto-fallback, caching, availability berbasis health check, streaming, dukungan multimodal, dan deteksi reasoning capability.

---

## ✨ Highlight Fitur

| Fitur | Deskripsi | Versi |
|---|---|---|
| 🔌 **Multi-Provider API** | Satu antarmuka API untuk Ollama (Lokal), Gemini (Cloud), dan NVIDIA NIM (Cloud) | `beta0.1.x` |
| 🌊 **SSE Streaming** | Respons real-time token-by-token melalui Server-Sent Events | `beta0.1.5` |
| 📊 **Vector Embedding** | Pembuatan embedding teks untuk pipeline RAG / Semantic Search | `beta0.1.6` |
| 🖼️ **Multimodal Support** | Memproses input teks + gambar pada model yang mendukung | `beta0.1.7` |
| 🔑 **Dynamic API Keys** | Injeksi API key dinamis dan dukungan rotasi key | `beta0.1.9` |
| 🛡️ **Auth & Rate Limiting** | Gateway auth berbasis Bearer token dan sliding-window rate limiter | `beta0.2.1` |
| 🗂️ **Session History** | Memori chat multi-turn dengan TTL auto-cleanup | `beta0.2.2` |
| 🩺 **Provider Health Check** | Probing provider di background dan filter availability berbasis health | `beta0.2.3` |
| ⚡ **Caching Layer** | Cache in-memory (LRU + TTL) untuk optimasi latensi dan biaya | `beta0.2.4` |
| 📦 **Batch Processing** | Eksekusi konkuren untuk banyak prompt/teks dalam satu request | `beta0.2.5` |
| 🚀 **Integrasi NVIDIA NIM** | Integrasi provider NVIDIA NIM yang OpenAI-compatible | `beta0.2.6` |
| 🧠 **Smart Auto-Fallback** | Auto provider mode dengan prioritas routing dan fallback elegan | `beta0.2.7` |
| 💡 **Reasoning Capability** | Deteksi model reasoning/thinking dan expose capability model | `beta0.2.8` |

---

## 🏗️ Tech Stack

| Layer | Teknologi |
|---|---|
| **Backend** | Python 3.11+, FastAPI, Pydantic v2, asyncio |
| **Providers** | Ollama, Google Gemini API, NVIDIA NIM |
| **Transport** | REST API, SSE (Server-Sent Events) |
| **Infra Services** | In-memory cache, health checker, batch service, session manager |
| **Testing** | pytest, pytest-asyncio, pytest-mock, respx |

---

## 🚀 Quick Start

```cmd
# Terminal 1 — Ollama (opsional, hanya jika pakai model lokal)
ollama serve

# Terminal 2 — Backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Buka **[http://localhost:8000/docs](http://localhost:8000/docs)** di browser.

> 📖 Panduan setup dan contoh curl lengkap ada di [`how_to_run.md`](./how_to_run.md)
> 🗺️ Roadmap dan modul plan ada di [`plan/ROADMAP.md`](./plan/ROADMAP.md)

---

## 📁 Struktur Project

```text
ai-local-api/
├── app/                                # Paket utama aplikasi
│   ├── api/                            # Lapisan REST API
│   │   ├── endpoints/                  # Handler endpoint
│   │   │   ├── models.py               # GET /api/v1/models
│   │   │   ├── generate.py             # POST /api/v1/generate
│   │   │   ├── stream.py               # POST /api/v1/stream
│   │   │   ├── embedding.py            # POST /api/v1/embedding
│   │   │   ├── chat.py                 # Endpoint chat POST/GET/DELETE
│   │   │   ├── cache.py                # Endpoint cache GET/DELETE
│   │   │   └── batch.py                # Endpoint batch/generate dan batch/embedding
│   │   ├── dependencies.py             # Singleton service dan dependency injection
│   │   └── router.py                   # Registrasi router /api/v1
│   ├── core/                           # Concern lintas layer (auth, logging, middleware, exceptions)
│   ├── providers/                      # Adapter provider (ollama, gemini, nvidia)
│   ├── schemas/                        # Kontrak request/response Pydantic
│   ├── services/                       # Orkestrasi (generator, cache, health, batch, session)
│   ├── utils/                          # Helper umum (image processing, dll.)
│   ├── config.py                       # Konfigurasi berbasis environment
│   └── main.py                         # Entry point FastAPI + lifespan
├── plan/                               # Roadmap, blueprint, dan task per versi
├── scripts/                            # Script utilitas
├── tests/                              # Grup unit/integration test
├── how_to_run.md                       # Panduan menjalankan service dan curl
├── pyproject.toml                      # Metadata build dan requirement Python
├── requirements.txt                    # Dependency runtime
├── README.md                           # Dokumentasi ringkas bilingual
├── README_EN.md                        # Dokumentasi English
└── README_ID.md                        # Dokumentasi Bahasa Indonesia
```

---

## 📋 Riwayat Rilis

### Phase 2 — Advanced Capabilities (`v0.2.x`)
| Versi | Modul | Highlight |
|---|---|---|
| `v0.2.8` | Reasoning Capability | Deteksi model reasoning dan flag capability |
| `v0.2.7` | Smart Routing & Fallback | Auto provider routing dan graceful degradation |
| `v0.2.6` | NVIDIA NIM Provider | Integrasi API NVIDIA yang OpenAI-compatible |
| `v0.2.5` | Batch Processing | Pemrosesan konkuren untuk multi-item request |
| `v0.2.4` | Caching Layer | Cache LRU + TTL dengan endpoint statistik |
| `v0.2.3` | Provider Health Check | Probing berkala dan tracking availability provider |
| `v0.2.2` | Conversation History | Session chat multi-turn dengan cleanup |
| `v0.2.1` | Auth & Rate Limiting | Gateway token auth dan pembatasan request |

### Phase 1 — Foundation & Core Providers (`v0.1.x`)
| Versi | Modul | Highlight |
|---|---|---|
| `v0.1.9` | Dynamic API Keys | Dukungan manajemen API key berbasis request |
| `v0.1.8` | Provider Testing | Fondasi unit test berbasis mock |
| `v0.1.7` | Multimodal Handling | Pipeline input gambar dan validasi |
| `v0.1.6` | Embedding Endpoint | Endpoint embedding teks dan adapter provider |
| `v0.1.5` | Streaming Adapter | SSE streaming real-time |
| `v0.1.4` | Gemini Provider | Integrasi text generation Google Gemini |
| `v0.1.3` | Provider & Ollama | Kontrak base provider dan implementasi Ollama |
| `v0.1.2` | Schema & Model Registry | Schema request/response dan registry capability model |
| `v0.1.1` | Foundation Core | Scaffolding project, config, logging, exception |

---

## 📄 Lisensi

Project privat — tidak untuk distribusi publik.
