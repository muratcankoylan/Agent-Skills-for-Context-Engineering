#!/usr/bin/env python3
"""Advance the continuous research loop by one step.

A single invocation either:

1. Pulls the oldest inbox item into a new run (if under budget).
2. Advances the oldest active run by exactly one safe state transition.
3. Parks runs that need human or model judgment.
4. Returns exit code 78 when there is no safe work to do.

The loop is intentionally conservative. It never invokes LLMs and never makes
network calls that are not whitelisted. The default `--allow-fetch` is off, so
the loop scheduler that runs unattended only manages bookkeeping until a human
or another adapter retrieves the source.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loop_common import (
    QUEUE_DIR,
    REPORTS_DIR,
    RESEARCHER,
    ROOT,
    RUNS_DIR,
    append_jsonl,
    categorize_runs,
    load_config,
    load_run_state,
    queue_lock,
    read_jsonl,
    runs_created_today,
    today_utc,
    utc_now,
    write_jsonl,
)


FAILURE_LOG = REPORTS_DIR / "loop-failures.jsonl"
LOOP_EVENTS = REPORTS_DIR / "loop-events.jsonl"
PARKED_FILE = QUEUE_DIR / "parked.jsonl"
DONE_FILE = QUEUE_DIR / "done.jsonl"
QUARANTINE_FILE = QUEUE_DIR / "quarantine.jsonl"
INBOX_FILE = QUEUE_DIR / "inbox.jsonl"
HTTP_REQUESTS_FILE = REPORTS_DIR / "http-requests.jsonl"
RESEARCH_LOOP = RESEARCHER / "scripts" / "research_loop.py"
USER_AGENT = "context-engineering-researcher/0.1 (+https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering)"
MAX_FETCH_BYTES = 1_500_000
DEFAULT_HTTP_RETRY_MAX = 3
DEFAULT_HTTP_RETRY_BASE_DELAY = 1.0
DEFAULT_HTTP_RETRY_MAX_DELAY = 60.0


def record_event(event: dict[str, Any]) -> None:
    event = dict(event)
    event["timestamp"] = utc_now()
    append_jsonl(LOOP_EVENTS, event)


def record_failure(event: dict[str, Any]) -> None:
    event = dict(event)
    event["timestamp"] = utc_now()
    append_jsonl(FAILURE_LOG, event)


def record_http_request(event: dict[str, Any]) -> None:
    event = dict(event)
    event["timestamp"] = utc_now()
    append_jsonl(HTTP_REQUESTS_FILE, event)


def http_requests_today() -> int:
    if not HTTP_REQUESTS_FILE.exists():
        return 0
    today = today_utc()
    count = 0
    for line in HTTP_REQUESTS_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("timestamp", "").startswith(today):
            count += 1
    return count


def failures_today() -> int:
    if not FAILURE_LOG.exists():
        return 0
    today = today_utc()
    count = 0
    for line in FAILURE_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("timestamp", "").startswith(today):
            count += 1
    return count


def park_run(run_id: str, reason: str) -> None:
    with queue_lock("parked"):
        parked = read_jsonl(PARKED_FILE)
        if any(record.get("run_id") == run_id for record in parked):
            return
        parked.append({"run_id": run_id, "reason": reason, "parked_at": utc_now()})
        write_jsonl(PARKED_FILE, parked)


def unpark_run(run_id: str) -> None:
    with queue_lock("parked"):
        parked = [record for record in read_jsonl(PARKED_FILE) if record.get("run_id") != run_id]
        write_jsonl(PARKED_FILE, parked)


def mark_done(run_id: str, status: str, reason: str) -> None:
    with queue_lock("done"):
        done = read_jsonl(DONE_FILE)
        if any(record.get("run_id") == run_id for record in done):
            return
        done.append({"run_id": run_id, "status": status, "reason": reason, "closed_at": utc_now()})
        write_jsonl(DONE_FILE, done)


def quarantine_source(record: dict[str, Any], reason: str) -> None:
    record = dict(record)
    record["quarantined_at"] = utc_now()
    record["quarantine_reason"] = reason
    with queue_lock("quarantine"):
        append_jsonl(QUARANTINE_FILE, record)


def peek_inbox_item() -> dict[str, Any] | None:
    inbox = read_jsonl(INBOX_FILE)
    if not inbox:
        return None
    inbox.sort(key=lambda record: record.get("discovered_at", ""))
    return inbox[0]


def remove_inbox_item(source_id: str) -> None:
    inbox = read_jsonl(INBOX_FILE)
    inbox = [record for record in inbox if record.get("source_id") != source_id]
    write_jsonl(INBOX_FILE, inbox)


def reap_closed_runs() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not RUNS_DIR.exists():
        return events
    done_ids = {record.get("run_id") for record in read_jsonl(DONE_FILE)}
    for run_dir in sorted(RUNS_DIR.iterdir()):
        if not run_dir.is_dir():
            continue
        state = load_run_state(run_dir)
        if not state or state.get("current_state") != "closed":
            continue
        if run_dir.name in done_ids:
            continue
        unpark_run(run_dir.name)
        mark_done(
            run_dir.name,
            status=state.get("close_status") or "unknown",
            reason=state.get("close_reason") or "",
        )
        events.append({"action": "reaped", "run_id": run_dir.name})
    return events


def init_run(source: dict[str, Any]) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(RESEARCH_LOOP),
        "init",
        "--title",
        source.get("title") or source.get("url") or "untitled",
        "--url",
        source.get("url", ""),
        "--author-or-org",
        source.get("author_or_org", ""),
        "--source-type",
        normalize_source_type(source.get("source_type")),
        "--reason",
        source.get("candidate_reason", ""),
    ]
    completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return {"ok": False, "stderr": completed.stderr.strip(), "stdout": completed.stdout.strip()}
    run_relative = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else ""
    return {"ok": True, "run_relative": run_relative}


def normalize_source_type(value: str | None) -> str:
    allowed = {"paper", "engineering_blog", "documentation", "benchmark", "code", "talk", "other"}
    if isinstance(value, str) and value in allowed:
        return value
    return "other"


def _http_request_with_retry(
    request: urllib.request.Request,
    max_retries: int = DEFAULT_HTTP_RETRY_MAX,
    base_delay: float = DEFAULT_HTTP_RETRY_BASE_DELAY,
    max_delay: float = DEFAULT_HTTP_RETRY_MAX_DELAY,
) -> urllib.request.addinfourl:
    """Open a URL with exponential backoff on 429 / 5xx / transient errors."""
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return urllib.request.urlopen(request, timeout=30)
        except urllib.error.HTTPError as exc:
            last_error = exc
            if attempt >= max_retries or exc.code not in {429, 500, 502, 503, 504}:
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            delay = random.uniform(0.0, delay)
            time.sleep(delay)
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt >= max_retries:
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            delay = random.uniform(0.0, delay)
            time.sleep(delay)
    raise last_error or RuntimeError("HTTP retry loop exited without result")


def fetch_url(
    url: str,
    dest_dir: Path,
    dry_run: bool = False,
    max_retries: int = DEFAULT_HTTP_RETRY_MAX,
) -> dict[str, Any]:
    if not url.lower().startswith(("http://", "https://")):
        return {"ok": False, "error": f"unsupported url scheme: {url[:32]}", "url": url}

    record_http_request({"url": url, "dry_run": dry_run})

    if dry_run:
        return {"ok": False, "error": "dry-run: HTTP retrieval disabled", "url": url}

    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", url).strip("-")[:120] or "source"
    target = dest_dir / f"{safe_name}.html"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    try:
        with _http_request_with_retry(request, max_retries=max_retries) as response:
            final_url = getattr(response, "url", url)
            if not final_url.lower().startswith(("http://", "https://")):
                return {"ok": False, "error": "redirect changed scheme", "url": final_url}
            content_type = response.headers.get("Content-Type", "")
            data = response.read(MAX_FETCH_BYTES + 1)
            truncated = len(data) > MAX_FETCH_BYTES
            data = data[:MAX_FETCH_BYTES]
            target.write_bytes(data)
            return {
                "ok": True,
                "path": str(target.relative_to(ROOT)),
                "bytes": len(data),
                "content_type": content_type,
                "truncated": truncated,
                "final_url": final_url,
            }
    except urllib.error.HTTPError as exc:
        return {"ok": False, "error": f"http {exc.code}", "url": url}
    except urllib.error.URLError as exc:
        return {"ok": False, "error": f"network error: {exc.reason}", "url": url}
    except TimeoutError:
        return {"ok": False, "error": "timeout", "url": url}


def attempt_retrieval(
    run_dir: Path,
    url: str,
    dry_run: bool = False,
    max_retries: int = DEFAULT_HTTP_RETRY_MAX,
) -> dict[str, Any]:
    raw_dir = run_dir / "sources" / "evidence" / "raw"
    return fetch_url(url, raw_dir, dry_run=dry_run, max_retries=max_retries)


def append_evidence_pointer(run_dir: Path, raw_record: dict[str, Any]) -> None:
    summary_path = run_dir / "sources" / "evidence" / "retrieval.md"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    line = (
        f"- {raw_record.get('path', '')} ({raw_record.get('bytes', 0)} bytes, "
        f"{raw_record.get('content_type', '')}) retrieved at {utc_now()}\n"
    )
    with summary_path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def update_run_queue_retrieval(run_dir: Path, status: str, raw_paths: list[str], notes: str) -> None:
    queue = run_dir / "sources" / "queue.jsonl"
    if not queue.exists():
        return
    records = [json.loads(line) for line in queue.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not records:
        return
    records[0].update(
        {
            "retrieval_status": status,
            "retrieved_at": utc_now(),
            "raw_evidence": raw_paths,
            "retrieval_notes": notes,
        }
    )
    queue.write_text("\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n", encoding="utf-8")


def advance_initialized(
    run_dir: Path,
    state: dict[str, Any],
    allow_fetch: bool,
    dry_run: bool = False,
    max_retries: int = DEFAULT_HTTP_RETRY_MAX,
) -> dict[str, Any]:
    url = state.get("source_url")
    run_id = run_dir.name
    if not url:
        park_run(run_id, "no source URL on run-state.json")
        return {"action": "parked", "run_id": run_id, "reason": "no source URL"}
    if not allow_fetch:
        park_run(run_id, "automatic retrieval disabled; needs manual retrieve")
        return {"action": "parked", "run_id": run_id, "reason": "fetch disabled"}
    fetched = attempt_retrieval(run_dir, url, dry_run=dry_run, max_retries=max_retries)
    if not fetched.get("ok"):
        park_run(run_id, f"retrieval failed: {fetched.get('error')}")
        record_failure({"phase": "retrieval", "run_id": run_id, "url": url, "error": fetched.get("error")})
        return {"action": "parked", "run_id": run_id, "reason": fetched.get("error")}
    append_evidence_pointer(run_dir, fetched)
    update_run_queue_retrieval(
        run_dir,
        status="retrieved",
        raw_paths=[fetched["path"]],
        notes=f"auto fetch via loop_step; content_type={fetched.get('content_type', '')}",
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(RESEARCH_LOOP),
            "retrieve",
            "--run-dir",
            str(run_dir),
            "--notes",
            "auto fetch via loop_step",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        record_failure(
            {"phase": "retrieve-state", "run_id": run_id, "stderr": completed.stderr.strip()}
        )
        park_run(run_id, "could not record retrieved state")
        return {"action": "parked", "run_id": run_id, "reason": "state transition failed"}
    return {"action": "advanced", "run_id": run_id, "to_state": "retrieved", "bytes": fetched.get("bytes")}


def advance_retrieved(run_dir: Path) -> dict[str, Any]:
    run_id = run_dir.name
    park_run(run_id, "needs source evaluation by human or judge agent")
    return {"action": "parked", "run_id": run_id, "reason": "needs evaluation"}


def advance_run(
    run_dir: Path,
    allow_fetch: bool,
    dry_run: bool = False,
    max_retries: int = DEFAULT_HTTP_RETRY_MAX,
) -> dict[str, Any]:
    state = load_run_state(run_dir)
    if not state:
        park_run(run_dir.name, "missing run-state.json")
        return {"action": "parked", "run_id": run_dir.name, "reason": "missing state"}
    current = state.get("current_state")
    if current == "initialized":
        return advance_initialized(run_dir, state, allow_fetch, dry_run=dry_run, max_retries=max_retries)
    if current == "retrieved":
        return advance_retrieved(run_dir)
    if current in {"evaluated", "proposed", "novelty_checked", "validated"}:
        park_run(run_dir.name, f"needs human or model action from state {current}")
        return {"action": "parked", "run_id": run_dir.name, "reason": f"needs action from {current}"}
    if current == "pr_ready":
        park_run(run_dir.name, "PR is ready for human merge approval")
        return {"action": "parked", "run_id": run_dir.name, "reason": "needs merge approval"}
    if current == "closed":
        unpark_run(run_dir.name)
        mark_done(
            run_dir.name,
            status=state.get("close_status") or "unknown",
            reason=state.get("close_reason") or "",
        )
        return {"action": "closed", "run_id": run_dir.name}
    park_run(run_dir.name, f"unknown current state {current}")
    return {"action": "parked", "run_id": run_dir.name, "reason": f"unknown state {current}"}


def loop_step(
    config: dict[str, Any],
    allow_fetch: bool,
    dry_run: bool = False,
    max_retries: int = DEFAULT_HTTP_RETRY_MAX,
) -> dict[str, Any]:
    budgets = config.get("budgets", {})
    max_active = budgets.get("max_active_runs", 3)
    max_runs_today = budgets.get("max_runs_per_day", 6)
    max_failures = budgets.get("max_failures_per_day", 5)
    max_parked = budgets.get("max_parked", 12)
    max_http_requests = budgets.get("max_http_requests_per_day")
    # `mode` governs future paid-LLM feeds, not stdlib HTTP retrieval. Retrieval is
    # controlled by --allow-fetch alone so the daemon can stage evidence without
    # incurring paid-API spend.

    reaped = reap_closed_runs()
    for event in reaped:
        record_event({"phase": "reap", **event})

    if failures_today() >= max_failures:
        record_event({"action": "stop", "reason": "failure budget exceeded"})
        return {"ok": True, "action": "stop", "reason": "failure budget exceeded"}

    if max_http_requests is not None and http_requests_today() >= max_http_requests:
        record_event({"action": "stop", "reason": "HTTP request budget exceeded"})
        return {"ok": True, "action": "stop", "reason": "HTTP request budget exceeded"}

    if dry_run:
        # In dry-run mode we still park initialized runs so the state machine
        # advances, but we do not perform real HTTP retrieval.
        pass

    buckets = categorize_runs()
    active = buckets["active"]
    parked = read_jsonl(PARKED_FILE)
    if len(parked) >= max_parked:
        record_event({"action": "stop", "reason": "parked queue full"})
        return {"ok": True, "action": "stop", "reason": "parked queue full"}

    if len(active) < max_active and runs_created_today() < max_runs_today:
        with queue_lock("inbox"):
            # Re-check budgets inside the lock so concurrent loop_step invocations
            # cannot both pass the pre-check and exceed max_active/max_per_day.
            current_buckets = categorize_runs()
            if (
                len(current_buckets["active"]) < max_active
                and runs_created_today() < max_runs_today
            ):
                source = peek_inbox_item()
                if source:
                    init = init_run(source)
                    if not init.get("ok"):
                        remove_inbox_item(source.get("source_id"))
                        quarantine_source(
                            source,
                            reason=f"init failed: {init.get('stderr', '')[:200]}",
                        )
                        record_failure(
                            {
                                "phase": "init",
                                "source": source.get("url"),
                                "stderr": init.get("stderr"),
                            }
                        )
                        record_event({"action": "init-failed", "source": source.get("url")})
                        return {"ok": True, "action": "init-failed", "source": source.get("url")}
                    remove_inbox_item(source.get("source_id"))
                    event = {
                        "action": "initialized",
                        "source": source.get("url"),
                        "run": init.get("run_relative"),
                    }
                    record_event(event)
                    return {"ok": True, **event}

    if not active:
        record_event({"action": "no-op", "reason": "no active runs and inbox empty or budget reached"})
        return {"ok": True, "action": "no-op"}

    active.sort(key=lambda path: load_run_state(path).get("updated_at", "") if load_run_state(path) else "")
    target = active[0]
    result = advance_run(target, allow_fetch, dry_run=dry_run, max_retries=max_retries)
    record_event({"phase": "advance", **result})
    return {"ok": True, **result}


def main() -> int:
    parser = argparse.ArgumentParser(description="Advance the continuous research loop by one step")
    parser.add_argument("--allow-fetch", action="store_true", help="permit HTTP GET retrieval of source URLs")
    parser.add_argument("--dry-run", action="store_true", help="do not make real HTTP requests or spend budget")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    config = load_config()
    result = loop_step(config, args.allow_fetch, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"loop_step: {result.get('action')} {result.get('reason') or ''}".strip())
    if result.get("action") == "no-op":
        return 78
    return 0


if __name__ == "__main__":
    sys.exit(main())
