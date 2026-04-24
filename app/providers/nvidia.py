"""
NVIDIA NIM AI provider implementation.

Connects to NVIDIA's cloud-hosted inference API via OpenAI-compatible REST endpoints.
See: https://build.nvidia.com/

NVIDIA NIM API endpoints used:
- POST /chat/completions  → text generation (OpenAI format)
- POST /embeddings        → vector embedding (requires input_type)
- GET  /models            → model listing (for health probes)

Key differences from OpenAI standard:
- Embedding models require `input_type` parameter ("query" | "passage")
- Model IDs use org/name format (e.g. "meta/llama-3.3-70b-instruct")
"""

import json
from typing import AsyncGenerator, Optional

import httpx
from loguru import logger

from app.core.exceptions import (
    ProviderAPIError,
    ProviderConnectionError,
    ProviderTimeoutError,
)
from app.providers.base import BaseProvider
from app.services.reasoning_capability import detect_nvidia_reasoning


class NvidiaProvider(BaseProvider):
    """
    Provider implementation for NVIDIA NIM (OpenAI-compatible).

    Communicates with NVIDIA's cloud API using httpx.AsyncClient.
    Uses OpenAI chat/completions format for generation and streaming.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        timeout: int = 120,
    ):
        """
        Initialize NvidiaProvider.

        Args:
            api_key: NVIDIA API key (nvapi-...).
            base_url: NVIDIA NIM API base URL.
            timeout: Request timeout in seconds.
        """
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout),
        )
        logger.info(
            "NvidiaProvider initialized: {url} (timeout={timeout}s)",
            url=base_url,
            timeout=timeout,
        )

    @property
    def name(self) -> str:
        return "nvidia"

    async def generate(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> dict:
        """
        Generate text using NVIDIA NIM's /chat/completions endpoint.

        Converts the prompt to OpenAI chat format and extracts the
        assistant message from the response.

        NVIDIA API request format:
            POST /chat/completions
            {
                "model": "meta/llama-3.3-70b-instruct",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 4096
            }

        NVIDIA API response format:
            {
                "id": "chatcmpl-abc123",
                "choices": [{
                    "message": {"role": "assistant", "content": "Hi!"},
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}
            }
        """
        # Build messages in OpenAI chat format
        messages = [{"role": "user", "content": prompt}]

        payload: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
        }

        try:
            response = await self._client.post(
                "/chat/completions",
                json=payload,
            )
        except httpx.TimeoutException:
            raise ProviderTimeoutError(
                provider=self.name,
                timeout=self._timeout,
            )
        except httpx.ConnectError:
            raise ProviderConnectionError(
                provider=self.name,
                detail=f"Connection failed to {self._base_url}",
            )

        if response.status_code != 200:
            raise ProviderAPIError(
                provider=self.name,
                status=response.status_code,
                detail=response.text[:200],
            )

        data = response.json()

        # Extract content from OpenAI format
        choices = data.get("choices", [])
        output = ""
        if choices:
            output = choices[0].get("message", {}).get("content", "")

        usage_data = data.get("usage", {})

        return {
            "output": output,
            "model": data.get("model", model),
            "provider": self.name,
            "usage": {
                "prompt_tokens": usage_data.get("prompt_tokens"),
                "completion_tokens": usage_data.get("completion_tokens"),
                "total_tokens": usage_data.get("total_tokens"),
            },
            "metadata": {
                "id": data.get("id"),
                "finish_reason": choices[0].get("finish_reason") if choices else None,
            },
        }

    async def stream(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream tokens from NVIDIA NIM's /chat/completions endpoint.

        NVIDIA streams via standard SSE (Server-Sent Events) in OpenAI format.
        Each line is prefixed with "data: " followed by a JSON chunk.

        Example SSE lines:
            data: {"choices":[{"delta":{"content":"Hello"}}]}
            data: {"choices":[{"delta":{"content":" world"}}]}
            data: [DONE]
        """
        messages = [{"role": "user", "content": prompt}]

        payload: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
            "stream": True,
        }

        try:
            async with self._client.stream(
                "POST",
                "/chat/completions",
                json=payload,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise ProviderAPIError(
                        provider=self.name,
                        status=response.status_code,
                        detail=error_text.decode("utf-8", errors="replace")[:200],
                    )

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    # SSE format: "data: {json}" or "data: [DONE]"
                    if not line.startswith("data: "):
                        continue

                    data_str = line[6:]  # Strip "data: " prefix

                    if data_str.strip() == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        logger.warning(
                            "NVIDIA stream: skipping malformed JSON line"
                        )
                        continue

                    # Extract token from delta
                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token

        except httpx.TimeoutException:
            raise ProviderTimeoutError(
                provider=self.name,
                timeout=self._timeout,
            )
        except httpx.ConnectError:
            raise ProviderConnectionError(
                provider=self.name,
                detail=f"Connection failed to {self._base_url}",
            )

    async def embedding(
        self,
        model: str,
        input_text: str,
    ) -> list[float]:
        """
        Generate embedding vector using NVIDIA NIM's /embeddings endpoint.

        Note: NVIDIA asymmetric embedding models require `input_type` parameter.
        We default to "query" which works for search/retrieval use cases.

        NVIDIA API request format:
            POST /embeddings
            {
                "model": "nvidia/nv-embedqa-e5-v5",
                "input": "text to embed",
                "input_type": "query"
            }
        """
        payload: dict = {
            "model": model,
            "input": input_text,
            "input_type": "query",
        }

        try:
            response = await self._client.post(
                "/embeddings",
                json=payload,
            )
        except httpx.TimeoutException:
            raise ProviderTimeoutError(
                provider=self.name,
                timeout=self._timeout,
            )
        except httpx.ConnectError:
            raise ProviderConnectionError(
                provider=self.name,
                detail=f"Connection failed to {self._base_url}",
            )

        if response.status_code != 200:
            raise ProviderAPIError(
                provider=self.name,
                status=response.status_code,
                detail=response.text[:200],
            )

        data = response.json()
        embeddings = data.get("data", [])

        if not embeddings:
            raise ProviderAPIError(
                provider=self.name,
                status=200,
                detail="Empty embedding returned from NVIDIA NIM",
            )

        return embeddings[0].get("embedding", [])

    def supports_image(self, model: str) -> bool:
        """
        Check if model supports image input.

        Currently NVIDIA NIM vision models are not integrated —
        returns False. Multimodal support can be added in a future version.
        """
        return False

    async def fetch_models(self) -> list:
        """Fetch available models from NVIDIA API."""
        from app.services.model_registry import ModelCapability
        try:
            response = await self._client.get("/models")
            if response.status_code != 200:
                return []
                
            data = response.json()
            models = []
            
            for item in data.get("data", []):
                name = item.get("id")
                if not name:
                    continue
                    
                is_embedding = "embed" in name.lower() or "bge" in name.lower() or "arctic" in name.lower()
                is_vision = "vision" in name.lower() or "vl" in name.lower()
                
                models.append(
                    ModelCapability(
                        name=name,
                        provider=self.name,
                        supports_text=not is_embedding,
                        supports_image=is_vision,
                        supports_embedding=is_embedding,
                        supports_streaming=not is_embedding,
                        supports_reasoning=(
                            False
                            if is_embedding
                            else detect_nvidia_reasoning(name)
                        ),
                    )
                )
            return models
        except Exception as e:
            logger.warning("Failed to fetch NVIDIA models: {e}", e=e)
            return []

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
        logger.debug("NvidiaProvider HTTP client closed")
