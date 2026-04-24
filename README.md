# 🧠 Multi-Provider AI Core

> **[🇬🇧 English](./README_EN.md)** | **[🇮🇩 Bahasa Indonesia](./README_ID.md)**

**Multi-Provider AI Core** is a robust backend API gateway that unifies multiple AI providers (**Ollama**, **Gemini**, **NVIDIA NIM**) under a single, standardized REST API.

The system is designed as a production-ready AI engine, featuring smart routing, graceful auto-fallback, response caching, and full support for reasoning models, streaming, and multimodal inputs.

---

## ✨ Feature Highlights

| Feature | Description | Version |
|---|---|---|
| 🔌 **Multi-Provider API** | Unified API interface for Ollama (Local), Gemini, and NVIDIA NIM (Cloud) | `beta0.1.x` |
| 🌊 **SSE Streaming** | Real-time token-by-token generation via Server-Sent Events | `beta0.1.5` |
| 📊 **Vector Embedding** | Text embedding generation to empower RAG / Semantic Search pipelines | `beta0.1.6` |
| 🖼️ **Multimodal Support** | Process both images (base64) and text across compatible providers | `beta0.1.7` |
| 🔑 **Dynamic API Keys** | Dynamically inject custom API keys via request headers (no hardcoding needed) | `beta0.1.9` |
| 🛡️ **Auth & Rate Limiting** | Bearer token security and sliding-window rate limiting | `beta0.2.1` |
| 🗂️ **Session History** | Managed multi-turn conversation memory with auto-cleanup | `beta0.2.2` |
| 🩺 **Provider Health Check** | Background availability probing and dynamic provider status tracking | `beta0.2.3` |
| ⚡ **Caching Layer** | In-memory response caching (LRU + TTL) for cost and latency optimization | `beta0.2.4` |
| 📦 **Batch Processing** | High-throughput concurrent execution for multiple prompts/texts | `beta0.2.5` |
| 🚀 **NVIDIA NIM** | Full integration with NVIDIA's OpenAI-compatible API endpoint | `beta0.2.6` |
| 🧠 **Smart Auto-Fallback** | Intelligent routing that prioritizes cloud models and gracefully falls back to local on failure | `beta0.2.7` |
| 💡 **Reasoning Capability** | Seamlessly detect thinking models (e.g. DeepSeek R1) and isolate thought reasoning output | `beta0.2.8` |

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.10+, FastAPI, Pydantic v2, asyncio |
| **Testing** | Pytest (Fully Mocked Provider Tests) |
| **AI Providers** | Ollama (Local), Google Gemini API (Cloud), NVIDIA NIM (Cloud) |
| **Transport** | REST API, SSE (Server-Sent Events) |

---

## 🚀 Quick Start

```cmd
# Terminal 1 — Ollama (optional, if using local models)
ollama serve

# Terminal 2 — Backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Open **[http://localhost:8000/docs](http://localhost:8000/docs)** in your browser for the interactive Swagger API documentation.

> 📖 The complete setup and command-line execution guide is available in [`how_to_run.md`](./how_to_run.md)
> 📘 Detailed API documentation is available at [`docs/API_DOCUMENTATION.md`](./docs/API_DOCUMENTATION_version_beta0.2.8.md)

---

## 📁 Project Structure

```text
ai-local-api/
├── app/
│   ├── api/                    # REST API endpoints & router
│   ├── core/                   # Exception handlers, middleware, config
│   ├── providers/              # Provider abstractions (Ollama, Gemini, NVIDIA)
│   ├── schemas/                # Pydantic models (Request/Response schemas)
│   ├── services/               # Core logic (Generator, Chat, Batch, Cache, etc.)
│   └── main.py                 # FastAPI application entry point
├── docs/                       # Detailed API documentation
├── plan/                       # Roadmap, milestones, & blueprint docs
├── tests/                      # Unit tests (pytest)
└── how_to_run.md               # Quick start & CURL guide
```

---

## 📄 License

Private project — not intended for public distribution.
