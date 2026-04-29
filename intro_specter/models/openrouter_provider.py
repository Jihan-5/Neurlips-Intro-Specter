"""OpenRouter provider.

OpenRouter aggregates many providers (OpenAI, Anthropic, Google, Mistral,
Meta, etc.) behind one OpenAI-compatible API. We subclass `OpenAIProvider`
and point ``base_url`` at OpenRouter's endpoint.

Quirks handled here:
* Some downstream providers (notably Cloudflare Workers AI, which
  OpenRouter routes Mistral 7B v0.1 to) reject ``seed=0`` with
  ``/seed must be >= 1``. We clamp seed to ``max(seed, 1)`` for any
  OpenRouter call so all our headline seed=0 runs succeed.
* ``response_format=json_object`` is supported by most routes; the
  parse-and-retry layer handles the few that ignore it.
"""

from __future__ import annotations

from .base import CompletionResult
from .openai_provider import OpenAIProvider


class OpenRouterProvider(OpenAIProvider):
    name = "openrouter"
    default_base_url = "https://openrouter.ai/api/v1"
    use_response_format_json = True

    def __init__(self, cache=None, api_key_env: str = "OPENROUTER_API_KEY", base_url: str | None = None):
        super().__init__(cache=cache, api_key_env=api_key_env, base_url=base_url)

    def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        temperature: float = 0.0,
        seed: int | None = None,
        max_tokens: int = 4096,
    ) -> CompletionResult:
        # Clamp seed to >= 1 because some downstream OpenRouter providers
        # (Cloudflare in particular) reject seed=0.
        if seed is not None and seed < 1:
            seed = seed + 1
        return super().complete(
            system=system, user=user, model=model,
            temperature=temperature, seed=seed, max_tokens=max_tokens,
        )
