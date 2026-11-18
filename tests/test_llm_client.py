from types import SimpleNamespace

import pytest
from pydantic import SecretStr
from litellm import RateLimitError, AuthenticationError

from llm_schema.config.provider import (
    LLMProvider,
    LLMProviderSettings,
    ProviderCredentials,
)

from llm_schema.llm.client import (
    LLMResponse,
    MultiProviderLLMClient,
)

def create_test_settings():
    return LLMProviderSettings(
        providers={
            LLMProvider.GEMINI: ProviderCredentials(
                api_key=SecretStr("gemini-test-key"),
                model="gemini-2.5-flash",
            ),
            LLMProvider.GROQ: ProviderCredentials(
                api_key=SecretStr("groq-test-key"),
                model="openai/gpt-oss-120b",
            ),
        },
        provider_order=[
            LLMProvider.GEMINI,
            LLMProvider.GROQ,
        ],
    )

def test_fallback_uses_next_provider_after_rate_limit(monkeypatch):
    client = MultiProviderLLMClient(create_test_settings())
    attempted = []

    def mock_complete(provider, prompt):
        attempted.append(provider)

        if provider == LLMProvider.GEMINI:
            raise RateLimitError(
                message="Rate limit exceeded",
                llm_provider="gemini",
                model="gemini-2.5-flash",
            )

        return LLMResponse(
            content="Success from Groq",
            provider=provider,
            model="openai/gpt-oss-120b",
        )

    monkeypatch.setattr(client, "complete", mock_complete)

    result = client.complete_with_fallback("Test prompt")

    assert result.content == "Success from Groq"
    assert result.provider == LLMProvider.GROQ
    assert attempted == [LLMProvider.GEMINI, LLMProvider.GROQ]


def test_fallback_raises_error_when_all_providers_fail(monkeypatch):
    client = MultiProviderLLMClient(create_test_settings())

    def mock_complete(provider, prompt):
        raise RateLimitError(
            message="Rate limit exceeded",
            llm_provider=provider.value,
            model=client._build_model_name(provider),
        )

    monkeypatch.setattr(client, "complete", mock_complete)

    with pytest.raises(RuntimeError, match="All configured LLM providers failed"):
        client.complete_with_fallback("Test prompt")


def test_authentication_error_does_not_trigger_fallback(monkeypatch):
    client = MultiProviderLLMClient(create_test_settings())
    attempted = []

    def mock_complete(provider, prompt):
        attempted.append(provider)

        raise AuthenticationError(
            message="Invalid API key",
            llm_provider=provider.value,
            model=client._build_model_name(provider),
        )

    monkeypatch.setattr(client, "complete", mock_complete)

    with pytest.raises(AuthenticationError):
        client.complete_with_fallback("Test prompt")

    assert attempted == [LLMProvider.GEMINI]


def test_complete_returns_llm_response(monkeypatch):
    settings = LLMProviderSettings(
        providers={
            LLMProvider.GEMINI: ProviderCredentials(
                api_key=SecretStr("test-key"),
                model="gemini-2.5-flash",
            )
        },
        provider_order=[LLMProvider.GEMINI],
    )

    def mock_completion(**kwargs):
        assert kwargs["model"] == "gemini/gemini-2.5-flash"
        assert kwargs["messages"][0]["content"] == "Hello"

        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="Hello back!")
                )
            ]
        )

    monkeypatch.setattr(
        "llm_schema.llm.client.completion",
        mock_completion,
    )

    client = MultiProviderLLMClient(settings)
    result = client.complete(LLMProvider.GEMINI, "Hello")

    assert result.content == "Hello back!"
    assert result.provider == LLMProvider.GEMINI
    assert result.model == "gemini-2.5-flash"

def create_test_settings():
    return LLMProviderSettings(
        providers={
            LLMProvider.GEMINI: ProviderCredentials(
                api_key=SecretStr("gemini-test-key"),
                model="gemini-2.5-flash",
            ),
            LLMProvider.GROQ: ProviderCredentials(
                api_key=SecretStr("groq-test-key"),
                model="openai/gpt-oss-120b",
            ),
        },
        provider_order=[
            LLMProvider.GEMINI,
            LLMProvider.GROQ,
        ],
    )
def test_fallback_uses_next_provider_after_rate_limit(monkeypatch):
    client = MultiProviderLLMClient(create_test_settings())
    attempted = []

    def mock_complete(provider, prompt):
        attempted.append(provider)

        if provider == LLMProvider.GEMINI:
            raise RateLimitError(
                message="Rate limit exceeded",
                llm_provider="gemini",
                model="gemini-2.5-flash",
            )

        return LLMResponse(
            content="Success from Groq",
            provider=provider,
            model="openai/gpt-oss-120b",
        )

    monkeypatch.setattr(client, "complete", mock_complete)

    result = client.complete_with_fallback("Test prompt")

    assert result.content == "Success from Groq"
    assert result.provider == LLMProvider.GROQ
    assert attempted == [LLMProvider.GEMINI, LLMProvider.GROQ]