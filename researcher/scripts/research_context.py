#!/usr/bin/env python3
"""Read-only, source-bound corpus context for supervised research.

Selection is explicit, not semantic routing. The byte budget applies to the exact
UTF-8 model_context string. Every selected claim/mechanism and section reference
is mandatory; complete section bodies are disclosed in selection/source order
only while they fit. Omitted bodies remain visible in the map. This is a corpus
evidence pack, not skill activation, authority, or an accepted ContextPackage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit


PACK_SCHEMA = "research-context/v1"
RECORD_SCHEMA = "research-context-record/v1"
MAX_CONTEXT_BYTES = 1_048_576
MAX_SOURCE_BYTES = 4_194_304
MAX_TOTAL_SOURCE_BYTES = 16_777_216
MAX_SELECTIONS = 64
INDEX_PATH = "researcher/corpus/index.json"
MECHANISM_PATH = "researcher/mechanisms/registry.jsonl"
CLAIM_PATH = "researcher/claims/index.jsonl"
SKILL_NAME = re.compile(r"[a-z][a-z0-9-]{0,95}\Z")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
PUBLIC_PREFIXES = (
    "skills/",
    "docs/",
    "template/",
    "examples/",
    "researcher/rubrics/",
    "researcher/templates/",
    "researcher/scripts/",
    "researcher/corpus/",
    "researcher/mechanisms/",
    "researcher/claims/",
)
SOURCE_SUFFIXES = {
    ".md",
    ".py",
    ".ts",
    ".tsx",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".sh",
}
CLAIM_FIELDS = {
    "claim_id",
    "claim_text",
    "owning_skill",
    "section",
    "source_url",
    "retrieved_at",
    "evidence_strength",
    "volatility",
    "last_reviewed",
}
MECHANISM_FIELDS = {
    "mechanism_id",
    "owning_skill",
    "status",
    "activation_scenario",
    "behavior_change",
    "evidence",
    "failure_modes",
}


class ContextError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code


def _json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ContextError(
            "INVALID_RECORD", "context data is not finite UTF-8 JSON"
        ) from exc


def _digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _json_loads(text: str) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ContextError("INVALID_RECORD", "duplicate JSON field")
            result[key] = value
        return result

    def reject_constant(_value: str) -> None:
        raise ContextError("INVALID_RECORD", "non-finite JSON value")

    try:
        return json.loads(
            text, object_pairs_hook=unique, parse_constant=reject_constant
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ContextError("INVALID_RECORD", "invalid source JSON") from exc


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ContextError("INVALID_RECORD", f"{label} must be a nonempty string")
    return value


def _strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise ContextError("INVALID_RECORD", f"{label} must be a string array")
    if len(set(value)) != len(value):
        raise ContextError("INVALID_RECORD", f"{label} contains duplicates")
    return value


def _public_path(value: str) -> str:
    if not isinstance(value, str):
        raise ContextError(
            "UNSAFE_SOURCE", "source path must be a public relative string"
        )
    path = PurePosixPath(value)
    if (
        not isinstance(value, str)
        or not value
        or path.is_absolute()
        or path.as_posix() != value
        or "\\" in value
        or any(part in {".", ".."} or part.startswith(".") for part in path.parts)
        or any(ord(char) < 32 for char in value)
        or not value.startswith(PUBLIC_PREFIXES)
        or path.suffix not in SOURCE_SUFFIXES
    ):
        raise ContextError(
            "UNSAFE_SOURCE", "source path is outside the public corpus surface"
        )
    return value


class _Sources:
    def __init__(self, root: Path, expected: Mapping[str, str] | None):
        self.root = Path(root)
        if expected is not None and not isinstance(expected, Mapping):
            raise ContextError(
                "INVALID_DIGEST", "expected source digests must be a mapping"
            )
        self.expected = dict(expected or {})
        for path, digest in self.expected.items():
            _public_path(path)
            if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
                raise ContextError(
                    "INVALID_DIGEST", "expected source digest is invalid"
                )
        self.data: dict[str, bytes] = {}
        self.total_bytes = 0

    def read(self, path: str) -> bytes:
        path = _public_path(path)
        if path in self.data:
            return self.data[path]
        if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
            raise ContextError(
                "UNSUPPORTED_FILESYSTEM", "no-follow source reads are required"
            )
        descriptors: list[int] = []
        try:
            directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            descriptors.append(os.open(self.root, directory_flags))
            parts = PurePosixPath(path).parts
            for part in parts[:-1]:
                descriptors.append(
                    os.open(part, directory_flags, dir_fd=descriptors[-1])
                )
            descriptors.append(
                os.open(
                    parts[-1],
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=descriptors[-1],
                )
            )
            before = os.fstat(descriptors[-1])
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise ContextError(
                    "UNSAFE_SOURCE", "source must be a single-link regular file"
                )
            if before.st_size > MAX_SOURCE_BYTES:
                raise ContextError("SOURCE_LIMIT", "source exceeds the read limit")
            chunks: list[bytes] = []
            length = 0
            while chunk := os.read(
                descriptors[-1], min(65_536, MAX_SOURCE_BYTES + 1 - length)
            ):
                chunks.append(chunk)
                length += len(chunk)
                if length > MAX_SOURCE_BYTES:
                    raise ContextError("SOURCE_LIMIT", "source exceeds the read limit")
            after = os.fstat(descriptors[-1])
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            ):
                raise ContextError("SOURCE_CHANGED", "source changed during capture")
            payload = b"".join(chunks)
            if len(payload) != after.st_size:
                raise ContextError("SOURCE_CHANGED", "source capture is incomplete")
        except FileNotFoundError as exc:
            raise ContextError(
                "SOURCE_MISSING", "required corpus source is missing"
            ) from exc
        except OSError as exc:
            raise ContextError(
                "UNSAFE_SOURCE", "required source cannot be opened safely"
            ) from exc
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)
        self.total_bytes += len(payload)
        if self.total_bytes > MAX_TOTAL_SOURCE_BYTES:
            raise ContextError("SOURCE_LIMIT", "combined sources exceed the read limit")
        if path in self.expected and _digest(payload) != self.expected[path]:
            raise ContextError(
                "SOURCE_DIGEST_MISMATCH", "source differs from its expected bytes"
            )
        self.data[path] = payload
        return payload

    def text(self, path: str) -> str:
        try:
            return self.read(path).decode("utf-8")
        except UnicodeError as exc:
            raise ContextError("INVALID_SOURCE", "source is not UTF-8") from exc

    def receipt(self, path: str) -> dict[str, Any]:
        payload = self.read(path)
        return {"path": path, "sha256": _digest(payload), "size_bytes": len(payload)}


def _registry(
    sources: _Sources, path: str, id_field: str, fields: set[str]
) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    offset = 0
    for line_number, raw_line in enumerate(
        sources.read(path).splitlines(keepends=True), 1
    ):
        start = offset
        offset += len(raw_line)
        if not raw_line.strip():
            continue
        try:
            record = _json_loads(raw_line.decode("utf-8"))
        except UnicodeError as exc:
            raise ContextError("INVALID_SOURCE", "registry is not UTF-8") from exc
        if not isinstance(record, dict) or set(record) != fields:
            raise ContextError(
                "INVALID_RECORD", "registry record has unexpected fields"
            )
        identifier = _string(record.get(id_field), id_field)
        if identifier in records:
            raise ContextError("INVALID_RECORD", "registry identity is duplicated")
        for key in fields - {"evidence", "failure_modes"}:
            _string(record[key], key)
        for key in fields & {"evidence", "failure_modes"}:
            _strings(record[key], key)
        records[identifier] = {
            "record": record,
            "reference": {
                "path": path,
                "line_start": line_number,
                "line_end": line_number,
                "byte_start": start,
                "byte_end": offset,
                "sha256": _digest(raw_line),
            },
        }
    return records


def _sections(skill: str, path: str, payload: bytes) -> list[dict[str, Any]]:
    try:
        text = payload.decode("utf-8")
    except UnicodeError as exc:
        raise ContextError("INVALID_SOURCE", "skill source is not UTF-8") from exc
    lines = text.splitlines(keepends=True)
    if not lines:
        raise ContextError("INVALID_SOURCE", "skill source is empty")
    boundaries: list[tuple[int, str]] = [(0, "Overview and metadata")]
    fence_char = ""
    fence_size = 0
    for index, line in enumerate(lines):
        stripped = line.rstrip("\r\n")
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", stripped)
        if fence:
            delimiter, suffix = fence.groups()
            if not fence_char:
                fence_char, fence_size = delimiter[0], len(delimiter)
            elif (
                delimiter[0] == fence_char
                and len(delimiter) >= fence_size
                and not suffix.strip()
            ):
                fence_char, fence_size = "", 0
            continue
        if not fence_char and stripped.startswith("## "):
            boundaries.append((index, stripped[3:].strip()))
    if fence_char:
        raise ContextError("INVALID_SOURCE", "skill contains an unclosed code fence")
    sections: list[dict[str, Any]] = []
    offset = 0
    for number, (start, title) in enumerate(boundaries):
        end = boundaries[number + 1][0] if number + 1 < len(boundaries) else len(lines)
        if end == start:
            continue
        content = "".join(lines[start:end])
        section_bytes = content.encode("utf-8")
        sections.append(
            {
                "section_id": f"{skill}:{start + 1}",
                "skill": skill,
                "path": path,
                "title": title,
                "line_start": start + 1,
                "line_end": end,
                "byte_start": offset,
                "byte_end": offset + len(section_bytes),
                "sha256": _digest(section_bytes),
                "disclosure": "omitted_budget",
                "text": content,
            }
        )
        offset += len(section_bytes)
    return sections


def _provenance(
    value: str, sources: _Sources, claims: Mapping[str, Any]
) -> dict[str, Any]:
    if value in claims:
        return {"kind": "claim_reference", "claim_id": value}
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or any(ord(char) < 32 for char in value)
        ):
            raise ContextError(
                "UNSAFE_SOURCE",
                "external provenance must be a credential-free HTTPS link",
            )
        return {"kind": "external_link", "url": value, "retrieval": "not_fetched"}
    return {"kind": "local_source", **sources.receipt(value)}


@dataclass(frozen=True)
class ContextPack:
    model_context: str

    @property
    def digest(self) -> str:
        return _digest(self.model_context.encode("utf-8"))

    @property
    def metrics(self) -> dict[str, Any]:
        body = _json_loads(self.model_context)
        sections = body["sections"]
        included = [
            section for section in sections if section["disclosure"] == "included"
        ]
        return {
            "measurement_scope": "deterministic_coverage_budget_provenance_only",
            "semantic_quality_measured": False,
            "selection_method": "explicit_skill_order",
            "selected_skills": len(body["selected_skills"]),
            "source_files": len(body["source_receipts"]),
            "sections_total": len(sections),
            "sections_included": len(included),
            "sections_omitted": len(sections) - len(included),
            "claims_retained": len(body["claims"]),
            "mechanisms_retained": len(body["mechanisms"]),
            "included_source_bytes": sum(
                section["byte_end"] - section["byte_start"] for section in included
            ),
            "model_context_bytes": len(self.model_context.encode("utf-8")),
            "max_bytes": body["max_bytes"],
            "model_calls": 0,
            "network_calls": 0,
        }

    def as_record(self) -> dict[str, Any]:
        return {
            "schema": RECORD_SCHEMA,
            "model_context": self.model_context,
            "digest": self.digest,
            "metrics": self.metrics,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> ContextPack:
        if (
            not isinstance(record, Mapping)
            or set(record) != {"schema", "model_context", "digest", "metrics"}
            or record.get("schema") != RECORD_SCHEMA
        ):
            raise ContextError("INVALID_PACK", "context record shape is invalid")
        context = record.get("model_context")
        if not isinstance(context, str):
            raise ContextError("INVALID_PACK", "model context must be UTF-8 text")
        try:
            context_length = len(context.encode("utf-8"))
        except UnicodeError as exc:
            raise ContextError(
                "INVALID_PACK", "model context must be UTF-8 text"
            ) from exc
        if context_length > MAX_CONTEXT_BYTES:
            raise ContextError("INVALID_PACK", "model context is invalid or oversized")
        pack = cls(context)
        try:
            body = _json_loads(context)
            if (
                not isinstance(body, dict)
                or body.get("schema") != PACK_SCHEMA
                or _json_bytes(body).decode("utf-8") != context
            ):
                raise ContextError(
                    "INVALID_PACK", "context must use the canonical pack encoding"
                )
            if record["digest"] != pack.digest or record["metrics"] != pack.metrics:
                raise ContextError("PACK_TAMPERED", "context record binding differs")
        except (KeyError, TypeError, UnicodeError) as exc:
            raise ContextError("INVALID_PACK", "context body is malformed") from exc
        return pack


def build_context_pack(
    root: Path,
    selected_skills: Sequence[str],
    max_bytes: int,
    *,
    expected_digests: Mapping[str, str] | None = None,
) -> ContextPack:
    if (
        isinstance(selected_skills, (str, bytes))
        or not isinstance(selected_skills, Sequence)
        or not 1 <= len(selected_skills) <= MAX_SELECTIONS
    ):
        raise ContextError(
            "INVALID_SELECTION", "explicit bounded skill selection is required"
        )
    selected = list(selected_skills)
    if any(
        not isinstance(skill, str) or not SKILL_NAME.fullmatch(skill)
        for skill in selected
    ):
        raise ContextError("INVALID_SELECTION", "skill identity is invalid")
    if len(set(selected)) != len(selected):
        raise ContextError("DUPLICATE_SKILL", "skill selection contains duplicates")
    if (
        isinstance(max_bytes, bool)
        or not isinstance(max_bytes, int)
        or not 1 <= max_bytes <= MAX_CONTEXT_BYTES
    ):
        raise ContextError(
            "INVALID_BUDGET", "max_bytes is outside the supported byte budget"
        )
    sources = _Sources(root, expected_digests)
    index = _json_loads(sources.text(INDEX_PATH))
    if (
        not isinstance(index, dict)
        or not isinstance(index.get("skills"), list)
        or index.get("mechanism_registry") != MECHANISM_PATH
        or index.get("claim_registry") != CLAIM_PATH
    ):
        raise ContextError(
            "INVALID_RECORD", "corpus index registry bindings are invalid"
        )
    skills: dict[str, dict[str, Any]] = {}
    for entry in index["skills"]:
        if not isinstance(entry, dict):
            raise ContextError("INVALID_RECORD", "skill index entry is invalid")
        name = _string(entry.get("name"), "skill name")
        if (
            name in skills
            or not SKILL_NAME.fullmatch(name)
            or entry.get("path") != f"skills/{name}/SKILL.md"
        ):
            raise ContextError(
                "INVALID_RECORD", "skill path or identity binding is invalid"
            )
        for key in ("claim_ids", "mechanism_ids", "activation_scenarios"):
            _strings(entry.get(key), key)
        skills[name] = entry
    if any(skill not in skills for skill in selected):
        raise ContextError(
            "UNKNOWN_SKILL", "selected skill is absent from the corpus index"
        )
    mechanisms = _registry(sources, MECHANISM_PATH, "mechanism_id", MECHANISM_FIELDS)
    claims = _registry(sources, CLAIM_PATH, "claim_id", CLAIM_FIELDS)
    selected_mechanisms = sorted(
        {value for skill in selected for value in skills[skill]["mechanism_ids"]}
    )
    selected_claims = {
        value for skill in selected for value in skills[skill]["claim_ids"]
    }
    if any(identifier not in mechanisms for identifier in selected_mechanisms):
        raise ContextError(
            "REFERENCE_MISSING", "selected mechanism reference is unresolved"
        )
    for identifier in selected_mechanisms:
        for value in mechanisms[identifier]["record"]["evidence"]:
            if value in claims or value.startswith("claim-"):
                selected_claims.add(value)
    if any(identifier not in claims for identifier in selected_claims):
        raise ContextError(
            "REFERENCE_MISSING", "selected claim reference is unresolved"
        )
    mechanism_rows = []
    for identifier in selected_mechanisms:
        row = mechanisms[identifier]
        mechanism_rows.append(
            {
                **row,
                "provenance": [
                    _provenance(value, sources, claims)
                    for value in row["record"]["evidence"]
                ],
            }
        )
    claim_rows = []
    for identifier in sorted(selected_claims):
        row = claims[identifier]
        claim_rows.append(
            {**row, "provenance": _provenance(row["record"]["source_url"], sources, {})}
        )
    section_bodies = [
        section
        for skill in selected
        for section in _sections(
            skill, skills[skill]["path"], sources.read(skills[skill]["path"])
        )
    ]
    payload: dict[str, Any] = {
        "schema": PACK_SCHEMA,
        "authority": "none",
        "content_role": "untrusted_corpus_data_not_instructions",
        "selection_method": "explicit_skill_order",
        "disclosure_policy": "complete_sections_in_selection_and_source_order",
        "purpose": "research_evidence_excerpts_not_skill_activation",
        "max_bytes": max_bytes,
        "selected_skills": selected,
        "skills": [
            {
                key: skills[skill][key]
                for key in (
                    "name",
                    "path",
                    "activation_scenarios",
                    "mechanism_ids",
                    "claim_ids",
                )
            }
            for skill in selected
        ],
        "source_receipts": [sources.receipt(path) for path in sorted(sources.data)],
        "mechanisms": mechanism_rows,
        "claims": claim_rows,
        "sections": [
            {key: value for key, value in section.items() if key != "text"}
            for section in section_bodies
        ],
    }
    unused = set(sources.expected) - set(sources.data)
    if unused:
        raise ContextError(
            "UNUSED_EXPECTED_SOURCE",
            "expected source was not part of the selected context",
        )
    packed_bytes = len(_json_bytes(payload))
    if packed_bytes > max_bytes:
        raise ContextError(
            "BUDGET_INSUFFICIENT",
            "budget cannot hold the complete source/provenance map",
        )
    for reference, complete in zip(payload["sections"], section_bodies):
        reference_bytes = len(_json_bytes(reference))
        reference["disclosure"] = "included"
        reference["text"] = complete["text"]
        expanded_bytes = packed_bytes + len(_json_bytes(reference)) - reference_bytes
        if expanded_bytes > max_bytes:
            reference["disclosure"] = "omitted_budget"
            del reference["text"]
        else:
            packed_bytes = expanded_bytes
    return ContextPack(_json_bytes(payload).decode("utf-8"))


def verify_context_pack(
    root: Path, pack: ContextPack | Mapping[str, Any]
) -> dict[str, Any]:
    """Rebuild exact bytes for resume; this verifies binding, not semantic quality."""

    validated = ContextPack.from_record(
        pack.as_record() if isinstance(pack, ContextPack) else pack
    )
    body = _json_loads(validated.model_context)
    try:
        expected = {
            receipt["path"]: receipt["sha256"] for receipt in body["source_receipts"]
        }
        rebuilt = build_context_pack(
            root, body["selected_skills"], body["max_bytes"], expected_digests=expected
        )
    except (KeyError, TypeError) as exc:
        raise ContextError("INVALID_PACK", "context references are malformed") from exc
    if rebuilt.model_context != validated.model_context:
        raise ContextError(
            "PACK_TAMPERED", "context differs from deterministic source reconstruction"
        )
    return {"verified": True, "digest": validated.digest, **validated.metrics}


def run_context_scenarios(root: Path) -> dict[str, Any]:
    """Small read-only benchmark of context mechanics against the current corpus."""

    results: list[dict[str, Any]] = []
    for name, skills in (
        ("single_skill", ["context-fundamentals"]),
        ("shared_claims", ["context-fundamentals", "context-optimization"]),
    ):
        try:
            pack = build_context_pack(root, skills, 65_536)
            result = verify_context_pack(root, pack.as_record())
            results.append({"case": name, "passed": True, "metrics": result})
        except ContextError as exc:
            results.append({"case": name, "passed": False, "error_code": exc.code})
    for name, skills, budget, digests, expected in (
        (
            "insufficient_budget",
            ["context-fundamentals"],
            1,
            None,
            "BUDGET_INSUFFICIENT",
        ),
        (
            "unknown_skill",
            ["nonexistent-research-context-skill"],
            65_536,
            None,
            "UNKNOWN_SKILL",
        ),
        (
            "duplicate_selection",
            ["context-fundamentals", "context-fundamentals"],
            65_536,
            None,
            "DUPLICATE_SKILL",
        ),
        (
            "wrong_digest",
            ["context-fundamentals"],
            65_536,
            {INDEX_PATH: "sha256:" + "0" * 64},
            "SOURCE_DIGEST_MISMATCH",
        ),
    ):
        try:
            build_context_pack(root, skills, budget, expected_digests=digests)
            results.append(
                {"case": name, "passed": False, "error_code": "unexpected_success"}
            )
        except ContextError as exc:
            results.append(
                {"case": name, "passed": exc.code == expected, "error_code": exc.code}
            )
    return {
        "schema": "research-context-benchmark/v1",
        "authority": "none",
        "passed": all(item["passed"] for item in results),
        "cases_executed": len(results),
        "semantic_quality_measured": False,
        "measurement_scope": "deterministic_coverage_budget_provenance_only",
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--skills", nargs="+")
    parser.add_argument("--max-bytes", type=int, default=65_536)
    parser.add_argument("--benchmark", action="store_true")
    args = parser.parse_args()
    try:
        record = (
            run_context_scenarios(args.root)
            if args.benchmark
            else build_context_pack(
                args.root, args.skills or [], args.max_bytes
            ).as_record()
        )
        print(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2))
        return 0 if record.get("passed", True) else 1
    except ContextError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "authority": "none"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
