"""Provider-agnostic chat interface.

Every concrete provider (Anthropic, OpenAI, Mock, ...) returns a `CompletionResult`
that records tokens, latency, model name, temperature, and seed so we can audit cost
and reproducibility per the plan PDF's "log tokens, latency, model name, temperature,
and seed for every call" requirement.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ProviderError(RuntimeError):
    """Raised when a provider call fails after retries."""


class JSONParseError(ProviderError):
    """Raised when the model output cannot be coerced to JSON."""


@dataclass
class CompletionResult:
    text: str
    model: str
    provider: str
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0
    temperature: float = 0.0
    seed: int | None = None
    cache_hit: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

    def parse_json(self) -> dict[str, Any]:
        return _coerce_json(self.text)


_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _coerce_json(text: str) -> dict[str, Any]:
    """Best-effort JSON extraction. Models sometimes wrap JSON in ``` fences or add
    a trailing prose paragraph; this helper strips both before parsing.
    """
    text = text.strip()
    if not text:
        raise JSONParseError("empty model output")
    candidates = []
    fence = _FENCED_JSON_RE.search(text)
    if fence:
        candidates.append(fence.group(1).strip())
    candidates.append(text)
    # As a last resort, find the outermost {...} block.
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        candidates.append(text[first : last + 1])
    for c in candidates:
        try:
            return json.loads(c)
        except json.JSONDecodeError:
            continue
    raise JSONParseError(f"could not parse JSON from model output:\n{text[:500]}")


class ChatProvider(ABC):
    """Abstract chat provider.

    Concrete implementations should call the provider's chat-completions API,
    populate `CompletionResult.raw` with whatever the SDK returned, and respect
    the `temperature` / `seed` arguments for reproducibility.
    """

    name: str = "abstract"

    @abstractmethod
    def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        temperature: float = 0.0,
        seed: int | None = None,
        max_tokens: int = 4096,
    ) -> CompletionResult: ...

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        model: str,
        temperature: float = 0.0,
        seed: int | None = None,
        max_tokens: int = 8192,  # bumped: long ALFWorld/Travel JSON truncates at 4k
        retries: int = 2,
    ) -> tuple[dict[str, Any], CompletionResult]:
        """Call `complete` and parse JSON. On parse failure, retry with a stricter
        reminder appended to the user message.
        """
        last_err: Exception | None = None
        attempt_user = user
        for attempt in range(retries + 1):
            res = self.complete(
                system=system,
                user=attempt_user,
                model=model,
                temperature=temperature,
                seed=seed,
                max_tokens=max_tokens,
            )
            try:
                return res.parse_json(), res
            except JSONParseError as e:
                last_err = e
                attempt_user = (
                    user
                    + f"\n\nNOTE: your previous response (attempt {attempt + 1}) was not valid"
                    " JSON. Output a single valid JSON object only, with no prose, no"
                    " markdown fences, and no commentary."
                )
        raise ProviderError(f"failed to obtain JSON after {retries + 1} attempts: {last_err}")
