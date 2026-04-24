"""
Unit tests for reasoning capability detection helpers.
"""

from types import SimpleNamespace

from app.services.reasoning_capability import (
    detect_gemini_reasoning,
    detect_nvidia_reasoning,
    detect_ollama_reasoning,
)


class TestDetectOllamaReasoning:
    """Tests for Ollama reasoning detection."""

    def test_detects_from_name_keyword(self):
        """Model names with reasoning keywords are marked as reasoning-capable."""
        assert detect_ollama_reasoning("qwq:latest") is True

    def test_detects_from_show_capabilities(self):
        """Ollama show metadata can enable reasoning support."""
        details = {"capabilities": ["completion", "thinking"]}
        assert detect_ollama_reasoning("qwen3:8b", details) is True

    def test_detects_from_show_family(self):
        """Known reasoning family in show metadata is treated as supported."""
        details = {"family": "qwen3"}
        assert detect_ollama_reasoning("qwen3:8b", details) is True

    def test_returns_false_for_unknown_model(self):
        """Unknown models without metadata markers remain false."""
        assert detect_ollama_reasoning("llama3.2") is False


class TestDetectGeminiReasoning:
    """Tests for Gemini reasoning detection."""

    def test_detects_bool_thinking_flag(self):
        """Boolean thinking metadata is treated as source of truth."""
        model = SimpleNamespace(thinking=True)
        assert detect_gemini_reasoning(model) is True

    def test_detects_nested_thinking_supported_flag(self):
        """Nested thinking metadata with supported attribute is accepted."""
        thinking = SimpleNamespace(supported=True)
        model = SimpleNamespace(thinking=thinking)
        assert detect_gemini_reasoning(model) is True

    def test_detects_from_dict_payload(self):
        """Dict payloads can also expose thinking support."""
        payload = {"thinking": {"supported": True}}
        assert detect_gemini_reasoning(payload) is True

    def test_returns_false_without_thinking_marker(self):
        """Models without thinking metadata remain false."""
        model = SimpleNamespace(supported_generation_methods=["generateContent"])
        assert detect_gemini_reasoning(model) is False


class TestDetectNvidiaReasoning:
    """Tests for NVIDIA reasoning detection."""

    def test_detects_curated_reasoning_model(self):
        """Known curated NVIDIA reasoning model ids are marked true."""
        assert detect_nvidia_reasoning("qwen/qwen3-next-80b-a3b-thinking") is True

    def test_returns_false_for_unknown_id(self):
        """Unknown NVIDIA ids default to false."""
        assert detect_nvidia_reasoning("meta/llama-3.3-70b-instruct") is False
