"""Anthropic API LLM provider implementation."""

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

from src.agents.llm.provider import LLMProvider
from src.config.settings import get_settings


class AnthropicProvider(LLMProvider):
    """LLM provider using Anthropic API directly."""

    def get_orchestrator_model(self) -> BaseChatModel:
        """
        Get model for Orchestrator Agent.

        Uses Claude 3.5 Haiku for fast, cost-effective decisions.

        Returns:
            BaseChatModel: Configured ChatAnthropic instance.

        Raises:
            ValueError: If Anthropic API key is not configured.
        """
        settings = get_settings()

        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic provider")

        return ChatAnthropic(
            model=settings.llm_model_orchestrator,
            api_key=settings.anthropic_api_key.get_secret_value(),
            max_tokens=1024,
        )

    def get_main_model(self) -> BaseChatModel:
        """
        Get model for Generator, Evaluator, and Information Gatherer agents.

        Uses Claude 3.7 Sonnet for high-quality outputs.

        Returns:
            BaseChatModel: Configured ChatAnthropic instance.

        Raises:
            ValueError: If Anthropic API key is not configured.
        """
        settings = get_settings()

        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic provider")

        return ChatAnthropic(
            model=settings.llm_model_main,
            api_key=settings.anthropic_api_key.get_secret_value(),
            max_tokens=4096,
        )
