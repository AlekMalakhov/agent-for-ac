"""Application configuration settings."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Slack Configuration
    slack_bot_token: SecretStr
    slack_app_token: SecretStr

    # Jira Configuration (API Token authentication)
    jira_site_url: str  # e.g., https://yourcompany.atlassian.net
    jira_user_email: str  # Email of the user who created the API token
    jira_api_token: SecretStr  # API token from Atlassian account settings

    # Sentry Configuration
    sentry_dsn: str | None = None

    # Logging Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Environment
    environment: Literal["local", "development", "staging", "production"] = "local"

    # LLM Configuration
    llm_provider: Literal["bedrock", "anthropic"] = "anthropic"

    # Anthropic API (when llm_provider = "anthropic")
    anthropic_api_key: SecretStr | None = None

    # AWS Bedrock (when llm_provider = "bedrock")
    aws_access_key_id: str | None = None
    aws_secret_access_key: SecretStr | None = None
    aws_region: str = "us-east-1"

    # Model Configuration
    llm_model_orchestrator: str = "claude-3-5-haiku-20241022"
    llm_model_main: str = "claude-3-7-sonnet-20250219"

    # Slack Context Configuration
    slack_context_enabled: bool = True
    slack_context_max_messages: int = 100
    slack_context_lookback_hours: int = 168  # 7 days

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate and normalize log level."""
        if isinstance(v, str):
            return v.upper()
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance (singleton pattern)."""
    return Settings()
