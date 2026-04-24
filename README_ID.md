# 🧠 AI Generative Core

> **[🇬🇧 English](./README_EN.md)** | **[🇮🇩 Bahasa Indonesia](./README_ID.md)**

**AI Generative Core** adalah sebuah backend API gateway yang menyatukan berbagai provider AI (**Ollama**, **Gemini**, **NVIDIA NIM**) ke dalam satu REST API seragam.

Sistem ini didesain sebagai *production-ready AI engine* dengan kemampuan *smart routing*, *graceful auto-fallback*, *caching*, dan dukungan penuh untuk model bernalar (reasoning), streaming, serta multimodal.

---

## ✨ Highlight Fitur

| Fitur | Deskripsi | Versi |
|---|---|---|
| 🔌 **Multi-Provider API** | Satu antarmuka API untuk Ollama (Lokal), Gemini, dan NVIDIA NIM (Cloud) | `beta0.1.x` |
| 🌊 **SSE Streaming** | Respons *real-time* token-by-token menggunakan Server-Sent Events | `beta0.1.5` |
| 📊 **Vector Embedding** | Dukungan *embedding* teks untuk pipeline RAG / Semantic Search | `beta0.1.6` |
| 🖼️ **Multimodal Support** | Dukungan input kombinasi gambar (base64) dan teks untuk provider yang mendukung | `beta0.1.7` |
| 🔑 **Dynamic API Keys** | Injeksi API key kustom secara dinamis melalui request header tanpa hardcode | `beta0.1.9` |
| 🛡️ **Auth & Rate Limiting** | Keamanan *Bearer token* dan *sliding window rate limiter* | `beta0.2.1` |
| 🗂️ **Session History** | *Memory management* untuk percakapan multi-turn secara otomatis | `beta0.2.2` |
| 🩺 **Provider Health Check** | *Probing* ketersediaan provider secara berkala di *background* | `beta0.2.3` |
| ⚡ **Caching Layer** | Respons *in-memory cache* (LRU + TTL) untuk penghematan *cost* dan latensi | `beta0.2.4` |
| 📦 **Batch Processing** | Eksekusi konkuren (paralel) untuk banyak prompt/teks sekaligus | `beta0.2.5` |
| 🚀 **NVIDIA NIM** | Integrasi penuh dengan API OpenAI-compatible dari NVIDIA | `beta0.2.6` |
| 🧠 **Smart Auto-Fallback** | *Routing* pintar: memprioritaskan cloud dan otomatis *fallback* ke lokal jika gagal | `beta0.2.7` |
| 💡 **Reasoning Capability** | Deteksi model bernalar (*thinking models* seperti DeepSeek R1) dan pemisahan output *thought* | `beta0.2.8` |

---

## 🏗️ Tech Stack

| Layer | Teknologi |
|---|---|
| **Backend** | Python 3.10+, FastAPI, Pydantic v2, asyncio |
| **Testing** | Pytest (Fully Mocked Provider Tests) |
| **AI Providers** | Ollama (Local), Google Gemini API (Cloud), NVIDIA NIM (Cloud) |
| **Transport** | REST API, SSE (Server-Sent Events) |

---

## 🚀 Quick Start

```cmd
# Terminal 1 — Ollama (opsional, jika ingin pakai model lokal)
ollama serve

# Terminal 2 — Backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Buka **[http://localhost:8000/docs](http://localhost:8000/docs)** di browser untuk mencoba Swagger UI API.

> 📖 Panduan lengkap cara menjalankan dan mengetes *curl* ada di [`how_to_run.md`](./how_to_run.md)
> 📘 Dokumentasi API detail tersedia di [`docs/API_DOCUMENTATION.md`](./docs/API_DOCUMENTATION_version_beta0.2.8.md)

---

## 📁 Struktur Project

```text
ai-local-api/
├── app/
│   ├── api/                    # REST API endpoints & router
│   ├── core/                   # Exception handlers, middleware, config
│   ├── providers/              # Abstraksi provider (Ollama, Gemini, NVIDIA)
│   ├── schemas/                # Pydantic models (Request/Response)
│   ├── services/               # Logic (Generator, Chat, Batch, Cache, dll)
│   └── main.py                 # FastAPI application entry point
├── docs/                       # Dokumentasi detail API
├── plan/                       # Dokumen roadmap, milestone, & blueprint
├── tests/                      # Unit testing (pytest)
└── how_to_run.md               # Quick start guide
```

---

## 📄 Lisensi

Project privat — tidak untuk distribusi publik.
