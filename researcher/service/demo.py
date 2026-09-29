"""Deterministic integration exercise, explicitly not scientific evidence."""

import json
from pathlib import Path

from researcher.scripts.schema_contract import canonicalize, sha256_bytes
from .contracts import load_config
from .providers import ModelResult
from .store import Store
from .workflow import Workflow, make_manifest


def demo_config() -> dict:
    return load_config(json.dumps({
        "schema": "research-service/v1",
        "repository": "muratcankoylan/Agent-Skills-for-Context-Engineering", "base_branch": "main",
        "models": {role: {"provider": "openai", "model": "fixture-model-v1",
                          "credential_env": "RESEARCH_DEMO_NEVER_RESOLVED",
                          "input_microusd_per_million_tokens": 1,
                          "output_microusd_per_million_tokens": 1}
                   for role in ("researcher", "critic", "skill_editor", "evaluator")},
        "limits": {"daily_model_calls": 20, "run_model_calls": 5,
                   "daily_budget_microusd": 1000, "run_budget_microusd": 100,
                   "context_bytes": 65536, "max_output_tokens": 4096, "timeout_seconds": 30,
                   "max_runs_per_tick": 1, "daily_source_requests": 20},
        "schedules": [{"id": "demo", "interval_seconds": 86400,
                       "query": "How should a research agent preserve evidence during context transfer?",
                       "skills": ["context-fundamentals"], "sources": ["arxiv"]}],
        "github": {"enabled": False, "credential_env": "RESEARCH_GITHUB_TOKEN",
                   "reviewer": "muratcankoylan", "notify": False},
    }))


def source(_name, _query, _directory):
    text = "Demonstration fixture: retain the source identifier when transferring an evidence excerpt."
    return {"source": "arxiv", "state": "observed", "captures": [],
            "evidence": [{"id": "fixture-evidence", "source": "fixture", "url": "https://example.org/fixture",
                          "text": text, "sha256": sha256_bytes(text.encode()), "evidence_scope": "synthetic_fixture"}],
            "receipt": {"request_count": 0, "total_bytes": 0, "item_count": 1}}


def model(request, *, credential):
    data = json.loads(request.prompt)
    if "Compare alternatives A and B" in request.system:
        preferred = "A" if "Fixture evidence-transfer check" in data["A"] else "B"
        result = {"preference": preferred, "critical_regression": False,
                  "reason": "Scripted fixture verdict; not a model judgment or benchmark."}
    elif "Audit the claims" in request.system:
        result = {"supported_claim_ids": ["fixture-claim"], "issues": [], "recommendation": "propose"}
    elif "Propose ONE exact text replacement" in request.system:
        document = data["corpus"]["documents"][0]
        # Preserve the existing section: only append a short fixture instruction
        # immediately after a non-locked heading. Nothing touches the checkout.
        headings = [line for line in document["text"].splitlines()
                    if line.startswith("## ") and line not in {"## When to Activate", "## Integration"}]
        anchor = headings[0] + "\n"
        result = {"path": document["path"], "old_text": anchor,
                  "new_text": anchor + "\nFixture evidence-transfer check: retain source identifiers with excerpts.\n",
                  "claim_ids": ["fixture-claim"], "rationale": "Synthetic integration exercise only."}
    else:
        item = data["evidence"][0]
        result = {"hypothesis": "A synthetic evidence-transfer instruction exercises the pipeline.",
                  "test_plan": "Use a fixture to verify exact citation and frozen candidate handling.",
                  "abstain": False, "claims": [{"id": "fixture-claim", "statement": item["text"],
                      "citations": [{"evidence_id": item["id"], "quote": item["text"]}],
                      "limitations": ["Synthetic source, no research-quality inference."]}]}
    return ModelResult(canonicalize(result).decode(), 1, 1, request.model, "fixture-request")


def run_demo(root: Path, directory: Path) -> dict:
    config = demo_config()
    store = Store(directory, config, initialize=True)
    manifest = make_manifest(root.resolve(), config, config["schedules"][0], fixture=True)
    store.enqueue("offline-demo-v1", manifest)
    workflow = Workflow(store, root, model=model, source=source,
                        credential=lambda _: "fixture-credential-never-sent")
    results = workflow.drain()
    return {"fixture": True, "network_calls": 0, "paid_model_calls": 0,
            "results": results, "status": store.status()}
