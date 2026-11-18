
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class LLMProvider(StrEnum):
    GEMINI = "gemini"
    GROQ = "groq"
    XAI = "xai"
    OPENAI = "openai"
    OPENROUTER = "openrouter"


class ProviderCredentials(BaseModel):
    """Configuration for an individual LLM provider."""

    model_config = ConfigDict(extra="forbid")

    api_key: SecretStr | None = None
    model: str | None = None

    @property
    def is_configured(self) -> bool:
        return bool(
            self.api_key
            and self.api_key.get_secret_value().strip()
            and self.model
            and self.model.strip()
        )


class LLMProviderSettings(BaseModel):
    """Central configuration for all supported LLM providers."""

    model_config = ConfigDict(extra="forbid")

    providers: dict[LLMProvider, ProviderCredentials] = Field(
        default_factory=dict
    )

    provider_order: list[LLMProvider] = Field(
        default_factory=lambda: list(LLMProvider)
    )

    timeout_seconds: int = Field(default=30, gt=0)

    @field_validator("provider_order")
    @classmethod
    def validate_provider_order(cls, providers):
        if len(providers) != len(set(providers)):
            raise ValueError("Duplicate providers in priority order")
        return providers

    @property
    def available_providers(self) -> list[LLMProvider]:
        return [
            provider
            for provider in self.provider_order
            if provider in self.providers
            and self.providers[provider].is_configured
        ]
