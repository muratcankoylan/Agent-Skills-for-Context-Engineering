"""Pangram AI-text detector client. DIAGNOSTIC ONLY.

Policy, stated once and enforced by design: detector scores are recorded as a
reported column in benchmark results. They are never fed back into the writing
loop as an optimization signal. Optimizing against a detector is (a) an
adversarial-evasion use we do not ship, and (b) scientifically confounded,
because evasion and quality are independent axes (you can evade while writing
garbage). The loop optimizes persona fidelity and slop reduction; whether that
moves detector scores is an experimental *finding*, not a target.

The detector is currently disabled. Explicit opt-in and credentials do not
authorize it: an admitted, budgeted connector must be implemented first.
"""

from __future__ import annotations

import os

from .base import LiveExecutionDisabled


class PangramClient:
    def __init__(self, timeout: float = 60.0, *, enabled: bool = False) -> None:
        self.enabled = enabled
        self.endpoint = os.environ.get("DWL_PANGRAM_URL", "https://text.api.pangramlabs.com")

    @property
    def available(self) -> bool:
        return False  # Credentials and opt-in alone never grant paid authority.

    def score(self, text: str) -> dict:
        """Refuse until admitted accounting and response contracts exist."""
        raise LiveExecutionDisabled("detector disabled pending admitted budgeted connector")
