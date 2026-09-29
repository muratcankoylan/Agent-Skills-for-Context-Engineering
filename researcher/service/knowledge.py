"""Bounded corpus retrieval and literal citation checks, without model calls.

BM25 ranks whole sections only within explicitly selected skills. Complete
documents remain the editable baseline; excerpts duplicate exact source bytes.
Scores measure lexical matching, not semantic relevance or evidence entailment.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
import math
import os
from pathlib import Path
import re
import stat
import unicodedata

from researcher.scripts.research_context import ContextError, _sections
from researcher.scripts.schema_contract import canonicalize, sha256_bytes

MAX_BYTES = 131_072
MAX_SECTIONS = 512
_SKILL = re.compile(r"[a-z][a-z0-9-]{0,95}\Z")


class KnowledgeError(ValueError):
    def __init__(self, code: str):
        super().__init__(f"knowledge validation failed: {code}")
        self.code = code


def _text(value: object, maximum: int, code: str) -> bytes:
    try:
        if not isinstance(value, str) or not value.strip() or "\x00" in value:
            raise KnowledgeError(code)
        encoded = value.encode("utf-8", errors="strict")
        if len(encoded) > maximum:
            raise KnowledgeError(code)
        return encoded
    except UnicodeError:
        raise KnowledgeError(code) from None


def _sequence(value: object, maximum: int, code: str) -> None:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or not 1 <= len(value) <= maximum
    ):
        raise KnowledgeError(code)


def _read(root: Path, relative: str) -> bytes:
    """Walk every component without following links, including root ancestors."""
    descriptors = []
    try:
        if not root.is_absolute() or ".." in root.parts:
            raise KnowledgeError("UNSAFE_PATH")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        descriptors.append(os.open(root.anchor, flags))
        for part in (*root.parts[1:], *Path(relative).parts[:-1]):
            descriptors.append(os.open(part, flags, dir_fd=descriptors[-1]))
        name = Path(relative).name
        descriptors.append(
            os.open(
                name,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=descriptors[-1],
            )
        )
        descriptor = descriptors[-1]
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise KnowledgeError("UNSAFE_PATH")
        if before.st_size > MAX_BYTES:
            raise KnowledgeError("SOURCE_TOO_LARGE")
        pieces, size = [], 0
        while chunk := os.read(descriptor, min(65_536, MAX_BYTES + 1 - size)):
            pieces.append(chunk)
            size += len(chunk)
            if size > MAX_BYTES:
                raise KnowledgeError("SOURCE_TOO_LARGE")
        after = os.fstat(descriptor)
        named = os.stat(name, dir_fd=descriptors[-2], follow_symlinks=False)

        def identity(item):
            return (
                item.st_dev,
                item.st_ino,
                item.st_size,
                item.st_mtime_ns,
                item.st_ctime_ns,
                item.st_mode,
                item.st_nlink,
            )

        if identity(before) != identity(after) or identity(after) != identity(named):
            raise KnowledgeError("SOURCE_CHANGED")
        if size != after.st_size:
            raise KnowledgeError("SOURCE_CHANGED")
        return b"".join(pieces)
    except FileNotFoundError:
        raise KnowledgeError("SOURCE_MISSING") from None
    except (OSError, ValueError, AttributeError) as error:
        if isinstance(error, KnowledgeError):
            raise
        raise KnowledgeError("UNSAFE_PATH") from None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _tokens(text: str) -> list[str]:
    # No task-specific keywords, stopword list, or source-text normalization.
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold())


def retrieve_corpus(
    root: Path, query: str, skills: Sequence[str], max_bytes: int
) -> dict:
    """Return complete baselines and ranked whole-section excerpts within budget.

    BM25 uses k1=1.2, b=0.75 and unique query tokens. Scores are rounded to integer
    millionths; ties use path and byte offset. Every section is either included
    or recorded as omitted. A budget unable to hold this map and all baselines
    fails rather than truncating a candidate-edit baseline.
    """
    _text(query, 4096, "INVALID_QUERY")
    terms = sorted(set(_tokens(query)))
    if not terms:
        raise KnowledgeError("INVALID_QUERY")
    _sequence(skills, 32, "INVALID_SKILLS")
    selected = list(skills)
    if any(
        not isinstance(skill, str) or not _SKILL.fullmatch(skill) for skill in selected
    ):
        raise KnowledgeError("INVALID_SKILLS")
    if len(set(selected)) != len(selected):
        raise KnowledgeError("INVALID_SKILLS")
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_BYTES:
        raise KnowledgeError("INVALID_BUDGET")
    if not isinstance(root, Path):
        raise KnowledgeError("UNSAFE_PATH")
    documents, sections, total = [], [], 0
    for skill in selected:
        path = f"skills/{skill}/SKILL.md"
        raw = _read(root, path)
        total += len(raw)
        if total > MAX_BYTES:
            raise KnowledgeError("SOURCE_TOO_LARGE")
        try:
            text = raw.decode("utf-8", errors="strict")
            _text(text, MAX_BYTES, "INVALID_SOURCE")
            rows = _sections(skill, path, raw)
        except (UnicodeError, ContextError):
            raise KnowledgeError("INVALID_SOURCE") from None
        digest = sha256_bytes(raw)
        documents.append({"path": path, "sha256": digest, "text": text})
        for row in rows:
            binding = {
                "path": path,
                "source_sha256": digest,
                "byte_start": row["byte_start"],
                "byte_end": row["byte_end"],
            }
            sections.append(
                {
                    "id": "excerpt_" + sha256_bytes(canonicalize(binding))[7:],
                    **binding,
                    "text": row["text"],
                }
            )
        if len(sections) > MAX_SECTIONS:
            raise KnowledgeError("SOURCE_TOO_LARGE")
    frequencies = [Counter(_tokens(row["text"])) for row in sections]
    average = sum(sum(row.values()) for row in frequencies) / len(sections)
    document_frequency = {
        term: sum(term in row for row in frequencies) for term in terms
    }
    for section, counts in zip(sections, frequencies, strict=True):
        length = sum(counts.values())
        score = 0.0
        for term in terms:
            frequency = counts[term]
            if frequency:
                df = document_frequency[term]
                idf = math.log1p((len(sections) - df + 0.5) / (df + 0.5))
                score += (
                    idf
                    * frequency
                    * 2.2
                    / (frequency + 1.2 * (0.25 + 0.75 * length / average))
                )
        section["score_micros"] = round(score * 1_000_000)
    ranked = sorted(
        sections, key=lambda row: (-row["score_micros"], row["path"], row["byte_start"])
    )
    omissions = [
        {
            key: row[key]
            for key in ("id", "path", "source_sha256", "byte_start", "byte_end")
        }
        | {"reason": "budget" if row["score_micros"] else "no_query_match"}
        for row in ranked
    ]
    result = {
        "schema": "research-corpus-retrieval/v1",
        "query": query,
        "selected_skills": selected,
        "documents": documents,
        "excerpts": [],
        "omissions": omissions,
        "methodology": "bm25-section-v1",
        "semantic_quality_measured": False,
    }
    if len(canonicalize(result)) > max_bytes:
        raise KnowledgeError("BUDGET_INSUFFICIENT")
    for section in ranked:
        if not section["score_micros"]:
            continue
        index = next(i for i, row in enumerate(omissions) if row["id"] == section["id"])
        omitted = omissions.pop(index)
        result["excerpts"].append(section)
        if len(canonicalize(result)) > max_bytes:
            result["excerpts"].pop()
            omissions.insert(index, omitted)
    return result


def validate_citations(citations: Sequence[dict], evidence: Sequence[dict]) -> None:
    """Check exact literal grounding only; no relevance or entailment judgment."""
    _sequence(citations, 64, "INVALID_CITATION")
    _sequence(evidence, 256, "INVALID_EVIDENCE")
    by_id, total = {}, 0
    for record in evidence:
        if (
            not isinstance(record, dict)
            or not {"id", "text", "sha256"} <= record.keys()
        ):
            raise KnowledgeError("INVALID_EVIDENCE")
        _text(record["id"], 256, "INVALID_EVIDENCE")
        raw = _text(record["text"], MAX_BYTES, "INVALID_EVIDENCE")
        total += len(raw)
        if total > 4 * 1024 * 1024:
            raise KnowledgeError("INVALID_EVIDENCE")
        if record["sha256"] != sha256_bytes(raw):
            raise KnowledgeError("EVIDENCE_DIGEST_MISMATCH")
        if record["id"] in by_id:
            raise KnowledgeError("DUPLICATE_EVIDENCE")
        by_id[record["id"]] = record["text"]
    seen = set()
    for citation in citations:
        if not isinstance(citation, dict) or set(citation) != {"evidence_id", "quote"}:
            raise KnowledgeError("INVALID_CITATION")
        _text(citation["evidence_id"], 256, "INVALID_CITATION")
        _text(citation["quote"], 8192, "INVALID_CITATION")
        key = citation["evidence_id"], citation["quote"]
        if key in seen:
            raise KnowledgeError("DUPLICATE_CITATION")
        if key[0] not in by_id or key[1] not in by_id[key[0]]:
            raise KnowledgeError("UNGROUNDED_CITATION")
        seen.add(key)
