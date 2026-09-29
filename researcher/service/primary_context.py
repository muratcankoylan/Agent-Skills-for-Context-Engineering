"""Bounded primary HTML observations, never scientific assessment or authority.

Selection consumes replay-verified discovery and its deterministic digest. The
article reader enforces its own exact URL, capture and inert extraction policy.
Cards expose exact normalized-text spans, not claims of complete paper reading.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit

from researcher.scripts import research_articles as articles
from researcher.scripts import research_articles_large as large_articles
from researcher.scripts.research_evidence import LocalResearchEvidenceStore
from researcher.scripts.schema_contract import canonicalize, sha256_bytes
from .contracts import ServiceError, digest
from .knowledge import _tokens
from .tracing import annotate, instrument

POLICY = "verified-discovery-primary-html-v1"
SELECTION_PROFILE = "host-diversity-fill-v1"
LIMITS = asdict(articles.ArticleLimits())


def read_profile_binding(profile=None):
    """No default field is added to historical manifests, effects or outcomes."""
    if profile is None:
        return None
    if profile != large_articles.PROFILE:
        raise ServiceError("INVALID_PRIMARY_READ_PROFILE")
    return large_articles.policy_binding()


def outcome_base(url, profile=None):
    binding = read_profile_binding(profile)
    if binding is None:
        return {"schema": "primary-read-outcome/v1", "source_url": url}
    return {"schema": "primary-read-outcome/v2", "source_url": url, "reader_policy": binding}


def _target(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        # Representation conversion preserves the exact discovered identifier,
        # including version. The final reader allowlist validates every byte.
        if (parsed.netloc == "arxiv.org" and parsed.path.startswith("/abs/")
                and not parsed.query and not parsed.fragment):
            value = urlunsplit((parsed.scheme, parsed.netloc,
                               "/html/" + parsed.path[5:], "", ""))
        articles._validate_url(value)
        return value
    except (ValueError, articles.ArticleError):
        return None


def select_primary(lanes, packet, limit, *, profile=None):
    """Default one/host; opt-in diversity first, then fill unused bounded slots.

    Both profiles select before requests. The optional second same-host URL is
    a separate observation, never a retry of a failed/unknown first request.
    """
    if type(limit) is not int or not 0 <= limit <= 2:
        raise ServiceError("INVALID_PRIMARY_READ_LIMIT")
    if profile is not None and profile != SELECTION_PROFILE:
        raise ServiceError("INVALID_PRIMARY_SELECTION_PROFILE")
    result = {"policy": POLICY, "limit": limit, "selected": [], "omissions": []}
    if profile is not None:
        result["selection_profile"] = profile
    if limit == 0:
        return result
    raw = {}
    for lane in lanes:
        for entry in lane.get("evidence", []):
            key = (entry["source"], entry["id"], entry["sha256"])
            if key in raw and raw[key] != entry:
                raise ServiceError("PRIMARY_DISCOVERY_BINDING_INVALID")
            raw[key] = entry
    hosts, urls, deferred = set(), set(), []
    for row in packet["items"]:
        key = (row["source"], row["source_id"], row["qualifiers"]["source_sha256"])
        entry = raw.get(key)
        if (entry is None or sha256_bytes(entry["text"].encode()) != entry["sha256"]
                or row["id"] != "context_" + digest({"source": key[0], "id": key[1],
                                                    "sha256": key[2]})[7:]):
            raise ServiceError("PRIMARY_DISCOVERY_BINDING_INVALID")
        reason = None
        if row["lexical_overlap"] <= 0:
            reason = "no_query_term_overlap"
        candidates = [entry["url"]]
        # Only explicit article/HTML locations, never arbitrary extracted links,
        # publisher redirects, PDFs or social expansion chains.
        candidates.extend(value for name, value in entry.get("metadata", [])
                          if name in {"article_url", "arxiv_html_url"})
        targets = sorted({url for value in candidates if (url := _target(value))})
        if not targets:
            reason = reason or "no_allowlisted_primary_html"
        target = targets[0] if targets else None
        host = urlsplit(target).hostname if target else None
        if target in urls:
            reason = reason or "duplicate_primary_url"
        elif host in hosts:
            if profile is not None and reason is None:
                deferred.append((row, entry, target, key))
            reason = reason or "host_read_limit"
        elif len(result["selected"]) >= limit:
            reason = reason or "primary_read_limit"
        if reason:
            result["omissions"].append({"discovery_id": row["id"], "reason": reason})
            continue
        selected = {"source_url": target, "discovery_id": row["id"],
                    "source": key[0], "source_id": key[1], "source_sha256": key[2],
                    "discovery_record_sha256": digest(entry)}
        result["selected"].append(selected)
        urls.add(target)
        hosts.add(host)
    if profile is not None:
        omissions = {row["discovery_id"]: row for row in result["omissions"]}
        for row, entry, target, key in deferred:
            if target in urls:
                omissions[row["id"]]["reason"] = "duplicate_primary_url"
            elif len(result["selected"]) >= limit:
                omissions[row["id"]]["reason"] = "primary_read_limit"
            else:
                result["selected"].append({"source_url": target, "discovery_id": row["id"],
                    "source": key[0], "source_id": key[1], "source_sha256": key[2],
                    "discovery_record_sha256": digest(entry)})
                urls.add(target)
                del omissions[row["id"]]
        result["omissions"] = list(omissions.values())
    return result


@instrument("source.primary")
def collect_primary(url: str, directory: Path, *, profile=None) -> dict:
    base = outcome_base(url, profile)
    reader = articles if profile is None else large_articles
    store = LocalResearchEvidenceStore(directory)
    try:
        article = reader.retrieve_article(url, store)
        annotate(outcome="completed")
        return {**base, "state": "observed", "article": article}
    except articles.ArticleError as exc:
        annotate(outcome="failed")
        return {**base, "state": "unavailable", "error_code": exc.code,
                "captures": list(exc.captures)}


@instrument("source.verify")
def verify_primary(url: str, outcome: dict, directory: Path, *, profile=None) -> None:
    """Replay without network; never infer historical transport cause."""
    expected = outcome_base(url, profile)
    if (type(outcome) is not dict or any(outcome.get(key) != value for key, value in expected.items())
            or _target(url) != url):
        raise ServiceError("PRIMARY_REPLAY_INVALID")
    base = set(expected) | {"state"}
    reader = articles if profile is None else large_articles
    state = outcome.get("state")
    if state == "deferred":
        if set(outcome) != base | {"error_code"} or outcome["error_code"] != "LOCAL_ARXIV_SPACING":
            raise ServiceError("PRIMARY_REPLAY_INVALID")
        return
    store = LocalResearchEvidenceStore(directory, read_only=True)
    try:
        if state == "observed" and set(outcome) == base | {"article"}:
            if outcome["article"].get("source_url") != url:
                raise ServiceError("PRIMARY_REPLAY_INVALID")
            if profile is not None and outcome["article"].get("limits") != expected["reader_policy"]["limits"]:
                raise ServiceError("PRIMARY_REPLAY_INVALID")
            reader.replay_article(store, outcome["article"])
        elif state == "unavailable" and set(outcome) == base | {"error_code", "captures"}:
            reader.replay_article_failure(store, url, outcome["error_code"], outcome["captures"])
        else:
            raise ServiceError("PRIMARY_REPLAY_INVALID")
    except (articles.ArticleError, KeyError, TypeError, AttributeError):
        raise ServiceError("PRIMARY_REPLAY_INVALID") from None


def build_primary_context(query, selection, outcomes):
    """Pure card projection after capture replay, with unresolved assessments."""
    if len(outcomes) != len(selection["selected"]):
        raise ServiceError("PRIMARY_OUTCOME_COUNT_INVALID")
    result = {"schema": "research-primary-context/v1", "authority": "none",
              "evidence_qualified": False, "research_quality_assessed": False,
              "full_paper_verified": False, "policy": POLICY,
              "configured_read_limit": selection["limit"], "cards": [], "gaps": [],
              "selection_omissions": selection["omissions"]}
    if "selection_profile" in selection:
        if selection["selection_profile"] != SELECTION_PROFILE:
            raise ServiceError("INVALID_PRIMARY_SELECTION_PROFILE")
        result["selection_profile"] = selection["selection_profile"]
    terms = set(_tokens(query))
    for selected, outcome in zip(selection["selected"], outcomes, strict=True):
        if outcome["source_url"] != selected["source_url"]:
            raise ServiceError("PRIMARY_SELECTION_MISMATCH")
        if outcome["state"] != "observed":
            result["gaps"].append({"selected_from": selected, "state": outcome["state"],
                "error_code": outcome["error_code"], "captures": outcome.get("captures", []),
                "historic_cause_verified": False})
            if "reader_policy" in outcome:
                result["gaps"][-1]["reader_policy"] = outcome["reader_policy"]
            continue
        article = outcome["article"]
        raw = article["text"].encode("utf-8")
        if (sha256_bytes(raw) != article["text_sha256"] or len(raw) != article["text_bytes"]
                or article["source_url"] != selected["source_url"]):
            raise ServiceError("PRIMARY_TEXT_BINDING_INVALID")
        ranked = []
        for span in article["spans"]:
            start, end = span["start_byte"], span["end_byte"]
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(raw):
                raise ServiceError("PRIMARY_SPAN_INVALID")
            try:
                text = raw[start:end].decode("utf-8")
            except UnicodeError:
                raise ServiceError("PRIMARY_SPAN_INVALID") from None
            if end - start > 4096 or sha256_bytes(raw[start:end]) != span["sha256"]:
                raise ServiceError("PRIMARY_SPAN_INVALID")
            ranked.append((-len(terms & set(_tokens(text))), start,
                           {**span, "text": text}))
        ranked.sort(key=lambda row: row[:2])
        excerpts = sorted([row[2] for row in ranked[:2]], key=lambda row: row["start_byte"])
        card = {"id": "primary_" + digest({"selection": selected,
                                         "article": digest(article)})[7:],
                "authority": "none", "observation_only": True,
                "evidence_scope": "primary_html_observation", "selected_from": selected,
                "capture": article["capture"], "article_sha256": digest(article),
                "source_url": article["source_url"], "parser_policy": article["parser_policy"],
                "reader_sha256": article["reader_sha256"], "scope": article["scope"],
                "span_basis": article["span_basis"], "text_sha256": article["text_sha256"],
                "text_bytes": len(raw), "available_text_bytes": article["available_text_bytes"],
                "omitted_text_bytes": article["omitted_text_bytes"], "text_status": article["text_status"],
                "excerpt_omitted_bytes": len(raw) - sum(e["end_byte"] - e["start_byte"] for e in excerpts),
                "excerpts": excerpts, "full_paper_verified": False,
                "research_quality_assessed": False,
                "assessments": {name: {"status": "unresolved", "evidence_anchors": []}
                                for name in ("mechanism", "method", "claims", "limitations")}}
        result["cards"].append(card)
        if "reader_policy" in outcome:
            card["reader_policy"] = outcome["reader_policy"]
    if len(canonicalize(result)) > 32768:
        raise ServiceError("PRIMARY_CONTEXT_BUDGET")
    return result


def project_primary_evidence(context):
    """Narrow model projection after the caller replays the primary captures.

    This validates retained excerpts, not the untransmitted source text. A
    partial excerpt cannot independently prove its parent digest; capture replay
    remains required. Private capture locators and selection metadata stay out.
    No model execution, claim qualification or acceptance is performed here.
    """
    try:
        if (len(canonicalize(context)) > 32768
                or context["schema"] != "research-primary-context/v1"
                or context["authority"] != "none" or context["evidence_qualified"] is not False
                or context["research_quality_assessed"] is not False
                or context["full_paper_verified"] is not False
                or type(context["cards"]) is not list or len(context["cards"]) > 2):
            raise ValueError()
        result, seen = [], set()
        for card in context["cards"]:
            total, available, omitted = (card[key] for key in
                                         ("text_bytes", "available_text_bytes", "omitted_text_bytes"))
            if (card["authority"] != "none" or card["observation_only"] is not True
                    or card["evidence_scope"] != "primary_html_observation"
                    or card["full_paper_verified"] is not False
                    or card["research_quality_assessed"] is not False
                    or card["span_basis"] != "normalized-extracted-text-utf8-bytes/v1"
                    or any(type(n) is not int for n in (total, available, omitted))
                    or not 1 <= total <= 100000 or available < total or omitted != available - total
                    or card["text_status"] != ("byte_capped" if omitted else "bounded_extraction")
                    or not re.fullmatch(r"sha256:[0-9a-f]{64}", card["text_sha256"])
                    or not re.fullmatch(r"sha256:[0-9a-f]{64}", card["article_sha256"])
                    or card["id"] != "primary_" + digest({"selection": card["selected_from"],
                                                         "article": card["article_sha256"]})[7:]
                    or type(card["excerpts"]) is not list or not 1 <= len(card["excerpts"]) <= 2):
                raise ValueError()
            end_previous, retained = 0, b""
            for excerpt in card["excerpts"]:
                start, end = excerpt["start_byte"], excerpt["end_byte"]
                raw = excerpt["text"].encode("utf-8")
                if (type(start) is not int or type(end) is not int
                        or not end_previous <= start < end <= total or not 1 <= len(raw) <= 4096
                        or len(raw) != end - start or sha256_bytes(raw) != excerpt["sha256"]):
                    raise ValueError()
                end_previous = end
                retained += raw
                identity = "primaryspan_" + digest({"card": card["id"], "start": start,
                                                   "end": end, "sha256": excerpt["sha256"]})[7:]
                if identity in seen:
                    raise ValueError()
                seen.add(identity)
                result.append({"id": identity, "source": "primary-html", "text": excerpt["text"],
                    "sha256": excerpt["sha256"], "evidence_scope": "primary_html_observation",
                    "qualifiers": {"summary_kind": "article_body", "content_depth": "article_text",
                        "source_truncated": "true" if omitted else "false",
                        "selection_truncated": start != 0 or end != total,
                        "source_sha256": card["text_sha256"], "byte_start": start, "byte_end": end}})
            if (type(card["excerpt_omitted_bytes"]) is not int
                    or card["excerpt_omitted_bytes"] != total - len(retained)
                    or (len(retained) == total and sha256_bytes(retained) != card["text_sha256"])):
                raise ValueError()
        return result
    except (KeyError, ValueError, TypeError, AttributeError, UnicodeError, RecursionError):
        raise ServiceError("PRIMARY_PROJECTION_INVALID") from None
