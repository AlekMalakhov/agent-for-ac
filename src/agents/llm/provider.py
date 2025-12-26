"""Abstract LLM provider interface."""

from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel

from src.config.settings import get_settings


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def get_orchestrator_model(self) -> BaseChatModel:
        """
        Get model for Orchestrator Agent.

        Uses a faster, cheaper model (Claude 3.5 Haiku) for quick decisions.

        Returns:
            BaseChatModel: Configured chat model instance.
        """
        pass

    @abstractmethod
    def get_main_model(self) -> BaseChatModel:
        """
        Get model for Generator, Evaluator, and Information Gatherer agents.

        Uses a higher quality model (Claude 3.7 Sonnet) for complex tasks.

        Returns:
            BaseChatModel: Configured chat model instance.
        """
        pass


def get_llm_provider() -> LLMProvider:
    """
    Factory function to get configured LLM provider.

    Reads the LLM_PROVIDER setting and returns the appropriate provider instance.

    Returns:
        LLMProvider: Configured provider instance (Anthropic or Bedrock).

    Raises:
        ValueError: If unknown provider is configured.
    """
    settings = get_settings()

    if settings.llm_provider == "anthropic":
        from src.agents.llm.anthropic import AnthropicProvider

        return AnthropicProvider()
    elif settings.llm_provider == "bedrock":
        from src.agents.llm.bedrock import BedrockProvider

        return BedrockProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
