# 05 — Pydantic Schemas

---

## Common Types

File: `app/schemas/common.py`

```python
from enum import Enum

class ProviderEnum(str, Enum):
    OLLAMA = "ollama"
    GEMINI = "gemini"
```

---

## Request Schemas

File: `app/schemas/requests.py`

```python
from pydantic import BaseModel, Field
from typing import Optional
from app.schemas.common import ProviderEnum


class GenerateRequest(BaseModel):
    """Request for text/multimodal generation."""
    provider: ProviderEnum
    model: str = Field(..., examples=["llama3.2", "gemini-2.0-flash"])
    input: str = Field(..., min_length=1, description="Text prompt")
    images: Optional[list[str]] = Field(
        default=None,
        description="List of base64-encoded images or image URLs"
    )
    stream: bool = Field(default=False, description="Use /stream endpoint instead")


class StreamRequest(BaseModel):
    """Request for SSE streaming generation."""
    provider: ProviderEnum
    model: str
    input: str = Field(..., min_length=1)
    images: Optional[list[str]] = None


class EmbeddingRequest(BaseModel):
    """Request for vector embedding."""
    provider: ProviderEnum
    model: str = Field(..., examples=["nomic-embed-text", "text-embedding-004"])
    input: str = Field(..., min_length=1, description="Text to embed")
```

---

## Response Schemas

File: `app/schemas/responses.py`

```python
from pydantic import BaseModel
from typing import Optional


class UsageInfo(BaseModel):
    """Token usage information."""
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class GenerateResponse(BaseModel):
    """Standard response for generation."""
    output: str
    provider: str
    model: str
    usage: Optional[UsageInfo] = None
    metadata: Optional[dict] = None


class ModelInfo(BaseModel):
    """Model metadata for /models endpoint."""
    name: str
    provider: str
    supports_text: bool
    supports_image: bool
    supports_embedding: bool


class EmbeddingResponse(BaseModel):
    """Response for embedding generation."""
    embedding: list[float]
    provider: str
    model: str


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    code: str
    detail: Optional[str] = None
```

---

## Schema Relationship Diagram

```
GenerateRequest ──→ GeneratorService ──→ GenerateResponse
StreamRequest   ──→ GeneratorService ──→ SSE stream (token chunks)
EmbeddingRequest──→ GeneratorService ──→ EmbeddingResponse
(none)          ──→ ModelRegistry    ──→ list[ModelInfo]
```

> **Next**: See [06-config-and-env.md](./06-config-and-env.md)
