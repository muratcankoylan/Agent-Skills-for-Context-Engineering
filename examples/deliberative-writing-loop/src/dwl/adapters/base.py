"""Offline adapter contract and durable estimate reservations.

Prices below are fixture forecasts, NOT verified vendor prices or hard spend
bounds. Paid adapters are disabled until an admitted SDK/broker replaces them.
Reservations count before effects and survive unknown outcomes and restarts.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from pathlib import Path
import threading
import uuid

from ..state import atomic_json, locked, read_json


class BudgetExceeded(RuntimeError):
    pass


class LiveExecutionDisabled(RuntimeError):
    pass


# Unverified fixture USD/million-token estimates. Never a billing guarantee.
DEFAULT_PRICES = {
    "anthropic": (5.0, 25.0),
    "openai": (3.0, 15.0),
    "mock": (0.0, 0.0),
}


class Budget:
    def __init__(self, max_calls: int = 200, max_usd: float = 10.0,
                 ledger_path: Path | None = None) -> None:
        if type(max_calls) is not int or not 0 <= max_calls <= 10000:
            raise ValueError("max_calls must be an integer in 0..10000")
        if isinstance(max_usd, bool):
            raise ValueError("max_usd must be finite and nonnegative")
        try:
            amount = Decimal(str(max_usd))
        except InvalidOperation as error:
            raise ValueError("max_usd must be finite and nonnegative") from error
        if not amount.is_finite() or not 0 <= amount <= 1000000:
            raise ValueError("max_usd must be finite and nonnegative")
        # Round limits down, reservations up. No floating-point admission math.
        self.max_calls = max_calls
        self.max_microusd = int(amount * 1000000)
        self.max_usd = self.max_microusd / 1000000
        self.ledger_path = Path(ledger_path) if ledger_path is not None else None
        self._lock = threading.RLock()
        self._memory = self._empty()
        self._transaction(lambda state: None)

    def _empty(self):
        return {"schema": "dwl-budget/v1", "max_calls": self.max_calls,
                "max_microusd": self.max_microusd, "prices": DEFAULT_PRICES, "reservations": []}

    def _validate(self, state):
        if (type(state) is not dict or set(state) != set(self._empty())
                or state["schema"] != "dwl-budget/v1" or state["max_calls"] != self.max_calls
                or state["max_microusd"] != self.max_microusd
                or state["prices"] != {k: list(v) for k, v in DEFAULT_PRICES.items()}
                or type(state["reservations"]) is not list or len(state["reservations"]) > self.max_calls):
            raise ValueError("budget identity changed or ledger malformed")
        seen = set()
        for row in state["reservations"]:
            if (type(row) is not dict or set(row) != {"id", "provider", "reserved", "settled", "label"}
                    or not isinstance(row["id"], str) or len(row["id"]) != 32 or row["id"] in seen
                    or row["provider"] not in DEFAULT_PRICES or type(row["reserved"]) is not int
                    or row["reserved"] < 0 or not isinstance(row["label"], str)
                    or (row["settled"] is not None and (type(row["settled"]) is not int or row["settled"] < 0))):
                raise ValueError("budget reservation malformed")
            seen.add(row["id"])

    def _transaction(self, mutate):
        with self._lock:
            if self.ledger_path is None:
                return mutate(self._memory)
            with locked(self.ledger_path.with_suffix(self.ledger_path.suffix + ".lock")):
                state = read_json(self.ledger_path) if self.ledger_path.exists() else self._empty()
                if self.ledger_path.exists():
                    self._validate(state)
                result = mutate(state)
                atomic_json(self.ledger_path, state)
                return result

    @staticmethod
    def _cost(provider, input_tokens, output_tokens):
        if provider not in DEFAULT_PRICES or any(type(v) is not int or not 0 <= v <= 1000000000
                                                 for v in (input_tokens, output_tokens)):
            raise ValueError("invalid usage or provider")
        prices = DEFAULT_PRICES[provider]
        return int((Decimal(str(prices[0])) * input_tokens + Decimal(str(prices[1])) * output_tokens)
                   .to_integral_value(rounding=ROUND_CEILING))

    def charge(self, provider: str, est_input_tokens: int, est_output_tokens: int) -> str:
        estimate = self._cost(provider, est_input_tokens, est_output_tokens)
        def reserve(state):
            rows = state["reservations"]
            if any(r["settled"] is not None and r["settled"] > r["reserved"] for r in rows):
                raise BudgetExceeded("prior settlement exceeded estimate; manual reconciliation required")
            liability = sum(r["reserved"] if r["settled"] is None else r["settled"] for r in rows)
            if len(rows) >= self.max_calls or liability + estimate > self.max_microusd:
                raise BudgetExceeded("call or reserved-estimate cap reached")
            identity = uuid.uuid4().hex
            rows.append({"id": identity, "provider": provider, "reserved": estimate,
                         "settled": None, "label": ""})
            return identity
        return self._transaction(reserve)

    def settle(self, provider: str, input_tokens: int, output_tokens: int, label: str,
               reservation_id: str | None = None) -> None:
        cost = self._cost(provider, input_tokens, output_tokens)
        if not isinstance(label, str) or len(label) > 200:
            raise ValueError("invalid label")
        def finish(state):
            matches = [r for r in state["reservations"] if r["provider"] == provider
                       and (r["id"] == reservation_id if reservation_id else r["settled"] is None)]
            if len(matches) != 1 or matches[0]["settled"] is not None:
                raise ValueError("reservation missing, ambiguous or already settled")
            matches[0].update(settled=cost, label=label)
        self._transaction(finish)

    @property
    def calls(self):
        return self.summary()["calls"]

    @property
    def spent_usd(self):
        return self.summary()["spent_usd"]

    def summary(self) -> dict:
        def report(state):
            rows = state["reservations"]
            settled = sum(r["settled"] or 0 for r in rows)
            reserved = sum(r["reserved"] for r in rows if r["settled"] is None)
            return {"calls": len(rows), "spent_usd": settled / 1000000,
                    "reserved_usd": reserved / 1000000, "liability_microusd": settled + reserved,
                    "unknown_calls": sum(r["settled"] is None for r in rows),
                    "max_calls": self.max_calls, "max_usd": self.max_usd,
                    "accounting": "unverified_price_estimate_not_billing"}
        return self._transaction(report)


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class LLMAdapter:
    provider: str = "base"
    model: str = ""

    def identity(self) -> dict:
        return {"provider": self.provider, "model": self.model,
                "endpoint": getattr(self, "endpoint", None)}

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
        # Offline prompt estimate only. Not a provable tokenizer or billing bound.
        return max(len(text) // 4, 1) + 16


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
        reservation = self.budget.charge(self.provider, self._estimate_tokens(system + user), max_tokens)
        self.calls.append({"system": system, "user": user, "label": label})
        text = self.responses.pop(0) if self.responses else f"[mock:{label or 'response'}]"
        response = LLMResponse(
            text=text,
            input_tokens=self._estimate_tokens(system + user),
            output_tokens=self._estimate_tokens(text),
            model=self.model,
        )
        self.budget.settle(self.provider, response.input_tokens, response.output_tokens, label, reservation)
        return response
