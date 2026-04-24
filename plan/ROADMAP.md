# AI Generative Core — Development Roadmap

> **Project**: ai-local-api  
> **Format**: Modular Versioning (beta0.X.Y)  
> **Created**: 2026-04-22  
> **Last Updated**: 2026-04-24  
> **Current Version**: 0.2.8

---

## 📋 Roadmap Overview — Phase 1 (beta0.1.X)

```
beta0.1.1   beta0.1.2   beta0.1.3   beta0.1.4   beta0.1.5   beta0.1.6   beta0.1.7   beta0.1.8   beta0.1.9
  │           │           │           │           │           │           │           │           │
  ▼           ▼           ▼           ▼           ▼           ▼           ▼           ▼           ▼
┌─────┐   ┌─────┐   ┌─────────┐  ┌────────┐  ┌────────┐  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌────────┐
│Found│──▶│Sche-│──▶│Provider │──▶│Gemini  │──▶│Stream- │  │Embed-   │ │Multi-    │ │Provider │ │Dynamic │
│ation│   │ma & │   │Abstract │  │Provider│  │ing     │  │ding     │ │modal     │ │Testing  │ │API Keys│
│Core │   │Regi-│   │& Ollama │  │        │  │Adapter │  │Endpoint │ │Handling  │ │         │ │        │
│     │   │stry │   │         │  │        │  │        │  │         │ │          │ │         │ │        │
└─────┘   └─────┘   └─────────┘  └────────┘  └────────┘  └─────────┘ └──────────┘ └─────────┘ └────────┘
 Day 1     Day 2      Day 3       Day 4       Day 5       Day 5       Day 6-7      Day 8       Day 9
```

**Dependency Chain:**
```
0.1.1 ──▶ 0.1.2 ──▶ 0.1.3 ──▶ 0.1.4 ──▶ 0.1.5 ──▶ 0.1.7 ──▶ 0.1.8 ──▶ 0.1.9
                                    │
                                    └──▶ 0.1.6 (parallel with 0.1.5)
```

> **Note**: beta0.1.5 dan beta0.1.6 bisa dikerjakan **parallel** karena keduanya depend on 0.1.4 tapi tidak saling depend.

---

## 📊 Version Matrix — Phase 1 (beta0.1.X) ✅ COMPLETE

| Version | Modul | Scope | Depends On | Status |
|---|---|---|---|---|
| **beta0.1.1** | Foundation Core | Scaffolding, config, errors, logging | — | ✅ Done |
| **beta0.1.2** | Schema & Model Registry | Pydantic schemas, registry, GET /models | 0.1.1 | ✅ Done |
| **beta0.1.3** | Provider & Ollama | BaseProvider, OllamaProvider, POST /generate | 0.1.2 | ✅ Done |
| **beta0.1.4** | Gemini Provider | GeminiProvider text generation | 0.1.3 | ✅ Done |
| **beta0.1.5** | Streaming Adapter | SSE streaming (Ollama + Gemini), POST /stream | 0.1.4 | ✅ Done |
| **beta0.1.6** | Embedding Endpoint | Embedding (Ollama + Gemini), POST /embedding | 0.1.4 | ✅ Done |
| **beta0.1.7** | Multimodal Handling | Image input support, image utils | 0.1.5 | ✅ Done |
| **beta0.1.8** | Provider Testing | Unit testing untuk provider (fully mocked) | 0.1.7 | ✅ Done |
| **beta0.1.9** | Dynamic API Keys | Custom API Key via Request Headers (No Hardcode) | 0.1.8 | ✅ Done |

---

## 🎯 Capability Progression — Phase 1

| Capability | 0.1.1 | 0.1.2 | 0.1.3 | 0.1.4 | 0.1.5 | 0.1.6 | 0.1.7 | 0.1.8 | 0.1.9 |
|---|---|---|---|---|---|---|---|---|---|
| Server runs | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Config & env | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Error handling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Logging | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| List models | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ollama text gen | — | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Gemini text gen | — | — | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SSE streaming | — | — | — | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| Embedding | — | — | — | — | — | ✅ | ✅ | ✅ | ✅ |
| Image input | — | — | — | — | — | — | ✅ | ✅ | ✅ |
| Fully Tested | — | — | — | — | — | — | — | ✅ | ✅ |
| Dynamic API Keys| — | — | — | — | — | — | — | — | ✅ |

---

## 📊 Version Matrix — Phase 2 (beta0.2.X) ✅ COMPLETE

| Version | Modul | Scope | Depends On | Status |
|---|---|---|---|---|
| **beta0.2.1** | Auth & Rate Limiting | Service token auth, sliding window rate limiter | 0.1.9 | ✅ Done |
| **beta0.2.2** | Conversation History | Multi-turn chat, session manager, auto-cleanup | 0.2.1 | ✅ Done |
| **beta0.2.3** | Provider Health Check | Periodic probes, smart model listing, status endpoint | 0.2.1 | ✅ Done |
| **beta0.2.4** | Caching Layer | Response cache, LRU eviction, cache stats | 0.2.1 | ✅ Done |
| **beta0.2.5** | Batch Processing | Multiple prompts in one request, concurrent execution | 0.2.4 | ✅ Done |
| **beta0.2.6** | NVIDIA NIM Provider | Explore & integrate NVIDIA NIM API (OpenAI-compatible) | 0.2.5 | ✅ Done |
| **beta0.2.7** | Smart Routing & Fallback | Auto provider mode, Graceful degradation | 0.2.6 | ✅ Done |
| **beta0.2.8** | Reasoning Capability | Reasoning discovery, thinking output support | 0.2.7 | ✅ Done |

**Dependency Chain (Phase 2):**
```
0.1.9 ──▶ 0.2.1 ──▶ 0.2.2
               │
               ├──▶ 0.2.3 (parallel with 0.2.2)
               │
               └──▶ 0.2.4 ──▶ 0.2.5 ──▶ 0.2.6 ──▶ 0.2.7 ──▶ 0.2.8
```

---

## 🎯 Capability Progression — Phase 2

| Capability | 0.2.1 | 0.2.2 | 0.2.3 | 0.2.4 | 0.2.5 | 0.2.6 | 0.2.7 | 0.2.8 |
|---|---|---|---|---|---|---|---|---|
| Gateway auth | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Rate limiting | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multi-turn chat | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Provider probing | — | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Response caching | — | — | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| Batch generation | — | — | — | — | ✅ | ✅ | ✅ | ✅ |
| NVIDIA provider  | — | — | — | — | — | ✅ | ✅ | ✅ |
| Dynamic models   | — | — | — | — | — | ✅ | ✅ | ✅ |
| Smart routing    | — | — | — | — | — | — | ✅ | ✅ |
| Auto Fallback    | — | — | — | — | — | — | ✅ | ✅ |
| Reasoning detect | — | — | — | — | — | — | — | ✅ |

---

## 📂 Folder Structure

```
plan/
├── blueprint/                                   # Architecture blueprint (static)
├── ROADMAP.md                                   # ← You are here
├── current_version/                             # Current state snapshot
│
├── beta0.1.1 ... beta0.2.5/                     # ✅ Done (Older versions)
│
├── beta0.2.6-nvidia-nim-provider/               # ✅ Done
│   ├── plan-design-nvidia-nim-provider-beta0.2.6.md
│   └── ...
│
└── beta0.2.7-smart-routing/                     # ✅ Done
    ├── plan-design-smart-routing-beta0.2.7.md
    ├── task1-schemas-and-enum.md
    ├── task2-priority-selection-logic.md
    ├── task3-fallback-loop-generate-chat.md
    ├── task4-fallback-loop-stream-embed.md
    ├── task5-unit-tests.md
    └── task6-documentation.md

├── beta0.2.8-reasoning-capability/              # ✅ Done
│   └── plan-design-reasoning-capability-beta0.2.8.md
```

---

## 🔮 Future Versions (Post beta0.2.X)

| Version | Module | Description |
|---|---|---|
| beta0.3.1 | New Provider: OpenAI | OpenAI GPT integration |
| beta0.3.2 | New Provider: Anthropic | Claude integration |
| beta0.4.1 | RAG Pipeline | Vector DB integration |
| beta0.4.2 | SaaS Multitenancy | Tenant isolation, usage tracking |

---

## 🧭 Prioritization Rationale

1. **Foundation (0.1.1)** — Tanpa ini, tidak ada yang bisa berjalan
2. **Schema & Registry (0.1.2)** — Data contract harus fix sebelum logic
3. **Ollama first (0.1.3)** — Local = cepat develop, no API key needed
4. **Gemini second (0.1.4)** — Validasi multi-provider architecture
5. **Streaming (0.1.5)** — Critical UX untuk chat-based SaaS
6. **Embedding (0.1.6)** — Enabler untuk RAG dan semantic search
7. **Multimodal (0.1.7)** — Highest complexity, butuh semua layer siap dulu
8. **Auth & Rate Limiting (0.2.1)** — Security gate sebelum fitur lain terbuka
9. **Conversation History (0.2.2)** — Enabler untuk stateful chat
10. **Provider Health Check (0.2.3)** — Availability awareness, smart model routing
11. **Caching Layer (0.2.4)** — Performance optimization, reduce API cost
12. **Batch Processing (0.2.5)** — Throughput untuk SaaS workloads (bulk generation & embedding)
13. **NVIDIA NIM Provider (0.2.6)** — Ekspansi provider ke cloud GPU-powered models (OpenAI-compatible)
14. **Smart Routing (0.2.7)** — Menambahkan reliabilitas maksimal dengan graceful degradation otomatis
15. **Reasoning Capability (0.2.8)** — Identifikasi model reasoning dan dukung output pemikiran.

### Prinsip

- **Fondasi dulu** → baru fitur
- **Satu provider dulu** → baru multi-provider
- **Text dulu** → baru multimodal
- **Sync dulu** → baru streaming
- **Security dulu** → baru fitur production
- **Explore dulu** → baru production integration
- **Setiap versi bisa ditest independen**
