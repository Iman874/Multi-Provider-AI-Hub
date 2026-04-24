"""
Google Gemini AI provider implementation.

Connects to Google Gemini API via the official google-genai SDK.
See: https://ai.google.dev/gemini-api/docs

SDK package: google-genai
"""

from typing import AsyncGenerator, Optional

from loguru import logger

from app.core.exceptions import (
    ProviderAPIError,
    ProviderConnectionError,
    ProviderTimeoutError,
)
from app.providers.base import BaseProvider
from app.services.key_manager import KeyManager
from app.services.reasoning_capability import detect_gemini_reasoning
from app.utils.image import base64_to_bytes, detect_mime_type

try:
    from google import genai
    from google.genai import types
except ImportError:
    raise ImportError(
        "google-genai package not installed. "
        "Install with: pip install google-genai"
    )


class GeminiProvider(BaseProvider):
    """
    Provider implementation for Google Gemini.

    Uses the official google-genai SDK for all API interactions.
    The SDK handles authentication, retries, and connection management.
    """

    def __init__(self, key_manager: KeyManager, timeout: int = 120):
        """
        Initialize GeminiProvider.

        Args:
            key_manager: KeyManager instance with Gemini API keys.
            timeout: Request timeout in seconds.
        """
        self._key_manager = key_manager
        self._timeout = timeout
        logger.info(
            "GeminiProvider initialized (timeout={timeout}s, keys={keys})",
            timeout=timeout,
            keys=key_manager.total_count,
        )

    def _get_client(self) -> tuple[genai.Client, str]:
        """
        Create a per-request genai.Client using the next available key.

        Returns:
            Tuple of (genai.Client, key_used_string)
        """
        key = self._key_manager.get_key()
        client = genai.Client(api_key=key)
        return client, key

    @property
    def name(self) -> str:
        return "gemini"

    def _build_contents(
        self,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> list:
        """
        Build Gemini contents list with text and optional image parts.

        For text-only: ["prompt text"]
        For multimodal: ["prompt text", Part.from_data(bytes, mime), ...]
        """
        contents: list = [prompt]

        if images:
            for img_b64 in images:
                # Convert base64 → raw bytes
                img_bytes = base64_to_bytes(img_b64)
                # Detect MIME type
                mime = detect_mime_type(img_b64)
                # Create Gemini Part
                part = types.Part.from_bytes(
                    data=img_bytes,
                    mime_type=mime,
                )
                contents.append(part)

        return contents

    async def generate(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> dict:
        """
        Generate text using Gemini's generate_content API.

        For this version, only text input is supported.
        Image support will be added in beta0.1.7.

        SDK call:
            client.models.generate_content(
                model="gemini-2.5-pro",
                contents=["Hello"]
            )

        Response:
            response.text → "Hello! How can I help you?"
            response.usage_metadata → token counts
        """
        # Build contents (text-only or multimodal)
        contents = self._build_contents(prompt, images)

        max_attempts = 2

        for attempt in range(max_attempts):
            client, key = self._get_client()

            try:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        http_options=types.HttpOptions(
                            timeout=self._timeout * 1000,  # SDK uses milliseconds
                        ),
                    ),
                )
                
                # Success
                self._key_manager.report_success(key)
                break
                
            except Exception as e:
                error_str = str(e)

                # Check if rate limited
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    self._key_manager.report_failure(key)
                    if attempt < max_attempts - 1:
                        logger.warning(
                            "Gemini rate limited with key {masked}, retrying with next key",
                            masked=self._key_manager.mask_key(key),
                        )
                        continue

                # Timeout detection
                if "timeout" in error_str.lower() or "deadline" in error_str.lower():
                    raise ProviderTimeoutError(
                        provider=self.name,
                        timeout=self._timeout,
                    )

                # Connection error detection
                if "connect" in error_str.lower() or "network" in error_str.lower():
                    raise ProviderConnectionError(
                        provider=self.name,
                        detail=error_str[:200],
                    )

                # Rate limiting and other API errors
                # Try to extract status code from error
                status_code = 500
                if hasattr(e, "status_code"):
                    status_code = e.status_code
                elif hasattr(e, "code"):
                    status_code = e.code
                elif "429" in error_str:
                    status_code = 429
                elif "403" in error_str:
                    status_code = 403
                elif "404" in error_str:
                    status_code = 404

                raise ProviderAPIError(
                    provider=self.name,
                    status=status_code,
                    detail=error_str[:200],
                )

        # Extract output text
        output_text = ""
        try:
            output_text = response.text or ""
        except Exception:
            # Some responses may not have text (e.g. safety blocked)
            if response.candidates:
                parts = response.candidates[0].content.parts
                output_text = "".join(p.text for p in parts if hasattr(p, "text"))

        # Extract usage metadata
        usage = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            um = response.usage_metadata
            usage = {
                "prompt_tokens": getattr(um, "prompt_token_count", None),
                "completion_tokens": getattr(um, "candidates_token_count", None),
                "total_tokens": getattr(um, "total_token_count", None),
            }

        return {
            "output": output_text,
            "model": model,
            "provider": self.name,
            "usage": usage or None,
            "metadata": None,
        }

    async def stream(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream tokens from Gemini's generate_content_stream API.

        The SDK returns an iterable of chunks. Each chunk has a .text
        attribute containing the next token fragment.

        Note: google-genai SDK's streaming is synchronous iteration.
        We wrap it in async context for compatibility with our async interface.
        """
        # Build contents (text-only or multimodal)
        contents = self._build_contents(prompt, images)

        client, key = self._get_client()

        try:
            response = client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    http_options=types.HttpOptions(
                        timeout=self._timeout * 1000,
                    ),
                ),
            )

            for chunk in response:
                # Extract text from chunk
                token = ""
                try:
                    token = chunk.text or ""
                except Exception:
                    # Some chunks may not have text
                    if chunk.candidates:
                        parts = chunk.candidates[0].content.parts
                        token = "".join(
                            p.text for p in parts if hasattr(p, "text")
                        )

                if token:
                    yield token

            # Report success after stream is done
            self._key_manager.report_success(key)

        except Exception as e:
            error_str = str(e)

            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                self._key_manager.report_failure(key)

            if "timeout" in error_str.lower() or "deadline" in error_str.lower():
                raise ProviderTimeoutError(
                    provider=self.name,
                    timeout=self._timeout,
                )

            if "connect" in error_str.lower() or "network" in error_str.lower():
                raise ProviderConnectionError(
                    provider=self.name,
                    detail=error_str[:200],
                )

            status_code = 500
            if hasattr(e, "status_code"):
                status_code = e.status_code
            elif hasattr(e, "code"):
                status_code = e.code
            elif "429" in error_str:
                status_code = 429
            elif "403" in error_str:
                status_code = 403

            raise ProviderAPIError(
                provider=self.name,
                status=status_code,
                detail=error_str[:200],
            )

    async def embedding(
        self,
        model: str,
        input_text: str,
    ) -> list[float]:
        """
        Generate embedding vector using Gemini's embed_content API.
        """
        max_attempts = 2

        for attempt in range(max_attempts):
            client, key = self._get_client()

            try:
                result = client.models.embed_content(
                    model=model,
                    contents=input_text,
                )
                
                # Success
                self._key_manager.report_success(key)
                break
                
            except Exception as e:
                error_str = str(e)

                # Check if rate limited
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    self._key_manager.report_failure(key)
                    if attempt < max_attempts - 1:
                        logger.warning(
                            "Gemini rate limited with key {masked}, retrying with next key",
                            masked=self._key_manager.mask_key(key),
                        )
                        continue

                if "timeout" in error_str.lower() or "deadline" in error_str.lower():
                    raise ProviderTimeoutError(
                        provider=self.name,
                        timeout=self._timeout,
                    )

                if "connect" in error_str.lower() or "network" in error_str.lower():
                    raise ProviderConnectionError(
                        provider=self.name,
                        detail=error_str[:200],
                    )

                status_code = 500
                if hasattr(e, "status_code"):
                    status_code = e.status_code
                elif hasattr(e, "code"):
                    status_code = e.code
                elif "429" in error_str:
                    status_code = 429
                elif "403" in error_str:
                    status_code = 403
                elif "404" in error_str:
                    status_code = 404

                raise ProviderAPIError(
                    provider=self.name,
                    status=status_code,
                    detail=error_str[:200],
                )

        # Extract embedding vector
        if not result.embeddings or not result.embeddings[0].values:
            raise ProviderAPIError(
                provider=self.name,
                status=200,
                detail="Empty embedding returned from Gemini",
            )

        return list(result.embeddings[0].values)

    def supports_image(self, model: str) -> bool:
        """
        Check if model supports image input.

        Returns True — actual capability validation is done by
        ModelRegistry at the service layer level.
        """
        return True

    async def fetch_models(self) -> list:
        """Fetch available models from Gemini API."""
        from app.services.model_registry import ModelCapability
        try:
            client, key = self._get_client()
            models_iter = client.models.list()
            
            models = []
            for m in models_iter:
                name = m.name.replace("models/", "")
                
                # Basic heuristic
                is_embedding = "embed" in name.lower()
                
                models.append(
                    ModelCapability(
                        name=name,
                        provider=self.name,
                        supports_text=not is_embedding,
                        supports_image=not is_embedding,
                        supports_embedding=is_embedding,
                        supports_streaming=not is_embedding,
                        supports_reasoning=(
                            False
                            if is_embedding
                            else detect_gemini_reasoning(m)
                        ),
                    )
                )
            return models
        except Exception as e:
            logger.warning("Failed to fetch Gemini models: {e}", e=e)
            return []

    async def close(self) -> None:
        """
        No-op - google-genai SDK manages its own connections.
        """
        logger.debug("GeminiProvider close (no-op, SDK managed)")
