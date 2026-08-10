#!/usr/bin/env python3
"""Build and reconcile the repository's deterministic corpus inventory.

The inventory is a derived view, never an authority over its inputs. It has no
wall-clock timestamp or embedded Git SHA. Instead it binds to exact canonical
input bytes through ``source_tree_digest`` and lists every contributing path
and digest. This avoids self-referential commit hashes in a committed output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

try:
    from skill_frontmatter import parse_frontmatter
except ModuleNotFoundError:  # Imported as researcher.scripts.build_inventory.
    from researcher.scripts.skill_frontmatter import parse_frontmatter


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY = ROOT / "researcher" / "corpus" / "inventory.json"
DEFAULT_SUMMARY = ROOT / "researcher" / "generated" / "corpus-summary.md"
SCHEMA_VERSION = "1.0.0"

VALIDATOR_OWNERSHIP = (
    {
        "id": "governance-policy",
        "path": "researcher/scripts/validate_governance.py",
        "owns": ["authority vocabulary", "constitutional invariants", "generated authority view"],
    },
    {
        "id": "repository-inventory",
        "path": "researcher/scripts/build_inventory.py",
        "owns": ["identifier uniqueness", "cross-artifact references", "live counts", "generated inventory"],
    },
    {
        "id": "export-policy",
        "path": "researcher/scripts/validate_export.py",
        "owns": ["classification export routes", "public projections", "staged export closure"],
    },
    {
        "id": "schema-contract",
        "path": "researcher/scripts/validate_schemas.py",
        "owns": ["schema registry", "canonical records", "legacy adapters", "conformance evidence"],
    },
    {
        "id": "platform-compatibility",
        "path": "researcher/scripts/validate_platform_compat.py",
        "owns": ["Agent Skills format", "platform install layouts", "reference validator"],
    },
    {
        "id": "repository-structure",
        "path": "researcher/scripts/validate_repo.py",
        "owns": ["content invariants", "rubric math", "source evaluations", "run fixtures"],
    },
    {
        "id": "skill-health",
        "path": "researcher/scripts/skill_health.py",
        "owns": ["skill body quality score"],
    },
    {
        "id": "activation-cases",
        "path": "researcher/scripts/check_activation_cases.py",
        "owns": ["activation boundary smoke tests"],
    },
    {
        "id": "adversarial-benchmarks",
        "path": "researcher/scripts/run_benchmarks.py",
        "owns": ["deterministic benchmark composition", "adversarial scenario execution"],
    },
)

LIVE_DOCUMENT_LINKS = {
    "README.md": "researcher/generated/corpus-summary.md",
    "AGENTS.md": "researcher/generated/corpus-summary.md",
    "CLAUDE.md": "researcher/generated/corpus-summary.md",
    "researcher/README.md": "generated/corpus-summary.md",
}


class InventoryError(ValueError):
    """Raised for structural errors that prevent deterministic parsing."""


class DuplicateKeyError(InventoryError):
    pass


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    artifact_id: str | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_json_bytes(value: Any) -> bytes:
    """Canonical bytes for deterministic repository views.

    This is the repository's v1 sorted-key profile. SPEC-003 replaces it with
    a registered cross-language canonicalization profile for durable records.
    Inventory values are limited to strings, integers, booleans, null, lists,
    and objects, so JSON number edge cases cannot enter this view.
    """

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def record_digest(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json_text(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_reject_duplicate_keys)


def atomic_write_text(path: Path, text: str) -> None:
    """Flush and atomically replace one generated file in its target directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if hasattr(os, "O_DIRECTORY"):
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except Exception:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


class InventoryBuilder:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.findings: list[Finding] = []
        self.sources: dict[str, dict[str, Any]] = {}
        self.skill_names: set[str] = set()
        self.mechanisms: dict[str, dict[str, Any]] = {}
        self.claims: dict[str, dict[str, Any]] = {}

    def add_finding(
        self,
        code: str,
        path: Path | str,
        message: str,
        artifact_id: str | None = None,
    ) -> None:
        self.findings.append(Finding(code, self.relative(path), artifact_id, message))

    def relative(self, path: Path | str) -> str:
        value = Path(path)
        if not value.is_absolute():
            normalized = PurePosixPath(str(value).replace("\\", "/"))
            if normalized.is_absolute() or ".." in normalized.parts:
                raise InventoryError(f"path escapes repository: {path}")
            return normalized.as_posix()
        try:
            # Preserve the lexical repository path here. add_source resolves
            # the target separately so a symlink can be reported against its
            # in-repository name instead of escaping before a typed finding is
            # emitted.
            lexical = Path(os.path.abspath(value))
            return lexical.relative_to(self.root).as_posix()
        except ValueError as exc:
            raise InventoryError(f"path escapes repository: {path}") from exc

    def add_source(self, path: Path) -> tuple[str, int]:
        relative = self.relative(path)
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(self.root)
        except (OSError, ValueError) as exc:
            self.add_finding("PATH_ESCAPE", relative, f"source is missing or escapes repository: {exc}")
            return "sha256:" + "0" * 64, 0
        if path.is_symlink() or not resolved.is_file():
            self.add_finding("PATH_ESCAPE", relative, "canonical input must be a regular non-symlink file")
            return "sha256:" + "0" * 64, 0
        body = resolved.read_bytes()
        digest = sha256_bytes(body)
        self.sources[relative] = {"path": relative, "digest": digest, "size_bytes": len(body)}
        return digest, len(body)

    def load_json(self, path: Path) -> Any | None:
        self.add_source(path)
        try:
            return parse_json_text(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
            self.add_finding("PARSE_ERROR", path, str(exc))
            return None

    def load_jsonl(self, path: Path) -> list[tuple[int, dict[str, Any], str]]:
        self.add_source(path)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            self.add_finding("PARSE_ERROR", path, str(exc))
            return []
        records: list[tuple[int, dict[str, Any], str]] = []
        for line_number, raw in enumerate(lines, start=1):
            if not raw.strip():
                continue
            try:
                value = parse_json_text(raw)
            except (json.JSONDecodeError, DuplicateKeyError) as exc:
                self.add_finding("PARSE_ERROR", path, f"line {line_number}: {exc}")
                continue
            if not isinstance(value, dict):
                self.add_finding("PARSE_ERROR", path, f"line {line_number}: expected object")
                continue
            records.append((line_number, value, record_digest(value)))
        return records

    @staticmethod
    def _category(owner: str, records: Iterable[dict[str, Any]], **extra: Any) -> dict[str, Any]:
        materialized = list(records)
        return {"owner": owner, "count": len(materialized), "records": materialized, **extra}

    def build(self) -> dict[str, Any]:
        skills = self.build_skills()
        mechanisms = self.build_mechanisms()
        claims = self.build_claims()
        ledgers = self.build_ledgers()
        corpus, relationships = self.build_corpus_index()
        activation = self.build_activation_cases()
        relationships["skill_activation_cases"] = sorted(
            (
                {"skill_id": record["expected_primary_skill"], "case_id": record["id"]}
                for record in activation["records"]
            ),
            key=lambda item: (item["skill_id"], item["case_id"]),
        )
        router = self.build_router_prompts()
        scenarios, goldens = self.build_adversarial()
        effectiveness = self.build_effectiveness_tasks()
        benchmark_runners = self.build_benchmark_runners()
        examples = self.build_examples()
        manifests = self.build_manifests()
        validators = self.build_validators()
        schemas = self.build_schemas()
        export_contracts = self.build_export_contracts()
        schema_contracts = self.build_schema_contracts()
        self.validate_live_document_links()

        artifacts = {
            "skills": skills,
            "mechanisms": mechanisms,
            "claims": claims,
            "mechanism_ledgers": ledgers,
            "corpus_index": corpus,
            "activation_cases": activation,
            "router_prompts": router,
            "adversarial_scenarios": scenarios,
            "adversarial_goldens": goldens,
            "effectiveness_tasks": effectiveness,
            "benchmark_runners": benchmark_runners,
            "examples": examples,
            "manifests": manifests,
            "validators": validators,
            "schemas": schemas,
            "export_contracts": export_contracts,
            "schema_contracts": schema_contracts,
        }
        source_records = sorted(self.sources.values(), key=lambda item: item["path"])
        source_tree_digest = sha256_bytes(
            canonical_json_bytes({"schema_version": SCHEMA_VERSION, "sources": source_records})
        )
        unresolved = sorted(
            (finding.to_dict() for finding in self.findings),
            key=lambda item: (item["code"], item["path"], item["artifact_id"] or "", item["message"]),
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "repository_revision": {
                "kind": "canonical_source_tree",
                "digest": source_tree_digest,
                "git_commit_excluded_to_avoid_self_reference": True,
            },
            "source_tree_digest": source_tree_digest,
            "sources": source_records,
            "artifacts": artifacts,
            "relationships": relationships,
            "compatibility": {
                "plugin_versions": manifests["versions"],
                "manifest_skill_sets": manifests["skill_sets"],
                "benchmark_runner": {
                    "router": benchmark_runners["status"]["router"],
                    "effectiveness": benchmark_runners["status"]["effectiveness"],
                    "paid_results": "runtime_or_published_only",
                },
                "historical_reports_are_snapshots": True,
            },
            "validator_ownership": validators["records"],
            "unresolved_references": unresolved,
        }

    def build_skills(self) -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        skills_dir = self.root / "skills"
        if not skills_dir.exists():
            self.add_finding("PARSE_ERROR", skills_dir, "skills directory is missing")
            return self._category("skills/*/SKILL.md", records)
        for skill_dir in sorted(path for path in skills_dir.iterdir() if path.is_dir()):
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                self.add_finding("PARSE_ERROR", skill_file, "SKILL.md is missing", skill_dir.name)
                continue
            digest, _ = self.add_source(skill_file)
            try:
                frontmatter, issues = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
            except (OSError, UnicodeError) as exc:
                self.add_finding("PARSE_ERROR", skill_file, str(exc), skill_dir.name)
                continue
            for issue in issues:
                self.add_finding("PARSE_ERROR", skill_file, issue, skill_dir.name)
            name = frontmatter.get("name")
            if not isinstance(name, str) or not name:
                name = skill_dir.name
            if name != skill_dir.name:
                self.add_finding(
                    "SKILL_PATH_MISMATCH",
                    skill_file,
                    f"frontmatter name {name!r} does not match directory {skill_dir.name!r}",
                    str(name),
                )
            if name in self.skill_names:
                self.add_finding("DUPLICATE_SKILL_ID", skill_file, "duplicate skill identifier", name)
            self.skill_names.add(name)
            records.append({"id": name, "path": self.relative(skill_file), "digest": digest})
        return self._category("skills/*/SKILL.md", sorted(records, key=lambda item: item["id"]))

    def build_mechanisms(self) -> dict[str, Any]:
        path = self.root / "researcher" / "mechanisms" / "registry.jsonl"
        records: list[dict[str, Any]] = []
        for line_number, value, digest in self.load_jsonl(path):
            mechanism_id = value.get("mechanism_id")
            if not isinstance(mechanism_id, str) or not mechanism_id:
                self.add_finding("PARSE_ERROR", path, f"line {line_number}: mechanism_id is required")
                continue
            if mechanism_id in self.mechanisms:
                self.add_finding(
                    "DUPLICATE_MECHANISM_ID", path, f"duplicate at line {line_number}", mechanism_id
                )
            owner = value.get("owning_skill")
            if owner not in self.skill_names:
                self.add_finding(
                    "DANGLING_SKILL", path, f"unknown owning_skill {owner!r}", mechanism_id
                )
            self.mechanisms[mechanism_id] = value
            records.append(
                {
                    "id": mechanism_id,
                    "owning_skill": owner,
                    "status": value.get("status"),
                    "line": line_number,
                    "digest": digest,
                }
            )
        return self._category(
            "researcher/mechanisms/registry.jsonl", sorted(records, key=lambda item: item["id"])
        )

    def build_claims(self) -> dict[str, Any]:
        path = self.root / "researcher" / "claims" / "index.jsonl"
        records: list[dict[str, Any]] = []
        for line_number, value, digest in self.load_jsonl(path):
            claim_id = value.get("claim_id")
            if not isinstance(claim_id, str) or not claim_id:
                self.add_finding("PARSE_ERROR", path, f"line {line_number}: claim_id is required")
                continue
            if claim_id in self.claims:
                self.add_finding("DUPLICATE_CLAIM_ID", path, f"duplicate at line {line_number}", claim_id)
            owner = value.get("owning_skill")
            if owner not in self.skill_names:
                self.add_finding("DANGLING_SKILL", path, f"unknown owning_skill {owner!r}", claim_id)
            self.claims[claim_id] = value
            records.append(
                {
                    "id": claim_id,
                    "owning_skill": owner,
                    "volatility": value.get("volatility"),
                    "line": line_number,
                    "digest": digest,
                }
            )
        return self._category(
            "researcher/claims/index.jsonl", sorted(records, key=lambda item: item["id"])
        )

    def build_ledgers(self) -> dict[str, Any]:
        ledger_dir = self.root / "researcher" / "mechanisms" / "ledgers"
        accepted_path = ledger_dir / "accepted.jsonl"
        rejected_path = ledger_dir / "rejected.jsonl"
        accepted = self.load_jsonl(accepted_path)
        rejected = self.load_jsonl(rejected_path)
        records: list[dict[str, Any]] = []
        accepted_ids: set[str] = set()
        durable_provenance: set[str] = set()
        superseded_lines = {
            value.get("supersedes_legacy_line")
            for _, value, _ in accepted
            if isinstance(value.get("supersedes_legacy_line"), int)
        }
        seen_event_ids: set[str] = set()
        for ledger_name, path, entries in (
            ("accepted", accepted_path, accepted),
            ("rejected", rejected_path, rejected),
        ):
            for line_number, value, digest in entries:
                mechanism_id = value.get("mechanism_id")
                event_id = value.get("event_id")
                if isinstance(event_id, str):
                    if event_id in seen_event_ids:
                        self.add_finding(
                            "DUPLICATE_LEDGER_EVENT_ID", path, f"duplicate event at line {line_number}", event_id
                        )
                    seen_event_ids.add(event_id)
                if not isinstance(mechanism_id, str) or not mechanism_id:
                    self.add_finding("PARSE_ERROR", path, f"line {line_number}: mechanism_id is required")
                    continue
                if ledger_name == "accepted":
                    accepted_ids.add(mechanism_id)
                    if mechanism_id not in self.mechanisms:
                        self.add_finding(
                            "ORPHAN_ACCEPTED_LEDGER_EVENT", path, "mechanism is absent from registry", mechanism_id
                        )
                    elif self.mechanisms[mechanism_id].get("status") != "accepted":
                        self.add_finding(
                            "LEDGER_STATUS_MISMATCH", path, "accepted ledger disagrees with registry", mechanism_id
                        )
                    source = value.get("source") or value.get("source_path")
                    source_exists = isinstance(source, str) and (self.root / source).exists()
                    has_commit = isinstance(value.get("source_commit"), str) and bool(value["source_commit"])
                    if source_exists and (value.get("event_type") is None or has_commit):
                        durable_provenance.add(mechanism_id)
                    if isinstance(value.get("run_dir"), str) and line_number not in superseded_lines:
                        run_path = self.root / value["run_dir"]
                        if not run_path.exists():
                            self.add_finding(
                                "DANGLING_LEDGER_RUN",
                                path,
                                f"line {line_number}: run_dir is unavailable",
                                mechanism_id,
                            )
                records.append(
                    {
                        "ledger": ledger_name,
                        "line": line_number,
                        "event_id": event_id,
                        "mechanism_id": mechanism_id,
                        "event_type": value.get("event_type", "legacy"),
                        "digest": digest,
                    }
                )
        for mechanism_id, mechanism in sorted(self.mechanisms.items()):
            if mechanism.get("status") == "accepted" and mechanism_id not in accepted_ids:
                self.add_finding(
                    "MISSING_ACCEPTED_LEDGER_EVENT",
                    accepted_path,
                    "accepted registry mechanism has no accepted-ledger event",
                    mechanism_id,
                )
            if mechanism.get("status") == "accepted" and mechanism_id not in durable_provenance:
                self.add_finding(
                    "DANGLING_LEDGER_SOURCE",
                    accepted_path,
                    "accepted mechanism has no durable public provenance event",
                    mechanism_id,
                )
        return self._category(
            "researcher/mechanisms/ledgers/*.jsonl",
            records,
            accepted_event_count=len(accepted),
            rejected_event_count=len(rejected),
            accepted_mechanism_count=len(accepted_ids),
        )

    def build_corpus_index(self) -> tuple[dict[str, Any], dict[str, Any]]:
        path = self.root / "researcher" / "corpus" / "index.json"
        value = self.load_json(path)
        records: list[dict[str, Any]] = []
        mechanism_relations: list[dict[str, str]] = []
        claim_relations: list[dict[str, str]] = []
        indexed_skills: set[str] = set()
        indexed_mechanisms: set[str] = set()
        indexed_claims: set[str] = set()
        if not isinstance(value, dict) or not isinstance(value.get("skills"), list):
            self.add_finding("UNKNOWN_SCHEMA", path, "corpus index must contain a skills list")
            return self._category("researcher/corpus/index.json", records), {
                "skill_mechanisms": [],
                "skill_claims": [],
                "skill_activation_cases": [],
            }
        for item in value["skills"]:
            if not isinstance(item, dict):
                self.add_finding("UNKNOWN_SCHEMA", path, "skill entry must be an object")
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name:
                self.add_finding("UNKNOWN_SCHEMA", path, "skill entry is missing name")
                continue
            if name in indexed_skills:
                self.add_finding("DUPLICATE_SKILL_ID", path, "duplicate corpus skill", name)
            indexed_skills.add(name)
            if name not in self.skill_names:
                self.add_finding("DANGLING_SKILL", path, "indexed skill is not published", name)
            expected_path = f"skills/{name}/SKILL.md"
            if item.get("path") != expected_path:
                self.add_finding(
                    "SKILL_PATH_MISMATCH", path, f"expected {expected_path}, got {item.get('path')}", name
                )
            mechanism_ids = item.get("mechanism_ids", [])
            claim_ids = item.get("claim_ids", [])
            if not isinstance(mechanism_ids, list) or not isinstance(claim_ids, list):
                self.add_finding("UNKNOWN_SCHEMA", path, "mechanism_ids and claim_ids must be lists", name)
                continue
            for mechanism_id in mechanism_ids:
                if mechanism_id not in self.mechanisms:
                    self.add_finding(
                        "DANGLING_MECHANISM", path, "unknown mechanism reference", str(mechanism_id)
                    )
                    continue
                indexed_mechanisms.add(mechanism_id)
                owner = self.mechanisms[mechanism_id].get("owning_skill")
                if owner != name:
                    self.add_finding(
                        "MECHANISM_OWNER_MISMATCH",
                        path,
                        f"registry owner is {owner!r}, index consumer is {name!r}",
                        mechanism_id,
                    )
                mechanism_relations.append({"skill_id": name, "mechanism_id": mechanism_id})
            for claim_id in claim_ids:
                if claim_id not in self.claims:
                    self.add_finding("DANGLING_CLAIM", path, "unknown claim reference", str(claim_id))
                    continue
                indexed_claims.add(claim_id)
                relation = "owned" if self.claims[claim_id].get("owning_skill") == name else "related"
                claim_relations.append(
                    {"skill_id": name, "claim_id": claim_id, "relationship": relation}
                )
            skill_path = self.root / expected_path
            body_claim_ids: list[str] = []
            if skill_path.exists():
                text = skill_path.read_text(encoding="utf-8")
                body_claim_ids = sorted(claim_id for claim_id in self.claims if claim_id in text)
            records.append(
                {
                    "id": name,
                    "path": item.get("path"),
                    "activation_scenarios": item.get("activation_scenarios", []),
                    "mechanism_ids": sorted(mechanism_ids),
                    "claim_ids": sorted(claim_ids),
                    "explicit_body_claim_ids": body_claim_ids,
                }
            )
        for skill_id in sorted(self.skill_names - indexed_skills):
            self.add_finding("UNINDEXED_SKILL", path, "published skill is absent from corpus index", skill_id)
        for mechanism_id in sorted(set(self.mechanisms) - indexed_mechanisms):
            self.add_finding(
                "UNINDEXED_MECHANISM", path, "registry mechanism is absent from corpus relationships", mechanism_id
            )
        for claim_id in sorted(set(self.claims) - indexed_claims):
            self.add_finding("UNINDEXED_CLAIM", path, "claim is absent from corpus relationships", claim_id)
        return (
            self._category(
                "researcher/corpus/index.json",
                sorted(records, key=lambda item: item["id"]),
                semantics="curated_relationship_source",
            ),
            {
                "skill_mechanisms": sorted(
                    mechanism_relations, key=lambda item: (item["skill_id"], item["mechanism_id"])
                ),
                "skill_claims": sorted(
                    claim_relations, key=lambda item: (item["skill_id"], item["claim_id"])
                ),
                "skill_activation_cases": [],
            },
        )

    def build_activation_cases(self) -> dict[str, Any]:
        path = self.root / "researcher" / "fixtures" / "activation-cases.jsonl"
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        for line_number, value, digest in self.load_jsonl(path):
            case_id = value.get("case_id")
            if not isinstance(case_id, str) or not case_id:
                self.add_finding("PARSE_ERROR", path, f"line {line_number}: case_id is required")
                continue
            if case_id in seen:
                self.add_finding(
                    "DUPLICATE_ACTIVATION_CASE_ID", path, f"duplicate at line {line_number}", case_id
                )
            seen.add(case_id)
            referenced = [value.get("expected_primary_skill")]
            referenced.extend(value.get("acceptable_secondary_skills", []))
            referenced.extend(value.get("rejected_skills", []))
            for skill_id in referenced:
                if skill_id not in self.skill_names:
                    self.add_finding(
                        "DANGLING_SKILL", path, f"activation case references {skill_id!r}", case_id
                    )
            records.append(
                {
                    "id": case_id,
                    "expected_primary_skill": value.get("expected_primary_skill"),
                    "line": line_number,
                    "digest": digest,
                }
            )
        return self._category(
            "researcher/fixtures/activation-cases.jsonl", sorted(records, key=lambda item: item["id"])
        )

    def build_router_prompts(self) -> dict[str, Any]:
        path = self.root / "researcher" / "benchmarks" / "router" / "prompts.jsonl"
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        for line_number, value, digest in self.load_jsonl(path):
            prompt_id = value.get("prompt_id")
            if not isinstance(prompt_id, str) or not prompt_id:
                self.add_finding("PARSE_ERROR", path, f"line {line_number}: prompt_id is required")
                continue
            if prompt_id in seen:
                self.add_finding(
                    "DUPLICATE_ROUTER_PROMPT_ID", path, f"duplicate at line {line_number}", prompt_id
                )
            seen.add(prompt_id)
            referenced = [value.get("expected_primary_skill")]
            referenced.extend(value.get("acceptable_secondary_skills", []))
            referenced.extend(value.get("rejected_skills", []))
            for skill_id in referenced:
                if skill_id not in self.skill_names:
                    self.add_finding("DANGLING_SKILL", path, f"router prompt references {skill_id!r}", prompt_id)
            if not isinstance(value.get("prompt"), str) or not value["prompt"].strip():
                self.add_finding("UNKNOWN_SCHEMA", path, "router prompt text is required", prompt_id)
            records.append(
                {
                    "id": prompt_id,
                    "expected_primary_skill": value.get("expected_primary_skill"),
                    "line": line_number,
                    "digest": digest,
                }
            )
        return self._category(
            "researcher/benchmarks/router/prompts.jsonl", sorted(records, key=lambda item: item["id"])
        )

    def build_adversarial(self) -> tuple[dict[str, Any], dict[str, Any]]:
        scenario_dir = self.root / "researcher" / "benchmarks" / "scenarios"
        scenario_records: list[dict[str, Any]] = []
        scenarios: dict[str, dict[str, Any]] = {}
        for path in sorted(scenario_dir.glob("*.jsonl")):
            for line_number, value, digest in self.load_jsonl(path):
                scenario_id = value.get("scenario_id")
                if not isinstance(scenario_id, str) or not scenario_id:
                    self.add_finding("PARSE_ERROR", path, f"line {line_number}: scenario_id is required")
                    continue
                if scenario_id in scenarios:
                    self.add_finding(
                        "DUPLICATE_SCENARIO_ID", path, f"duplicate at line {line_number}", scenario_id
                    )
                scenarios[scenario_id] = value
                scenario_records.append(
                    {
                        "id": scenario_id,
                        "expected_gate": value.get("expected_gate"),
                        "path": self.relative(path),
                        "line": line_number,
                        "digest": digest,
                    }
                )
        golden_path = self.root / "researcher" / "benchmarks" / "goldens" / "adversarial-goldens.json"
        golden_value = self.load_json(golden_path)
        golden_records: list[dict[str, Any]] = []
        if not isinstance(golden_value, dict):
            self.add_finding("UNKNOWN_SCHEMA", golden_path, "golden file must be an object")
            golden_value = {}
        for scenario_id in sorted(set(scenarios) - set(golden_value)):
            self.add_finding("MISSING_GOLDEN", golden_path, "scenario has no golden", scenario_id)
        for scenario_id in sorted(set(golden_value) - set(scenarios)):
            self.add_finding("ORPHAN_GOLDEN", golden_path, "golden has no scenario", scenario_id)
        for scenario_id, golden in sorted(golden_value.items()):
            expected_gate = golden.get("expected_gate") if isinstance(golden, dict) else None
            if scenario_id in scenarios and expected_gate != scenarios[scenario_id].get("expected_gate"):
                self.add_finding(
                    "GOLDEN_GATE_MISMATCH", golden_path, "golden and scenario expected_gate differ", scenario_id
                )
            golden_records.append(
                {"id": scenario_id, "expected_gate": expected_gate, "digest": record_digest(golden)}
            )
        return (
            self._category(
                "researcher/benchmarks/scenarios/*.jsonl",
                sorted(scenario_records, key=lambda item: item["id"]),
            ),
            self._category("researcher/benchmarks/goldens/adversarial-goldens.json", golden_records),
        )

    def build_effectiveness_tasks(self) -> dict[str, Any]:
        tasks_dir = self.root / "researcher" / "benchmarks" / "effectiveness" / "tasks"
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        if not tasks_dir.exists():
            self.add_finding("INVALID_EFFECTIVENESS_TASK", tasks_dir, "tasks directory is missing")
            return self._category("researcher/benchmarks/effectiveness/tasks/*", records)
        for task_dir in sorted(path for path in tasks_dir.iterdir() if path.is_dir()):
            metadata_path = task_dir / "metadata.json"
            metadata = self.load_json(metadata_path)
            if not isinstance(metadata, dict):
                self.add_finding("INVALID_EFFECTIVENESS_TASK", metadata_path, "metadata must be an object")
                continue
            task_id = metadata.get("id")
            slug = metadata.get("slug")
            if not isinstance(task_id, str) or not isinstance(slug, str):
                self.add_finding("INVALID_EFFECTIVENESS_TASK", metadata_path, "id and slug are required")
                continue
            if task_id in seen:
                self.add_finding(
                    "DUPLICATE_EFFECTIVENESS_TASK_ID", metadata_path, "duplicate task id", task_id
                )
            seen.add(task_id)
            expected_dir = f"{task_id}-{slug}"
            if task_dir.name != expected_dir:
                self.add_finding(
                    "INVALID_EFFECTIVENESS_TASK",
                    task_dir,
                    f"directory must be named {expected_dir}",
                    task_id,
                )
            required = [task_dir / "README.md", task_dir / "task.md", task_dir / "verify.sh"]
            starting = task_dir / "starting"
            for required_path in required:
                if not required_path.is_file():
                    self.add_finding(
                        "INVALID_EFFECTIVENESS_TASK", required_path, "required task file is missing", task_id
                    )
                else:
                    self.add_source(required_path)
            if not starting.is_dir() or not any(path.is_file() for path in starting.rglob("*")):
                self.add_finding(
                    "INVALID_EFFECTIVENESS_TASK", starting, "starting directory must contain a file", task_id
                )
            else:
                for starting_file in sorted(path for path in starting.rglob("*") if path.is_file()):
                    self.add_source(starting_file)
            verify = task_dir / "verify.sh"
            if verify.exists() and not (verify.stat().st_mode & stat.S_IXUSR):
                self.add_finding(
                    "INVALID_EFFECTIVENESS_TASK", verify, "verify.sh must be executable", task_id
                )
            for key in ("target_skill", "irrelevant_skill"):
                skill_id = metadata.get(key)
                if skill_id != "none" and skill_id not in self.skill_names:
                    self.add_finding(
                        "DANGLING_SKILL", metadata_path, f"{key} references {skill_id!r}", task_id
                    )
            records.append(
                {
                    "id": task_id,
                    "slug": slug,
                    "path": self.relative(task_dir),
                    "target_skill": metadata.get("target_skill"),
                    "irrelevant_skill": metadata.get("irrelevant_skill"),
                    "metadata_digest": record_digest(metadata),
                }
            )
        return self._category(
            "researcher/benchmarks/effectiveness/tasks/*", sorted(records, key=lambda item: item["id"])
        )

    def build_examples(self) -> dict[str, Any]:
        examples_dir = self.root / "examples"
        records: list[dict[str, Any]] = []
        for example_dir in sorted(path for path in examples_dir.iterdir() if path.is_dir()):
            readme = example_dir / "README.md"
            if not readme.exists():
                self.add_finding("PARSE_ERROR", example_dir, "example directory is missing README.md")
                continue
            digest, _ = self.add_source(readme)
            records.append({"id": example_dir.name, "path": self.relative(example_dir), "digest": digest})
        return self._category("examples/*/README.md", records)

    def build_benchmark_runners(self) -> dict[str, Any]:
        runner_dir = self.root / "researcher" / "benchmarks" / "sdk-runner"
        records: list[dict[str, Any]] = []
        for relative in [
            "package.json",
            "package-lock.json",
            "tsconfig.json",
            "src/common.ts",
            "src/runRouter.ts",
            "src/runEffectiveness.ts",
        ]:
            path = runner_dir / relative
            if not path.exists():
                self.add_finding("PARSE_ERROR", path, "benchmark runner contract file is missing", relative)
                continue
            digest, size = self.add_source(path)
            records.append(
                {
                    "id": relative.replace("/", ":"),
                    "path": self.relative(path),
                    "digest": digest,
                    "size_bytes": size,
                }
            )
        return self._category(
            "researcher/benchmarks/sdk-runner",
            sorted(records, key=lambda item: item["id"]),
            status={"router": "operational", "effectiveness": "scaffold"},
        )

    def build_manifests(self) -> dict[str, Any]:
        marketplace_path = self.root / ".claude-plugin" / "marketplace.json"
        plugin_path = self.root / ".plugin" / "plugin.json"
        root_skill_path = self.root / "SKILL.md"
        marketplace = self.load_json(marketplace_path)
        plugin = self.load_json(plugin_path)
        root_skill_digest, _ = self.add_source(root_skill_path)
        root_version: str | None = None
        try:
            version_lines = [
                line.partition(":")[2].strip()
                for line in root_skill_path.read_text(encoding="utf-8").splitlines()
                if line.startswith("**Version**:")
            ]
            if len(version_lines) == 1:
                root_version = version_lines[0]
            else:
                self.add_finding("UNKNOWN_SCHEMA", root_skill_path, "expected exactly one **Version** line")
        except (OSError, UnicodeError) as exc:
            self.add_finding("PARSE_ERROR", root_skill_path, str(exc))
        marketplace_version = None
        marketplace_skills: list[str] = []
        if isinstance(marketplace, dict):
            marketplace_version = marketplace.get("metadata", {}).get("version")
            plugins = marketplace.get("plugins")
            if isinstance(plugins, list) and len(plugins) == 1 and isinstance(plugins[0], dict):
                raw_paths = plugins[0].get("skills", [])
                if isinstance(raw_paths, list):
                    marketplace_skills = sorted(Path(value).name for value in raw_paths if isinstance(value, str))
        plugin_version = plugin.get("version") if isinstance(plugin, dict) else None
        versions = {
            "marketplace": marketplace_version,
            "open_plugin": plugin_version,
            "collection_skill": root_version,
        }
        if len(set(versions.values())) != 1:
            self.add_finding("PLUGIN_VERSION_MISMATCH", plugin_path, f"version surfaces differ: {versions}")
        actual_skills = sorted(self.skill_names)
        if marketplace_skills != actual_skills:
            self.add_finding(
                "MANIFEST_SKILL_MISMATCH",
                marketplace_path,
                f"manifest={marketplace_skills}, published={actual_skills}",
            )
        records = [
            {"id": "claude-marketplace", "path": self.relative(marketplace_path), "version": marketplace_version},
            {"id": "open-plugin", "path": self.relative(plugin_path), "version": plugin_version},
            {
                "id": "collection-skill",
                "path": self.relative(root_skill_path),
                "version": root_version,
                "digest": root_skill_digest,
            },
        ]
        return self._category(
            "publication manifests",
            records,
            versions=versions,
            skill_sets={"published": actual_skills, "marketplace": marketplace_skills},
        )

    def build_validators(self) -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        for descriptor in VALIDATOR_OWNERSHIP:
            path = self.root / descriptor["path"]
            if not path.exists():
                self.add_finding("PARSE_ERROR", path, "declared validator is missing", descriptor["id"])
                continue
            digest, _ = self.add_source(path)
            records.append({**descriptor, "digest": digest})
        return self._category("declared validator ownership", records)

    def build_schemas(self) -> dict[str, Any]:
        path = self.root / "researcher" / "corpus" / "inventory.schema.json"
        value = self.load_json(path)
        records: list[dict[str, Any]] = []
        if isinstance(value, dict):
            records.append(
                {
                    "id": "repository-inventory-v1",
                    "path": self.relative(path),
                    "schema_id": value.get("$id"),
                    "digest": record_digest(value),
                }
            )
        return self._category("researcher/corpus/inventory.schema.json", records)

    def build_export_contracts(self) -> dict[str, Any]:
        paths = [
            "governance/export-policy.yaml",
            "governance/export-policy.schema.json",
            "researcher/exports/schemas/export-records.schema.json",
            "researcher/fixtures/export/restricted-request.json",
            "researcher/fixtures/export/private-root/restricted-source.json",
            "researcher/exports/examples/restricted-citation-v1/export-manifest.json",
            "researcher/exports/examples/restricted-citation-v1/citation/restricted-fixture.json",
            "researcher/scripts/export_policy.py",
        ]
        records: list[dict[str, Any]] = []
        for relative in paths:
            path = self.root / relative
            if not path.exists():
                self.add_finding("PARSE_ERROR", path, "export contract artifact is missing", relative)
                continue
            digest, size = self.add_source(path)
            records.append({"id": relative, "path": relative, "digest": digest, "size_bytes": size})
        return self._category("governance/export-policy.yaml and export fixtures", records)

    def build_schema_contracts(self) -> dict[str, Any]:
        registry_path = self.root / "researcher/schemas/registry.json"
        registry = self.load_json(registry_path)
        records: list[dict[str, Any]] = []
        if not isinstance(registry, dict) or not isinstance(registry.get("entries"), list):
            self.add_finding("UNKNOWN_SCHEMA", registry_path, "schema registry has no entries array")
            return self._category("researcher/schemas/registry.json", records)
        seen: set[tuple[str, str]] = set()
        id_prefixes = registry.get("id_prefixes")
        registered_prefixes: dict[str, str] = {}
        for index, entry in enumerate(registry["entries"]):
            if not isinstance(entry, dict):
                self.add_finding("UNKNOWN_SCHEMA", registry_path, f"entry {index} is not an object")
                continue
            kind = entry.get("kind")
            version = entry.get("version")
            key = (kind, version)
            if not isinstance(kind, str) or not isinstance(version, str):
                self.add_finding("UNKNOWN_SCHEMA", registry_path, f"entry {index} lacks kind/version")
                continue
            if key in seen:
                self.add_finding("DUPLICATE_SCHEMA_ID", registry_path, "kind/version is duplicated", kind)
            seen.add(key)
            prefix = entry.get("id_prefix")
            if isinstance(prefix, str):
                registered_prefixes[prefix] = kind
            schema_relative = entry.get("schema_path")
            expected_digest = entry.get("schema_digest")
            if not isinstance(schema_relative, str) or not isinstance(expected_digest, str):
                self.add_finding("UNKNOWN_SCHEMA", registry_path, "schema path or digest is missing", kind)
                continue
            schema_path = self.root / schema_relative
            if not schema_path.is_file():
                self.add_finding("PARSE_ERROR", schema_path, "registered schema file is missing", kind)
                continue
            digest, _ = self.add_source(schema_path)
            if digest != expected_digest:
                self.add_finding(
                    "SCHEMA_DIGEST_MISMATCH",
                    schema_path,
                    f"registry={expected_digest}, actual={digest}",
                    kind,
                )
            golden_paths = entry.get("golden_paths")
            if not isinstance(golden_paths, list) or not golden_paths:
                self.add_finding("UNKNOWN_SCHEMA", registry_path, "schema has no golden", kind)
            else:
                for golden_relative in golden_paths:
                    if not isinstance(golden_relative, str):
                        self.add_finding("UNKNOWN_SCHEMA", registry_path, "golden path is not text", kind)
                        continue
                    golden_path = self.root / golden_relative
                    if not golden_path.is_file():
                        self.add_finding("PARSE_ERROR", golden_path, "registered golden is missing", kind)
                    else:
                        self.add_source(golden_path)
            records.append(
                {
                    "id": f"{kind}@{version}",
                    "kind": kind,
                    "version": version,
                    "schema_path": schema_relative,
                    "schema_digest": digest,
                    "owner_spec": entry.get("owner_spec"),
                    "status": entry.get("status"),
                    "compatibility": entry.get("compatibility"),
                    "id_prefix": prefix,
                }
            )
        if id_prefixes != registered_prefixes:
            self.add_finding(
                "SCHEMA_PREFIX_MISMATCH",
                registry_path,
                "registry id_prefixes disagree with schema entries",
            )
        supporting_paths = [
            "researcher/schemas/registry.schema.json",
            "researcher/schemas/fixtures/canonicalization-v1.json",
            "researcher/schemas/fixtures/editable-surface-policy-v1.json",
            "researcher/schemas/public-legacy-sources.json",
            "researcher/schemas/generated/conformance-report.json",
            "researcher/schemas/generated/current-artifacts-report.json",
            "researcher/schemas/generated/migration-dry-run.json",
            "researcher/schemas/generated/compatibility-matrix.md",
            "researcher/schemas/README.md",
            "researcher/artifacts/README.md",
            "researcher/runbooks/schema-migration.md",
            "researcher/scripts/schema_contract.py",
            "researcher/scripts/artifact_store.py",
            "researcher/scripts/migrate_legacy.py",
            "researcher/scripts/tests/test_schema_contract.py",
            "researcher/scripts/tests/test_artifact_store.py",
            "researcher/schemas/typescript/.gitignore",
            "researcher/schemas/typescript/package.json",
            "researcher/schemas/typescript/package-lock.json",
            "researcher/schemas/typescript/tsconfig.json",
            "researcher/schemas/typescript/src/canonicalize.ts",
            "researcher/schemas/typescript/src/conformance.ts",
            "researcher/schemas/typescript/src/errors.ts",
            "researcher/schemas/typescript/src/index.ts",
            "researcher/schemas/typescript/src/json.ts",
            "researcher/schemas/typescript/src/registry.ts",
            "researcher/schemas/typescript/src/semantics.ts",
            "researcher/schemas/typescript/test/conformance.test.ts",
            "researcher/schemas/typescript/test/runtime-registry.test.ts",
        ]
        for relative in supporting_paths:
            path = self.root / relative
            if not path.is_file():
                self.add_finding("PARSE_ERROR", path, "schema contract artifact is missing", relative)
            else:
                self.add_source(path)
        return self._category(
            "researcher/schemas/registry.json",
            sorted(records, key=lambda item: item["id"]),
            canonicalization_profile=registry.get("canonicalization_profile"),
            id_prefix_count=len(registered_prefixes),
        )

    def validate_live_document_links(self) -> None:
        for relative, required_link in LIVE_DOCUMENT_LINKS.items():
            path = self.root / relative
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                self.add_finding("PARSE_ERROR", path, str(exc))
                continue
            if required_link not in text:
                self.add_finding(
                    "STALE_COUNT",
                    path,
                    f"live document must link to generated inventory: {required_link}",
                )


def render_summary(inventory: dict[str, Any]) -> str:
    artifacts = inventory["artifacts"]
    rows = [
        ("Published skills", artifacts["skills"]["count"]),
        ("Mechanism registry records", artifacts["mechanisms"]["count"]),
        ("Accepted-ledger events", artifacts["mechanism_ledgers"]["accepted_event_count"]),
        ("Rejected-ledger events", artifacts["mechanism_ledgers"]["rejected_event_count"]),
        ("Provenance-tracked claims", artifacts["claims"]["count"]),
        ("Activation cases", artifacts["activation_cases"]["count"]),
        ("Router prompts", artifacts["router_prompts"]["count"]),
        ("Adversarial scenarios", artifacts["adversarial_scenarios"]["count"]),
        ("Adversarial goldens", artifacts["adversarial_goldens"]["count"]),
        ("Effectiveness tasks", artifacts["effectiveness_tasks"]["count"]),
        ("Example projects", artifacts["examples"]["count"]),
    ]
    lines = [
        "<!-- GENERATED by researcher/scripts/build_inventory.py. DO NOT EDIT. -->",
        "# Live corpus inventory",
        "",
        "This is a generated view of canonical repository artifacts, not a second source of truth.",
        "",
        f"- Schema: `{inventory['schema_version']}`",
        f"- Source tree: `{inventory['source_tree_digest']}`",
        f"- Unresolved references: `{len(inventory['unresolved_references'])}`",
        "",
        "| Artifact | Count |",
        "| --- | ---: |",
        *[f"| {label} | {count} |" for label, count in rows],
        "",
        "## Compatibility",
        "",
        f"- Plugin version: `{artifacts['manifests']['versions']['open_plugin']}`",
        f"- Router runner: `{inventory['compatibility']['benchmark_runner']['router']}`",
        f"- Effectiveness runner: `{inventory['compatibility']['benchmark_runner']['effectiveness']}`",
        "",
        (
            "Historical reports retain the counts and measurements from their dated snapshot. "
            "Current documents should link here instead of copying live totals."
        ),
        "",
    ]
    return "\n".join(lines)


def print_findings(findings: Iterable[Finding]) -> None:
    for finding in findings:
        identity = f" ({finding.artifact_id})" if finding.artifact_id else ""
        print(f"[{finding.code}] {finding.path}{identity}: {finding.message}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="fail on unresolved references or generated drift")
    modes.add_argument("--write", action="store_true", help="atomically refresh generated inventory and summary")
    modes.add_argument("--json", action="store_true", help="print the generated inventory without writing")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    inventory_path = args.inventory or root / "researcher" / "corpus" / "inventory.json"
    summary_path = args.summary or root / "researcher" / "generated" / "corpus-summary.md"
    builder = InventoryBuilder(root)
    try:
        inventory = builder.build()
    except (InventoryError, OSError) as exc:
        print(f"[PARSE_ERROR] {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(pretty_json(inventory), end="")
        print_findings(builder.findings)
        return 1 if builder.findings else 0

    if builder.findings:
        print_findings(builder.findings)
        print(f"Inventory generation failed: {len(builder.findings)} unresolved finding(s)", file=sys.stderr)
        return 1

    inventory_text = pretty_json(inventory)
    summary_text = render_summary(inventory)
    if args.write:
        atomic_write_text(inventory_path, inventory_text)
        atomic_write_text(summary_path, summary_text)
        print(
            f"Inventory written: {artifacts_count(inventory)} artifact records, "
            f"digest {inventory['source_tree_digest'][7:19]}"
        )
        return 0

    drift: list[Finding] = []
    if not inventory_path.exists() or inventory_path.read_text(encoding="utf-8") != inventory_text:
        drift.append(
            Finding("GENERATED_DRIFT", str(inventory_path.relative_to(root)), None, "run build_inventory.py --write")
        )
    if not summary_path.exists() or summary_path.read_text(encoding="utf-8") != summary_text:
        drift.append(
            Finding("STALE_COUNT", str(summary_path.relative_to(root)), None, "generated summary is stale")
        )
    if drift:
        print_findings(drift)
        return 1
    print(
        f"Inventory check passed: {artifacts_count(inventory)} artifact records, "
        f"{len(inventory['sources'])} canonical sources, digest {inventory['source_tree_digest'][7:19]}"
    )
    return 0


def artifacts_count(inventory: dict[str, Any]) -> int:
    return sum(
        category.get("count", 0)
        for category in inventory["artifacts"].values()
        if isinstance(category, dict)
    )


if __name__ == "__main__":
    raise SystemExit(main())
