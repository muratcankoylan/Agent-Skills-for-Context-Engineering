"""Bounded, credential-isolated process for native model HTTP calls.

Only the fixed provider adapter executes here. This is not a sandbox for model
generated code. The parent records intent before starting this process.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys

from researcher.scripts.schema_contract import parse_json_strict
from .providers import ModelRequest, ModelResult, ProviderError, complete


def bounded_complete(request: ModelRequest, *, credential: str) -> ModelResult:
    payload = json.dumps({"request": asdict(request), "credential": credential}).encode()
    if len(payload) > 1_048_576:
        raise ProviderError("REQUEST_LIMIT", "Request too large.", ambiguous=False)
    root = Path(__file__).resolve().parents[2]
    try:
        result = subprocess.run(
            [sys.executable, "-B", "-m", "researcher.service.model_worker"],
            input=payload, capture_output=True, cwd=root,
            env={"PATH": os.defpath, "PYTHONPATH": str(root), "PYTHONUTF8": "1"},
            timeout=request.timeout_seconds, check=False,
        )
    except subprocess.TimeoutExpired:
        # The remote request may have completed. Never retry it automatically.
        raise ProviderError("MODEL_WALL_TIMEOUT", "Model outcome is unknown.") from None
    except OSError:
        raise ProviderError("MODEL_WORKER_START_FAILED", "Worker did not start.", ambiguous=False) from None
    if result.returncode or len(result.stdout) > 2_097_152 or result.stderr:
        raise ProviderError("MODEL_WORKER_FAILED", "Model outcome is unknown.")
    try:
        value = parse_json_strict(result.stdout.decode("utf-8"))
        if set(value) == {"error", "ambiguous"}:
            raise ProviderError(value["error"], "Native adapter failed.", ambiguous=value["ambiguous"])
        if set(value) != {"result"}:
            raise ValueError("record")
        return ModelResult(**value["result"])
    except ProviderError:
        raise
    except (ValueError, TypeError, UnicodeError):
        raise ProviderError("MODEL_WORKER_OUTPUT_INVALID", "Model outcome is unknown.") from None


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(1_048_577)
        if len(raw) > 1_048_576:
            return 2
        value = parse_json_strict(raw.decode("utf-8"))
        result = complete(ModelRequest(**value["request"]), credential=value["credential"])
        output = {"result": asdict(result)}
    except ProviderError as exc:
        output = {"error": exc.code, "ambiguous": exc.ambiguous}
    except Exception:
        output = {"error": "MODEL_WORKER_FAILED", "ambiguous": True}
    sys.stdout.write(json.dumps(output, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
