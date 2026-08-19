"""Pangram AI-text detector client. DIAGNOSTIC ONLY.

Policy, stated once and enforced by design: detector scores are recorded as a
reported column in benchmark results. They are never fed back into the writing
loop as an optimization signal. Optimizing against a detector is (a) an
adversarial-evasion use we do not ship, and (b) scientifically confounded,
because evasion and quality are independent axes (you can evade while writing
garbage). The loop optimizes persona fidelity and slop reduction; whether that
moves detector scores is an experimental *finding*, not a target.

Endpoint and response shape follow Pangram's public text API; both are
configurable because vendor APIs move. Requires PANGRAM_API_KEY.
"""

from __future__ import annotations

import os

import httpx

_API_URL = os.environ.get("DWL_PANGRAM_URL", "https://text.api.pangramlabs.com")


class PangramClient:
    def __init__(self, timeout: float = 60.0) -> None:
        self._client = httpx.Client(timeout=timeout)

    @property
    def available(self) -> bool:
        return bool(os.environ.get("PANGRAM_API_KEY"))

    def score(self, text: str) -> dict:
        """Returns {"ai_likelihood": float, "raw": dict} or {"error": str}."""
        key = os.environ.get("PANGRAM_API_KEY", "")
        if not key:
            return {"error": "PANGRAM_API_KEY not set; detector column skipped"}
        try:
            response = self._client.post(
                _API_URL,
                headers={"x-api-key": key, "content-type": "application/json"},
                json={"text": text},
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            return {"error": f"pangram request failed: {exc}"}
        likelihood = data.get("ai_likelihood", data.get("likelihood"))
        return {"ai_likelihood": likelihood, "raw": data}
