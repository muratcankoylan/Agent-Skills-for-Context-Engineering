"""Adapter contract, budget enforcement, and the test double.

Every LLM call in the harness flows through Budget.charge() *before* the
request is sent. A run can never exceed its call or dollar cap by more than
the single in-flight request. Prices are configurable because they change;
defaults are deliberately conservative (overestimates).
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field


class BudgetExceeded(RuntimeError):
    pass


# USD per million tokens (input, output). Overridable via env or Budget kwargs.
# Conservative defaults so the forecast errs high.
DEFAULT_PRICES = {
    "anthropic": (5.0, 25.0),
    "openai": (3.0, 15.0),
    "mock": (0.0, 0.0),
}


@dataclass
class Budget:
    max_calls: int = 200
    max_usd: float = 10.0
    calls: int = 0
    spent_usd: float = 0.0
    log: list[dict] = field(default_factory=list)

    def charge(self, provider: str, est_input_tokens: int, est_output_tokens: int) -> None:
        """Pre-charge with estimates; call settle() with real usage after."""
        if self.calls + 1 > self.max_calls:
            raise BudgetExceeded(f"call cap reached ({self.max_calls})")
        in_price, out_price = DEFAULT_PRICES.get(provider, (5.0, 25.0))
        est = (est_input_tokens * in_price + est_output_tokens * out_price) / 1e6
        if self.spent_usd + est > self.max_usd:
            raise BudgetExceeded(
                f"budget cap would be exceeded: spent ${self.spent_usd:.2f}, "
                f"next call estimated ${est:.2f}, cap ${self.max_usd:.2f}"
            )
        self.calls += 1

    def settle(self, provider: str, input_tokens: int, output_tokens: int, label: str) -> None:
        in_price, out_price = DEFAULT_PRICES.get(provider, (5.0, 25.0))
        cost = (input_tokens * in_price + output_tokens * out_price) / 1e6
        self.spent_usd += cost
        self.log.append(
            {
                "label": label,
                "provider": provider,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "usd": round(cost, 6),
                "ts": time.time(),
            }
        )

    def summary(self) -> dict:
        return {
            "calls": self.calls,
            "spent_usd": round(self.spent_usd, 4),
            "max_calls": self.max_calls,
            "max_usd": self.max_usd,
        }


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class LLMAdapter:
    provider: str = "base"
    model: str = ""

    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        label: str = "",
    ) -> LLMResponse:
        raise NotImplementedError

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        # ~4 chars per token is a safe overestimate for English prose.
        return max(len(text) // 4, 1) + 16


def _require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(
            f"{name} is not set. Add it as a secret (Cursor dashboard: Cloud Agents > Secrets) "
            "or export it in your shell."
        )
    return value


class MockAdapter(LLMAdapter):
    """Deterministic test double. Replays queued responses or echoes a stub.

    Records every call so tests can assert on prompts without network access.
    """

    provider = "mock"
    model = "mock-1"

    def __init__(self, responses: list[str] | None = None, budget: Budget | None = None) -> None:
        self.responses = list(responses or [])
        self.budget = budget or Budget(max_calls=10_000, max_usd=1.0)
        self.calls: list[dict] = []

    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        label: str = "",
    ) -> LLMResponse:
        self.budget.charge(self.provider, self._estimate_tokens(system + user), max_tokens)
        self.calls.append({"system": system, "user": user, "label": label})
        text = self.responses.pop(0) if self.responses else f"[mock:{label or 'response'}]"
        response = LLMResponse(
            text=text,
            input_tokens=self._estimate_tokens(system + user),
            output_tokens=self._estimate_tokens(text),
            model=self.model,
        )
        self.budget.settle(self.provider, response.input_tokens, response.output_tokens, label)
        return response
