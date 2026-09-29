"""Pure, finite-input packet-policy evaluation with no acceptance authority.

This evaluator performs no capture replay, I/O, model call or authentication.
The caller supplies verified observations and resolves the frozen dataset.
Declared groups are labels, not evidence of statistical independence. Results
measure packet selection and preservation only, never semantic effectiveness.
"""

from __future__ import annotations

import re
from typing import Any

if __package__:
    from .research_discovery import (
        _CAPTURE_SCOPE,
        _SOURCE_MODES,
        _canonical_url,
        _work_identity,
        DiscoveryError,
        build_discovery_packet,
        expand_discovery_provenance,
    )
    from .schema_contract import (
        ContractError,
        canonicalize,
        parse_json_strict,
        sha256_bytes,
    )
else:
    from research_discovery import (
        _CAPTURE_SCOPE,
        _SOURCE_MODES,
        _canonical_url,
        _work_identity,
        DiscoveryError,
        build_discovery_packet,
        expand_discovery_provenance,
    )
    from schema_contract import (
        ContractError,
        canonicalize,
        parse_json_strict,
        sha256_bytes,
    )


MAX_DATASET_BYTES = 4 * 1024 * 1024
MAX_CASES = 16
MAX_EVALUATIONS = 48
_SLUG = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
_SourceOracle = tuple[dict[str, bytes], dict[str, bytes], bytes, bytes]


class ExperimentError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _snapshot(value: Any, maximum: int) -> dict:
    if type(value) is not dict:
        raise ExperimentError("INVALID_DOCUMENT", "input must be a JSON object")
    try:
        body = canonicalize(value)
    except (ContractError, RecursionError, UnicodeError) as error:
        raise ExperimentError(
            "INVALID_JSON", "input must be bounded integer-only JSON"
        ) from error
    if len(body) > maximum:
        raise ExperimentError(
            "INPUT_TOO_LARGE", "canonical input exceeds its byte limit"
        )
    return parse_json_strict(body.decode("utf-8"))


def validate_policy(doc: Any) -> dict:
    """Return an owned strict policy snapshot; only compact is editable."""
    value = _snapshot(doc, 1024)
    if (
        set(value) != {"schema", "compact"}
        or value["schema"] != "packet-policy/v1"
        or type(value["compact"]) is not bool
    ):
        raise ExperimentError(
            "INVALID_POLICY", "policy must contain only schema and boolean compact"
        )
    return value


def _source_oracle(observations: list) -> _SourceOracle:
    """Bind source occurrences independently of packet construction/selection.

    URL identity and source-mode constants are shared contract primitives, but
    no builder output supplies expected text, attribution, or capture bindings.
    Canonical bytes prevent later in-place builder mutation from changing them.
    """
    contents, provenance = {}, {}
    lanes, pending_links = [], []
    try:
        for lane_index, lane in enumerate(observations):
            record = lane["record"]
            lane_projection = {
                "lane_id": lane["lane_id"],
                "facet": lane["facet"],
                "query": lane["query"],
                "run_question": record["query"],
                "run_id": record["run_id"],
                "manifest_digest": record["manifest_digest"],
                "observation_digest": sha256_bytes(canonicalize(record)),
                "network_mode": record["network_mode"],
                "status": record["status"],
                "sources": [],
            }
            for source_index, source in enumerate(record["sources"]):
                source_name = source["source"]
                adapter, mode, query_applied, _ = _SOURCE_MODES[source_name]
                captures = [
                    {
                        key: capture[key]
                        for key in ("body_sha256", "metadata_sha256", "size_bytes")
                    }
                    for capture in source["captures"]
                ]
                source_projection = {
                    "source": source_name,
                    "adapter_source": adapter,
                    "mode": mode,
                    "query_applied": query_applied,
                    "status": source["status"],
                    "effective_query": record["query"] if query_applied else "",
                    "lead_count": len(source["leads"]),
                    "capture_complete": source["capture_complete"],
                    "captures": captures,
                }
                for key in ("error_code", "retry_after_seconds"):
                    if key in source:
                        source_projection[key] = source[key]
                lane_projection["sources"].append(source_projection)
                for lead_index, lead in enumerate(source["leads"]):
                    work_id, canonical_url, version = _work_identity(lead["url"])
                    occurrence = f"{lane_index}:{source_index}:{lead_index}"
                    contents.setdefault(work_id, []).append(
                        {
                            "occurrence_id": occurrence,
                            "title": lead["title"],
                            "summary": lead["summary"],
                            "published_at": lead["published_at"],
                            "metadata": lead["metadata"],
                            "summary_scope": "provider_supplied_text_not_verified_full_paper",
                        }
                    )
                    provenance.setdefault(
                        work_id,
                        {
                            "work_id": work_id,
                            "canonical_url": canonical_url,
                            "occurrences": [],
                        },
                    )["occurrences"].append(
                        {
                            "occurrence_id": occurrence,
                            "lane_id": lane["lane_id"],
                            "facet": lane["facet"],
                            "query": lane["query"],
                            "effective_query": record["query"] if query_applied else "",
                            "run_id": record["run_id"],
                            "source": source_name,
                            "adapter_source": lead["source"],
                            "lead_identity": lead["identity"],
                            "original_url": lead["url"],
                            "version": version,
                            "captures": captures,
                            "capture_scope": _CAPTURE_SCOPE,
                        }
                    )
                    seen_links = set()
                    for key, url in lead["metadata"]:
                        if not url.lower().startswith("https://"):
                            continue
                        link_url = _canonical_url(url)
                        if link_url in seen_links or link_url == _canonical_url(
                            lead["url"]
                        ):
                            continue
                        seen_links.add(link_url)
                        pending_links.append(
                            {
                                "url": link_url,
                                "work_id": _work_identity(link_url)[0],
                                "from_work_id": work_id,
                                "occurrence_id": occurrence,
                                "metadata_field": key,
                                "status": "pending_unverified",
                                "intended_use": "candidate_primary_source_lookup",
                                "primary_source_confirmed": False,
                                "authority": "none",
                            }
                        )
            lanes.append(lane_projection)
        return (
            {
                work_id: canonicalize({"work_id": work_id, "observations": rows})
                for work_id, rows in contents.items()
            },
            {work_id: canonicalize(row) for work_id, row in provenance.items()},
            canonicalize(lanes),
            canonicalize(pending_links),
        )
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise ExperimentError(
            "INVALID_OBSERVATIONS", "cannot bind original source occurrences"
        ) from error


def _prepare_dataset(
    doc: Any,
) -> tuple[dict, list[tuple[dict | DiscoveryError, _SourceOracle]]]:
    value = _snapshot(doc, MAX_DATASET_BYTES)
    if (
        set(value) != {"schema", "authority", "cases"}
        or value["schema"] != "packet-experiment-input/v1"
        or value["authority"] != "none"
        or type(value["cases"]) is not list
        or not 1 <= len(value["cases"]) <= MAX_CASES
    ):
        raise ExperimentError(
            "INVALID_DATASET", "dataset fields or case count are invalid"
        )
    ids, inputs, references = set(), set(), []
    evaluations = 0
    for case in value["cases"]:
        if type(case) is not dict or set(case) != {
            "case_id",
            "group_id",
            "question",
            "observations",
            "packet_budgets",
        }:
            raise ExperimentError("INVALID_CASE", "case fields are invalid")
        for key in ("case_id", "group_id"):
            label = case[key]
            if (
                not isinstance(label, str)
                or len(label) > 64
                or not _SLUG.fullmatch(label)
            ):
                raise ExperimentError(
                    "INVALID_CASE", "case and group IDs must be safe slugs"
                )
        if case["case_id"] in ids:
            raise ExperimentError("DUPLICATE_CASE", "case ID is repeated")
        ids.add(case["case_id"])
        question = case["question"]
        if (
            not isinstance(question, str)
            or not question.strip()
            or "\x00" in question
            or len(question.encode("utf-8")) > 4096
            or type(case["observations"]) is not list
        ):
            raise ExperimentError(
                "INVALID_CASE", "question or observations are invalid"
            )
        identity = sha256_bytes(
            canonicalize({"question": question, "observations": case["observations"]})
        )
        if identity in inputs:
            raise ExperimentError(
                "DUPLICATE_INPUT",
                "renamed cases repeat the same question and observations",
            )
        inputs.add(identity)
        budgets = case["packet_budgets"]
        if (
            type(budgets) is not list
            or not 1 <= len(budgets) <= 3
            or any(type(n) is not int or not 16384 <= n <= 262144 for n in budgets)
            or len(set(budgets)) != len(budgets)
        ):
            raise ExperimentError(
                "INVALID_BUDGET", "select one to three distinct integer packet budgets"
            )
        evaluations += len(budgets)
        if evaluations > MAX_EVALUATIONS:
            raise ExperimentError(
                "INVALID_DATASET", "dataset exceeds the evaluation limit"
            )
        oracle = _source_oracle(case["observations"])
        try:
            # Give the builder an owned copy, never the dataset or the oracle.
            reference = build_discovery_packet(
                question,
                parse_json_strict(canonicalize(case["observations"]).decode()),
                262144,
            )
        except DiscoveryError as error:
            # An otherwise valid source corpus can exceed the reference budget.
            # Other discovery errors identify malformed dataset inputs.
            if error.code != "BUDGET_INSUFFICIENT":
                raise ExperimentError("INVALID_OBSERVATIONS", error.code) from error
            reference = error
        references.append((reference, oracle))
    return value, references


def validate_dataset(doc: Any) -> dict:
    """Validate at most 16 cases/48 pairings and 4 MiB of canonical JSON."""
    return _prepare_dataset(doc)[0]


def _packet_envelope(packet: dict, question: str, budget: int, compact: bool) -> bool:
    """Check fixed packet controls independently of builder-authored claims."""
    expected = {
        "schema": "local-research-discovery/v2"
        if compact
        else "local-research-discovery/v1",
        "authority": "none",
        "production_ready": False,
        "content_role": "untrusted_discovery_data",
        "question": question,
        "max_bytes": budget,
        "selection_policy": "round_robin_lanes_whole_work_records_not_relevance_ranking",
        "accepted_claims": 0,
        "model_calls": 0,
        "paid_calls": 0,
        "semantic_relevance_measured": False,
        "independent_corroboration_measured": False,
        "provenance_verification": "caller_required_not_performed_by_pure_builder",
    }
    if compact:
        expected["occurrence_defaults"] = {"capture_scope": _CAPTURE_SCOPE}
    population_fields = {
        "lanes",
        "work_index",
        "selected_works",
        "omitted_works",
        "pending_primary_source_leads",
        "metrics",
    }
    return set(packet) == set(expected) | population_fields and canonicalize(
        {key: packet.get(key) for key in expected}
    ) == canonicalize(expected)


def _invariants(
    packet: dict,
    reference: dict,
    budget: int,
    oracle: _SourceOracle,
    question: str,
    compact: bool,
) -> dict[str, bool]:
    expected = {row["work_id"]: row for row in reference["selected_works"]}
    selected = packet["selected_works"]
    selected_ids = [row["work_id"] for row in selected]
    omitted_ids = [row["work_id"] for row in packet["omitted_works"]]
    metrics = packet["metrics"]
    selected_occurrences = sum(len(row["observations"]) for row in selected)
    source_contents, source_provenance, source_lanes, source_links = oracle
    expanded = expand_discovery_provenance(packet)
    original_provenance = (
        len(expanded) == len(source_provenance)
        and len({row["work_id"] for row in expanded}) == len(expanded)
        and all(
            canonicalize(row) == source_provenance.get(row["work_id"])
            for row in expanded
        )
    )
    return {
        "reference_complete": len(expected) == reference["metrics"]["unique_works"]
        and set(expected) == set(source_contents),
        "exact_budget": len(canonicalize(packet)) == metrics["packet_bytes"] <= budget,
        "provenance_preserved": expanded == reference["work_index"]
        and original_provenance,
        # Input/control metadata must bind the request as well as the source
        # envelope. A symmetric builder bug cannot certify its own question,
        # ceiling, policy label, or authority/content classification.
        "source_metadata_preserved": _packet_envelope(packet, question, budget, compact)
        and _packet_envelope(reference, question, 262144, False)
        and packet["lanes"] == reference["lanes"]
        and canonicalize(packet["lanes"]) == source_lanes
        and packet["pending_primary_source_leads"]
        == reference["pending_primary_source_leads"]
        and canonicalize(packet["pending_primary_source_leads"]) == source_links,
        "selected_text_preserved": all(
            row == expected.get(row["work_id"])
            and canonicalize(row) == source_contents.get(row["work_id"])
            for row in selected
        ),
        "selection_accounting": (
            len(selected_ids) == len(set(selected_ids)) == metrics["selected_works"]
            and len(omitted_ids) == len(set(omitted_ids)) == metrics["omitted_works"]
            and not set(selected_ids).intersection(omitted_ids)
            and set(selected_ids + omitted_ids) == set(expected)
            and all(row["reason"] == "budget" for row in packet["omitted_works"])
            and selected_occurrences == metrics["selected_occurrences"]
            and metrics["raw_leads"] == reference["metrics"]["raw_leads"]
            and metrics["unique_works"] == len(expected)
            and metrics["duplicate_occurrences"] == metrics["raw_leads"] - len(expected)
            and metrics["omitted_occurrences"]
            == metrics["raw_leads"] - selected_occurrences
        ),
        "no_authority": packet["authority"] == "none"
        and packet["production_ready"] is False
        and packet["semantic_relevance_measured"] is False
        and packet["independent_corroboration_measured"] is False
        and all(
            type(packet[key]) is int and packet[key] == 0
            for key in ("accepted_claims", "model_calls", "paid_calls")
        ),
    }


def evaluate_policy(policy: Any, dataset: Any) -> dict:
    """Measure a policy on supplied finite inputs; failed proof means no score."""
    policy = validate_policy(policy)
    dataset, references = _prepare_dataset(dataset)
    results = []
    for case, (reference, oracle) in zip(dataset["cases"], references, strict=True):
        for budget in case["packet_budgets"]:
            row = {
                "case_id": case["case_id"],
                "group_id": case["group_id"],
                "packet_budget_bytes": budget,
                "status": "failed",
                "error_code": None,
                "packet_digest": None,
                "reference_digest": None,
                "metrics": None,
                "invariants": None,
            }
            if isinstance(reference, DiscoveryError):
                row["error_code"] = "REFERENCE_" + reference.code
            else:
                row["reference_digest"] = sha256_bytes(canonicalize(reference))
                if (
                    reference["metrics"]["selected_works"]
                    != reference["metrics"]["unique_works"]
                ):
                    row["error_code"] = "REFERENCE_INCOMPLETE"
                else:
                    try:
                        packet = build_discovery_packet(
                            case["question"],
                            parse_json_strict(
                                canonicalize(case["observations"]).decode()
                            ),
                            budget,
                            compact=policy["compact"],
                        )
                        checks = _invariants(
                            packet,
                            reference,
                            budget,
                            oracle,
                            case["question"],
                            policy["compact"],
                        )
                    except DiscoveryError as error:
                        row["error_code"] = error.code
                    else:
                        row.update(
                            packet_digest=sha256_bytes(canonicalize(packet)),
                            metrics=packet["metrics"],
                            invariants=checks,
                        )
                        if all(checks.values()):
                            row["status"] = "success"
                        else:
                            row["error_code"] = "MANDATORY_INVARIANT_FAILED"
            results.append(row)
    return {
        "schema": "private-packet-evaluation/v1",
        "authority": "none",
        "policy": policy,
        "policy_digest": sha256_bytes(canonicalize(policy)),
        "dataset_digest": sha256_bytes(canonicalize(dataset)),
        "case_count": len(dataset["cases"]),
        "declared_group_count": len({case["group_id"] for case in dataset["cases"]}),
        "evaluation_count": len(results),
        "results": results,
        "semantic_effectiveness": False,
        "independence_verified": False,
        "model_calls": 0,
        "paid_calls": 0,
    }


def compare_evaluations(baseline: Any, candidate: Any, *, dataset: Any) -> dict:
    """Recompute exact input-bound records before making a descriptive decision.

    Any regression overrides gains elsewhere; any failed row leaves evidence
    insufficient. Lexicographic preference is more selected works, then fewer
    packet bytes. This is neither statistical inference nor a promotion gate.
    """
    dataset = validate_dataset(dataset)
    evaluations = []
    for record in (baseline, candidate):
        record = _snapshot(record, 1024 * 1024)
        if "policy" not in record:
            raise ExperimentError(
                "INVALID_EVALUATION", "evaluation has no policy binding"
            )
        expected = evaluate_policy(record["policy"], dataset)
        if canonicalize(record) != canonicalize(expected):
            raise ExperimentError(
                "EVALUATION_MISMATCH",
                "evaluation does not match recomputed frozen inputs",
            )
        evaluations.append(record)
    baseline, candidate = evaluations
    pairs = []
    for left, right in zip(baseline["results"], candidate["results"], strict=True):
        if left["status"] != "success" or right["status"] != "success":
            relation = "unavailable"
        else:
            left_value = (
                left["metrics"]["selected_works"],
                -left["metrics"]["packet_bytes"],
            )
            right_value = (
                right["metrics"]["selected_works"],
                -right["metrics"]["packet_bytes"],
            )
            relation = (
                "better"
                if right_value > left_value
                else "worse"
                if right_value < left_value
                else "equal"
            )
        pairs.append(
            {
                "case_id": left["case_id"],
                "group_id": left["group_id"],
                "packet_budget_bytes": left["packet_budget_bytes"],
                "relation": relation,
            }
        )
    relations = {pair["relation"] for pair in pairs}
    decision = (
        "insufficient_evidence"
        if "unavailable" in relations
        else "rejected"
        if "worse" in relations
        else "candidate_dominates"
        if "better" in relations
        else "no_improvement"
    )
    return {
        "schema": "private-packet-comparison/v1",
        "authority": "none",
        "dataset_digest": baseline["dataset_digest"],
        "baseline_policy_digest": baseline["policy_digest"],
        "candidate_policy_digest": candidate["policy_digest"],
        "baseline_evaluation_digest": sha256_bytes(canonicalize(baseline)),
        "candidate_evaluation_digest": sha256_bytes(canonicalize(candidate)),
        "decision": decision,
        "pairs": pairs,
        "semantic_effectiveness": False,
        "independence_verified": False,
        "model_calls": 0,
        "paid_calls": 0,
    }
