# AI Generative Core — Project Blueprint

> **Version**: 1.0.0  
> **Framework**: FastAPI (Python 3.11+)  
> **Codename**: `ai-local-api`  
> **Created**: 2026-04-22

---

## 🎯 Misi

Membangun **centralized AI gateway** yang berfungsi sebagai universal API untuk berbagai operasi AI generative — text generation, multimodal input, embedding, dan streaming — dengan arsitektur yang bersih dan scalable untuk digunakan ulang sebagai core engine di banyak SaaS project.

---

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│              (Any SaaS Frontend / Service / CLI)                │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / SSE
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │/generate │ │ /stream  │ │ /models  │ │   /embedding      │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┬──────────┘  │
│       │             │            │                 │             │
│       ▼             ▼            ▼                 ▼             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    SERVICE LAYER                            ││
│  │  ┌──────────────────┐  ┌─────────────────────────────────┐ ││
│  │  │ GeneratorService │  │       ModelRegistry             │ ││
│  │  │  • route()       │  │  • list_models()                │ ││
│  │  │  • validate()    │  │  • get_model_capabilities()     │ ││
│  │  │  • normalize()   │  │  • register_model()             │ ││
│  │  └────────┬─────────┘  └─────────────────────────────────┘ ││
│  │           │                                                 ││
│  └───────────┼─────────────────────────────────────────────────┘│
│              │                                                   │
│              ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   PROVIDER LAYER                            ││
│  │  ┌────────────────────┐   ┌────────────────────────────┐   ││
│  │  │  OllamaProvider   │   │     GeminiProvider         │   ││
│  │  │  • generate()     │   │     • generate()           │   ││
│  │  │  • stream()       │   │     • stream()             │   ││
│  │  │  • embedding()    │   │     • embedding()          │   ││
│  │  │  • supports_image │   │     • supports_image       │   ││
│  │  └────────┬───────────┘   └──────────┬─────────────────┘   ││
│  │           │                          │                      ││
│  └───────────┼──────────────────────────┼──────────────────────┘│
└──────────────┼──────────────────────────┼───────────────────────┘
               │                          │
               ▼                          ▼
        ┌──────────────┐          ┌──────────────────┐
        │  Ollama API  │          │  Google Gemini   │
        │  (localhost)  │          │  API (cloud)     │
        └──────────────┘          └──────────────────┘
```

---

## 📂 Project Structure

```
ai-local-api/
├── plan/                          # Blueprint & documentation
│   ├── 00-overview.md             # ← You are here
│   ├── 01-project-structure.md    # Folder & file layout
│   ├── 02-provider-layer.md       # Provider abstraction design
│   ├── 03-service-layer.md        # Service & registry design
│   ├── 04-api-layer.md            # Endpoint specifications
│   ├── 05-schemas.md              # Pydantic models & contracts
│   ├── 06-config-and-env.md       # Configuration system
│   ├── 07-error-handling.md       # Error strategy & codes
│   └── 08-implementation-order.md # Step-by-step build order
│
├── app/                           # Main application
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Settings & env loading
│   │
│   ├── api/                       # API Layer
│   │   ├── __init__.py
│   │   ├── router.py              # Central router
│   │   ├── endpoints/
│   │   │   ├── __init__.py
│   │   │   ├── generate.py        # POST /generate
│   │   │   ├── stream.py          # POST /stream
│   │   │   ├── models.py          # GET /models
│   │   │   └── embedding.py       # POST /embedding
│   │   └── dependencies.py        # FastAPI dependencies (DI)
│   │
│   ├── schemas/                   # Pydantic Models
│   │   ├── __init__.py
│   │   ├── requests.py            # Request schemas
│   │   ├── responses.py           # Response schemas
│   │   └── common.py              # Shared enums & types
│   │
│   ├── services/                  # Service Layer
│   │   ├── __init__.py
│   │   ├── generator.py           # GeneratorService
│   │   └── model_registry.py      # ModelRegistry
│   │
│   ├── providers/                 # Provider Layer
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract BaseProvider
│   │   ├── ollama.py              # OllamaProvider
│   │   └── gemini.py              # GeminiProvider
│   │
│   ├── core/                      # Cross-cutting concerns
│   │   ├── __init__.py
│   │   ├── exceptions.py          # Custom exceptions
│   │   ├── logging.py             # Logging setup
│   │   └── middleware.py          # Request/response logging
│   │
│   └── utils/                     # Utilities
│       ├── __init__.py
│       └── image.py               # Image processing helpers
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── test_providers/
│   ├── test_services/
│   └── test_api/
│
├── .env.example                   # Environment template
├── .gitignore
├── pyproject.toml                 # Project metadata & deps
├── requirements.txt               # Pinned dependencies
└── README.md
```

---

## 📦 Core Dependencies

| Package | Purpose | Version |
|---|---|---|
| `fastapi` | Web framework | `>=0.115` |
| `uvicorn[standard]` | ASGI server | `>=0.34` |
| `pydantic` | Data validation | `>=2.0` |
| `pydantic-settings` | Env config | `>=2.0` |
| `httpx` | Async HTTP client | `>=0.28` |
| `google-genai` | Google Gemini SDK | `>=1.0` |
| `sse-starlette` | Server-Sent Events | `>=2.0` |
| `python-dotenv` | .env loading | `>=1.0` |
| `loguru` | Structured logging | `>=0.7` |

---

## 🔑 Design Principles

1. **Provider Agnostic** — Business logic never touches provider-specific code
2. **Single Responsibility** — Each layer has exactly one job
3. **Open/Closed** — Adding a new provider = 1 new file, 0 changes to existing code
4. **Contract-First** — All inputs/outputs defined by Pydantic schemas
5. **Async-Native** — All I/O operations are async
6. **SaaS-Ready** — Designed to be embedded as a submodule or package in any project

---

## 📋 Blueprint Documents

| # | Document | Purpose |
|---|---|---|
| 00 | `00-overview.md` | High-level architecture & goals |
| 01 | `01-project-structure.md` | Detailed file layout & responsibilities |
| 02 | `02-provider-layer.md` | Abstract base & provider implementations |
| 03 | `03-service-layer.md` | Service logic & model registry |
| 04 | `04-api-layer.md` | Endpoint specs with request/response examples |
| 05 | `05-schemas.md` | All Pydantic model definitions |
| 06 | `06-config-and-env.md` | Configuration & environment variables |
| 07 | `07-error-handling.md` | Error codes, exception hierarchy, middleware |
| 08 | `08-implementation-order.md` | Step-by-step build sequence |

> **Next**: See [01-project-structure.md](./01-project-structure.md) for detailed file responsibilities.
