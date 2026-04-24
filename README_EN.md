# 🧠 Multi-Provider AI Core

> **[🇬🇧 English](./README_EN.md)** | **[🇮🇩 Bahasa Indonesia](./README_ID.md)**

**Multi-Provider AI Core** is a roadmap-driven backend API gateway that unifies multiple AI providers (**Ollama**, **Gemini**, **NVIDIA NIM**) under one standardized REST API.

The system is designed as a production-ready AI engine with smart routing, graceful auto-fallback, caching, health-aware model availability, streaming, multimodal support, and reasoning capability detection.

---

## ✨ Feature Highlights

| Feature | Description | Version |
|---|---|---|
| 🔌 **Multi-Provider API** | Unified API interface for Ollama (Local), Gemini (Cloud), and NVIDIA NIM (Cloud) | `beta0.1.x` |
| 🌊 **SSE Streaming** | Real-time token-by-token generation via Server-Sent Events | `beta0.1.5` |
| 📊 **Vector Embedding** | Text embedding generation for RAG / Semantic Search pipelines | `beta0.1.6` |
| 🖼️ **Multimodal Support** | Process text + image inputs on supported models | `beta0.1.7` |
| 🔑 **Dynamic API Keys** | Dynamic API key injection and key rotation support | `beta0.1.9` |
| 🛡️ **Auth & Rate Limiting** | Bearer token gateway auth and sliding-window rate limiting | `beta0.2.1` |
| 🗂️ **Session History** | Managed multi-turn chat memory with TTL auto-cleanup | `beta0.2.2` |
| 🩺 **Provider Health Check** | Background provider probing and health-aware availability filter | `beta0.2.3` |
| ⚡ **Caching Layer** | In-memory response caching (LRU + TTL) for latency and cost optimization | `beta0.2.4` |
| 📦 **Batch Processing** | Concurrent execution for multiple prompts/texts in a single request | `beta0.2.5` |
| 🚀 **NVIDIA NIM Integration** | OpenAI-compatible NVIDIA NIM provider integration | `beta0.2.6` |
| 🧠 **Smart Auto-Fallback** | Auto provider mode with priority routing and graceful fallback | `beta0.2.7` |
| 💡 **Reasoning Capability** | Reasoning/thinking model detection exposed in model capabilities | `beta0.2.8` |

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11+, FastAPI, Pydantic v2, asyncio |
| **Providers** | Ollama, Google Gemini API, NVIDIA NIM |
| **Transport** | REST API, SSE (Server-Sent Events) |
| **Infra Services** | In-memory cache, health checker, batch service, session manager |
| **Testing** | pytest, pytest-asyncio, pytest-mock, respx |

---

## 🚀 Quick Start

```cmd
# Terminal 1 — Ollama (optional, only if using local models)
ollama serve

# Terminal 2 — Backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Open **[http://localhost:8000/docs](http://localhost:8000/docs)** in your browser.

> 📖 Full setup and curl examples are available in [`how_to_run.md`](./how_to_run.md)
> 🗺️ Roadmap and module plan are available in [`plan/ROADMAP.md`](./plan/ROADMAP.md)

---

## 📁 Project Structure

```text
ai-local-api/
├── app/                                # Main application package
│   ├── api/                            # REST API layer
│   │   ├── endpoints/                  # Route handlers
│   │   │   ├── models.py               # GET /api/v1/models
│   │   │   ├── generate.py             # POST /api/v1/generate
│   │   │   ├── stream.py               # POST /api/v1/stream
│   │   │   ├── embedding.py            # POST /api/v1/embedding
│   │   │   ├── chat.py                 # POST/GET/DELETE chat session endpoints
│   │   │   ├── cache.py                # GET/DELETE cache endpoints
│   │   │   └── batch.py                # POST batch/generate and batch/embedding
│   │   ├── dependencies.py             # Service singletons and dependency injection
│   │   └── router.py                   # /api/v1 router registration
│   ├── core/                           # Cross-cutting concerns (auth, logging, middleware, exceptions)
│   ├── providers/                      # Provider adapters (ollama, gemini, nvidia)
│   ├── schemas/                        # Pydantic request/response contracts
│   ├── services/                       # Orchestration (generator, cache, health, batch, sessions)
│   ├── utils/                          # Shared helpers (image processing, etc.)
│   ├── config.py                       # Environment-based settings
│   └── main.py                         # FastAPI entry point + lifespan
├── plan/                               # Roadmap, blueprint, and per-version tasks
├── scripts/                            # Utility scripts
├── tests/                              # Unit/integration test groups
├── how_to_run.md                       # Execution and curl guide
├── pyproject.toml                      # Build metadata and Python requirement
├── requirements.txt                    # Runtime dependencies
├── README.md                           # Bilingual overview
├── README_EN.md                        # English documentation
└── README_ID.md                        # Indonesian documentation
```

---

## 📋 Release History

### Phase 2 — Advanced Capabilities (`v0.2.x`)
| Version | Module | Highlight |
|---|---|---|
| `v0.2.8` | Reasoning Capability | Reasoning model detection and capability flag support |
| `v0.2.7` | Smart Routing & Fallback | Auto provider routing and graceful degradation |
| `v0.2.6` | NVIDIA NIM Provider | NVIDIA OpenAI-compatible API integration |
| `v0.2.5` | Batch Processing | Concurrent processing for multi-item requests |
| `v0.2.4` | Caching Layer | LRU + TTL caching with stats endpoints |
| `v0.2.3` | Provider Health Check | Periodic probes and provider availability tracking |
| `v0.2.2` | Conversation History | Multi-turn session management with cleanup |
| `v0.2.1` | Auth & Rate Limiting | Gateway token auth and request throttling |

### Phase 1 — Foundation & Core Providers (`v0.1.x`)
| Version | Module | Highlight |
|---|---|---|
| `v0.1.9` | Dynamic API Keys | Request-driven key management support |
| `v0.1.8` | Provider Testing | Mocked unit testing foundations |
| `v0.1.7` | Multimodal Handling | Image input and validation pipeline |
| `v0.1.6` | Embedding Endpoint | Text embedding endpoint and adapters |
| `v0.1.5` | Streaming Adapter | Real-time SSE streaming |
| `v0.1.4` | Gemini Provider | Google Gemini text generation integration |
| `v0.1.3` | Provider & Ollama | Base provider contract and Ollama implementation |
| `v0.1.2` | Schema & Model Registry | Request/response schemas and model capability registry |
| `v0.1.1` | Foundation Core | Project scaffolding, config, logging, exceptions |

---

## 📄 License

Private project — not intended for public distribution.
