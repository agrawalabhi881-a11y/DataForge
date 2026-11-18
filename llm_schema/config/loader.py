
import os
from pathlib import Path

from dotenv import load_dotenv

from llm_schema.config.provider import (
    LLMProvider,
    LLMProviderSettings,
    ProviderCredentials,
)


def load_provider_settings(
    env_file: str | Path | None = None,
) -> LLMProviderSettings:
    """Load LLM provider settings from environment variables."""

    if env_file is not None:
        load_dotenv(dotenv_path=env_file, override=False)
    else:
        load_dotenv(override=False)

    provider_env = {
        LLMProvider.GEMINI: ("GEMINI_API_KEY", "GEMINI_MODEL"),
        LLMProvider.GROQ: ("GROQ_API_KEY", "GROQ_MODEL"),
        LLMProvider.XAI: ("XAI_API_KEY", "XAI_MODEL"),
        LLMProvider.OPENAI: ("OPENAI_API_KEY", "OPENAI_MODEL"),
        LLMProvider.OPENROUTER: (
            "OPENROUTER_API_KEY",
            "OPENROUTER_MODEL",
        ),
    }

    providers = {}

    for provider, (key_name, model_name) in provider_env.items():
        api_key = os.getenv(key_name)
        model = os.getenv(model_name)

        providers[provider] = ProviderCredentials(
            api_key=api_key or None,
            model=model or None,
        )

    order_value = os.getenv(
        "LLM_PROVIDER_ORDER",
        "gemini,groq,openrouter",
    )

    provider_order = [
        LLMProvider(item.strip().lower())
        for item in order_value.split(",")
        if item.strip()
    ]

    timeout = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

    return LLMProviderSettings(
        providers=providers,
        provider_order=provider_order,
        timeout_seconds=timeout,
    )
