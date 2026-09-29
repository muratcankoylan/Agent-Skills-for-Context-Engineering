"""Cooperative foreground drain, never durable execution or spending authority.

A stop request is checked before a new operation, not inside an admitted effect.
The current effect must commit its actual result or uncertainty before unwinding.
This process-local signal is deliberately absent from immutable run identities.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import threading


class StopRequested(KeyboardInterrupt):
    """Control flow, not a research failure or an evaluation-denominator row."""


_STOP = ContextVar("research_foreground_stop", default=None)


@contextmanager
def stop_scope(event):
    if not isinstance(event, threading.Event):
        raise TypeError("STOP_EVENT_REQUIRED")
    token = _STOP.set(event)
    try:
        yield
    finally:
        _STOP.reset(token)


def check_stop():
    event = _STOP.get()
    if event is not None and event.is_set():
        raise StopRequested()
