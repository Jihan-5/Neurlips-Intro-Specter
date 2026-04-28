"""Provider registry — maps a string name to a `ChatProvider` factory.

Lets configs say `provider: anthropic` without import-time coupling.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .base import ChatProvider, ProviderError
from .cache import SQLiteCache

_REGISTRY: dict[str, Callable[..., ChatProvider]] = {}


def register_provider(name: str, factory: Callable[..., ChatProvider]) -> None:
    _REGISTRY[name] = factory


def build_provider(name: str, **kwargs: Any) -> ChatProvider:
    name = name.lower()
    if name not in _REGISTRY:
        raise ProviderError(
            f"unknown provider {name!r}. Registered: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name](**kwargs)


def _register_defaults() -> None:
    def _anthropic(**kw: Any) -> ChatProvider:
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(**kw)

    def _openai(**kw: Any) -> ChatProvider:
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(**kw)

    def _together(**kw: Any) -> ChatProvider:
        from .together_provider import TogetherProvider

        return TogetherProvider(**kw)

    def _mock(**kw: Any) -> ChatProvider:
        from .mock import MockProvider

        return MockProvider(**kw)

    register_provider("anthropic", _anthropic)
    register_provider("openai", _openai)
    register_provider("together", _together)
    register_provider("mock", _mock)


_register_defaults()


__all__ = ["build_provider", "register_provider", "SQLiteCache"]
