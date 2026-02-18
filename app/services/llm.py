"""Unified LLM client — supports Gemini, Anthropic, and OpenAI."""

import logging

from app.config import settings

logger = logging.getLogger(__name__)

PROVIDERS = ("gemini", "anthropic", "openai")


def is_configured() -> bool:
    """Check if the active LLM provider has a valid API key."""
    keys = {
        "anthropic": settings.anthropic_api_key,
        "gemini": settings.google_api_key,
        "openai": settings.openai_api_key,
    }
    return bool(keys.get(settings.llm_provider))


def complete(prompt: str, max_tokens: int = 4096) -> str:
    """Send a prompt to the configured LLM and return the response text."""
    provider = settings.llm_provider

    dispatch = {
        "anthropic": _anthropic_complete,
        "gemini": _gemini_complete,
        "openai": _openai_complete,
    }

    fn = dispatch.get(provider)
    if not fn:
        raise ValueError(f"Unknown LLM provider: {provider}. Use one of: {PROVIDERS}")

    return fn(prompt, max_tokens)


# ── Provider implementations ───────────────────────

def _gemini_complete(prompt: str, max_tokens: int) -> str:
    from google import genai

    client = genai.Client(api_key=settings.google_api_key)
    response = client.models.generate_content(
        model=settings.llm_model,
        contents=prompt,
        config={"max_output_tokens": max_tokens},
    )
    return response.text


def _anthropic_complete(prompt: str, max_tokens: int) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.llm_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _openai_complete(prompt: str, max_tokens: int) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.llm_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
