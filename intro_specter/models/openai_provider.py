"""OpenAI provider (used for baselines that originally targeted GPT-class models)."""

from __future__ import annotations

import os
import time
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .base import ChatProvider, CompletionResult, ProviderError
from .cache import SQLiteCache, make_key


class OpenAIProvider(ChatProvider):
    name = "openai"

    def __init__(
        self,
        cache: SQLiteCache | None = None,
        api_key_env: str = "OPENAI_API_KEY",
    ) -> None:
        try:
            import openai  # noqa: F401
        except ImportError as e:
            raise ProviderError("openai package not installed.") from e
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ProviderError(f"{api_key_env} not set")
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._cache = cache

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        reraise=True,
    )
    def _call(self, **kwargs: Any) -> Any:
        return self._client.chat.completions.create(**kwargs)

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
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        if seed is not None:
            kwargs["seed"] = seed
        resp = self._call(**kwargs)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        choice = resp.choices[0]
        usage = resp.usage
        result = CompletionResult(
            text=choice.message.content or "",
            model=model,
            provider=self.name,
            tokens_input=getattr(usage, "prompt_tokens", 0) or 0,
            tokens_output=getattr(usage, "completion_tokens", 0) or 0,
            latency_ms=latency_ms,
            temperature=temperature,
            seed=seed,
            cache_hit=False,
            raw={"id": resp.id, "finish_reason": choice.finish_reason},
        )
        if self._cache is not None:
            self._cache.put(key, result)
        return result
