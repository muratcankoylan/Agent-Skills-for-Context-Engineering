"""One durable, cumulative authority for bounded OpenAI research and evaluations.

All live calls share this Store, including failures and resumed runs. Reservations
are never refunded from token estimates. This authority does not cover API calls
made outside it, provider price changes, taxes, or managed agent sessions. Use a
dedicated provider project hard spend limit as a second boundary.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import re
import threading
import time
from urllib.parse import unquote

from researcher.scripts.schema_contract import canonicalize, parse_json_strict, sha256_bytes
from .agents_runtime import _read, _write
from .contracts import ServiceError, digest, parse_output
from .environment import read_env_file
from .model_worker import bounded_complete
from .providers import ModelRequest
from .store import Store
from .tracing import Tracer, annotate, current_span, traced

# Standard short-context rates, with the most expensive input/cache-write rate.
# Every input byte plus 4096 framing tokens is reserved as a token. No tool,
# regional, storage, background, fast-tier or >272k-context calls are admitted.
PRICING = {
    "schema": "openai-bounded-pricing/v1", "model": "gpt-6-sol",
    "input_microusd_per_million": 2_500_000,
    "output_microusd_per_million": 10_000_000,
    "source": "https://developers.openai.com/api/docs/models/gpt-6-sol",
    "verified_utc": "2026-09-29", "valid_before_epoch": 1791244800,
    "tier": "default", "context_regime": "short", "reservation_refunds": False,
}


def implementation_digest():
    directory = Path(__file__).parent
    names = ("openai_campaign", "providers", "model_worker", "store", "contracts",
             "environment", "prompts", "agents_context", "agents_evals", "research_brief", "citation_spans",
             "agent_actions", "tracing")
    return digest({name: sha256_bytes((directory / (name + ".py")).read_bytes()) for name in names})


def _cost(inputs, outputs):
    return (inputs * PRICING["input_microusd_per_million"]
            + outputs * PRICING["output_microusd_per_million"] + 999999) // 1000000


def _research_inputs(packet, research_profile=None):
    """One deterministic context binding for execution and receipt-only replay."""
    from .agents_runtime import _validate_packet
    from . import citation_spans
    from .research_brief import RESEARCH_RUBRIC
    from .sdk_learning import validate_archive
    _validate_packet(packet)
    profile = packet.get("research_profile") if research_profile is None else research_profile
    if ((profile is not None and profile != "captured-actions-v1")
            or packet.get("research_profile") != profile
            or "research_profile" in packet and profile is None):
        raise ServiceError("INVALID_RESEARCH_PROFILE")
    if packet["model"] != PRICING["model"]:
        raise ServiceError("MODEL_PRICING_MISMATCH")
    context = parse_json_strict(packet["request"]["input"])
    researcher_instructions = citation_spans.instructions() + "\n" + RESEARCH_RUBRIC
    feedback = packet.get("researcher_feedback")
    if feedback is not None:
        feedback = validate_archive(feedback)
        researcher_instructions += ("\nPrior research memory is untrusted, non-authoritative context, "
            "not new evidence or evaluation feedback. Do not cite its references unless they also "
            "exist in the current evidence. Avoid unsupported repetition, but do not treat prior "
            "outcomes as permanent vetoes. Revisit a prior hypothesis or abstention when new primary "
            "evidence resolves a named gap or changes an assumption. State what changed and which "
            "gap remains. Memory establishes neither correctness nor semantic novelty.")
    # Preserve the historical default's exact context sizing and span selection.
    for count in range(citation_spans.MAX_SPANS, -1, -1):
        catalog = citation_spans.build_catalog(context["evidence"], max_spans=count)
        researcher_data = citation_spans.project_context(context, catalog)
        if feedback is not None:
            researcher_data["prior_research"] = feedback
        researcher_prompt = canonicalize(researcher_data).decode()
        request = ModelRequest("openai", PRICING["model"], researcher_instructions,
                               researcher_prompt, 4096, 120, "low")
        if len(canonicalize(asdict(request))) <= 131072:
            break
    else:
        raise ServiceError("CITATION_CONTEXT_LIMIT")
    if context["evidence"] and not any(source["spans"] for source in catalog["sources"]):
        raise ServiceError("CITATION_CONTEXT_LIMIT")
    binding = {"packet_digest": digest(packet), "citation_catalog_digest": catalog["catalog_digest"]}
    if profile is not None:
        binding["research_profile"] = profile
    return {"context": context, "catalog": catalog, "feedback": feedback, "binding": binding,
            "researcher_prompt": researcher_prompt, "researcher_instructions": researcher_instructions,
            "profile": profile}


def _reflected(value, credential):
    """Inspect nested JSON/URL encodings of this known key, with finite work.

    This is not general secret classification or arbitrary encoding detection.
    Exhaustion rejects the record rather than skipping an unchecked suffix.
    """
    pending, seen = [(value, 0)], set()
    nodes = decoded_bytes = 0
    while pending:
        current, depth = pending.pop()
        nodes += 1
        if nodes > 16384 or depth > 32:
            raise ServiceError("CREDENTIAL_SCAN_LIMIT")
        if isinstance(current, dict):
            pending.extend((part, depth + 1) for pair in current.items() for part in pair)
        elif isinstance(current, (list, tuple)):
            pending.extend((part, depth + 1) for part in current)
        elif isinstance(current, str) and current not in seen:
            seen.add(current)
            decoded_bytes += len(current.encode("utf-8"))
            if decoded_bytes > 1048576:
                raise ServiceError("CREDENTIAL_SCAN_LIMIT")
            if credential in current:
                return True
            decoded = unquote(current)
            if decoded != current:
                pending.append((decoded, depth + 1))
            if current.lstrip().startswith(("{", "[", '"')):
                try:
                    pending.append((parse_json_strict(current), depth + 1))
                except (ValueError, TypeError, RecursionError):
                    pass
    return False


def configuration(cap_microusd, prior_spend_microusd):
    if (type(cap_microusd) is not int or not 1 <= cap_microusd <= 100_000_000
            or type(prior_spend_microusd) is not int or not 0 <= prior_spend_microusd < cap_microusd):
        raise ServiceError("INVALID_CAMPAIGN_BUDGET")
    remaining = cap_microusd - prior_spend_microusd
    return {"schema": "openai-budget-authority/v1", "cap_microusd": cap_microusd,
            "prior_spend_microusd": prior_spend_microusd, "pricing": PRICING,
            "concurrency": 1, "limits": {"daily_model_calls": 480, "run_model_calls": 1,
                "daily_source_requests": 0, "run_source_requests": 0,
                "daily_budget_microusd": remaining, "run_budget_microusd": remaining,
                "lifetime_budget_microusd": remaining}}


def initialize(directory: Path, *, cap_microusd: int, prior_spend_microusd: int):
    """Explicit one-time operation. There is intentionally no reset/top-up command."""
    config = configuration(cap_microusd, prior_spend_microusd)
    directory = directory.absolute()
    if directory.exists() or directory.is_symlink():
        raise ServiceError("BUDGET_AUTHORITY_ALREADY_EXISTS")
    directory.mkdir(mode=0o700, parents=False)
    _write(directory / "authority.json", config)
    return Store(directory, config, initialize=True)


class Campaign:
    backend = "bounded_native_responses"

    def __init__(self, directory: Path, *, credential=None, concurrency=1, model_call=None,
                 progress=None, now=None):
        if type(concurrency) is not int or concurrency != 1:
            raise ServiceError("CAMPAIGN_CONCURRENCY_MUST_BE_ONE")
        self.directory = directory.absolute()
        config = _read(self.directory / "authority.json")
        if config != configuration(config.get("cap_microusd"), config.get("prior_spend_microusd")):
            raise ServiceError("BUDGET_AUTHORITY_DRIFT")
        self.store = Store(self.directory, config)
        self.credential = credential
        self.model_call = model_call or bounded_complete
        self.progress = progress or (lambda event: print(json.dumps(event), flush=True))
        self.now = now or (lambda: int(time.time()))
        self.tracer = Tracer.at(self.directory)

    @property
    def fixture_execution(self):
        return self.model_call is not bounded_complete

    def execution_identity(self):
        return {"backend": self.backend, "implementation_digest": implementation_digest()}

    def status(self):
        with self.store._history_snapshot() as db:
            rows = list(db.execute("SELECT state,reserved_microusd,output,output_digest FROM effects"))
            reserved = sum(row["reserved_microusd"] for row in rows)
            usage = {"input_tokens": 0, "output_tokens": 0, "estimated_upper_cost_microusd": 0}
            for row in rows:
                if row["state"] == "completed":
                    output = Store._history_value(row["output"], row["output_digest"], 2_000_000)
                    for field in usage:
                        usage[field] += output["usage"][field]
        config = self.store.config
        return {"schema": "openai-campaign-status/v1", "authorized_cap_microusd": config["cap_microusd"],
                "prior_spend_microusd": config["prior_spend_microusd"],
                "reserved_microusd": reserved,
                "available_microusd": config["limits"]["lifetime_budget_microusd"] - reserved,
                "attempted_calls": len(rows), "completed_calls": sum(r["state"] == "completed" for r in rows),
                "unresolved_calls": sum(r["state"] in {"unknown", "started"} for r in rows),
                "observed_usage": usage, "invoice_verified": False, "reservation_refunds": False}

    @traced("model.call")
    def call(self, campaign: str, item: str, *, instructions: str, prompt: str,
             max_output_tokens=4096, reasoning_effort="low", binding=None):
        """Exactly one attempt for an immutable item. Replays require no credential."""
        if any(not isinstance(x, str) or not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,160}", x)
               for x in (campaign, item)):
            raise ServiceError("INVALID_CAMPAIGN_ID")
        if (not isinstance(instructions, str) or not isinstance(prompt, str) or not prompt.strip()
                or type(max_output_tokens) is not int or not 256 <= max_output_tokens <= 8192
                or reasoning_effort not in {"none", "low", "medium", "high"}):
            raise ServiceError("INVALID_CAMPAIGN_REQUEST")
        request = ModelRequest("openai", PRICING["model"], instructions, prompt,
                               max_output_tokens, 120, reasoning_effort)
        encoded = canonicalize(asdict(request))
        if len(encoded) > 131072:
            raise ServiceError("CAMPAIGN_CONTEXT_LIMIT")
        input_ceiling = len(encoded) + 4096
        reserve = _cost(input_ceiling, max_output_tokens)
        annotate(provider="openai", input_bytes=len(encoded), reserved_microusd=reserve,
                 transport="subprocess" if self.model_call is bounded_complete else "injected")
        current_span().reference("model_ref", request.model)
        current_span().reference("operation_ref", campaign + ":" + item)
        inputs = {"request": asdict(request), "binding": binding,
                  "implementation_digest": implementation_digest(), "pricing": PRICING}
        job = "openai-" + digest([campaign, item])[7:]
        manifest = {"schema": "openai-bounded-work/v1", "campaign": campaign, "item": item,
                    "inputs": inputs, "input_token_ceiling": input_ceiling, "reservation_microusd": reserve}
        with self.store.worker_lock():
            self.store.recover()
            saved = self.store.completed_effect(job, "response", inputs)
            if saved is not None:
                annotate(outcome="replayed", replayed=True)
                # A crash between receipt commit and terminal status is local
                # bookkeeping, not permission to submit the request again.
                self.store.finish(job, "execution_complete")
                self.progress({"event": "model_replayed", "campaign": campaign, "item": item})
                return saved
            if self.model_call is bounded_complete:
                raise ServiceError("NATIVE_AGENT_EXECUTION_RETIRED_USE_CODEX_SDK")
            if self.now() >= PRICING["valid_before_epoch"]:
                raise ServiceError("PRICING_REVIEW_REQUIRED")
            if (not isinstance(self.credential, str) or not self.credential
                    or len(self.credential) > 4096
                    or any(ord(c) < 33 or ord(c) > 126 for c in self.credential)):
                raise ServiceError("OPENAI_CREDENTIAL_REQUIRED")
            if _reflected(manifest, self.credential):
                raise ServiceError("CREDENTIAL_IN_CONTEXT")
            self.store.enqueue(job, manifest)
            if self.store.next_job(job) is None:
                raise ServiceError("CAMPAIGN_ITEM_NOT_RUNNABLE")
            self.store.reserve(job, "response", inputs, model_calls=1, micros=reserve, now=self.now())
            stop = threading.Event()
            started = time.monotonic()
            def tick():
                while not stop.wait(5):
                    self.progress({"event": "model_waiting", "campaign": campaign, "item": item,
                                   "elapsed_seconds": int(time.monotonic() - started)})
            observer = threading.Thread(target=tick, daemon=True)
            observer.start()
            self.progress({"event": "model_started", "campaign": campaign, "item": item,
                           "reserved_microusd": reserve})
            try:
                result = self.model_call(request, credential=self.credential)
                if (result.model != request.model or result.service_tier != "default"
                        or not result.request_id or type(result.input_tokens) is not int
                        or type(result.output_tokens) is not int
                        or not 0 <= result.input_tokens <= input_ceiling
                        or not 0 <= result.output_tokens <= max_output_tokens):
                    raise ServiceError("MODEL_RECEIPT_OUT_OF_CONTRACT")
                if _reflected(asdict(result), self.credential):
                    raise ServiceError("CREDENTIAL_REFLECTION")
                receipt = {"schema": "openai-bounded-response/v1", "response": asdict(result),
                    "usage": {"input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
                        "estimated_upper_cost_microusd": _cost(result.input_tokens, result.output_tokens)},
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "request_digest": digest(inputs), "reserved_microusd": reserve}
                self.store.complete_effect(job, "response", receipt)
                self.store.finish(job, "execution_complete")
                self.progress({"event": "model_completed", "campaign": campaign, "item": item,
                               "usage": receipt["usage"], "latency_ms": receipt["latency_ms"]})
                annotate(input_tokens=result.input_tokens, output_tokens=result.output_tokens,
                         estimated_cost_microusd=receipt["usage"]["estimated_upper_cost_microusd"],
                         output_bytes=len(result.text.encode("utf-8")), usage_known=True, outcome="completed")
                return receipt
            except Exception as error:
                code = getattr(error, "code", "MODEL_OUTCOME_UNKNOWN")
                if not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9_]{1,100}", code):
                    code = "MODEL_OUTCOME_UNKNOWN"
                self.store.fail_effect(job, "response", code, ambiguous=getattr(error, "ambiguous", True))
                raise ServiceError(code) from None
            finally:
                stop.set()
                observer.join(timeout=1)

    @traced("agent.research")
    def research(self, campaign, packet, *, research_profile=None, action_sink=None):
        """Three tool-free roles, then deterministic citation/edit validation.

        Caller must construct the packet from verified retrieval captures; packet
        hashes alone do not authenticate an arbitrary caller's evidence.
        """
        from .agents_context import validate_result
        from . import citation_spans
        from .prompts import instructions
        from .research_brief import RESEARCH_RUBRIC
        prepared = _research_inputs(packet, research_profile)
        context, catalog, feedback, binding = (prepared[key] for key in
                                               ("context", "catalog", "feedback", "binding"))
        profile = prepared["profile"]
        if action_sink is not None and (profile is None or not callable(action_sink)):
            raise ServiceError("INVALID_RESEARCH_PROFILE")
        def ask(role, data):
            citation_boundary = ("\nClaim citation evidence_id must be one of these external evidence IDs: "
                + canonicalize([row["id"] for row in context["evidence"]]).decode()
                + ". Corpus documents and excerpt IDs describe the baseline, not research evidence. "
                  "Discuss baseline limitations in the hypothesis/test plan, not as externally evidenced claims.")
            receipt = self.call(campaign, role, instructions=instructions(role) + "\n" + RESEARCH_RUBRIC + citation_boundary,
                                prompt=canonicalize(data).decode(), binding=binding)
            return parse_output(receipt["response"]["text"], role)
        if profile is None:
            receipt = self.call(campaign, "researcher", instructions=prepared["researcher_instructions"],
                                prompt=prepared["researcher_prompt"], binding=binding)
            research = citation_spans.resolve_research(receipt["response"]["text"], catalog, context["evidence"])
        else:
            from .agent_actions import run_actions
            actions = run_actions(self.call, campaign, context, catalog, feedback=feedback, binding=binding)
            research = actions["research"]
        # A cheap objective boundary precedes the next paid role. A critic must
        # never be asked to legitimize nonexistent IDs or nonliteral quotations.
        validate_result(canonicalize({"schema": "managed-research-proposal/v1", "authority": "none",
            "research": research, "critic": {"supported_claim_ids": [], "issues": [],
                "recommendation": "abstain"}, "proposal": None}).decode(), packet["corpus"], packet["evidence"])
        if profile is not None and action_sink is not None:
            action_sink(actions["transcript"])
        critic = ask("critic", {**context, "research": research})
        output = {"schema": "managed-research-proposal/v1", "authority": "none",
                  "research": research, "critic": critic, "proposal": None}
        validate_result(canonicalize(output).decode(), packet["corpus"], packet["evidence"])
        if not research["abstain"] and critic["recommendation"] == "propose":
            output["proposal"] = ask("skill_editor", {**context, "research": research, "critic": critic})
        return validate_result(canonicalize(output).decode(), packet["corpus"], packet["evidence"])

    @traced("agent.evaluate")
    def evaluate(self, campaign, plan, *, max_output_tokens=2048):
        """Fresh tool-free tasks, gold-free projection, no retries or cherry-picking."""
        from .agents_evals import _plan, compare_results, make_result, task_request
        plan = _plan(plan)
        if plan["model"] != PRICING["model"]:
            raise ServiceError("MODEL_PRICING_MISMATCH")
        results, failures, origins = [], [], {}
        for item in plan["items"]:
            request = task_request(plan, item["item_id"])
            try:
                receipt = self.call(campaign, item["item_id"], instructions=request["instructions"],
                    prompt=request["prompt"], max_output_tokens=max_output_tokens,
                    binding={"plan_digest": plan["plan_digest"], "prompt_digest": request["prompt_digest"]})
                raw = receipt["response"]
                try:
                    response = parse_json_strict(raw["text"])
                except (ValueError, TypeError, RecursionError):
                    response = raw["text"]  # Completed format failures remain in the denominator.
                usage = {"input_tokens": raw["input_tokens"], "output_tokens": raw["output_tokens"],
                         "cost_microusd": receipt["usage"]["estimated_upper_cost_microusd"],
                         "latency_ms": receipt["latency_ms"]}
                result = make_result(plan, item["item_id"], status="completed", response=response,
                    usage=usage, execution="live_declared",
                    session_id=receipt["sdk"]["thread_id"] if self.backend == "codex_sdk" else raw["request_id"],
                    resolved_model=raw["model"])
                if self.backend == "codex_sdk":
                    origins[item["item_id"]] = {"result_digest": result["result_digest"], "receipt": receipt}
            except ServiceError as error:
                failures.append({"item_id": item["item_id"], "code": error.code})
                result = make_result(plan, item["item_id"], status="unknown", execution="live_declared")
            results.append(result)
        execution = {"schema": "openai-eval-execution/v1", "authority": "none",
                "plan_digest": plan["plan_digest"], "results": results, "failures": failures,
                "comparison": compare_results(plan, results), "budget": self.status(),
                "backend": "responses", "held_out_effectiveness_demonstrated": False}
        if self.backend == "codex_sdk":
            execution.update(schema="codex-eval-execution/v1", backend="codex_sdk", origins=origins,
                             fixture=self.fixture_execution, runtime=self.execution_identity())
        return execution


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "status", "pause", "resume", "api", "eval", "research"))
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--cap-microusd", type=int)
    parser.add_argument("--prior-spend-microusd", type=int)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--campaign")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--sdk-python", type=Path)
    parser.add_argument("--port", type=int, default=8788)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            initialize(args.authority, cap_microusd=args.cap_microusd,
                       prior_spend_microusd=args.prior_spend_microusd)
        values = read_env_file(args.env_file) if args.env_file else {}
        if args.command in {"research", "eval"}:
            from .codex_campaign import CodexCampaign
            if args.sdk_python is None:
                raise ServiceError("CODEX_EXECUTOR_CONFIGURATION_REQUIRED")
            campaign = CodexCampaign(args.authority, credential=values.get("OPENAI_API_KEY"),
                concurrency=args.concurrency, sdk_python=str(args.sdk_python), live=args.live)
        else:
            campaign = Campaign(args.authority, concurrency=args.concurrency)
        if args.command == "api":
            from .api import serve_api
            if args.env_file is None or args.live:
                raise ServiceError("OPERATOR_ENV_REQUIRED_NO_MODEL_ACTIVATION")
            serve_api(campaign.store, Path.cwd(), "127.0.0.1", args.port,
                      values.get("RESEARCH_OPERATOR_TOKEN", ""))
            return 0
        if args.command in {"init", "status", "pause", "resume"}:
            if args.command in {"pause", "resume"}:
                campaign.store.pause(args.command == "pause")
            result = campaign.status()
            from .codex_campaign import sdk_status
            result["sdk"] = sdk_status(campaign.store)
        else:
            if not args.live or args.input is None or args.output is None or args.campaign is None:
                raise ServiceError("EXPLICIT_LIVE_INPUT_OUTPUT_REQUIRED")
            if args.output.exists() or args.output.is_symlink():
                raise ServiceError("OUTPUT_ALREADY_EXISTS")
            data = _read(args.input)
            result = (campaign.evaluate(args.campaign, data) if args.command == "eval"
                      else campaign.research(args.campaign, data))
            _write(args.output, result)
        print(json.dumps(result if args.command in {"init", "status", "pause", "resume"} else campaign.status(), indent=2))
        return 0
    except (ServiceError, ValueError, OSError) as error:
        print(json.dumps({"error": getattr(error, "code", "CAMPAIGN_INPUT_ERROR")}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
