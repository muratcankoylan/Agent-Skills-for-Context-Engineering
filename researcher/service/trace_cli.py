"""Explicit trace inspection and one-batch export. Never starts research work."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from .contracts import ServiceError
from .environment import read_env_file
from .trace_export import _prepare, export_payload, preflight_config
from .trace_events import export_events, project_events
from .tracing import MAX_EXPORT, TOOLS, TraceJournal, otlp_payload


def journal_at(state: Path, *, read_only=True) -> TraceJournal:
    directory = state.absolute() / "telemetry"
    if not directory.is_dir():
        raise ServiceError("TRACE_JOURNAL_NOT_FOUND")
    return TraceJournal(directory, initialize=False, read_only=read_only)


def export_pending(journal: TraceJournal, *, credential: str, project_id: str,
                   live=False, limit=MAX_EXPORT, transport=None, allow_default_project=False) -> dict:
    if live is not True:
        raise ServiceError("TRACE_EXPORT_LIVE_REQUIRED")
    rows = journal.rows(limit=limit, pending=True)
    if not rows:
        return {"schema": "trace-export-result/v1", "status": "empty", "attempted": False,
                "span_count": 0, "rejected_spans": 0, "warning": False, "error_code": None}
    payload = otlp_payload(rows)
    _prepare(payload, credential, project_id, allow_default_project=allow_default_project)
    project_events(payload)  # Validate both phases before claiming or networking.
    span_ids = [row["span_id"] for row in rows]
    journal.require_event_roots(span_ids)
    # A delivery intent is diagnostics only. It never releases a reservation,
    # restarts an effect, or establishes exactly-once delivery.
    attempt = journal.begin_export(span_ids)
    events = export_events(payload, credential=credential, project_id=project_id, transport=transport,
                           allow_default_project=allow_default_project)
    journal.record_event_export(attempt, events)
    traces = None
    if events["status"] in {"exported", "empty"}:
        traces = export_payload(payload, credential=credential, project_id=project_id, transport=transport,
                                allow_default_project=allow_default_project)
    # Two independent effects, never an atomic or exactly-once transaction. A
    # failed first phase cannot dispatch the second; either uncertainty remains
    # durably claimed even after restart. Historical v1 receipts are unchanged.
    result = {"schema": "trace-export-result/v2", "status": (traces or events)["status"],
              "attempted": events["attempted"] or bool(traces and traces["attempted"]),
              "span_count": len(rows), "events": events, "traces": traces}
    journal.finish_export(attempt, result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("tools", help="Inspect the fixed operation vocabulary; no dynamic tool loading")
    preflight = commands.add_parser("preflight", help="Check explicit export configuration without networking or opening state")
    preflight.add_argument("--env-file", type=Path, required=True)
    preflight.add_argument("--allow-default-project", action="store_true",
                           help="Approve the explicitly configured default Production project; never fills a blank")
    for name in ("status", "list", "deliveries", "preview", "export", "prune"):
        command = commands.add_parser(name)
        command.add_argument("--state", type=Path, required=True, help="Existing private service state directory")
        if name in {"list", "deliveries", "preview", "export"}:
            command.add_argument("--limit", type=int, default=MAX_EXPORT)
        if name in {"list", "deliveries"}:
            command.add_argument("--after", type=int, default=0)
        if name == "export":
            command.add_argument("--env-file", type=Path, required=True)
            command.add_argument("--live", action="store_true")
            command.add_argument("--allow-default-project", action="store_true",
                                 help="Approve the explicitly configured default Production project; never fills a blank")
        if name == "prune":
            command.add_argument("--older-than-days", type=int, required=True)
            command.add_argument("--apply", action="store_true")
    managed = commands.add_parser("managed-preview", help="Read and sanitize a known session's available trace snapshot")
    managed.add_argument("--session-state", type=Path, required=True)
    managed.add_argument("--env-file", type=Path, required=True)
    managed.add_argument("--live-read", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "tools":
            value = {"schema": "research-trace-tools/v1", "dynamic_dispatch": False,
                     "operations": [{"name": name, "category": category, "external_effect": external}
                                    for name, (category, external) in sorted(TOOLS.items())]}
        elif args.command == "preflight":
            keys = read_env_file(args.env_file)
            value = preflight_config(credential=keys.get("RAINDROP_WRITE_KEY", ""),
                                     project_id=keys.get("RAINDROP_PROJECT_ID", ""),
                                     allow_default_project=args.allow_default_project)
        elif args.command == "managed-preview":
            if not args.live_read:
                raise ServiceError("TRACE_MANAGED_READ_APPROVAL_REQUIRED")
            from .agents_runtime import SessionLedger
            from .managed_traces import collect_managed_traces
            from .openai_agents import AgentsClient
            ledger = SessionLedger(args.session_state)
            _, state = ledger.load()
            if not state.get("session_id"):
                raise ServiceError("MANAGED_SESSION_ID_UNAVAILABLE")
            keys = read_env_file(args.env_file)
            value = collect_managed_traces(AgentsClient(keys.get("OPENAI_API_KEY", "")), state["session_id"])
        else:
            if args.command == "export" and not args.live:
                raise ServiceError("TRACE_EXPORT_LIVE_REQUIRED")
            if args.command == "prune" and (not args.apply or not 1 <= args.older_than_days <= 3650):
                raise ServiceError("TRACE_RETENTION_APPROVAL_REQUIRED")
            journal = journal_at(args.state, read_only=args.command not in {"export", "prune"})
            if args.command == "status":
                value = journal.status()
            elif args.command == "list":
                value = {"schema": "research-trace-page/v1", "rows": journal.rows(limit=args.limit, after=args.after)}
            elif args.command == "deliveries":
                value = {"schema": "research-trace-deliveries/v1", "rows": journal.export_rows(limit=args.limit, after=args.after)}
            elif args.command == "preview":
                rows = journal.rows(limit=args.limit, pending=True)
                payload = otlp_payload(rows) if rows else None
                value = {"span_count": len(rows), "payload": payload,
                         "event_payload": project_events(payload) if payload else []}
            elif args.command == "export":
                keys = read_env_file(args.env_file)
                value = export_pending(journal, credential=keys.get("RAINDROP_WRITE_KEY", ""),
                    project_id=keys.get("RAINDROP_PROJECT_ID", ""), live=True, limit=args.limit,
                    allow_default_project=args.allow_default_project)
            else:
                if not args.apply or not 1 <= args.older_than_days <= 3650:
                    raise ServiceError("TRACE_RETENTION_APPROVAL_REQUIRED")
                removed = journal.prune_exported(before_ns=time.time_ns() - args.older_than_days * 86400 * 10**9)
                value = {"removed_exported_spans": removed, "execution_state_changed": False}
        print(json.dumps(value, sort_keys=True))
        return 0 if value.get("status") not in {"partial", "rejected", "unknown"} and value.get("local_ready", True) else 1
    except Exception as error:
        # Do not let a provider error body or a private path reach CLI output.
        code = error.code if isinstance(error, ServiceError) and str(error.code).startswith(("TRACE_", "MANAGED_", "ENV_")) else "TRACE_OPERATION_FAILED"
        print(json.dumps({"error": code}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
