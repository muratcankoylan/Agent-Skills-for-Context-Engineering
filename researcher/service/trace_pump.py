"""Opt-in foreground trace delivery, never research or budget authority.

The coordinator calls ``tick`` after a completed cycle. One due tick makes at
most one existing, bounded export attempt; it does not create a thread, discover
credentials, initialize/repair a journal, prune evidence, or retry delivery.
Cadence and the failure latch are process-local. Durable per-span claims remain
in the journal across restarts, including interrupted or uncertain attempts.
"""
from __future__ import annotations

import math
from pathlib import Path
import threading
import time

from .contracts import ServiceError
from .trace_cli import export_pending, journal_at
from .trace_export import preflight_config
from .tracing import MAX_EXPORT

_LOCAL_ERRORS = frozenset({
    "TRACE_JOURNAL_NOT_FOUND", "TRACE_UNSAFE_PATH", "TRACE_CORRUPT_KEY",
    "TRACE_STORAGE_FAILED", "TRACE_RECOVERY_REQUIRED", "TRACE_READ_ONLY",
    "TRACE_EXPORT_ALREADY_ATTEMPTED", "TRACE_EXPORT_ALREADY_FINISHED",
    "TRACE_EXPORT_CAPACITY_REACHED", "TRACE_INVALID_EXPORT_RECEIPT",
    "TRACE_INVALID_RECORD", "TRACE_INVALID_OTLP", "TRACE_EXPORT_INVALID_PAYLOAD",
    "TRACE_EXPORT_CREDENTIAL_REFLECTION", "TRACE_EXPORT_INVALID_CREDENTIAL",
    "TRACE_EXPORT_INVALID_PROJECT", "TRACE_EXPORT_INVALID_DEFAULT_APPROVAL",
    "TRACE_EVENT_DUPLICATE_ROOT", "TRACE_EVENT_INVALID_RESULT", "TRACE_EVENT_ROOT_UNCONFIRMED",
})


def _error_code(error):
    # Never echo arbitrary exceptions, private paths, keys, or provider text.
    try:
        code = error.code if isinstance(error, ServiceError) else None
        if type(code) is str and code in _LOCAL_ERRORS:
            return code
    except Exception:
        pass
    return "TRACE_PUMP_LOCAL_FAILURE"


def _result(status, *, error=None, delivery=None):
    return {"schema": "trace-pump-result/v1", "status": status,
            "halted": status == "halted", "error_code": error, "delivery": delivery}


class TracePump:
    """Explicit export capability with one-batch, best-effort foreground ticks.

    Construct before research to reject invalid configuration without I/O. Keep
    this object in the trusted coordinator; credentials must not enter an SDK
    child or its prompts. ``transport`` and ``clock`` are trusted offline test
    seams, not remotely configurable plugins. The normal exporter owns its
    two ten-second absolute transport deadlines: Event creation, then linked
    OTLP spans. No flush-all or force bypass exists.
    """

    def __init__(self, state: Path, *, credential: str, project_id: str,
                 live=False, allow_default_project=False, interval_seconds=60,
                 limit=MAX_EXPORT, transport=None, clock=time.monotonic):
        if live is not True:
            raise ServiceError("TRACE_EXPORT_LIVE_REQUIRED")
        if (type(interval_seconds) is not int or not 5 <= interval_seconds <= 3600
                or type(limit) is not int or not 1 <= limit <= MAX_EXPORT
                or not callable(clock) or transport is not None and not callable(transport)):
            raise ServiceError("TRACE_PUMP_INVALID_CONFIGURATION")
        preflight = preflight_config(credential=credential, project_id=project_id,
                                     allow_default_project=allow_default_project)
        if preflight["error_codes"]:
            raise ServiceError(preflight["error_codes"][0])
        self._state = Path(state).absolute()
        self._credential, self._project_id = credential, project_id
        self._allow_default_project = allow_default_project
        self._interval, self._limit = interval_seconds, limit
        self._transport, self._clock = transport, clock
        self._guard = threading.Lock()
        self._last_tick = self._last_clock = None
        self._halt_code = None

    def tick(self) -> dict:
        """Return only closed metadata; delivery failures never restart research.

        Rejected/partial/unknown delivery or local failure latches this instance
        until operator reconfiguration/restart. Restart never clears journal
        claims, so it cannot resend those spans. Ordinary process interrupts
        still propagate; a committed intent remains quarantined in the journal.
        """
        if not self._guard.acquire(blocking=False):
            return _result("busy")
        try:
            if self._halt_code is not None:
                return _result("halted", error=self._halt_code)
            try:
                now = self._clock()
                if (type(now) not in {int, float} or not math.isfinite(now) or now < 0
                        or self._last_clock is not None and now < self._last_clock):
                    raise ValueError()
            except Exception:
                self._halt_code = "TRACE_PUMP_CLOCK_FAILED"
                return _result("halted", error=self._halt_code)
            self._last_clock = now
            if self._last_tick is not None and now - self._last_tick < self._interval:
                return _result("deferred")
            self._last_tick = now
            try:
                journal = journal_at(self._state, read_only=False)
                delivery = export_pending(journal, credential=self._credential,
                    project_id=self._project_id, live=True, limit=self._limit,
                    transport=self._transport, allow_default_project=self._allow_default_project)
            except Exception as error:
                self._halt_code = _error_code(error)
                return _result("halted", error=self._halt_code)
            if delivery["status"] in {"partial", "rejected", "unknown"}:
                self._halt_code = "TRACE_PUMP_DELIVERY_REVIEW_REQUIRED"
                return _result("halted", error=self._halt_code, delivery=delivery)
            return _result(delivery["status"], delivery=delivery)
        finally:
            self._guard.release()
