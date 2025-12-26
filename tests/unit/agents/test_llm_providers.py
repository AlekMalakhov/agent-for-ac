"""Unit tests for LLM provider implementations."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.language_models import BaseChatModel

from src.agents.llm import LLMProvider, get_llm_provider
from src.agents.llm.anthropic import AnthropicProvider
from src.agents.llm.bedrock import BedrockProvider


class TestLLMProviderInterface:
    """Tests for the abstract LLMProvider interface."""

    def test_llm_provider_is_abstract(self):
        """LLMProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LLMProvider()

    def test_provider_has_required_methods(self):
        """LLMProvider defines required abstract methods."""
        assert hasattr(LLMProvider, "get_orchestrator_model")
        assert hasattr(LLMProvider, "get_main_model")


class TestGetLLMProvider:
    """Tests for the get_llm_provider factory function."""

    @patch("src.agents.llm.provider.get_settings")
    def test_returns_anthropic_provider_when_configured(self, mock_settings):
        """Factory returns AnthropicProvider when llm_provider is 'anthropic'."""
        mock_settings.return_value.llm_provider = "anthropic"

        provider = get_llm_provider()

        assert isinstance(provider, AnthropicProvider)

    @patch("src.agents.llm.provider.get_settings")
    def test_returns_bedrock_provider_when_configured(self, mock_settings):
        """Factory returns BedrockProvider when llm_provider is 'bedrock'."""
        mock_settings.return_value.llm_provider = "bedrock"

        provider = get_llm_provider()

        assert isinstance(provider, BedrockProvider)

    @patch("src.agents.llm.provider.get_settings")
    def test_raises_error_for_unknown_provider(self, mock_settings):
        """Factory raises ValueError for unknown provider."""
        mock_settings.return_value.llm_provider = "unknown"

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_provider()


class TestAnthropicProvider:
    """Tests for AnthropicProvider implementation."""

    @patch("src.agents.llm.anthropic.get_settings")
    @patch("src.agents.llm.anthropic.ChatAnthropic")
    def test_get_orchestrator_model_returns_chat_model(
        self, mock_chat_anthropic, mock_settings
    ):
        """get_orchestrator_model returns configured ChatAnthropic instance."""
        mock_settings.return_value.llm_model_orchestrator = "claude-3-5-haiku-20241022"
        mock_settings.return_value.anthropic_api_key = MagicMock()
        mock_settings.return_value.anthropic_api_key.get_secret_value.return_value = (
            "test-key"
        )

        provider = AnthropicProvider()
        model = provider.get_orchestrator_model()

        mock_chat_anthropic.assert_called_once_with(
            model="claude-3-5-haiku-20241022",
            api_key="test-key",
            max_tokens=1024,
        )

    @patch("src.agents.llm.anthropic.get_settings")
    @patch("src.agents.llm.anthropic.ChatAnthropic")
    def test_get_main_model_returns_chat_model(
        self, mock_chat_anthropic, mock_settings
    ):
        """get_main_model returns configured ChatAnthropic instance."""
        mock_settings.return_value.llm_model_main = "claude-3-7-sonnet-20250219"
        mock_settings.return_value.anthropic_api_key = MagicMock()
        mock_settings.return_value.anthropic_api_key.get_secret_value.return_value = (
            "test-key"
        )

        provider = AnthropicProvider()
        model = provider.get_main_model()

        mock_chat_anthropic.assert_called_once_with(
            model="claude-3-7-sonnet-20250219",
            api_key="test-key",
            max_tokens=4096,
        )

    @patch("src.agents.llm.anthropic.get_settings")
    def test_raises_error_when_api_key_missing(self, mock_settings):
        """Raises ValueError when ANTHROPIC_API_KEY is not configured."""
        mock_settings.return_value.anthropic_api_key = None

        provider = AnthropicProvider()

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
            provider.get_orchestrator_model()

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
            provider.get_main_model()


class TestBedrockProvider:
    """Tests for BedrockProvider implementation."""

    @patch("src.agents.llm.bedrock.get_settings")
    @patch("src.agents.llm.bedrock.ChatBedrock")
    def test_get_orchestrator_model_returns_chat_model(
        self, mock_chat_bedrock, mock_settings
    ):
        """get_orchestrator_model returns configured ChatBedrock instance."""
        mock_settings.return_value.llm_model_orchestrator = "claude-3-5-haiku-20241022"
        mock_settings.return_value.aws_region = "us-east-1"

        provider = BedrockProvider()
        model = provider.get_orchestrator_model()

        mock_chat_bedrock.assert_called_once_with(
            model_id="anthropic.claude-3-5-haiku-20241022",
            region_name="us-east-1",
            credentials_profile_name=None,
            model_kwargs={"max_tokens": 1024},
        )

    @patch("src.agents.llm.bedrock.get_settings")
    @patch("src.agents.llm.bedrock.ChatBedrock")
    def test_get_main_model_returns_chat_model(
        self, mock_chat_bedrock, mock_settings
    ):
        """get_main_model returns configured ChatBedrock instance."""
        mock_settings.return_value.llm_model_main = "claude-3-7-sonnet-20250219"
        mock_settings.return_value.aws_region = "us-west-2"

        provider = BedrockProvider()
        model = provider.get_main_model()

        mock_chat_bedrock.assert_called_once_with(
            model_id="anthropic.claude-3-7-sonnet-20250219",
            region_name="us-west-2",
            credentials_profile_name=None,
            model_kwargs={"max_tokens": 4096},
        )
