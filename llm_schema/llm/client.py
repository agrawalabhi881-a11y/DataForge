
from dataclasses import dataclass
from litellm import completion
from litellm import (
    APIConnectionError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
    completion,
)

from llm_schema.config.provider import (
    LLMProvider,
    LLMProviderSettings,
)


@dataclass
class LLMResponse:
    """Represents a successful LLM response."""

    content: str
    provider: LLMProvider
    model: str


class MultiProviderLLMClient:
    """Synchronous client for multiple LLM providers."""

    def __init__(self, settings: LLMProviderSettings):
        self.settings = settings

    def _build_model_name(self, provider: LLMProvider) -> str:
        """Build the LiteLLM model identifier for a provider."""

        credentials = self.settings.providers[provider]

        if not credentials.model:
            raise ValueError(
                f"No model configured for provider: {provider.value}"
            )

        return f"{provider.value}/{credentials.model}"

    def complete(
        self,
        provider: LLMProvider,
        prompt: str,
    ) -> LLMResponse:
        """Send a prompt to one configured LLM provider."""

        if provider not in self.settings.available_providers:
            raise ValueError(
                f"Provider is not configured: {provider.value}"
            )

        credentials = self.settings.providers[provider]

        response = completion(
            model=self._build_model_name(provider),
            messages=[{"role": "user", "content": prompt}],
            api_key=credentials.api_key.get_secret_value(),
            timeout=self.settings.timeout_seconds,
        )

        content = response.choices[0].message.content

        if not isinstance(content, str) or not content.strip():
            raise ValueError("The LLM returned an empty response")

        return LLMResponse(
            content=content,
            provider=provider,
            model=credentials.model,
        )

    def complete_with_fallback(self, prompt: str) -> LLMResponse:
        """Try configured providers in priority order."""

        temporary_errors = (
            RateLimitError,
            ServiceUnavailableError,
            Timeout,
            APIConnectionError,
            InternalServerError,
        )

        failures = []

        for provider in self.settings.available_providers:
            try:
                return self.complete(provider, prompt)

            except temporary_errors as error:
                failures.append(
                    f"{provider.value}: {type(error).__name__}"
                )

        if not self.settings.available_providers:
            raise RuntimeError("No LLM providers are configured")

        raise RuntimeError(
            "All configured LLM providers failed. "
            + "; ".join(failures)
        )
