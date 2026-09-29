"""Repo-owned research -> critique -> frozen skill delta -> paired review loop.

No generated code is executed. All model and GitHub effects pass through the
durable reservation boundary. The current endpoint is a draft review packet,
not accepted knowledge, a scientific result or a production deployment.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
from typing import Callable
from urllib.parse import urlsplit

from researcher.scripts.artifact_store import (
    ArtifactAuthority, CandidateFreezer, EditableSurfacePolicy, LocalContentAddressedStore,
    _atomic_write_bytes, snapshot_tree,
)
from researcher.scripts.research_evidence import LocalResearchEvidenceStore
from researcher.scripts.build_inventory import markdown_level_two_sections
from researcher.scripts.schema_contract import canonicalize, new_typed_id, parse_json_strict, sha256_bytes
from researcher.scripts.skill_frontmatter import parse_frontmatter, split_frontmatter
from researcher.scripts.source_connectors import (
    ArxivAtomAdapter, RSSAtomAdapter, ConnectorError, LimitExceededError, MalformedResponseError,
    Limits, QuerySpec, RetryAfter, replay_discovery,
)
from .contracts import PAID_SOURCES, ServiceError, digest, model_reservation, parse_output
from .knowledge import retrieve_corpus, validate_citations
from .prompts import PROMPT_VERSION, instructions
from .providers import ModelRequest, ProviderError, complete
from .model_worker import bounded_complete
from .store import Store
from .shutdown import check_stop
from .tracing import Tracer, annotate, current_span, instrument, traced

FEEDS = {
    "deepmind": "https://deepmind.google/blog/rss.xml",
    "huggingface": "https://huggingface.co/blog/feed.xml",
    "microsoft_research": "https://www.microsoft.com/en-us/research/feed/",
}


def _plain(value):
    return json.loads(json.dumps(value, allow_nan=False))


def implementation(root: Path) -> str:
    files = sorted((root / "researcher/service").glob("*.py"))
    files += sorted((root / "researcher/scripts").glob("*.py"))
    files += [root / "requirements-dev.txt", root / "researcher/service/requirements-mcp.txt"]
    if not files:
        raise ServiceError("IMPLEMENTATION_MISSING")
    identity = {}
    for path in files:
        if path.is_symlink() or path.resolve() != path or not path.is_file():
            raise ServiceError("UNSAFE_IMPLEMENTATION_PATH")
        identity[path.relative_to(root).as_posix()] = sha256_bytes(path.read_bytes())
    dependencies = {}
    for package in ("jsonschema", "PyYAML", "skills-ref", "mcp", "httpx"):
        try:
            dependencies[package] = version(package)
        except PackageNotFoundError:
            dependencies[package] = "not-installed"
    return digest({"source_files": identity, "python_version": list(sys.version_info[:3]),
                   "installed_versions": dependencies})


def git_head(root: Path) -> str:
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                            capture_output=True, text=True, timeout=10, check=False)
    head = result.stdout.strip()
    if result.returncode or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ServiceError("REPOSITORY_IDENTITY_UNAVAILABLE")
    return head


def make_manifest(root: Path, config: dict, schedule: dict, *, fixture: bool = False,
                  window_end: int | None = None) -> dict:
    if schedule.get("mode", "research") == "retrieve":
        if window_end is None:
            current = int(time.time())
            window_end = current // 86400 * 86400
            if current - window_end < 30:
                raise ServiceError("RETRIEVAL_WINDOW_NOT_READY")
        if type(window_end) is not int or window_end < 86400 or window_end % 86400:
            raise ServiceError("INVALID_RETRIEVAL_WINDOW")
        return {"schema": "retrieval-work/v1", "config_digest": digest(config),
                "implementation_digest": implementation(root), "baseline_commit": git_head(root),
                "schedule": schedule, "fixture": fixture,
                "window_start": window_end - 86400, "window_end": window_end,
                "retrieval_policy": "daily-observation-v1"}
    corpus = retrieve_corpus(root, schedule["query"], schedule["skills"], config["limits"]["context_bytes"])
    return {"schema": "research-work/v1", "config_digest": digest(config),
            "implementation_digest": implementation(root), "baseline_commit": git_head(root),
            "corpus_digest": digest(corpus), "schedule": schedule, "fixture": fixture,
            "prompt_version": PROMPT_VERSION}


def admit_due(store: Store, root: Path, *, now: int | None = None) -> list[str]:
    current = int(time.time()) if now is None else now
    if type(current) is not int or current < 0:
        raise ServiceError("INVALID_CLOCK")
    store.observe_clock(current)
    admitted = []
    for schedule in store.config["schedules"]:
        slot = current // schedule["interval_seconds"] * schedule["interval_seconds"]
        retrieval = schedule.get("mode", "research") == "retrieve"
        # Preserve exact completed UTC windows while allowing provider ingestion lag.
        # No request is made at midnight with an end_time in the provider's present.
        if retrieval and current - slot < 30:
            continue
        job = f"{schedule['id']}:{slot}"
        manifest = make_manifest(root, store.config, schedule,
                                 window_end=slot if retrieval else None)
        if store.enqueue(job, manifest):
            admitted.append(job)
    return admitted


def _credential(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ServiceError("CREDENTIAL_UNAVAILABLE")
    return value


SOURCE_LIMITS = Limits(max_items=6, max_requests=1, max_pages=1, max_bytes=500_000,
                       max_seconds=30, max_redirects=0)


def source_adapter(name: str, **kwargs):
    if name == "arxiv":
        return ArxivAtomAdapter(search_scope="title_abstract", sort_by="relevance",
                                include_provenance=True, **kwargs)
    elif name in FEEDS:
        return RSSAtomAdapter(FEEDS[name], allowed_hosts=(urlsplit(FEEDS[name]).hostname,),
                              include_provenance=True, **kwargs)
    else:
        raise ServiceError("UNREGISTERED_SOURCE")


def normalized_source(name: str, result) -> dict:
    if isinstance(result, RetryAfter):
        return {"source": name, "state": "rate_limited", "evidence": [],
                "retry_after_seconds": result.retry_after_seconds}
    evidence = []
    for item in result.items:
        text = item.title + "\n\n" + item.summary
        evidence.append({"id": item.identity, "source": name, "url": item.url,
                         "text": text, "sha256": sha256_bytes(text.encode("utf-8")),
                         "evidence_scope": "discovery_summary", "metadata": _plain(item.metadata)})
    return {"source": name, "state": "observed", "evidence": evidence, "next_cursor": result.next_cursor}


@instrument("source.retrieve")
def collect_source(name: str, query: str, directory: Path) -> dict:
    annotate(provider=name, transport="https")
    captures = []
    evidence_store = LocalResearchEvidenceStore(directory)
    def capture(observation, body):
        result = evidence_store.capture(observation, body)
        captures.append(result.as_record())
        return result
    # One HTTP request per lane. Company feeds are a window, not semantic search.
    adapter = source_adapter(name, capture_sink=capture)
    result = adapter.discover(QuerySpec(query if name == "arxiv" else ""), SOURCE_LIMITS)
    annotate(source_requests=result.receipt.request_count, output_bytes=result.receipt.total_bytes,
             items=result.receipt.item_count, outcome="completed")
    return {**normalized_source(name, result), "captures": captures, "receipt": _plain(asdict(result.receipt))}


@instrument("source.verify")
def verify_source(name: str, query: str, lane: dict, directory: Path):
    evidence_store = LocalResearchEvidenceStore(directory, read_only=True)
    captures = [(evidence_store.read_observation(item), evidence_store.read_body(item)) for item in lane["captures"]]
    replayed = replay_discovery(lambda **kwargs: source_adapter(name, **kwargs), captures,
                               QuerySpec(query if name == "arxiv" else ""), SOURCE_LIMITS)
    expected = normalized_source(name, replayed)
    if {key: value for key, value in lane.items() if key not in {"captures", "receipt"}} != expected:
        raise ServiceError("SOURCE_REPLAY_MISMATCH")
    for key in ("request_count", "total_bytes", "item_count"):
        if lane["receipt"][key] != asdict(replayed.receipt)[key]:
            raise ServiceError("SOURCE_RECEIPT_MISMATCH")


def apply_edit(proposal: dict, corpus: dict, supported: list[str]) -> tuple[str, str]:
    documents = {item["path"]: item for item in corpus["documents"]}
    if proposal["path"] not in documents or not set(proposal["claim_ids"]) <= set(supported):
        raise ServiceError("UNSUPPORTED_EDIT")
    original = documents[proposal["path"]]["text"]
    if original.count(proposal["old_text"]) != 1:
        raise ServiceError("EDIT_ANCHOR_NOT_UNIQUE")
    changed = original.replace(proposal["old_text"], proposal["new_text"], 1)
    if changed == original or len(changed.encode("utf-8")) > 131072:
        raise ServiceError("INVALID_EDIT_SIZE")
    before_meta, before_body = split_frontmatter(original)
    after_meta, after_body = split_frontmatter(changed)
    parsed, problems = parse_frontmatter(changed)
    if before_meta != after_meta or problems or parsed.get("name") != proposal["path"].split("/")[1]:
        raise ServiceError("FRONTMATTER_CHANGED")
    def sections(body):
        result, malformed = markdown_level_two_sections(body)
        if malformed or any(len(values) != 1 for values in result.values()):
            raise ServiceError("DUPLICATE_OR_MALFORMED_SECTION")
        return {name: values[0] for name, values in result.items()}
    before, after = sections(before_body), sections(after_body)
    if list(before) != list(after):
        raise ServiceError("SKILL_SECTION_STRUCTURE_CHANGED")
    def raw_sections(text):
        # Conservative raw-span guard in addition to rendered Markdown checks.
        # Comments, whitespace and fenced text still enter the model's context.
        headings = list(re.finditer(r"(?m)^## [^\r\n]+\r?$", text))
        if len({m.group(0) for m in headings}) != len(headings):
            raise ServiceError("DUPLICATE_OR_MALFORMED_SECTION")
        return {m.group(0).removeprefix("## ").rstrip("\r"): text[m.start():headings[i+1].start() if i+1 < len(headings) else len(text)]
                for i, m in enumerate(headings)}
    raw_before, raw_after = raw_sections(original), raw_sections(changed)
    for locked in ("When to Activate", "Integration"):
        if (locked not in before or before[locked] != after[locked]
                or raw_before.get(locked) != raw_after.get(locked)):
            raise ServiceError("LOCKED_SKILL_SECTION_CHANGED")
    return original, changed


class Workflow:
    def __init__(self, store: Store, root: Path, *, live: bool = False,
                 model: Callable = complete, source: Callable = collect_source,
                 credential: Callable[[str], str] = _credential,
                 retrieval_source: Callable | None = None,
                 retrieval_verify: Callable | None = None,
                 primary_reader: Callable | None = None,
                 primary_replayer: Callable | None = None,
                 primary_wait: Callable[[float], None] = time.sleep):
        self.store, self.root, self.live = store, root.resolve(), live
        self.model, self.source, self.credential = model, source, credential
        self.retrieval_source, self.retrieval_verify = retrieval_source, retrieval_verify
        self.primary_reader, self.primary_replayer = primary_reader, primary_replayer
        self.primary_wait = primary_wait
        self.tracer = Tracer.at(store.directory)

    @traced("workflow.effect")
    def effect(self, job: str, name: str, inputs: dict, call: Callable,
               *, _retrieval_failure_isolation: bool = False, **reservation) -> dict | None:
        check_stop()
        current_span().reference("operation_ref", job + ":" + name)
        annotate(model_calls=reservation.get("model_calls", 0),
                 source_requests=reservation.get("source_requests", 0),
                 reserved_microusd=reservation.get("micros", 0))
        saved = self.store.reserve(job, name, inputs, **reservation)
        if saved is not None:
            annotate(outcome="replayed", replayed=True)
            return saved
        stopped = threading.Event()
        started = time.monotonic()
        def progress():
            while not stopped.wait(5):
                print(json.dumps({"event": "effect_waiting", "effect": name,
                                  "job_digest": digest(job),
                                  "elapsed_seconds": int(time.monotonic() - started)}), flush=True)
        observer = threading.Thread(target=progress, daemon=True)
        observer.start()
        print(json.dumps({"event": "effect_started", "effect": name,
                          "job_digest": digest(job)}), flush=True)
        try:
            result = call()
            self.store.complete_effect(job, name, result)
            annotate(outcome="completed")
            return result
        except Exception as exc:
            code = getattr(exc, "code", "DEPENDENCY_FAILURE")
            if not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9_]{1,100}", code):
                code = "DEPENDENCY_FAILURE"
            local_spacing = isinstance(exc, ServiceError) and code == "SOURCE_RATE_LIMIT"
            remote_failure = (isinstance(exc, (LimitExceededError, MalformedResponseError))
                              or isinstance(exc, ConnectorError) and code in {
                                  "HTTP_STATUS", "TIME_LIMIT", "TRANSPORT_FAILURE", "DNS_FAILURE", "DNS_CAPACITY"})
            if _retrieval_failure_isolation and (local_spacing or remote_failure):
                annotate(outcome="failed", ambiguous=not local_spacing)
                self.store.record_retrieval_failure(job, name, inputs, code,
                                                    ambiguous=not local_spacing)
                return None
            self.store.fail_effect(job, name, code, ambiguous=getattr(exc, "ambiguous", True))
            raise ServiceError(code) from None
        finally:
            stopped.set()
            observer.join(timeout=1)

    @traced("model.call")
    def ask(self, job: str, role: str, data: dict, *, suffix: str = "") -> dict:
        config = self.store.config
        route, limits = config["models"][role], config["limits"]
        annotate(provider=route["provider"], role=role, fixture=not self.live)
        current_span().reference("model_ref", route["model"])
        prompt = canonicalize(data).decode("utf-8")
        system = instructions(role)
        if len(prompt.encode("utf-8")) > limits["context_bytes"] + 65536:
            raise ServiceError("MODEL_INPUT_LIMIT")
        tokens, micros = model_reservation(config, role, len((prompt + system).encode("utf-8")))
        annotate(input_bytes=len((prompt + system).encode("utf-8")), reserved_microusd=micros)
        request = ModelRequest(route["provider"], route["model"], system, prompt,
                               limits["max_output_tokens"], limits["timeout_seconds"])
        inputs = {"request": asdict(request), "role": role, "prompt_version": PROMPT_VERSION,
                  "config_digest": digest(config)}
        saved = self.store.completed_effect(job, "model-" + role + suffix, inputs)
        if saved is not None:
            annotate(outcome="replayed", replayed=True)
            return parse_output(saved["response"]["text"], role)
        if self.model is complete:
            raise ServiceError("NATIVE_AGENT_EXECUTION_RETIRED_USE_CODEX_ORGANIZATION")
        # Resolve before creating an intent so missing credentials do not become
        # ambiguous effects. The value never enters inputs or receipts.
        credential = self.credential(route["credential_env"])
        def call():
            result = (bounded_complete if self.model is complete else self.model)(request, credential=credential)
            pending = [result.text]
            try:
                pending.append(parse_json_strict(result.text))
            except (ValueError, TypeError, RecursionError):
                pass  # Invalid JSON is retained as a completed billable failure.
            reflected = False
            while pending:
                value = pending.pop()
                if isinstance(value, dict):
                    pending.extend(value.keys())
                    pending.extend(value.values())
                elif isinstance(value, list):
                    pending.extend(value)
                elif isinstance(value, str) and credential in value:
                    reflected = True
                    break
            if reflected:
                raise ProviderError("SECRET_IN_MODEL_OUTPUT", "Model output contained a credential.")
            if result.input_tokens > tokens or result.output_tokens > limits["max_output_tokens"]:
                raise ProviderError("USAGE_EXCEEDS_RESERVATION", "Provider usage exceeded its reservation.")
            return {"response": asdict(result), "role": role, "request_digest": digest(inputs)}
        record = self.effect(job, "model-" + role + suffix, inputs, call, model_calls=1, micros=micros)
        annotate(input_tokens=record["response"]["input_tokens"],
                 output_tokens=record["response"]["output_tokens"], usage_known=True,
                 output_bytes=len(record["response"]["text"].encode("utf-8")), outcome="completed")
        # Save a completed billable response even if its semantic JSON is invalid.
        return parse_output(record["response"]["text"], role)

    def freeze(self, job: str, manifest: dict, proposal: dict, changed: str) -> dict:
        inputs = {"proposal": proposal, "text_digest": sha256_bytes(changed.encode("utf-8")),
                  "manifest_digest": digest(manifest)}
        previous = self.store.checkpoint(job, "freeze", inputs)
        directory = self.store.directory / ("candidate-" + digest(job)[7:23])
        cas = LocalContentAddressedStore(self.store.directory / "candidate-cas")
        freezer = CandidateFreezer(cas, editable_surface_policy=EditableSurfacePolicy(
            policy_id="service-data-only-skill-body-v1", roots_by_surface={"skill-body": [proposal["path"]]}))
        if previous:
            # Re-verify the retained frozen population before using it again.
            self.frozen_text(previous, proposal["path"])
            return previous
        target = directory / proposal["path"]
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _atomic_write_bytes(target, changed.encode("utf-8"))
        _, tree_digest = snapshot_tree(directory)
        record = {"schema_version": "1.0.0", "kind": "CandidateArtifact", "id": new_typed_id("cand"),
                  "candidate_type": "skill_change", "parent_candidate_ids": [],
                  "root_production_epoch": "inactive-development:" + manifest["baseline_commit"],
                  "target_editable_surface": "skill-body", "declared_changed_surfaces": [proposal["path"]],
                  "artifact_ref_ids": [], "draft_tree_digest": tree_digest,
                  "causal_hypothesis_ref": digest(proposal),
                  "preservation_obligations": ["frontmatter", "activation-boundary", "integration-boundary"],
                  "proposed_by": "research-service-skill-editor", "classification": "private_operational",
                  "created_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")}
        receipt = freezer.freeze(record, directory, expected_draft_digest=tree_digest)
        return self.store.checkpoint(job, "freeze", inputs, {"candidate": record, "receipt": receipt})

    def frozen_text(self, frozen: dict, path: str) -> str:
        cas = LocalContentAddressedStore(self.store.directory / "candidate-cas")
        freezer = CandidateFreezer(cas, editable_surface_policy=EditableSurfacePolicy(
            policy_id="service-data-only-skill-body-v1", roots_by_surface={"skill-body": [path]}))
        receipt = frozen["receipt"]
        authority = ArtifactAuthority("service-data-evaluator", frozenset({"artifact.read"}),
                                      frozenset({receipt["candidate_id"]}), "private_operational")
        with tempfile.TemporaryDirectory(prefix="evaluation-", dir=self.store.directory) as folder:
            destination = Path(folder) / "frozen"
            freezer.materialize(receipt, destination, authority)
            return (destination / path).read_text(encoding="utf-8")

    def primary_context(self, job: str, manifest: dict, lanes: list, packet: dict) -> dict:
        from .primary_context import (
            LIMITS, POLICY, build_primary_context, collect_primary, select_primary, verify_primary,
            outcome_base, read_profile_binding,
        )
        schedule = manifest["schedule"]
        profile = schedule.get("primary_read_profile")
        profile_binding = read_profile_binding(profile)
        profile_kwargs = {} if profile is None else {"profile": profile}
        bound = {"manifest": digest(manifest), "discovery": digest(packet),
                 "lanes": digest(lanes), "policy": POLICY}
        if profile_binding is not None:
            bound["reader_policy"] = profile_binding
        selection_profile = schedule.get("primary_selection_profile")
        if selection_profile is not None:
            bound["selection_profile"] = selection_profile
        selection = select_primary(lanes, packet, schedule.get("primary_read_limit", 0), profile=selection_profile)
        selection = self.store.checkpoint(job, "primary-selection", bound, selection)
        reader = self.primary_reader or collect_primary
        replayer = self.primary_replayer or verify_primary
        outcomes = []
        directory = self.store.directory / "primary-evidence"
        for index, selected in enumerate(selection["selected"]):
            url = selected["source_url"]
            policy = {"policy": POLICY, "url": url,
                      "limits": LIMITS if profile_binding is None else profile_binding["limits"],
                      "implementation_digest": manifest["implementation_digest"],
                      "query": schedule["query"], "window_start": manifest["window_start"],
                      "window_end": manifest["window_end"]}
            if profile_binding is not None:
                policy["reader_policy"] = profile_binding
            if selection_profile is not None:
                policy["selection_profile"] = selection_profile
            inputs = {"manifest": digest(manifest), "selection": selected, "policy": policy}
            name = "primary-" + str(index)
            outcome = self.store.completed_effect(job, name, inputs)
            if outcome is None:
                key = digest(policy)
                cached = None if manifest["fixture"] else self.store.cached_source(key)

                def observe(url=url, cached=cached, key=key, name=name):
                    if cached is not None:
                        return cached
                    if not manifest["fixture"]:
                        try:
                            # Share arXiv's durable three-second gate with discovery.
                            source = "arxiv" if urlsplit(url).hostname == "arxiv.org" else "primary-html"
                            self.store.claim_source(key, source, job, name)
                        except ServiceError as exc:
                            if exc.code != "SOURCE_RATE_LIMIT":
                                raise
                            # A fast arXiv discovery must not starve its primary
                            # read. Wait once under the worker lock and existing
                            # request reservation. No HTTP attempt has occurred.
                            self.primary_wait(3)
                            try:
                                self.store.claim_source(key, source, job, name)
                            except ServiceError as retry:
                                if retry.code != "SOURCE_RATE_LIMIT":
                                    raise
                                return {**outcome_base(url, profile), "state": "deferred",
                                        "error_code": "LOCAL_ARXIV_SPACING"}
                    return reader(url, directory, **profile_kwargs)

                outcome = self.effect(job, name, inputs, observe,
                                      source_requests=0 if cached is not None else 1)
            replayer(url, outcome, directory, **profile_kwargs)
            self.store.checkpoint(job, name, inputs, outcome)
            outcomes.append(outcome)
        context = build_primary_context(schedule["query"], selection, outcomes)
        return self.store.checkpoint(job, "primary-context", bound, context)

    @traced("workflow.retrieve")
    def retrieve(self, job: str, manifest: dict) -> dict:
        """Daily discovery ends at an inert context digest, before any agent call.

        Completed pages remain observation-only. Continuation tokens are retained
        for audit but are never committed as a complete source watermark.
        """
        from .context_digest import build_context_digest
        from .retrieval_sources import collect, source_limits, verify

        config, schedule = self.store.config, manifest["schedule"]
        if manifest["fixture"] and (self.retrieval_source is None or self.retrieval_verify is None):
            raise ServiceError("FIXTURE_REQUIRES_OFFLINE_ADAPTERS")
        if (manifest["fixture"] and schedule.get("primary_read_limit", 0)
                and (self.primary_reader is None or self.primary_replayer is None)):
            raise ServiceError("FIXTURE_REQUIRES_OFFLINE_PRIMARY_ADAPTERS")
        if not self.live and not manifest["fixture"]:
            raise ServiceError("LIVE_EXECUTION_REQUIRES_OPT_IN")
        expected = make_manifest(self.root, config, schedule, fixture=manifest["fixture"],
                                 window_end=manifest.get("window_end"))
        if manifest != expected:
            raise ServiceError("WORK_INPUTS_CHANGED")
        start, end = manifest["window_start"], manifest["window_end"]
        collector, verifier = self.retrieval_source or collect, self.retrieval_verify or verify
        lanes, failures = [], []
        for name in schedule["sources"]:
            query = schedule["source_queries"][name]
            limits = source_limits(name)
            bound_limits = asdict(limits)
            bound_limits["max_milliseconds"] = int(bound_limits.pop("max_seconds") * 1000)
            policy = {"policy": manifest["retrieval_policy"], "source": name,
                      "query": query, "window_start": start, "window_end": end,
                      "limits": bound_limits}
            inputs = {"policy": policy, "manifest_digest": digest(manifest)}
            effect_name = "retrieval-" + name
            outcome = self.store.retrieval_effect_outcome(job, effect_name, inputs)
            failure_name = "retrieval-failure-" + name
            retained_gap = self.store.checkpoint(job, failure_name, inputs)
            blocked = {"source": name, "effect_name": effect_name,
                       "error_code": "SOURCE_OUTCOME_UNRESOLVED", "effect_state": "blocked",
                       "reservation_retained": False}
            failure = None
            if retained_gap is not None and retained_gap == blocked and outcome is None:
                failure = blocked
            elif outcome is not None and outcome["state"] in {"unknown", "failed"}:
                failure = {"source": name, "effect_name": effect_name,
                           "error_code": outcome["error_code"], "effect_state": outcome["state"],
                           "reservation_retained": True}
            elif retained_gap is not None:
                raise ServiceError("RETRIEVAL_FAILURE_CHECKPOINT_MISMATCH")
            lane = outcome["output"] if outcome and outcome["state"] == "completed" else None
            if lane is None and failure is None:
                cache_key = digest(policy)
                try:
                    cached = None if manifest["fixture"] else self.store.cached_source(cache_key)
                except ServiceError as exc:
                    if exc.code != "SOURCE_OUTCOME_UNRESOLVED":
                        raise
                    failure, cached = blocked, None
                credential = None
                if failure is None and cached is None and name in PAID_SOURCES:
                    credential = self.credential(config["source_credentials"][name])
                    from researcher.scripts.source_search import credential_value
                    try:
                        if credential is None:
                            raise ValueError()
                        credential_value(credential)
                    except ValueError:
                        raise ServiceError("INVALID_SOURCE_CREDENTIAL") from None
                def observe(n=name, q=query, cached=cached, key=cache_key,
                            effect_name=effect_name, secret=credential):
                    if cached is not None:
                        return cached
                    if not manifest["fixture"]:
                        try:
                            self.store.claim_source(key, n, job, effect_name)
                        except ServiceError as exc:
                            if n != "arxiv" or exc.code != "SOURCE_RATE_LIMIT":
                                raise
                            # A preceding job's primary read shares this durable
                            # gate. Wait once BEFORE dispatch, under the same
                            # reservation/worker lock; never retry the collector.
                            self.primary_wait(3)
                            self.store.claim_source(key, n, job, effect_name)
                    return collector(n, q, self.store.directory / "evidence",
                                     start_time=start, end_time=end, credential=secret)
                if failure is None:
                    lane = self.effect(job, effect_name, inputs, observe,
                        _retrieval_failure_isolation=True,
                        source_requests=0 if cached is not None else limits.max_requests,
                        micros=0 if cached is not None else
                            config.get("source_cost_microusd", {}).get(name, 0) * limits.max_requests)
                    if lane is None:
                        outcome = self.store.retrieval_effect_outcome(job, effect_name, inputs)
                        if outcome is None or outcome["state"] not in {"unknown", "failed"}:
                            raise ServiceError("RETRIEVAL_FAILURE_OUTCOME_INVALID")
                        failure = {"source": name, "effect_name": effect_name,
                                   "error_code": outcome["error_code"], "effect_state": outcome["state"],
                                   "reservation_retained": True}
            if failure is not None:
                self.store.checkpoint(job, failure_name, inputs, failure)
                failures.append(failure)
                lanes.append({"source": name, "state": "unavailable", "evidence": [], "next_cursor": None})
                continue
            verifier(name, query, lane, self.store.directory / "evidence",
                     start_time=start, end_time=end)
            self.store.checkpoint(job, effect_name, inputs, lane)
            lanes.append(lane)
        history_inputs = {"manifest": digest(manifest)}
        prior = self.store.checkpoint(job, "prior-retrieval", history_inputs)
        if prior is None:
            prior = {"entries": self.store.prior_retrieval(job, manifest)}
            self.store.checkpoint(job, "prior-retrieval", history_inputs, prior)
        packet = build_context_digest(schedule["query"], lanes, max_bytes=32768,
                                      max_items=20, previous=prior["entries"])
        primary = self.primary_context(job, manifest, lanes, packet)
        report = {"schema": "research-retrieval-report/v1", "job": job,
                  "disposition": "retrieval_only", "evidence_qualified": False,
                  "production_ready": False, "fixture": manifest["fixture"],
                  "schedule_id": schedule["id"], "window_start": start, "window_end": end,
                  "context_digest": packet, "primary_context": primary,
                  "collection_completed": True,
                  "reconciliation_required": any(f["effect_state"] in {"unknown", "blocked"} for f in failures),
                  "source_failures": failures,
                  "sources": [{"source": lane["source"], "state": lane["state"],
                               "items": len(lane["evidence"])} for lane in lanes]}
        self.store.checkpoint(job, "report", history_inputs, report)
        self.store.finish(job, "reconciliation_required" if report["reconciliation_required"] else "retrieval_complete")
        return report

    @traced("workflow.execute")
    def execute(self, job: str, manifest: dict) -> dict:
        current_span().reference("operation_ref", job)
        annotate(fixture=bool(manifest.get("fixture", False)))
        config, schedule = self.store.config, manifest["schedule"]
        if schedule.get("mode", "research") == "retrieve":
            return self.retrieve(job, manifest)
        if manifest["fixture"] and (self.model is complete or self.source is collect_source
                                    or self.credential is _credential):
            raise ServiceError("FIXTURE_REQUIRES_OFFLINE_ADAPTERS")
        if manifest["fixture"] and schedule.get("mcp_reads"):
            raise ServiceError("FIXTURE_CANNOT_CALL_MCP")
        if not self.live and not manifest["fixture"]:
            raise ServiceError("LIVE_EXECUTION_REQUIRES_OPT_IN")
        if manifest != make_manifest(self.root, config, schedule, fixture=manifest["fixture"]):
            raise ServiceError("WORK_INPUTS_CHANGED")
        corpus = retrieve_corpus(self.root, schedule["query"], schedule["skills"], config["limits"]["context_bytes"])
        self.store.checkpoint(job, "corpus", {"manifest": digest(manifest)}, corpus)
        lanes = []
        for name in schedule["sources"]:
            inputs = {"source": name, "query": schedule["query"], "manifest_digest": digest(manifest)}
            day = time.strftime("%Y-%m-%d", time.gmtime())
            # Request policy identity survives code deployments. A changed parser
            # must re-extract/verify retained bytes, not purchase a new daily slot.
            cache_key = digest({"day": day, "source": name, "query": schedule["query"] if name == "arxiv" else ""})
            cached = None if manifest["fixture"] else self.store.cached_source(cache_key)
            def call_source(n=name):
                if cached is not None:
                    return cached
                if not manifest["fixture"]:
                    self.store.claim_source(cache_key, n, job, "source-" + n)
                return self.source(n, schedule["query"], self.store.directory / "evidence")
            lane = self.effect(job, "source-" + name, inputs, call_source,
                               source_requests=0 if cached is not None else 1)
            lanes.append(lane)
            if not manifest["fixture"]:
                verify_source(name, schedule["query"], lane, self.store.directory / "evidence")
        for read in schedule.get("mcp_reads", []):
            from .mcp_worker import bounded_collect_mcp
            item = next(t for t in config["mcp_tools"] if t["registration"]["id"] == read["id"])
            inputs = {"registration": item["registration"], "arguments": read["arguments"],
                      "manifest_digest": digest(manifest), "max_cost_microusd": item["max_cost_microusd"]}
            name = "mcp-" + read["id"]
            lane = self.store.completed_effect(job, name, inputs)
            if lane is None:
                credential = self.credential(item["credential_env"]) if item["credential_env"] else None
                lane = self.effect(job, name, inputs,
                    lambda: bounded_collect_mcp(item["registration"], read["arguments"], credential=credential),
                    source_requests=12, micros=item["max_cost_microusd"])
            lanes.append(lane)
        evidence = [entry for lane in lanes for entry in lane["evidence"]]
        if not evidence:
            raise ServiceError("NO_CAPTURED_EVIDENCE")
        if len(canonicalize(evidence)) > 65536:
            raise ServiceError("EVIDENCE_CONTEXT_LIMIT")
        # Evidence validation is independent of whether a model later cites it.
        for entry in evidence:
            if not entry["text"] or sha256_bytes(entry["text"].encode("utf-8")) != entry["sha256"]:
                raise ServiceError("EVIDENCE_DIGEST_MISMATCH")
        if len({entry["id"] for entry in evidence}) != len(evidence):
            raise ServiceError("DUPLICATE_EVIDENCE")
        research_data = {"task": schedule["query"], "corpus": corpus, "evidence": evidence}
        memory_inputs = {"manifest": digest(manifest)}
        feedback = self.store.checkpoint(job, "prior-feedback", memory_inputs)
        if feedback is None:
            feedback = self.store.prior_feedback(job, manifest)
            research_data["prior_feedback"] = feedback
            while feedback["entries"] and len(canonicalize(research_data)) > config["limits"]["context_bytes"] + 65536:
                feedback["entries"].pop()
                feedback["omitted"]["budget"] += 1
            self.store.checkpoint(job, "prior-feedback", memory_inputs, feedback)
        research_data["prior_feedback"] = feedback
        research = self.ask(job, "researcher", research_data)
        ids = [claim["id"] for claim in research["claims"]]
        if len(set(ids)) != len(ids):
            raise ServiceError("DUPLICATE_CLAIM")
        for claim in research["claims"]:
            validate_citations(claim["citations"], evidence)
        self.store.checkpoint(job, "research", {"manifest": digest(manifest)}, research)
        if research["abstain"] or not ids:
            self.store.finish(job, "rejected", "RESEARCH_ABSTAINED")
            return {"status": "rejected"}
        critic = self.ask(job, "critic", {"task": schedule["query"], "claims": research["claims"], "evidence": evidence})
        if not set(critic["supported_claim_ids"]) <= set(ids):
            raise ServiceError("CRITIC_INVENTED_CLAIM")
        if critic["recommendation"] != "propose" or not critic["supported_claim_ids"]:
            self.store.finish(job, "rejected", "CRITIC_ABSTAINED")
            return {"status": "rejected"}
        proposal = self.ask(job, "skill_editor", {"task": schedule["query"], "corpus": corpus,
                          "hypothesis": research["hypothesis"], "test_plan": research["test_plan"],
                          "supported_claims": [c for c in research["claims"] if c["id"] in critic["supported_claim_ids"]]})
        original, changed = apply_edit(proposal, corpus, critic["supported_claim_ids"])
        candidate_identity = {"baseline_commit": manifest["baseline_commit"], "path": proposal["path"],
                              "text_sha256": sha256_bytes(changed.encode("utf-8"))}
        if self.store.candidate_seen(job, **candidate_identity):
            self.store.checkpoint(job, "duplicate-candidate", {"manifest": digest(manifest)}, candidate_identity)
            self.store.finish(job, "rejected", "DUPLICATE_CANDIDATE")
            return {"status": "rejected", "reason": "DUPLICATE_CANDIDATE", "fixture": manifest["fixture"],
                    "production_ready": False, "semantic_novelty_measured": False}
        frozen = self.freeze(job, manifest, proposal, changed)
        changed = self.frozen_text(frozen, proposal["path"])
        evaluations = []
        # Two fresh contexts, reversed order; no author rationale or earlier vote.
        candidate_first = int(digest(job)[-1], 16) % 2 == 0
        for index in range(2):
            first = candidate_first if index == 0 else not candidate_first
            judgment = self.ask(job, "evaluator", {"task": schedule["query"], "evidence": evidence,
                                 "A": changed if first else original, "B": original if first else changed}, suffix=f"-{index}")
            winner = "A" if first else "B"
            evaluations.append({"candidate_label": winner, "judgment": judgment,
                                "candidate_preferred": judgment["preference"] == winner and not judgment["critical_regression"]})
        passed = all(item["candidate_preferred"] for item in evaluations)
        report = {"schema": "research-service-review/v1", "job": job,
                  "baseline_commit": manifest["baseline_commit"], "corpus_digest": digest(corpus),
                  "research": research, "critic": critic, "proposal": proposal,
                  "candidate": frozen, "evaluations": evaluations,
                  "pilot_passed": passed, "downstream_effectiveness_measured": False,
                  "independent_human_evaluation": False, "production_ready": False,
                  "fixture": manifest["fixture"],
                  "remaining_gates": ["corpus metadata and claim synchronization", "held-out effectiveness benchmark",
                                      "full candidate repository validation", "human review and merge"]}
        self.store.checkpoint(job, "report", {"manifest": digest(manifest)}, report)
        if not passed:
            self.store.finish(job, "rejected", "PAIRED_REVIEW_DID_NOT_SUPPORT_CHANGE")
            return report
        if config["github"]["enabled"]:
            if manifest["fixture"]:
                raise ServiceError("FIXTURE_CANNOT_PUBLISH")
            from .github import publish_proposal
            published = publish_proposal(config, job, {"path": proposal["path"],
                "baseline_commit": manifest["baseline_commit"],
                "baseline_sha256": sha256_bytes(original.encode("utf-8")), "text": changed,
                "candidate_digest": sha256_bytes(changed.encode("utf-8")), "report_digest": digest(report)},
                credential=self.credential(config["github"]["credential_env"]),
                effect=lambda name, inputs, call: self.effect(job, name, inputs, call))
            self.store.checkpoint(job, "publication", {"report_digest": digest(report)}, published)
            self.store.finish(job, "published")
        else:
            self.store.finish(job, "proposal_ready")
        return report

    def drain(self, maximum: int = 1) -> list[dict]:
        results = []
        with self.store.worker_lock():
            self.store.recover()
            for _ in range(maximum):
                check_stop()
                record = self.store.next_job()
                if record is None:
                    break
                job = record["id"]
                try:
                    result = self.execute(job, record["manifest"])
                    results.append({"job": job, "result": result})
                except Exception as exc:
                    code = getattr(exc, "code", "WORKFLOW_FAILED")
                    if not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9_]{1,100}", code):
                        code = "WORKFLOW_FAILED"
                    self.store.finish(job, "failed", code)
                    results.append({"job": job, "error": code})
        return results
