# Task 2 — Request Schemas

> **Modul**: beta0.1.2 — Schema & Model Registry  
> **Estimasi**: Low (30–45 menit)  
> **Dependencies**: Task 1 (Common Types)

---

## 1. Judul Task

Implementasi `app/schemas/requests.py` — Pydantic models untuk semua request bodies (GenerateRequest, StreamRequest, EmbeddingRequest).

---

## 2. Deskripsi

Membuat Pydantic BaseModel untuk setiap jenis request yang akan diterima oleh API. Schemas ini memvalidasi input secara otomatis — type checking, required fields, min_length, enum validation — sehingga endpoint hanya menerima data yang valid.

---

## 3. Tujuan Teknis

- `GenerateRequest` — text/multimodal generation (provider, model, input, images, stream)
- `StreamRequest` — SSE streaming (provider, model, input, images)
- `EmbeddingRequest` — vector embedding (provider, model, input)
- Semua field memiliki type hint, validation, dan examples yang benar
- Auto-dokumentasi di Swagger UI

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/schemas/requests.py` dengan 3 request models

### ❌ Yang Tidak Dikerjakan

- Response schemas → task 3
- Endpoint implementations
- Custom validators (beyond Pydantic built-in)

---

## 5. Langkah Implementasi

### Step 1: Buat `app/schemas/requests.py`

```python
"""
Request schemas for AI Generative Core API.

These Pydantic models define and validate the structure of incoming
request bodies for all API endpoints.
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import ProviderEnum


class GenerateRequest(BaseModel):
    """
    Request body for POST /generate.

    Supports text-only and multimodal (text + images) generation.
    If images are provided, the model must support multimodal input.
    """

    provider: ProviderEnum = Field(
        ...,
        description="AI provider to use",
        examples=["ollama", "gemini"],
    )
    model: str = Field(
        ...,
        description="Model name",
        examples=["llama3.2", "gemini-2.0-flash"],
    )
    input: str = Field(
        ...,
        min_length=1,
        description="Text prompt for generation",
    )
    images: Optional[list[str]] = Field(
        default=None,
        description="Optional list of base64-encoded images or image URLs for multimodal input",
    )
    stream: bool = Field(
        default=False,
        description="If true, use POST /stream endpoint instead for SSE streaming",
    )


class StreamRequest(BaseModel):
    """
    Request body for POST /stream.

    Same as GenerateRequest but without the stream flag,
    since streaming is implicit for this endpoint.
    """

    provider: ProviderEnum = Field(
        ...,
        description="AI provider to use",
        examples=["ollama", "gemini"],
    )
    model: str = Field(
        ...,
        description="Model name",
        examples=["llama3.2", "gemini-2.0-flash"],
    )
    input: str = Field(
        ...,
        min_length=1,
        description="Text prompt for generation",
    )
    images: Optional[list[str]] = Field(
        default=None,
        description="Optional list of base64-encoded images for multimodal input",
    )


class EmbeddingRequest(BaseModel):
    """
    Request body for POST /embedding.

    Generates a vector embedding from the input text.
    The model must support embedding capability.
    """

    provider: ProviderEnum = Field(
        ...,
        description="AI provider to use",
        examples=["ollama", "gemini"],
    )
    model: str = Field(
        ...,
        description="Embedding model name",
        examples=["nomic-embed-text", "text-embedding-004"],
    )
    input: str = Field(
        ...,
        min_length=1,
        description="Text to generate embedding for",
    )
```

### Step 2: Verifikasi

```bash
python -c "
from app.schemas.requests import GenerateRequest, StreamRequest, EmbeddingRequest

# Valid GenerateRequest
req = GenerateRequest(provider='ollama', model='llama3.2', input='Hello world')
print(f'provider={req.provider}, model={req.model}, input={req.input}')
print(f'images={req.images}, stream={req.stream}')

# Valid with images
req2 = GenerateRequest(
    provider='gemini',
    model='gemini-2.0-flash',
    input='Describe this',
    images=['base64data...'],
    stream=False,
)
print(f'images count={len(req2.images)}')

# Valid EmbeddingRequest
emb = EmbeddingRequest(provider='ollama', model='nomic-embed-text', input='test')
print(f'embedding: provider={emb.provider}, model={emb.model}')
"
```

### Step 3: Validasi error handling

```bash
python -c "
from pydantic import ValidationError
from app.schemas.requests import GenerateRequest

# Missing required field
try:
    GenerateRequest(provider='ollama', model='llama3.2')
except ValidationError as e:
    print('Missing input:', e.error_count(), 'errors')

# Invalid provider
try:
    GenerateRequest(provider='openai', model='gpt-4', input='hi')
except ValidationError as e:
    print('Invalid provider:', e.error_count(), 'errors')

# Empty input
try:
    GenerateRequest(provider='ollama', model='llama3.2', input='')
except ValidationError as e:
    print('Empty input:', e.error_count(), 'errors')
"
```

Output yang diharapkan:

```
Missing input: 1 errors
Invalid provider: 1 errors
Empty input: 1 errors
```

---

## 6. Output yang Diharapkan

### File: `app/schemas/requests.py`

Isi seperti Step 1 di atas.

### Validation Behavior

| Input | Result |
|---|---|
| `provider="ollama", model="llama3.2", input="hi"` | ✅ Valid |
| `provider="gemini", model="gemini-2.0-flash", input="hi", images=["..."]` | ✅ Valid |
| `provider="openai", model="gpt-4", input="hi"` | ❌ Invalid provider |
| `provider="ollama", model="llama3.2"` | ❌ Missing input |
| `provider="ollama", model="llama3.2", input=""` | ❌ Empty input (min_length=1) |

---

## 7. Dependencies

- **Task 1** — `ProviderEnum` dari `app/schemas/common.py`

---

## 8. Acceptance Criteria

- [ ] File `app/schemas/requests.py` ada
- [ ] `GenerateRequest`, `StreamRequest`, `EmbeddingRequest` bisa di-import
- [ ] `GenerateRequest(provider="ollama", model="llama3.2", input="hi")` valid
- [ ] `GenerateRequest(provider="invalid", ...)` menghasilkan ValidationError
- [ ] `GenerateRequest(..., input="")` menghasilkan ValidationError (min_length=1)
- [ ] `GenerateRequest` tanpa `input` → ValidationError (required)
- [ ] `GenerateRequest.stream` default `False`
- [ ] `GenerateRequest.images` default `None`
- [ ] `StreamRequest` TIDAK memiliki field `stream`
- [ ] `EmbeddingRequest` TIDAK memiliki field `images`

---

## 9. Estimasi

**Low** — Pydantic model definitions, straightforward.
