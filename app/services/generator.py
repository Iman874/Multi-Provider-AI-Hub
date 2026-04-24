"""
Generator Service - Central orchestrator for AI operations.

All endpoint requests MUST go through this service.
The service handles:
1. Provider resolution (which provider to call)
2. Model validation (does the model exist in registry)
3. Capability checking (does the model support the requested operation)
4. Provider invocation (call the actual AI provider)
5. Response normalization (wrap in standard response schema)
"""

from typing import AsyncGenerator

from loguru import logger

from app.core.exceptions import (
    AIGatewayError,
    AllKeysExhaustedError,
    ModelCapabilityError,
    ProviderAPIError,
    ProviderConnectionError,
    ProviderNotFoundError,
    ProviderTimeoutError,
)
from app.providers.base import BaseProvider
from app.schemas.common import ProviderEnum
from app.schemas.requests import EmbeddingRequest, GenerateRequest, StreamRequest
from app.schemas.responses import EmbeddingResponse, GenerateResponse, UsageInfo
from app.services.model_registry import ModelCapability, ModelRegistry


class GeneratorService:
    """
    Orchestrator for all AI generation operations.

    This is the ONLY service that endpoints should call.
    Endpoints must NEVER call providers directly.
    """

    _AUTO_PROVIDER_PRIORITY = {
        "nvidia": 0,
        "gemini": 1,
        "ollama": 2,
    }
    _AUTO_RETRYABLE_ERRORS = (
        ProviderAPIError,
        ProviderTimeoutError,
        ProviderConnectionError,
        AllKeysExhaustedError,
    )

    def __init__(
        self,
        providers: dict[str, BaseProvider],
        registry: ModelRegistry,
        cache: "CacheService | None" = None,
        health_checker: "HealthChecker | None" = None,
    ):
        """
        Initialize GeneratorService.

        Args:
            providers: Dict mapping provider names to BaseProvider instances.
            registry: ModelRegistry instance for model lookup and validation.
            cache: Optional CacheService for response caching.
            health_checker: Optional HealthChecker for health-aware auto routing.
        """
        self._providers = providers
        self._registry = registry
        self._cache = cache
        self._health_checker = health_checker
        logger.info(
            "GeneratorService initialized with providers: {providers}, cache: {cache}, health_checker: {health}",
            providers=list(providers.keys()),
            cache="enabled" if cache and cache.is_enabled else "disabled",
            health="enabled" if health_checker else "disabled",
        )

    def _get_provider(self, provider_name: str) -> BaseProvider:
        """
        Resolve a provider by name.

        Args:
            provider_name: Provider identifier (e.g. "ollama").

        Returns:
            BaseProvider instance.

        Raises:
            ProviderNotFoundError: If the provider is not registered or disabled.
        """
        provider = self._providers.get(provider_name)
        if provider is None:
            raise ProviderNotFoundError(provider_name)
        return provider

    @staticmethod
    def _build_usage_info(payload: dict | None) -> UsageInfo | None:
        """
        Convert a provider usage payload into UsageInfo.

        Args:
            payload: Usage dictionary from a provider response.

        Returns:
            UsageInfo instance, or None when payload is empty.
        """
        if not payload:
            return None
        return UsageInfo(**payload)

    def _get_auto_routing_targets(
        self,
        requires_image: bool = False,
        is_embedding: bool = False,
        requires_streaming: bool = False,
    ) -> list[ModelCapability]:
        """
        Build ordered auto-routing targets filtered by capability and health.

        Args:
            requires_image: Whether the request includes images.
            is_embedding: Whether the request is for embeddings.
            requires_streaming: Whether the request requires streaming.

        Returns:
            Ordered list of candidate ModelCapability objects.

        Raises:
            ModelCapabilityError: If no model supports the requested capability.
            AIGatewayError: If capable models exist but none are currently available.
        """
        if is_embedding:
            capability = "embedding"
        elif requires_image:
            capability = "image"
        elif requires_streaming:
            capability = "streaming"
        else:
            capability = "text"

        candidates = [
            model
            for model in self._registry.list_models()
            if model.provider in self._providers
        ]

        filtered: list[ModelCapability] = []
        for model in candidates:
            if is_embedding:
                if not model.supports_embedding:
                    continue
            else:
                if not model.supports_text:
                    continue
                if requires_image and not model.supports_image:
                    continue
                if requires_streaming and not model.supports_streaming:
                    continue

            filtered.append(model)

        if not filtered:
            raise ModelCapabilityError(
                model="auto",
                capability=capability,
            )

        available = filtered
        if self._health_checker is not None:
            available = [
                model
                for model in filtered
                if self._health_checker.is_provider_up(model.provider)
            ]

        if not available:
            raise AIGatewayError(
                message="No available providers for auto routing",
                code="AUTO_ROUTING_UNAVAILABLE",
            )

        return sorted(
            available,
            key=lambda model: (
                self._AUTO_PROVIDER_PRIORITY.get(model.provider, 999),
                model.name,
            ),
        )

    async def _generate_single(self, request: GenerateRequest) -> GenerateResponse:
        """
        Execute a single-provider generate request.

        Args:
            request: Validated generate request with a concrete provider/model.

        Returns:
            Normalized GenerateResponse.
        """
        provider_name = request.provider.value
        provider = self._get_provider(provider_name)

        model_info = self._registry.get_model(
            provider=provider_name,
            name=request.model,
        )

        if not model_info.supports_text:
            raise ModelCapabilityError(
                model=request.model,
                capability="text",
            )

        if request.images and not model_info.supports_image:
            raise ModelCapabilityError(
                model=request.model,
                capability="image",
            )

        cache_key = None
        if self._cache and self._cache.is_enabled:
            cache_key = self._cache.make_key(
                provider=provider_name,
                model=request.model,
                prompt=request.input,
                images=request.images,
            )
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug(
                    "Cache HIT: provider={provider}, model={model}, key={key}",
                    provider=provider_name,
                    model=request.model,
                    key=cache_key[:8],
                )
                return GenerateResponse(
                    output=cached["output"],
                    provider=cached.get("provider", provider_name),
                    model=cached.get("model", request.model),
                    usage=self._build_usage_info(cached.get("usage")),
                    metadata={"cached": True},
                )

        logger.debug(
            "Generating: provider={provider}, model={model}",
            provider=provider_name,
            model=request.model,
        )

        result = await provider.generate(
            model=request.model,
            prompt=request.input,
            images=request.images,
        )

        if cache_key and self._cache:
            self._cache.put(cache_key, result)

        return GenerateResponse(
            output=result["output"],
            provider=result.get("provider", provider_name),
            model=result.get("model", request.model),
            usage=self._build_usage_info(result.get("usage")),
            metadata={"cached": False},
        )

    async def _stream_single(
        self, request: StreamRequest
    ) -> AsyncGenerator[str, None]:
        """
        Execute a single-provider stream request.

        Args:
            request: Validated stream request with a concrete provider/model.

        Yields:
            Token strings from the provider.
        """
        provider_name = request.provider.value
        provider = self._get_provider(provider_name)

        model_info = self._registry.get_model(
            provider=provider_name,
            name=request.model,
        )

        if not model_info.supports_text:
            raise ModelCapabilityError(
                model=request.model,
                capability="text",
            )

        if request.images and not model_info.supports_image:
            raise ModelCapabilityError(
                model=request.model,
                capability="image",
            )

        if not model_info.supports_streaming:
            raise ModelCapabilityError(
                model=request.model,
                capability="streaming",
            )

        logger.debug(
            "Streaming: provider={provider}, model={model}",
            provider=provider_name,
            model=request.model,
        )

        async for token in provider.stream(
            model=request.model,
            prompt=request.input,
            images=request.images,
        ):
            yield token

    async def _embedding_single(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Execute a single-provider embedding request.

        Args:
            request: Validated embedding request with a concrete provider/model.

        Returns:
            Normalized EmbeddingResponse.
        """
        provider_name = request.provider.value
        provider = self._get_provider(provider_name)

        model_info = self._registry.get_model(
            provider=provider_name,
            name=request.model,
        )

        if not model_info.supports_embedding:
            raise ModelCapabilityError(
                model=request.model,
                capability="embedding",
            )

        cache_key = None
        if self._cache and self._cache.is_enabled:
            cache_key = self._cache.make_key(
                provider=provider_name,
                model=request.model,
                prompt=request.input,
            )
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug(
                    "Cache HIT (embedding): key={key}",
                    key=cache_key[:8],
                )
                return EmbeddingResponse(
                    embedding=cached["embedding"],
                    provider=cached.get("provider", provider_name),
                    model=cached.get("model", request.model),
                )

        logger.debug(
            "Embedding: provider={provider}, model={model}",
            provider=provider_name,
            model=request.model,
        )

        vector = await provider.embedding(
            model=request.model,
            input_text=request.input,
        )

        if cache_key and self._cache:
            self._cache.put(
                cache_key,
                {
                    "embedding": vector,
                    "provider": provider_name,
                    "model": request.model,
                },
            )

        return EmbeddingResponse(
            embedding=vector,
            provider=provider_name,
            model=request.model,
        )

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """
        Generate text or multimodal response.

        Args:
            request: Validated generate request.

        Returns:
            Normalized GenerateResponse.
        """
        if request.provider != ProviderEnum.AUTO:
            return await self._generate_single(request)

        targets = self._get_auto_routing_targets(
            requires_image=bool(request.images),
        )
        last_error: Exception | None = None

        for target in targets:
            try:
                return await self._generate_single(
                    GenerateRequest(
                        provider=ProviderEnum(target.provider),
                        model=target.name,
                        input=request.input,
                        images=request.images,
                        stream=request.stream,
                    )
                )
            except self._AUTO_RETRYABLE_ERRORS as exc:
                last_error = exc
                logger.warning(
                    "Auto-fallback generate failed: provider={provider}, model={model}, error={error}",
                    provider=target.provider,
                    model=target.name,
                    error=str(exc),
                )

        raise AIGatewayError(
            message="All auto-routing targets failed.",
            code="AUTO_ROUTING_FAILED",
        ) from last_error

    async def stream(
        self, request: StreamRequest
    ) -> AsyncGenerator[str, None]:
        """
        Stream generated tokens from a provider or auto-routing target.

        Args:
            request: Validated stream request.

        Yields:
            Token strings as they are generated.
        """
        if request.provider != ProviderEnum.AUTO:
            async for token in self._stream_single(request):
                yield token
            return

        targets = self._get_auto_routing_targets(
            requires_image=bool(request.images),
            requires_streaming=True,
        )
        last_error: Exception | None = None

        for target in targets:
            iterator = self._stream_single(
                StreamRequest(
                    provider=ProviderEnum(target.provider),
                    model=target.name,
                    input=request.input,
                    images=request.images,
                )
            )

            try:
                first_token = await anext(iterator)
            except StopAsyncIteration:
                return
            except self._AUTO_RETRYABLE_ERRORS as exc:
                last_error = exc
                logger.warning(
                    "Auto-fallback stream failed before first token: provider={provider}, model={model}, error={error}",
                    provider=target.provider,
                    model=target.name,
                    error=str(exc),
                )
                continue

            yield first_token

            async for token in iterator:
                yield token
            return

        raise AIGatewayError(
            message="All auto-routing targets failed.",
            code="AUTO_ROUTING_FAILED",
        ) from last_error

    async def embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embedding vector from text.

        Args:
            request: Validated embedding request.

        Returns:
            Normalized EmbeddingResponse.
        """
        if request.provider != ProviderEnum.AUTO:
            return await self._embedding_single(request)

        targets = self._get_auto_routing_targets(
            is_embedding=True,
        )
        last_error: Exception | None = None

        for target in targets:
            try:
                return await self._embedding_single(
                    EmbeddingRequest(
                        provider=ProviderEnum(target.provider),
                        model=target.name,
                        input=request.input,
                    )
                )
            except self._AUTO_RETRYABLE_ERRORS as exc:
                last_error = exc
                logger.warning(
                    "Auto-fallback embedding failed: provider={provider}, model={model}, error={error}",
                    provider=target.provider,
                    model=target.name,
                    error=str(exc),
                )

        raise AIGatewayError(
            message="All auto-routing targets failed.",
            code="AUTO_ROUTING_FAILED",
        ) from last_error
