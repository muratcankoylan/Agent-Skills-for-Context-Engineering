#!/usr/bin/env python3
"""Advance the continuous research loop by one step.

A single invocation either:

1. Reports that an inbox item requires explicit human initialization.
2. Advances the oldest active run by exactly one safe bookkeeping transition.
3. Parks runs that need human or model judgment.
4. Returns exit code 78 when there is no safe work to do.

The loop is intentionally conservative. It never invokes LLMs or performs
network retrieval. A human must attach source evidence through the explicit
research-run command before the loop can advance the run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .loop_common import (
        QUEUE_DIR,
        REPORTS_DIR,
        append_jsonl,
        list_run_dirs,
        load_config,
        load_run_state,
        queue_lock,
        read_jsonl,
        require_runtime_queue_ledgers,
        utc_now,
        write_jsonl,
    )
    from .loop_daily import closed_run_projection, queue_snapshot
else:  # Direct script execution.
    from loop_common import (
        QUEUE_DIR,
        REPORTS_DIR,
        append_jsonl,
        list_run_dirs,
        load_config,
        load_run_state,
        queue_lock,
        read_jsonl,
        require_runtime_queue_ledgers,
        utc_now,
        write_jsonl,
    )
    from loop_daily import closed_run_projection, queue_snapshot


LOOP_EVENTS = REPORTS_DIR / "loop-events.jsonl"
PARKED_FILE = QUEUE_DIR / "parked.jsonl"
DONE_FILE = QUEUE_DIR / "done.jsonl"
LEGACY_REFERENCE_RUN_ID = "20260515-035228-executable-autonomous-research-frameworks"
RUN_PROJECTION_LOCK = "run-projection"


def record_event(event: dict[str, Any]) -> None:
    event = dict(event)
    event["timestamp"] = utc_now()
    append_jsonl(LOOP_EVENTS, event)


def park_run(run_id: str, reason: str) -> None:
    # Park and reap both replace parked.jsonl. They must share one transaction
    # lock or two individually atomic replacements can still lose an update.
    with queue_lock(RUN_PROJECTION_LOCK):
        parked = read_jsonl(PARKED_FILE)
        if any(record.get("run_id") == run_id for record in parked):
            return
        parked.append({"run_id": run_id, "reason": reason, "parked_at": utc_now()})
        write_jsonl(PARKED_FILE, parked)


def reap_closed_runs(run_dirs: list[Path] | None = None) -> list[dict[str, Any]]:
    """Idempotently reconcile closed states into done and out of parked.

    The two ledgers cannot be replaced atomically together. A single operation
    lock serializes writers, and queue health represents either crash window as
    ``pending_reap`` so the next step can finish reconciliation.
    """

    events: list[dict[str, Any]] = []
    candidates = run_dirs if run_dirs is not None else list_run_dirs()
    with queue_lock(RUN_PROJECTION_LOCK):
        parked = read_jsonl(PARKED_FILE)
        done = read_jsonl(DONE_FILE)
        done_ids = {record.get("run_id") for record in done}
        done_changed = False
        candidate_ids: set[str] = set()
        for run_dir in candidates:
            state = load_run_state(run_dir)
            if not state or state.get("current_state") != "closed":
                continue
            if (
                run_dir.name == LEGACY_REFERENCE_RUN_ID
                and state.get("close_status") == "reference-only"
            ):
                continue
            _closure, closure_errors = closed_run_projection(run_dir, state)
            if closure_errors:
                raise ValueError("cannot reap invalid closed run: " + "; ".join(closure_errors))
            candidate_ids.add(run_dir.name)
            was_done = run_dir.name in done_ids
            was_parked = any(
                record.get("run_id") == run_dir.name for record in parked
            )
            if not was_done:
                done.append(
                    {
                        "run_id": run_dir.name,
                        "status": state.get("close_status") or "unknown",
                        "reason": state.get("close_reason") or "",
                        "closed_at": state["state_history"][-1]["timestamp"],
                        "reaped_at": utc_now(),
                    }
                )
                done_ids.add(run_dir.name)
                done_changed = True
            if not was_done or was_parked:
                events.append({"action": "reaped", "run_id": run_dir.name})
        next_parked = [
            record
            for record in parked
            if record.get("run_id") not in candidate_ids
        ]
        if done_changed:
            write_jsonl(DONE_FILE, done)
        if next_parked != parked:
            write_jsonl(PARKED_FILE, next_parked)
    return events


def advance_initialized(run_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    run_id = run_dir.name
    if not state.get("source_url"):
        park_run(run_id, "no source URL on run-state.json")
        return {"action": "parked", "run_id": run_id, "reason": "no source URL"}
    park_run(run_id, "network retrieval removed; attach evidence manually")
    return {"action": "parked", "run_id": run_id, "reason": "manual retrieval required"}


def advance_retrieved(run_dir: Path) -> dict[str, Any]:
    run_id = run_dir.name
    park_run(run_id, "needs source evaluation by human or judge agent")
    return {"action": "parked", "run_id": run_id, "reason": "needs evaluation"}


def advance_run(run_dir: Path) -> dict[str, Any]:
    state = load_run_state(run_dir)
    if not state:
        park_run(run_dir.name, "missing run-state.json")
        return {"action": "parked", "run_id": run_dir.name, "reason": "missing state"}
    current = state.get("current_state")
    if current == "initialized":
        return advance_initialized(run_dir, state)
    if current == "retrieved":
        return advance_retrieved(run_dir)
    if current in {"evaluated", "proposed", "novelty_checked", "validated"}:
        park_run(run_dir.name, f"needs human or model action from state {current}")
        return {"action": "parked", "run_id": run_dir.name, "reason": f"needs action from {current}"}
    if current == "pr_ready":
        park_run(run_dir.name, "PR is ready for human merge approval")
        return {"action": "parked", "run_id": run_dir.name, "reason": "needs merge approval"}
    if current == "closed":
        return {"action": "closed", "run_id": run_dir.name}
    park_run(run_dir.name, f"unknown current state {current}")
    return {"action": "parked", "run_id": run_dir.name, "reason": f"unknown state {current}"}


def loop_step(config: dict[str, Any]) -> dict[str, Any]:
    require_runtime_queue_ledgers(QUEUE_DIR)
    budgets = config.get("budgets", {})
    max_parked = budgets.get("max_parked", 12)
    if type(max_parked) is not int or max_parked < 0:
        raise ValueError("max_parked must be a non-negative integer")
    # `mode` governs future LLM-judge feeds. This legacy step has no network
    # retrieval capability in any mode.

    snapshot = queue_snapshot(
        include_details=True,
        queue_dir=QUEUE_DIR,
        config=config,
    )
    if not (
        snapshot.get("parse_ok") is True
        and snapshot.get("referential_ok") is True
        and snapshot.get("unknown") == 0
    ):
        raise ValueError(
            "cannot advance with invalid runtime queues or runs: "
            + str(snapshot.get("parse_error") or snapshot.get("referential_errors"))
        )
    reaped = reap_closed_runs(snapshot.get("_pending_reap", []))
    for event in reaped:
        record_event({"phase": "reap", **event})

    snapshot = queue_snapshot(
        include_details=True,
        queue_dir=QUEUE_DIR,
        config=config,
    )
    if not (
        snapshot.get("parse_ok") is True
        and snapshot.get("referential_ok") is True
        and snapshot.get("unknown") == 0
        and snapshot.get("pending_reap") == 0
    ):
        raise ValueError(
            "closed-run reconciliation did not converge: "
            + str(snapshot.get("parse_error") or snapshot.get("referential_errors"))
        )
    buckets = snapshot["_buckets"]

    active = buckets["active"]
    parked = read_jsonl(PARKED_FILE)
    if len(parked) >= max_parked:
        record_event({"action": "stop", "reason": "parked queue full"})
        return {"ok": True, "action": "stop", "reason": "parked queue full"}

    if not active:
        record_event({"action": "no-op", "reason": "no active supervised runs"})
        return {"ok": True, "action": "no-op"}

    active.sort(key=lambda path: load_run_state(path).get("updated_at", "") if load_run_state(path) else "")
    target = active[0]
    result = advance_run(target)
    record_event({"phase": "advance", **result})
    return {"ok": True, **result}


def main() -> int:
    parser = argparse.ArgumentParser(description="Advance the continuous research loop by one step")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    config = load_config()
    result = loop_step(config)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"loop_step: {result.get('action')} {result.get('reason') or ''}".strip())
    if result.get("action") == "no-op":
        return 78
    return 0


if __name__ == "__main__":
    sys.exit(main())
