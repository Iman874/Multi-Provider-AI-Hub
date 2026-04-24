# 🧠 Multi-Provider AI Core

> **[🇬🇧 English](./README_EN.md)** | **[🇮🇩 Bahasa Indonesia](./README_ID.md)**

---

**Roadmap-driven AI gateway** for unifying Ollama, Gemini, and NVIDIA NIM behind one standardized REST API.

Sistem **AI gateway berbasis roadmap** untuk menyatukan Ollama, Gemini, dan NVIDIA NIM dalam satu REST API yang seragam.

---

## 🚀 Quick Start

```cmd
# Terminal 1 — Ollama (optional)
ollama serve

# Terminal 2 — Backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Open **[http://localhost:8000/docs](http://localhost:8000/docs)**

> 📖 Full setup guide: [`how_to_run.md`](./how_to_run.md)
> 🗺️ Roadmap source: [`plan/ROADMAP.md`](./plan/ROADMAP.md)

---

## 📁 Project Structure

```text
ai-local-api/
├── app/                    # FastAPI backend package
│   ├── api/                # Endpoints, router, dependencies
│   ├── core/               # Auth, logging, middleware, exceptions
│   ├── providers/          # Ollama, Gemini, NVIDIA provider adapters
│   ├── schemas/            # Pydantic contracts
│   ├── services/           # Generator, cache, health, batch, session logic
│   └── main.py             # Application entry point
├── plan/                   # Roadmap, blueprint, per-version tasks
├── scripts/                # Utility scripts
├── tests/                  # Test suite groups
└── how_to_run.md           # Run and curl guide
```

---

## 📄 License

Private project — not for public distribution.
