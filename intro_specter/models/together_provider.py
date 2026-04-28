"""Together AI provider.

Together's chat-completions endpoint is OpenAI-compatible, so we subclass
`OpenAIProvider` and override the base URL + the response_format toggle.

Default model when not specified by the caller:
``meta-llama/Llama-3.3-70B-Instruct-Turbo``.

Cross-family default for the second-model-family slice:
``Qwen/Qwen2.5-72B-Instruct-Turbo``.
"""

from __future__ import annotations

from .openai_provider import OpenAIProvider


class TogetherProvider(OpenAIProvider):
    name = "together"
    default_base_url = "https://api.together.xyz/v1"
    # Together supports response_format=json_object on most modern Llama / Qwen
    # turbo endpoints; flip to False if a particular model rejects it.
    use_response_format_json = True

    def __init__(self, cache=None, api_key_env: str = "TOGETHER_API_KEY", base_url: str | None = None):
        super().__init__(cache=cache, api_key_env=api_key_env, base_url=base_url)
