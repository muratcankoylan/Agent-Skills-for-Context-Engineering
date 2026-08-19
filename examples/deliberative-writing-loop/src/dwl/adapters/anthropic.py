"""Anthropic Messages API adapter.

Model ID is configurable because "latest" changes: set DWL_ANTHROPIC_MODEL or
pass model=. The default targets the current strongest general model alias;
check https://docs.anthropic.com/en/docs/about-claude/models before benchmark
runs and pin an explicit dated snapshot for reproducibility.
"""

from __future__ import annotations

import os

import httpx

from .base import Budget, LLMAdapter, LLMResponse, _require_env

DEFAULT_MODEL = os.environ.get("DWL_ANTHROPIC_MODEL", "claude-opus-4-1")
_API_URL = os.environ.get("DWL_ANTHROPIC_URL", "https://api.anthropic.com/v1/messages")


class AnthropicAdapter(LLMAdapter):
    provider = "anthropic"

    def __init__(self, model: str | None = None, budget: Budget | None = None, timeout: float = 120.0) -> None:
        self.model = model or DEFAULT_MODEL
        self.budget = budget or Budget()
        self._client = httpx.Client(timeout=timeout)

    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        label: str = "",
    ) -> LLMResponse:
        self.budget.charge(self.provider, self._estimate_tokens(system + user), max_tokens)
        response = self._client.post(
            _API_URL,
            headers={
                "x-api-key": _require_env("ANTHROPIC_API_KEY"),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
        response.raise_for_status()
        data = response.json()
        text = "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        )
        usage = data.get("usage", {})
        result = LLMResponse(
            text=text,
            input_tokens=int(usage.get("input_tokens", self._estimate_tokens(system + user))),
            output_tokens=int(usage.get("output_tokens", self._estimate_tokens(text))),
            model=data.get("model", self.model),
        )
        self.budget.settle(self.provider, result.input_tokens, result.output_tokens, label)
        return result
