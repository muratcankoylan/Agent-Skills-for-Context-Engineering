"""OpenAI Chat Completions adapter.

Model ID is configurable: set DWL_OPENAI_MODEL or pass model=. Pin an explicit
dated snapshot for benchmark runs; see https://platform.openai.com/docs/models.
"""

from __future__ import annotations

import os

import httpx

from .base import Budget, LLMAdapter, LLMResponse, _require_env

DEFAULT_MODEL = os.environ.get("DWL_OPENAI_MODEL", "gpt-5")
_API_URL = os.environ.get("DWL_OPENAI_URL", "https://api.openai.com/v1/chat/completions")


class OpenAIAdapter(LLMAdapter):
    provider = "openai"

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
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_completion_tokens": max_tokens,
        }
        # Reasoning-first models reject temperature; only send when non-default.
        if abs(temperature - 1.0) > 1e-9 and not self.model.startswith(("o", "gpt-5")):
            payload["temperature"] = temperature
        response = self._client.post(
            _API_URL,
            headers={
                "authorization": f"Bearer {_require_env('OPENAI_API_KEY')}",
                "content-type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage", {})
        result = LLMResponse(
            text=text,
            input_tokens=int(usage.get("prompt_tokens", self._estimate_tokens(system + user))),
            output_tokens=int(usage.get("completion_tokens", self._estimate_tokens(text))),
            model=data.get("model", self.model),
        )
        self.budget.settle(self.provider, result.input_tokens, result.output_tokens, label)
        return result
