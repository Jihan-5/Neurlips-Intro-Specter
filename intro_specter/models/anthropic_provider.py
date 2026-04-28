"""Anthropic Claude provider."""

from __future__ import annotations

import os
import time
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .base import ChatProvider, CompletionResult, ProviderError
from .cache import SQLiteCache, make_key


class AnthropicProvider(ChatProvider):
    name = "anthropic"

    def __init__(
        self,
        cache: SQLiteCache | None = None,
        api_key_env: str = "ANTHROPIC_API_KEY",
    ) -> None:
        try:
            import anthropic  # noqa: F401
        except ImportError as e:
            raise ProviderError(
                "anthropic package not installed. `uv pip install anthropic` or"
                " add it to pyproject.toml."
            ) from e
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ProviderError(f"{api_key_env} not set")
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self._cache = cache

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        reraise=True,
    )
    def _call(self, **kwargs: Any) -> Any:
        return self._client.messages.create(**kwargs)

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
        if self._cache is not None:
            key = make_key(
                provider=self.name,
                model=model,
                system=system,
                user=user,
                temperature=temperature,
                seed=seed,
                max_tokens=max_tokens,
            )
            cached = self._cache.get(key)
            if cached is not None:
                return cached

        t0 = time.perf_counter()
        # Anthropic API does not currently expose a `seed` parameter; we still log
        # it so that any cache key remains deterministic.
        msg = self._call(
            model=model,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0

        text = "".join(getattr(b, "text", "") for b in msg.content)
        usage = getattr(msg, "usage", None)
        result = CompletionResult(
            text=text,
            model=model,
            provider=self.name,
            tokens_input=getattr(usage, "input_tokens", 0) or 0,
            tokens_output=getattr(usage, "output_tokens", 0) or 0,
            latency_ms=latency_ms,
            temperature=temperature,
            seed=seed,
            cache_hit=False,
            raw={"id": getattr(msg, "id", None), "stop_reason": getattr(msg, "stop_reason", None)},
        )
        if self._cache is not None:
            self._cache.put(key, result)
        return result
