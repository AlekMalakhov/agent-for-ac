"""AWS Bedrock LLM provider implementation."""

from langchain_aws import ChatBedrock
from langchain_core.language_models import BaseChatModel

from src.agents.llm.provider import LLMProvider
from src.config.settings import get_settings


class BedrockProvider(LLMProvider):
    """LLM provider using AWS Bedrock."""

    def get_orchestrator_model(self) -> BaseChatModel:
        """
        Get model for Orchestrator Agent.

        Uses Claude 3.5 Haiku via Bedrock for fast, cost-effective decisions.

        Returns:
            BaseChatModel: Configured ChatBedrock instance.
        """
        settings = get_settings()

        return ChatBedrock(
            model_id=f"anthropic.{settings.llm_model_orchestrator}",
            region_name=settings.aws_region,
            credentials_profile_name=None,  # Uses environment variables
            model_kwargs={"max_tokens": 1024},
        )

    def get_main_model(self) -> BaseChatModel:
        """
        Get model for Generator, Evaluator, and Information Gatherer agents.

        Uses Claude 3.7 Sonnet via Bedrock for high-quality outputs.

        Returns:
            BaseChatModel: Configured ChatBedrock instance.
        """
        settings = get_settings()

        return ChatBedrock(
            model_id=f"anthropic.{settings.llm_model_main}",
            region_name=settings.aws_region,
            credentials_profile_name=None,  # Uses environment variables
            model_kwargs={"max_tokens": 4096},
        )
