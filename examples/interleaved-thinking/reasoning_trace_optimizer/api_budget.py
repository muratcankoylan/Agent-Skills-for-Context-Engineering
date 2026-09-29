"""Fail-closed attempt budgeting for paid example API calls.

The budget deliberately controls quantities known before a request: SDK attempt
count and requested output-token capacity. Input tokens and provider pricing are
not predictable locally, so they are recorded when reported but are not presented
as a dollar-cost ceiling.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any

DEFAULT_MAX_API_ATTEMPTS = 64
DEFAULT_MAX_RESERVED_OUTPUT_TOKENS = 300_000


class PaidAPIBudgetError(RuntimeError):
    """Base class for paid-call budget failures."""


class PaidAPIBudgetExceededError(PaidAPIBudgetError):
    """Raised before a call when its reservation would exceed a cap."""


class PaidAPIDryRunError(PaidAPIBudgetError):
    """Raised before a call because dry-run mode cannot produce evidence."""

    is_evidence = False

    def __init__(self, operation: str):
        self.operation = operation
        super().__init__(
            f"dry-run blocked paid operation {operation!r}; "
            "no API result or evaluation evidence was produced"
        )


class PaidAPIAccountingError(PaidAPIBudgetError):
    """Raised when a provider response cannot satisfy the accounting contract."""


@dataclass(frozen=True)
class PaidAPIAttemptRecord:
    """Immutable projection of one reserved SDK attempt."""

    sequence: int
    operation: str
    reserved_output_tokens: int
    status: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    error_type: str | None = None


@dataclass
class _MutableAttemptRecord:
    sequence: int
    operation: str
    reserved_output_tokens: int
    status: str = "reserved"
    input_tokens: int | None = None
    output_tokens: int | None = None
    error_type: str | None = None

    def project(self) -> PaidAPIAttemptRecord:
        return PaidAPIAttemptRecord(
            sequence=self.sequence,
            operation=self.operation,
            reserved_output_tokens=self.reserved_output_tokens,
            status=self.status,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            error_type=self.error_type,
        )


def _positive_integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _usage_value(usage: object, field: str) -> int | None:
    value = getattr(usage, field, None)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PaidAPIAccountingError(
            f"provider usage field {field!r} must be a non-negative integer"
        )
    return value


class PaidAPIAttempt:
    """Context manager that reserves before, and settles after, one SDK attempt."""

    def __init__(self, budget: PaidAPIBudget, sequence: int):
        self._budget = budget
        self._sequence = sequence
        self._settled = False

    def __enter__(self) -> PaidAPIAttempt:
        return self

    def record_usage(self, response: object) -> None:
        """Settle a successful attempt from an Anthropic-compatible response."""

        if self._settled:
            raise PaidAPIAccountingError("attempt has already been settled")

        usage = getattr(response, "usage", None)
        input_tokens = _usage_value(usage, "input_tokens") if usage is not None else None
        output_tokens = _usage_value(usage, "output_tokens") if usage is not None else None
        status = self._budget._settle_success(
            self._sequence,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self._settled = True
        if status == "succeeded_usage_unknown":
            raise PaidAPIAccountingError(
                "provider response omitted complete input/output token usage"
            )
        if status == "succeeded_over_reservation":
            raise PaidAPIAccountingError(
                "provider output usage exceeded the pre-call reservation"
            )

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any) -> bool:
        del tb
        if not self._settled:
            if exc_type is None:
                self._budget._settle_success(
                    self._sequence,
                    input_tokens=None,
                    output_tokens=None,
                )
                self._settled = True
                raise PaidAPIAccountingError(
                    "paid attempt exited without recording provider usage"
                )
            else:
                self._budget._settle_failure(self._sequence, exc)
            self._settled = True
        return False


class PaidAPIBudget:
    """Thread-safe cumulative attempt and output-reservation budget.

    Reservations are never refunded. An exception can occur after a provider has
    accepted a request, so failed attempts remain conservatively charge-unknown.
    SDK-managed retries must be disabled; a caller retry enters a new attempt and
    therefore receives its own record and reservation.
    """

    def __init__(
        self,
        *,
        max_api_attempts: int = DEFAULT_MAX_API_ATTEMPTS,
        max_reserved_output_tokens: int = DEFAULT_MAX_RESERVED_OUTPUT_TOKENS,
        dry_run: bool = False,
    ):
        self.max_api_attempts = _positive_integer(
            max_api_attempts,
            "max_api_attempts",
        )
        self.max_reserved_output_tokens = _positive_integer(
            max_reserved_output_tokens,
            "max_reserved_output_tokens",
        )
        if not isinstance(dry_run, bool):
            raise ValueError("dry_run must be a boolean")
        self.dry_run = dry_run
        self._records: list[_MutableAttemptRecord] = []
        self._reserved_output_tokens = 0
        self._lock = Lock()

    def attempt(self, operation: str, max_output_tokens: int) -> PaidAPIAttempt:
        """Reserve capacity for exactly one SDK attempt before caller code runs."""

        if not isinstance(operation, str) or not operation.strip():
            raise ValueError("operation must be a non-empty string")
        requested_tokens = _positive_integer(max_output_tokens, "max_output_tokens")
        if self.dry_run:
            raise PaidAPIDryRunError(operation)

        with self._lock:
            if len(self._records) >= self.max_api_attempts:
                raise PaidAPIBudgetExceededError(
                    f"API-attempt cap exhausted before {operation!r}"
                )
            projected_tokens = self._reserved_output_tokens + requested_tokens
            if projected_tokens > self.max_reserved_output_tokens:
                raise PaidAPIBudgetExceededError(
                    f"output-token reservation cap exceeded before {operation!r}"
                )

            sequence = len(self._records) + 1
            self._records.append(
                _MutableAttemptRecord(
                    sequence=sequence,
                    operation=operation,
                    reserved_output_tokens=requested_tokens,
                )
            )
            self._reserved_output_tokens = projected_tokens

        return PaidAPIAttempt(self, sequence)

    @property
    def records(self) -> tuple[PaidAPIAttemptRecord, ...]:
        """Return an immutable snapshot of all reserved attempts."""

        with self._lock:
            return tuple(record.project() for record in self._records)

    @property
    def reserved_output_tokens(self) -> int:
        with self._lock:
            return self._reserved_output_tokens

    @property
    def reported_input_tokens(self) -> int:
        with self._lock:
            return sum(record.input_tokens or 0 for record in self._records)

    @property
    def reported_output_tokens(self) -> int:
        with self._lock:
            return sum(record.output_tokens or 0 for record in self._records)

    def _record(self, sequence: int) -> _MutableAttemptRecord:
        try:
            return self._records[sequence - 1]
        except IndexError:
            raise PaidAPIAccountingError("unknown attempt sequence") from None

    def _settle_success(
        self,
        sequence: int,
        *,
        input_tokens: int | None,
        output_tokens: int | None,
    ) -> str:
        with self._lock:
            record = self._record(sequence)
            if record.status != "reserved":
                raise PaidAPIAccountingError("attempt has already been settled")
            record.input_tokens = input_tokens
            record.output_tokens = output_tokens
            if input_tokens is None or output_tokens is None:
                record.status = "succeeded_usage_unknown"
            elif output_tokens > record.reserved_output_tokens:
                record.status = "succeeded_over_reservation"
            else:
                record.status = "succeeded"
            return record.status

    def _settle_failure(
        self,
        sequence: int,
        error: BaseException | None,
    ) -> None:
        with self._lock:
            record = self._record(sequence)
            if record.status != "reserved":
                raise PaidAPIAccountingError("attempt has already been settled")
            record.status = "failed_charge_unknown"
            record.error_type = type(error).__name__ if error is not None else "UnknownError"
