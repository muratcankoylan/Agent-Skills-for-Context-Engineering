"""Disabled legacy Anthropic identity, not an admitted paid adapter.

Constructor-time model/endpoint configuration is retained for offline identity
tests. Historical defaults are not current model recommendations.
"""

from __future__ import annotations

import os

from .base import Budget, LLMAdapter, LLMResponse, LiveExecutionDisabled

DEFAULT_MODEL = "claude-opus-4-1"


class AnthropicAdapter(LLMAdapter):
    provider = "anthropic"

    def __init__(self, model: str | None = None, budget: Budget | None = None, timeout: float = 120.0) -> None:
        self.model = model or os.environ.get("DWL_ANTHROPIC_MODEL") or DEFAULT_MODEL
        self.endpoint = os.environ.get("DWL_ANTHROPIC_URL", "https://api.anthropic.com/v1/messages")
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
