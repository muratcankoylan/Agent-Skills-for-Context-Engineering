"""Durable single-session canary for the managed OpenAI Agents API.

The remote service owns model turns and compaction. This module owns the local
submission intent and recovery pointer. It deliberately does not translate a
session into a bounded ModelRequest: the public beta has no documented hard
per-session token/dollar cap. A timeout requests cancellation, not proof of stop.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import time

from researcher.scripts.artifact_store import _atomic_write_bytes
from researcher.scripts.schema_contract import canonicalize, parse_json_strict
from .contracts import ServiceError, digest
from .tracing import Tracer, annotate, current_span, traced

TERMINAL = {"completed", "failed", "cancelled", "invalid_output"}
PHASES = TERMINAL | {"prepared", "submitting", "running", "reconciliation_required"}
MAX_FILE_BYTES = 2_000_000


def _safe_file(path: Path, *, missing: bool = False):
    if missing and not path.exists() and not path.is_symlink():
        return
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
        or info.st_size > MAX_FILE_BYTES
    ):
        raise ServiceError("UNSAFE_MANAGED_STATE")


def _read(path: Path):
    _safe_file(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as source:
        raw = source.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ServiceError("MANAGED_STATE_SIZE_LIMIT")
    return parse_json_strict(raw.decode("utf-8"))


def _write(path: Path, value):
    _safe_file(path, missing=True)
    _atomic_write_bytes(path, canonicalize(value))


class SessionLedger:
    """One reviewed packet and at most one create attempt per private directory."""

    def __init__(self, directory: Path):
        self.directory = directory.absolute()
        if (
            not self.directory.is_dir()
            or self.directory.resolve() != self.directory
            or self.directory.stat().st_uid != os.getuid()
            or stat.S_IMODE(self.directory.stat().st_mode) != 0o700
        ):
            raise ServiceError("PRIVATE_STATE_DIRECTORY_REQUIRED")
        self.packet_path = self.directory / "packet.json"
        self.state_path = self.directory / "session.json"

    @contextlib.contextmanager
    def lock(self):
        path = self.directory / "session.lock"
        _safe_file(path, missing=True)
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ServiceError("MANAGED_WORKER_ALREADY_RUNNING") from None
            yield
        finally:
            os.close(fd)

    @classmethod
    def prepare(cls, directory: Path, packet: dict):
        # No existence-based resume during creation. The caller must use the
        # saved packet for later operations, never silently replace it.
        _validate_packet(packet)
        directory.mkdir(mode=0o700, parents=False, exist_ok=False)
        ledger = cls(directory)
        with ledger.lock():
            _write(ledger.packet_path, packet)
            state = {
                "schema": "managed-session-state/v1",
                "manifest_digest": digest(packet),
                "phase": "prepared",
                "session_id": None,
                "submitted_at": None,
                "deadline_at": None,
                "last_clock": 0,
                "revision": 0,
                "cancel": None,
                "observation": None,
                "reason": None,
                "result_digest": None,
            }
            ledger.save(state)
        return ledger

    def load(self):
        packet, envelope = _read(self.packet_path), _read(self.state_path)
        if (
            not isinstance(envelope, dict)
            or set(envelope) != {"record", "digest"}
            or digest(envelope["record"]) != envelope["digest"]
        ):
            raise ServiceError("MANAGED_STATE_DIGEST_MISMATCH")
        state = envelope["record"]
        if (
            state.get("schema") != "managed-session-state/v1"
            or state.get("manifest_digest") != digest(packet)
            or state.get("phase") not in PHASES
            or type(state.get("revision")) is not int
            or type(state.get("last_clock")) is not int
        ):
            raise ServiceError("MANAGED_MANIFEST_MISMATCH")
        if state["phase"] == "completed" and digest(
            _read(self.directory / "result.json")
        ) != state.get("result_digest"):
            raise ServiceError("MANAGED_RESULT_DIGEST_MISMATCH")
        return packet, state

    def save(self, state):
        state["revision"] += 1
        _write(self.state_path, {"record": state, "digest": digest(state)})

    def status(self):
        _, state = self.load()
        return {
            key: state[key]
            for key in (
                "phase",
                "session_id",
                "revision",
                "submitted_at",
                "deadline_at",
                "reason",
                "cancel",
                "observation",
            )
        } | {
            "production_ready": False,
            "hard_session_cost_cap": False,
            "remote_stop_confirmed": state["phase"] in TERMINAL,
            "result_digest": state.get("result_digest"),
        }


def prepare_packet(
    root: Path,
    *,
    model: str,
    query: str,
    skills: list[str],
    evidence: list,
    max_subagents: int = 0,
    fixture: bool = False,
    retrieval_context: dict | None = None,
) -> dict:
    from .agents_context import compile_request
    from .knowledge import retrieve_corpus
    from .workflow import git_head, implementation

    corpus = retrieve_corpus(root.resolve(), query, skills, 65536)
    request = compile_request(
        model=model,
        query=query,
        corpus=corpus,
        evidence=evidence,
        max_subagents=max_subagents,
        retrieval_context=retrieval_context,
    )
    packet = {
        "schema": "managed-research-packet/v1",
        "request": request,
        "corpus": corpus,
        "model": model,
        "query": query,
        "max_subagents": max_subagents,
        "evidence": evidence,
        "baseline_commit": git_head(root),
        "implementation_digest": implementation(root),
        "fixture": fixture,
    }
    if retrieval_context is not None:
        if retrieval_context["fixture"] != fixture:
            raise ServiceError("RETRIEVAL_HANDOFF_FIXTURE_MISMATCH")
        packet["retrieval_context"] = retrieval_context
    return packet


def _validate_packet(packet):
    from .agents_context import compile_request

    if (
        not isinstance(packet, dict)
        or packet.get("schema") != "managed-research-packet/v1"
        or type(packet.get("fixture")) is not bool
    ):
        raise ServiceError("MANAGED_INVALID_PACKET")
    expected = compile_request(
        model=packet["model"],
        query=packet["query"],
        corpus=packet["corpus"],
        evidence=packet["evidence"],
        max_subagents=packet["max_subagents"],
        retrieval_context=packet.get("retrieval_context"),
    )
    if ("retrieval_context" in packet
            and packet["retrieval_context"]["fixture"] != packet["fixture"]):
        raise ServiceError("RETRIEVAL_HANDOFF_FIXTURE_MISMATCH")
    if canonicalize(packet["request"]) != canonicalize(expected):
        raise ServiceError("MANAGED_REQUEST_DRIFT")


def _effective_session(session, packet):
    requested = packet["request"]["agent"]
    if not isinstance(session, dict) or not isinstance(session.get("agent"), dict):
        raise ServiceError("MANAGED_EFFECTIVE_CONFIGURATION_CHANGED")
    actual = session["agent"]
    if not isinstance(actual.get("text"), dict) or not isinstance(
        actual.get("multi_agent"), dict
    ):
        raise ServiceError("MANAGED_EFFECTIVE_CONFIGURATION_CHANGED")
    # Compare the policy projection as canonical JSON, not Python equality:
    # enabled=0 and JSON-schema additionalProperties=0 must not equal false.
    expected = {
        "object": "agent.session",
        "environment": {"type": "none"},
        "vault_ids": [],
        "model": requested["model"],
        "instructions": requested["instructions"],
        "tools": [{"type": "programmatic_tool_calling", "enabled": False}],
        "format": requested["text"]["format"],
        "enabled": requested["multi_agent"]["enabled"],
    }
    observed = {
        "object": session.get("object"),
        "environment": session.get("environment"),
        "vault_ids": session.get("vault_ids"),
        "model": actual.get("model"),
        "instructions": actual.get("instructions"),
        "tools": actual.get("tools"),
        "format": actual["text"].get("format"),
        "enabled": actual["multi_agent"].get("enabled"),
    }
    try:
        if canonicalize(observed) != canonicalize(expected):
            raise ServiceError("MANAGED_EFFECTIVE_CONFIGURATION_CHANGED")
    except (TypeError, ValueError, RecursionError):
        raise ServiceError("MANAGED_EFFECTIVE_CONFIGURATION_CHANGED") from None
    if requested["multi_agent"]["enabled"] and (
        type(actual["multi_agent"].get("max_concurrent_subagents")) is not int
        or actual["multi_agent"].get("max_concurrent_subagents")
        != requested["multi_agent"]["max_concurrent_subagents"]
    ):
        raise ServiceError("MANAGED_SUBAGENT_LIMIT_CHANGED")


def _pages(fetch):
    rows, seen_ids, seen_cursors, after = [], set(), set(), None
    # This ceiling is for observation, not a claim that the provider stopped.
    for _ in range(10):
        page = fetch(after)
        if (
            not isinstance(page, dict)
            or not isinstance(page.get("data"), list)
            or type(page.get("has_more")) is not bool
        ):
            raise ServiceError("MANAGED_INVALID_PAGE")
        for row in page["data"]:
            if not isinstance(row, dict):
                raise ServiceError("MANAGED_INVALID_PAGE")
            identity = row.get("id")
            if identity is not None:
                if not isinstance(identity, str) or identity in seen_ids:
                    raise ServiceError("MANAGED_DUPLICATE_RECORD")
                seen_ids.add(identity)
            rows.append(row)
        if len(rows) > 1000:
            raise ServiceError("MANAGED_HISTORY_LIMIT")
        if not page["has_more"]:
            return rows
        after = page.get("last_id")
        if (
            not isinstance(after, str)
            or not after
            or after in seen_cursors
            or not page["data"]
            or after != page["data"][-1].get("id")
        ):
            raise ServiceError("MANAGED_INVALID_CURSOR")
        seen_cursors.add(after)
    raise ServiceError("MANAGED_HISTORY_LIMIT")


def _usage(value):
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ServiceError("MANAGED_INVALID_USAGE")
    counts = {
        key: value.get(key) for key in ("input_tokens", "output_tokens", "total_tokens")
    }
    if (
        any(type(n) is not int or n < 0 for n in counts.values())
        or counts["total_tokens"] != counts["input_tokens"] + counts["output_tokens"]
    ):
        raise ServiceError("MANAGED_INVALID_USAGE")
    return counts


class ManagedResearch:
    def __init__(self, ledger: SessionLedger, client, *, clock=time.time):
        self.ledger, self.client, self.clock = ledger, client, clock
        self.tracer = Tracer.at(ledger.directory)

    def _clock(self, state):
        now = int(self.clock())
        if now < state["last_clock"]:
            raise ServiceError("CLOCK_MOVED_BACKWARDS")
        state["last_clock"] = now
        return now

    @traced("managed.submit")
    def submit(
        self, *, live: bool, acknowledge_cost_risk: bool, max_seconds: int = 120
    ):
        if not live or not acknowledge_cost_risk:
            raise ServiceError("MANAGED_LIVE_COST_ACK_REQUIRED")
        from .openai_agents import AgentsClient, _isolated
        if isinstance(self.client, AgentsClient) and self.client._transport is _isolated:
            raise ServiceError("MANAGED_SUBMISSION_RETIRED_USE_CODEX_SDK")
        if type(max_seconds) is not int or not 10 <= max_seconds <= 600:
            raise ServiceError("INVALID_MANAGED_DEADLINE")
        with self.ledger.lock():
            packet, state = self.ledger.load()
            _validate_packet(packet)
            if packet.get("fixture"):
                raise ServiceError("FIXTURE_CANNOT_SUBMIT")
            if state["phase"] != "prepared":
                # Even a missing session ID never authorizes a second POST.
                raise ServiceError("MANAGED_CREATE_ALREADY_ATTEMPTED")
            now = self._clock(state)
            context = packet.get("retrieval_context")
            if context is not None and (
                now < context["verified_at"]
                or now - context["window_end"] > context["maximum_age_seconds"]
            ):
                raise ServiceError("RETRIEVAL_HANDOFF_STALE")
            state.update(
                phase="submitting", submitted_at=now, deadline_at=now + max_seconds
            )
            self.ledger.save(state)
            try:
                session = self.client.create(packet["request"])
                if not isinstance(session.get("id"), str) or not re.fullmatch(
                    r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", session["id"]
                ):
                    raise ServiceError("MANAGED_INVALID_SESSION_ID")
                state.update(phase="running", session_id=session["id"])
                current_span().reference("session_ref", session["id"])
                self.ledger.save(state)
                _effective_session(session, packet)
            except (Exception, KeyboardInterrupt) as exc:
                known_id = getattr(exc, "session_id", None)
                if isinstance(known_id, str) and re.fullmatch(
                    r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", known_id
                ):
                    state["session_id"] = known_id
                state.update(
                    phase="reconciliation_required", reason="CREATE_OUTCOME_UNKNOWN"
                )
                self.ledger.save(state)
                if state["session_id"]:
                    state["reason"] = "CREATE_RESPONSE_REQUIRES_RECONCILIATION"
                    self._cancel(state)
                raise ServiceError("MANAGED_CREATE_RECONCILIATION_REQUIRED") from None
        return self.ledger.status()

    @traced("managed.watch")
    def watch(
        self, *, max_polls=24, poll_seconds=5, sleep=time.sleep, progress=lambda _: None
    ):
        if (
            type(max_polls) is not int
            or not 1 <= max_polls <= 120
            or type(poll_seconds) is not int
            or not 5 <= poll_seconds <= 60
        ):
            raise ServiceError("INVALID_MANAGED_POLL_LIMIT")
        try:
            for number in range(max_polls):
                annotate(poll=number + 1)
                result = self.observe()
                progress(
                    {
                        "event": "managed_progress",
                        "poll": number + 1,
                        "phase": result["phase"],
                        "session_id": result["session_id"],
                    }
                )
                if result["phase"] in TERMINAL:
                    return result
                if number + 1 < max_polls:
                    sleep(poll_seconds)
            self.cancel()
            return self.observe()
        except (Exception, KeyboardInterrupt):
            # A watch is a supervision promise. Even a failed read must not
            # abandon it without attempting to stop the known remote work.
            try:
                self.cancel()
            except Exception:
                pass  # The durable intent / known ID remains the recovery path.
            raise ServiceError("MANAGED_WATCH_FAILED_CHECK_REMOTE_STATE") from None

    @traced("managed.cancel")
    def cancel(self):
        with self.ledger.lock():
            _, state = self.ledger.load()
            # Stopping known remote work must remain possible after clock
            # rollback. Admission and observation still fail on rollback.
            self._cancel(state)
        return self.ledger.status()

    def _cancel(self, state):
        if state["phase"] in TERMINAL:
            return
        if not state["session_id"]:
            raise ServiceError("MANAGED_SESSION_ID_UNAVAILABLE")
        if state["cancel"] is not None:
            return  # Read-only observation resolves unknown cancellation.
        key = "cancel-" + state["manifest_digest"].split(":")[-1]
        state["cancel"] = {"key": key, "state": "intent"}
        self.ledger.save(state)
        try:
            self.client.cancel(state["session_id"], key)
            state["cancel"]["state"] = "acknowledged_not_confirmed"
        except Exception:
            state["cancel"]["state"] = "outcome_unknown"
        self.ledger.save(state)

    @traced("managed.observe")
    def observe(self):
        with self.ledger.lock():
            packet, state = self.ledger.load()
            if state["phase"] in TERMINAL:
                return self.ledger.status()
            if not state["session_id"]:
                if state["phase"] == "submitting":
                    state.update(
                        phase="reconciliation_required", reason="CREATE_OUTCOME_UNKNOWN"
                    )
                    self.ledger.save(state)
                raise ServiceError("MANAGED_SESSION_ID_UNAVAILABLE")
            now = self._clock(state)
            if now >= state["deadline_at"]:
                self._cancel(state)
            identity = state["session_id"]
            current_span().reference("session_ref", identity)
            try:
                session = self.client.retrieve(identity)
                if not isinstance(session, dict) or session.get("id") != identity:
                    raise ServiceError("MANAGED_SESSION_ID_MISMATCH")
                _effective_session(session, packet)
            except Exception as error:
                # A transport outage may be retried read-only, but a definitive
                # identity/policy mismatch must stop known work even outside watch.
                if (
                    not isinstance(error, ServiceError)
                    and getattr(error, "code", None) != "SESSION_ID_MISMATCH"
                ):
                    raise
                state.update(
                    phase="reconciliation_required",
                    reason="OBSERVED_SESSION_POLICY_MISMATCH",
                )
                self.ledger.save(state)
                self._cancel(state)
                raise
            turns = _pages(lambda after: self.client.turns(identity, after=after))
            if any(row.get("session_id") != identity for row in turns):
                raise ServiceError("MANAGED_TURN_SESSION_MISMATCH")
            allowed = {
                "queued",
                "in_progress",
                "waiting",
                "completed",
                "failed",
                "cancelled",
            }
            if any(row.get("status") not in allowed for row in turns):
                raise ServiceError("MANAGED_INVALID_TURN")
            roots = [row for row in turns if row.get("subagent_id") is None]
            state["observation"] = {
                "session_status": session["status"],
                "root_turns": len(roots),
                "subagent_turns": len(turns) - len(roots),
                "usage": _usage(session.get("usage")),
                "usage_is_final_bill": False,
                "turns": [
                    {
                        "id": row["id"],
                        "status": row["status"],
                        "subagent_id": row.get("subagent_id"),
                        "usage": _usage(row.get("usage")),
                    }
                    for row in turns
                ],
            }
            if (
                len(roots) > 1
                or session.get("required_actions")
                or session["status"] == "requires_action"
            ):
                state.update(
                    phase="reconciliation_required", reason="UNEXPECTED_REMOTE_WORK"
                )
                self._cancel(state)
            elif session["status"] == "failed":
                if roots and all(
                    row["status"] in {"completed", "failed", "cancelled"}
                    for row in turns
                ):
                    state.update(phase="failed", reason="REMOTE_SESSION_FAILED")
                else:
                    state.update(
                        phase="reconciliation_required",
                        reason="REMOTE_FAILURE_STOP_UNCONFIRMED",
                    )
                    self._cancel(state)
            elif (
                session["status"] == "idle"
                and roots
                and all(
                    row["status"] in {"completed", "failed", "cancelled"}
                    for row in turns
                )
            ):
                root = roots[0]
                if root["status"] != "completed":
                    state.update(
                        phase=root["status"],
                        reason="REMOTE_TURN_" + root["status"].upper(),
                    )
                elif any(row["status"] != "completed" for row in turns):
                    state.update(phase="failed", reason="SUBAGENT_TURN_FAILED")
                else:
                    self._result(packet, state, root["id"])
            self.ledger.save(state)
        return self.ledger.status()

    def _result(self, packet, state, turn_id):
        from .agents_context import validate_result

        rows = _pages(
            lambda after: self.client.items(state["session_id"], turn_id, after=after)
        )
        messages = [
            row
            for row in rows
            if row.get("turn_id") == turn_id
            and row.get("type") == "message"
            and row.get("role") == "assistant"
            and row.get("phase") == "final_answer"
        ]
        try:
            if len(messages) != 1 or messages[0].get("status") != "completed":
                raise ServiceError("MANAGED_FINAL_ANSWER_MISSING")
            content = messages[0].get("content")
            if (
                not isinstance(content, list)
                or not content
                or any(
                    part.get("type") != "output_text"
                    or not isinstance(part.get("text"), str)
                    for part in content
                )
            ):
                raise ServiceError("MANAGED_INVALID_FINAL_CONTENT")
            output = validate_result(
                "".join(part["text"] for part in content),
                packet["corpus"],
                packet["evidence"],
            )
            # Persist only the validated final artifact, not reasoning items.
            result = {
                "schema": "managed-research-result/v1",
                "manifest_digest": state["manifest_digest"],
                "session_id": state["session_id"],
                "turn_id": turn_id,
                "result": output,
                "production_ready": False,
                "independent_evaluation": "not_run",
            }
            _write(self.ledger.directory / "result.json", result)
            state.update(
                phase="completed",
                reason="AWAITING_INDEPENDENT_EVALUATION",
                result_digest=digest(result),
            )
        except (ServiceError, ValueError, TypeError, AttributeError):
            state.update(phase="invalid_output", reason="MANAGED_OUTPUT_REJECTED")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["prepare", "status", "run", "submit", "observe", "watch", "cancel"],
    )
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--query")
    parser.add_argument("--skill", action="append", default=[])
    parser.add_argument("--max-subagents", type=int, default=0)
    parser.add_argument("--credential-env", default="OPENAI_API_KEY")
    parser.add_argument("--env-file", type=Path,
                        help="Explicit private env file; blanks never fall back to process credentials")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--acknowledge-no-hard-session-cost-cap", action="store_true")
    parser.add_argument("--max-seconds", type=int, default=120)
    parser.add_argument("--max-polls", type=int, default=24)
    parser.add_argument("--poll-seconds", type=int, default=5)
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        if args.command == "prepare":
            if not args.evidence or not args.query or not args.model or not args.skill:
                raise ServiceError("MANAGED_INPUTS_REQUIRED")
            packet = prepare_packet(
                args.repo,
                model=args.model,
                query=args.query,
                skills=args.skill,
                evidence=_read(args.evidence),
                max_subagents=args.max_subagents,
            )
            ledger = SessionLedger.prepare(args.state.absolute(), packet)
        else:
            ledger = SessionLedger(args.state)
        if args.command in {"prepare", "status"}:
            result = ledger.status()
        else:
            from .openai_agents import AgentsClient

            if args.env_file is not None:
                from .environment import credential_reader, read_env_file
                credential = credential_reader(read_env_file(args.env_file),
                                               [args.credential_env])(args.credential_env)
            else:
                credential = os.environ.get(args.credential_env, "")
            if not credential:
                raise ServiceError("OPENAI_API_KEY_UNAVAILABLE")
            if args.command in {"submit", "run"}:
                from .workflow import implementation

                packet, _ = ledger.load()
                if packet["implementation_digest"] != implementation(
                    args.repo.resolve()
                ):
                    raise ServiceError("MANAGED_IMPLEMENTATION_CHANGED")
            runtime = ManagedResearch(ledger, AgentsClient(credential))
            if args.command in {"submit", "run"}:
                result = runtime.submit(
                    live=args.live,
                    acknowledge_cost_risk=args.acknowledge_no_hard_session_cost_cap,
                    max_seconds=args.max_seconds,
                )
                if args.command == "run":
                    result = runtime.watch(
                        max_polls=args.max_polls,
                        poll_seconds=args.poll_seconds,
                        progress=lambda row: print(json.dumps(row), flush=True),
                    )
            elif args.command == "observe":
                result = runtime.observe()
            elif args.command == "watch":
                result = runtime.watch(
                    max_polls=args.max_polls,
                    poll_seconds=args.poll_seconds,
                    progress=lambda row: print(json.dumps(row), flush=True),
                )
            else:
                result = runtime.cancel()
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        print(
            json.dumps({"error": getattr(exc, "code", "MANAGED_COMMAND_FAILED")}),
            flush=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
