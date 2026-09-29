"""Public, bounded research-task provenance. It never grants tool authority."""

from .contracts import array, digest, integer, obj, string, validate, ServiceError

HASH = string(71, pattern=r"^sha256:[0-9a-f]{64}$")
RETRIEVAL_CONTEXT_SCHEMA = obj({
    "schema": {"const": "research-retrieval-context/v1"},
    "authority": {"const": "none"},
    "job_digest": HASH,
    "manifest_digest": HASH,
    "report_digest": HASH,
    "evidence_digest": HASH,
    "query_digest": HASH,
    "window_start": integer(0, 2**53 - 1),
    "window_end": integer(86400, 2**53 - 1),
    "verified_at": integer(86400, 2**53 - 1),
    "maximum_age_seconds": integer(60, 604800),
    "fixture": {"type": "boolean"},
    "capture_replayed": {"const": True, "type": "boolean"},
    "scientific_quality_assessed": {"const": False, "type": "boolean"},
    "full_paper_verified": {"const": False, "type": "boolean"},
    "exhaustive_coverage": {"const": False, "type": "boolean"},
    "independent_corroboration": {"const": False, "type": "boolean"},
    "primary_cards": integer(1, 2),
    "primary_gaps": integer(0, 2),
    "discovery_omissions": integer(0, 256),
    "primary_selection_omissions": integer(0, 256),
    "primary_links": array(obj({
        "discovery_id": string(72, pattern=r"^context_[0-9a-f]{64}$"),
        "source_text_digest": HASH,
        "excerpt_ids": array(string(76, pattern=r"^primaryspan_[0-9a-f]{64}$"), 2, 1),
    }), 2, 1),
    "sources": array(obj({
        "source": string(64, pattern=r"^[a-z][a-z0-9_]{0,63}$"),
        "state": {"enum": ["observed", "rate_limited"]},
        "items": integer(0, 64),
        "window_applied": {"type": "boolean"},
        "window_resolution": {"enum": ["day", "second", "not_applied"]},
        "continuation_available": {"type": "boolean"},
        "partial": {"type": "boolean"},
    }), 7, 1),
})


def validate_retrieval_context(value, query, evidence):
    validate(value, RETRIEVAL_CONTEXT_SCHEMA, "RETRIEVAL_CONTEXT_INVALID")
    if (value["query_digest"] != digest(query)
            or value["evidence_digest"] != digest(evidence)
            or value["window_end"] != value["window_start"] + 86400
            or value["window_end"] % 86400
            or not 30 <= value["verified_at"] - value["window_end"] <= value["maximum_age_seconds"]
            or len({row["source"] for row in value["sources"]}) != len(value["sources"])):
        raise ServiceError("RETRIEVAL_CONTEXT_BINDING_INVALID")
    rows = {row["id"]: row for row in evidence}
    linked = []
    for link in value["primary_links"]:
        parent = rows.get(link["discovery_id"], {})
        if parent.get("evidence_scope") != "discovery_summary":
            raise ServiceError("RETRIEVAL_CONTEXT_LINK_INVALID")
        for identity in link["excerpt_ids"]:
            row = rows.get(identity, {})
            if (row.get("evidence_scope") != "primary_html_observation"
                    or row.get("qualifiers", {}).get("source_sha256") != link["source_text_digest"]):
                raise ServiceError("RETRIEVAL_CONTEXT_LINK_INVALID")
            linked.append(identity)
    if (len(value["primary_links"]) != value["primary_cards"]
            or len(set(linked)) != len(linked)
            or set(linked) != {row["id"] for row in evidence
                              if row["evidence_scope"] == "primary_html_observation"}):
        raise ServiceError("RETRIEVAL_CONTEXT_LINK_INVALID")


RESEARCH_RUBRIC = """When retrieval_context is supplied, retain its coverage and depth limits.
Analyze transfer to the selected context-engineering skill, not topical similarity.
The hypothesis must identify the mechanism, assumptions and target failure mode.
For each claim's limitations, distinguish author-reported method/results from your
inference; name the population/task, baseline, confounders, missing primary detail
and counterevidence where available. Say unknown when absent. Source repetition,
lexical ranking, social engagement and capture replay are not quality evidence.
The test_plan must specify a falsifiable paired baseline, held-out task family,
ablations, measured outcome, failure criterion and cost/latency constraints.
Do not treat adjacent-domain results as demonstrated transfer. Primary HTML is
partial normalized extraction; absent figures, tables or appendices remain gaps.
If these gaps prevent a defensible narrow improvement, abstain and specify the
next evidence acquisition or experiment. Never claim an experiment was executed.
"""
