"""
Ollama AI provider implementation.

Connects to a local (or remote) Ollama instance via HTTP API.
See: https://github.com/ollama/ollama/blob/main/docs/api.md

Ollama API endpoints used:
- POST /api/generate  → text & multimodal generation
- POST /api/embed     → vector embedding (beta0.1.6)
- GET  /api/tags      → model listing (future)
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
from app.services.key_manager import KeyManager
from app.services.reasoning_capability import detect_ollama_reasoning
from app.utils.image import strip_data_uri


class OllamaProvider(BaseProvider):
    """
    Provider implementation for Ollama (local LLM).

    Communicates with Ollama via its HTTP API using httpx.AsyncClient.
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 120,
        key_manager: KeyManager | None = None,
    ):
        """
        Initialize OllamaProvider.

        Args:
            base_url: Ollama API base URL (e.g. "http://localhost:11434")
            timeout: Request timeout in seconds.
            key_manager: Optional key manager for cloud models.
        """
        self._base_url = base_url
        self._timeout = timeout
        self._key_manager = key_manager
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout),
        )
        logger.info(
            "OllamaProvider initialized: {url} (timeout={timeout}s, cloud_keys={keys})",
            url=base_url,
            timeout=timeout,
            keys=key_manager.total_count if key_manager else 0,
        )

    def _get_auth_headers(self) -> tuple[dict[str, str], str | None]:
        """
        Get auth headers for the request.

        Returns:
            Tuple of (headers_dict, key_used).
        """
        if self._key_manager and self._key_manager.has_keys:
            key = self._key_manager.get_key()
            return {"Authorization": f"Bearer {key}"}, key
        return {}, None

    @property
    def name(self) -> str:
        return "ollama"

    async def generate(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> dict:
        """
        Generate text using Ollama's /api/generate endpoint.

        Sends a non-streaming request and returns the complete response.

        Ollama API request format:
            POST /api/generate
            { "model": "llama3.2", "prompt": "Hello", "stream": false }

        Ollama API response format:
            {
                "model": "llama3.2",
                "response": "Hi there!",
                "done": true,
                "total_duration": 1234567890,
                "prompt_eval_count": 5,
                "eval_count": 10
            }
        """
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        # Image support: strip data URI prefix for Ollama
        if images:
            payload["images"] = [strip_data_uri(img) for img in images]

        # Request headers for auth
        headers, key_used = self._get_auth_headers()

        try:
            response = await self._client.post(
                "/api/generate",
                json=payload,
                headers=headers,
            )
        except httpx.TimeoutException:
            raise ProviderTimeoutError(
                provider=self.name,
                timeout=self._timeout,
            )
        except httpx.ConnectError:
            raise ProviderConnectionError(
                provider=self.name,
                detail=f"Connection refused at {self._base_url}",
            )

        if response.status_code != 200:
            if key_used and response.status_code in (401, 429):
                self._key_manager.report_failure(key_used)
            raise ProviderAPIError(
                provider=self.name,
                status=response.status_code,
                detail=response.text[:200],
            )
            
        if key_used:
            self._key_manager.report_success(key_used)

        data = response.json()

        # Normalize to standard response format
        return {
            "output": data.get("response", ""),
            "model": data.get("model", model),
            "provider": self.name,
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count"),
                "completion_tokens": data.get("eval_count"),
                "total_tokens": (
                    (data.get("prompt_eval_count") or 0)
                    + (data.get("eval_count") or 0)
                )
                or None,
            },
            "metadata": {
                "total_duration_ns": data.get("total_duration"),
                "load_duration_ns": data.get("load_duration"),
            },
        }

    async def stream(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream tokens from Ollama's /api/generate endpoint.

        Ollama streams via NDJSON (newline-delimited JSON).
        Each line is a JSON object with a "response" field containing
        the next token, and a "done" field indicating completion.

        Example Ollama NDJSON lines:
            {"model":"llama3.2","response":"Hello","done":false}
            {"model":"llama3.2","response":" there","done":false}
            {"model":"llama3.2","response":"","done":true}
        """
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": True,
        }

        # Image support: strip data URI prefix for Ollama
        if images:
            payload["images"] = [strip_data_uri(img) for img in images]

        headers, key_used = self._get_auth_headers()

        try:
            async with self._client.stream(
                "POST",
                "/api/generate",
                json=payload,
                headers=headers,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    if key_used and response.status_code in (401, 429):
                        self._key_manager.report_failure(key_used)
                    raise ProviderAPIError(
                        provider=self.name,
                        status=response.status_code,
                        detail=error_text.decode("utf-8", errors="replace")[:200],
                    )

                if key_used:
                    self._key_manager.report_success(key_used)

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning(
                            "Ollama stream: skipping malformed JSON line"
                        )
                        continue

                    # Check if generation is complete
                    if data.get("done", False):
                        break

                    # Extract and yield the token
                    token = data.get("response", "")
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
                detail=f"Connection refused at {self._base_url}",
            )

    async def embedding(
        self,
        model: str,
        input_text: str,
    ) -> list[float]:
        """
        Generate embedding vector using Ollama's /api/embed endpoint.
        """
        payload: dict = {
            "model": model,
            "input": input_text,
        }

        headers, key_used = self._get_auth_headers()

        try:
            response = await self._client.post(
                "/api/embed",
                json=payload,
                headers=headers,
            )
        except httpx.TimeoutException:
            raise ProviderTimeoutError(
                provider=self.name,
                timeout=self._timeout,
            )
        except httpx.ConnectError:
            raise ProviderConnectionError(
                provider=self.name,
                detail=f"Connection refused at {self._base_url}",
            )

        if response.status_code != 200:
            if key_used and response.status_code in (401, 429):
                self._key_manager.report_failure(key_used)
            raise ProviderAPIError(
                provider=self.name,
                status=response.status_code,
                detail=response.text[:200],
            )

        data = response.json()
        embeddings = data.get("embeddings", [])
        
        if not embeddings:
            raise ProviderAPIError(
                provider=self.name,
                status=200,
                detail="Empty embedding returned from Ollama",
            )
            
        if key_used:
            self._key_manager.report_success(key_used)
            
        return embeddings[0]

    def supports_image(self, model: str) -> bool:
        """
        Check if model supports image input.

        Returns True — actual capability validation is done by
        ModelRegistry at the service layer level.
        """
        return True

    async def _fetch_model_details(self, name: str) -> dict | None:
        """
        Fetch detailed metadata for a single Ollama model.

        Args:
            name: Ollama model name as returned by /api/tags.

        Returns:
            Parsed JSON payload or None when the probe fails.
        """
        headers, _ = self._get_auth_headers()

        try:
            response = await self._client.post(
                "/api/show",
                json={"model": name},
                headers=headers,
            )
        except Exception as e:
            logger.debug(
                "Ollama show probe failed for {model}: {err}",
                model=name,
                err=str(e),
            )
            return None

        if response.status_code != 200:
            logger.debug(
                "Ollama show probe returned HTTP {status} for {model}",
                status=response.status_code,
                model=name,
            )
            return None

        try:
            return response.json()
        except ValueError:
            logger.debug("Ollama show probe returned invalid JSON for {model}", model=name)
            return None

    async def fetch_models(self) -> list:
        """Fetch available models from Ollama API."""
        from app.services.model_registry import ModelCapability
        try:
            response = await self._client.get("/api/tags")
            if response.status_code != 200:
                return []
                
            data = response.json()
            models = []
            
            for item in data.get("models", []):
                name = item.get("name")
                if not name:
                    continue
                    
                # Basic capability heuristic
                is_embedding = "embed" in name.lower()
                is_vision = "vision" in name.lower() or "llava" in name.lower() or "minicpm-v" in name.lower()
                model_details = None
                if not is_embedding:
                    model_details = await self._fetch_model_details(name)
                
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
                            else detect_ollama_reasoning(name, model_details)
                        ),
                    )
                )
            return models
        except Exception as e:
            logger.warning("Failed to fetch Ollama models: {e}", e=e)
            return []

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
        logger.debug("OllamaProvider HTTP client closed")
