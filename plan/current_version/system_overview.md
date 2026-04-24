# System Overview — AI Generative Core

> **Snapshot Version**: beta0.2.7-smart-routing
> **App Version**: 0.2.7  
> **Last Updated**: 2026-04-24  
> **Status**: ✅ All Phase 1, Phase 2, & Phase 3 (0.2.6, 0.2.7) features implemented

---

## Project Purpose

**AI Generative Core** is a universal AI Gateway API built as a backend microservice for SaaS applications. It provides a **single, unified REST API** to interact with multiple AI providers (currently Ollama and Google Gemini), abstracting away provider-specific differences.

The system enables any frontend or service to:
- Generate text responses from local or cloud AI models
- Stream AI-generated tokens in real-time via SSE
- Generate vector embeddings for semantic search / RAG pipelines
- Query available models and their capabilities
- Dynamically rotate API keys with automatic failover

---

## Current Capabilities

### ✅ Implemented Features (beta0.1.1 → beta0.1.9)

| # | Feature | Version | Status |
|---|---------|---------|--------|
| 1 | Foundation Core (config, logging, error handling, middleware) | beta0.1.1 | ✅ Done |
| 2 | Pydantic V2 schemas & Model Registry with capability flags | beta0.1.2 | ✅ Done |
| 3 | Ollama Provider (text generation via `/api/generate`) | beta0.1.3 | ✅ Done |
| 4 | Gemini Provider (text generation via `google-genai` SDK) | beta0.1.4 | ✅ Done |
| 5 | SSE Streaming (Ollama NDJSON + Gemini SDK streaming) | beta0.1.5 | ✅ Done |
| 6 | Embedding Endpoint (Ollama `/api/embed` + Gemini `embed_content`) | beta0.1.6 | ✅ Done |
| 7 | Multimodal Handling (base64 image input, MIME detection, size validation) | beta0.1.7 | ✅ Done |
| 8 | Provider Testing (test scaffolding with pytest + pytest-asyncio) | beta0.1.8 | ✅ Done |
| 9 | Dynamic API Keys (multi-key pool, round-robin rotation, auto-blacklist) | beta0.1.9 | ✅ Done |
| 10 | Auth & Rate Limiting (Single token auth, sliding window rate limiter) | beta0.2.1 | ✅ Done |
| 11 | Conversation History (Session management, TTL cleanup, multi-turn chat) | beta0.2.2 | ✅ Done |
| 12 | Provider Health Check (Background probing, status tracking, health endpoints) | beta0.2.3 | ✅ Done |
| 13 | Caching Layer (In-memory LRU cache, SHA-256 keys, TTL, Stats) | beta0.2.4 | ✅ Done |
| 14 | Batch Processing (Concurrent multi-item generate & embedding) | beta0.2.5 | ✅ Done |
| 15 | NVIDIA NIM Provider (Explore & integrate NVIDIA NIM API) | beta0.2.6 | ✅ Done |
| 16 | Smart Routing & Fallback (Auto provider mode, graceful fallback) | beta0.2.7 | ✅ Done |

### 🔌 Active API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check (app name, version, status) |
| `GET` | `/health/providers` | Detailed provider health status & summary |
| `GET` | `/api/v1/models` | List registered models (optional `?provider=` filter, `?include_unavailable=`) |
| `POST` | `/api/v1/generate` | Text / multimodal generation (sync) |
| `POST` | `/api/v1/stream` | Token-by-token generation via SSE |
| `POST` | `/api/v1/embedding` | Vector embedding generation |
| `POST` | `/api/v1/chat` | Multi-turn chat conversation |
| `GET` | `/api/v1/chat/{session_id}/history` | Get chat session history |
| `DELETE` | `/api/v1/chat/{session_id}` | Delete chat session |
| `GET` | `/api/v1/cache/stats` | Get cache statistics |
| `DELETE` | `/api/v1/cache` | Clear all cached entries |
| `POST` | `/api/v1/batch/generate` | Batch text generation (concurrent) |
| `POST` | `/api/v1/batch/embedding` | Batch embedding generation (concurrent) |

### 🤖 Registered Default Models

| Provider | Model | Text | Image | Embedding | Streaming |
|----------|-------|------|-------|-----------|-----------|
| ollama | `gemma4:e2b` | ✅ | ❌ | ❌ | ✅ |
| ollama | `qwen3-embedding:0.6b` | ❌ | ❌ | ✅ | ❌ |
| gemini | `gemini-2.5-pro` | ✅ | ✅ | ❌ | ✅ |
| gemini | `gemini-3.0-pro-preview` | ✅ | ✅ | ❌ | ✅ |
| gemini | `gemini-3.1-flash-preview` | ✅ | ✅ | ❌ | ✅ |
| gemini | `text-embedding-004` | ❌ | ❌ | ✅ | ❌ |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                     FastAPI Application                   │
│                        (main.py)                          │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                   Middleware Layer                    │  │
│  │            RequestLoggingMiddleware + CORS            │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │                                  │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │                    API Layer                          │  │
│  │   /models  /generate  /stream  /embedding            │  │
│  │   (parse → call service → return, zero logic)        │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │ Depends()                        │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │                  Service Layer                        │  │
│  │   GeneratorService (central orchestrator)             │  │
│  │   ModelRegistry (capability catalog)                  │  │
│  │   KeyManager (multi-key rotation + blacklist)         │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │                                  │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │                 Provider Layer                        │  │
│  │   BaseProvider (ABC) ← OllamaProvider                │  │
│  │                      ← GeminiProvider                │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │                                  │
└─────────────────────────┼──────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
     ┌──────────────┐       ┌──────────────┐
     │    Ollama     │       │   Google     │
     │  (localhost)  │       │   Gemini     │
     │   HTTP API    │       │   SDK API    │
     └──────────────┘       └──────────────┘
```

### Request Flow

```
Client Request
  → FastAPI Router (/api/v1/*)
    → Endpoint (parse + validate via Pydantic)
      → GeneratorService (resolve provider → validate model → check capability)
        → Provider.generate() / .stream() / .embedding()
          → External AI API (Ollama HTTP / Gemini SDK)
        ← Normalized response dict
      ← Pydantic Response model
    ← JSON / SSE Response
```

### Key Architecture Decisions

1. **3-Layer separation** — Endpoints have zero business logic; all orchestration lives in `GeneratorService`
2. **Provider abstraction** — Adding a new provider requires zero changes to endpoints or services
3. **Capability-based validation** — Model capabilities are checked before any provider call
4. **Factory pattern** — `create_provider()` is the single point of provider instantiation
5. **Singleton DI** — Services are initialized once at startup, injected via FastAPI `Depends()`

---

## Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Language** | Python | 3.12+ |
| **Web Framework** | FastAPI | ≥0.115 |
| **ASGI Server** | Uvicorn | ≥0.34 |
| **Data Validation** | Pydantic V2 | ≥2.0 |
| **Config Management** | pydantic-settings | ≥2.0 |
| **HTTP Client** | httpx (async) | ≥0.28 |
| **Gemini SDK** | google-genai | ≥1.0 |
| **SSE Streaming** | sse-starlette | ≥2.0 |
| **Logging** | loguru | ≥0.7 |
| **Env Loading** | python-dotenv | ≥1.0 |
| **Testing** | pytest + pytest-asyncio + pytest-mock + respx | ≥8.0 |
| **Local LLM** | Ollama | (external) |
| **Cloud AI** | Google Gemini API | (external) |

---

## Phase 2 & 3 — Completed Features

> 🚀 All listed Phase 2 & 3 modules have been successfully implemented and tested.

| Version | Module | Status |
|---------|--------|--------|
| beta0.2.1 | Auth & Rate Limiting | ✅ Done |
| beta0.2.2 | Conversation History | ✅ Done |
| beta0.2.3 | Provider Health Check | ✅ Done |
| beta0.2.4 | Caching Layer | ✅ Done |
| beta0.2.5 | Batch Processing | ✅ Done |
| beta0.2.6 | NVIDIA NIM Provider | ✅ Done |
| beta0.2.7 | Smart Routing & Fallback | ✅ Done |
