"""Mock chat provider for tests and dry runs.

Returns scripted responses keyed by `(system_prefix, user_prefix)` or by sequence.
Allows the entire pipeline to be exercised in unit tests without API calls.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

from .base import ChatProvider, CompletionResult


class MockProvider(ChatProvider):
    name = "mock"

    def __init__(
        self,
        scripted: list[str | dict[str, Any]] | None = None,
        responder: Callable[[str, str], str | dict[str, Any]] | None = None,
    ) -> None:
        self._scripted = list(scripted or [])
        self._responder = responder
        self._call_count = 0

    def _next(self, system: str, user: str) -> str:
        if self._responder is not None:
            out = self._responder(system, user)
            return out if isinstance(out, str) else json.dumps(out)
        if not self._scripted:
            raise RuntimeError("MockProvider exhausted: no more scripted responses")
        out = self._scripted.pop(0)
        return out if isinstance(out, str) else json.dumps(out)

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
        t0 = time.perf_counter()
        text = self._next(system, user)
        self._call_count += 1
        return CompletionResult(
            text=text,
            model=model,
            provider=self.name,
            tokens_input=len(user) // 4,
            tokens_output=len(text) // 4,
            latency_ms=(time.perf_counter() - t0) * 1000.0,
            temperature=temperature,
            seed=seed,
        )
