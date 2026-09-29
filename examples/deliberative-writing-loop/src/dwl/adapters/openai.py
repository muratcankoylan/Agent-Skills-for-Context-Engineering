"""Disabled legacy adapter identity; no live HTTP implementation remains.

Constructor-time configuration is retained for offline identity tests. A future
paid implementation requires the repository's admitted SDK/broker boundary.
"""

from __future__ import annotations

import os

from .base import Budget, LLMAdapter, LLMResponse, LiveExecutionDisabled

DEFAULT_MODEL = "gpt-5"


class OpenAIAdapter(LLMAdapter):
    provider = "openai"

    def __init__(self, model: str | None = None, budget: Budget | None = None, timeout: float = 120.0) -> None:
        self.model = model or os.environ.get("DWL_OPENAI_MODEL") or DEFAULT_MODEL
        self.endpoint = os.environ.get("DWL_OPENAI_URL", "https://api.openai.com/v1/chat/completions")
        self.budget = budget or Budget()

    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        label: str = "",
    ) -> LLMResponse:
        raise LiveExecutionDisabled("paid example adapter disabled pending admitted SDK/broker")
