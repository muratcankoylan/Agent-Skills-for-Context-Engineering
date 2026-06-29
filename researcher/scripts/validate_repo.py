#!/usr/bin/env python3
"""Validate the context-engineering skill corpus and researcher harness.

This script is intentionally deterministic. It checks structure, manifests, and
machine-readable artifacts without calling an LLM.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from skill_frontmatter import parse_frontmatter as parse_skill_frontmatter


REQUIRED_RESEARCHER_FILES = [
    "README.md",
    "source-registry.md",
    "mechanisms/README.md",
    "mechanisms/registry.jsonl",
    "mechanisms/ledgers/accepted.jsonl",
    "mechanisms/ledgers/rejected.jsonl",
    "claims/README.md",
    "claims/index.jsonl",
    "corpus/index.json",
    "benchmarks/README.md",
    "benchmarks/scenarios/adversarial.jsonl",
    "benchmarks/goldens/adversarial-goldens.json",
    "rubrics/content-curation.md",
    "rubrics/skill-change.md",
    "rubrics/harness-change.md",
    "rubrics/pairwise-skill-revision.md",
    "templates/source-evaluation.json",
    "templates/skill-proposal.md",
    "templates/mechanism-proposal.jsonl",
    "templates/research-thread.md",
    "runbooks/autonomous-research-loop.md",
    "runbooks/pr-readiness.md",
    "scripts/validate_repo.py",
    "scripts/validate_run.py",
    "scripts/research_loop.py",
    "scripts/novelty_check.py",
    "scripts/compare_skill_revisions.py",
    "scripts/check_activation_cases.py",
    "scripts/run_benchmarks.py",
    "fixtures/activation-cases.jsonl",
    "reports/benchmark-history.jsonl",
]


REQUIRED_SOURCE_EVAL_KEYS = {
    "evaluation_id",
    "timestamp",
    "source",
    "gatekeeper",
    "scoring",
    "decision",
    "extraction",
}


@dataclass
class Finding:
    severity: str
    path: str
    message: str


class Validator:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.findings: list[Finding] = []

    def error(self, path: Path | str, message: str) -> None:
        self.findings.append(Finding("error", self.rel(path), message))

    def warn(self, path: Path | str, message: str) -> None:
        self.findings.append(Finding("warning", self.rel(path), message))

    def rel(self, path: Path | str) -> str:
        p = Path(path)
        if not p.is_absolute():
            return str(p)
        try:
            return str(p.relative_to(self.root))
        except ValueError:
            return str(p)

    def run(self) -> dict[str, Any]:
        skill_names = self.validate_skills()
        self.validate_manifests(skill_names)
        self.validate_docs(skill_names)
        self.validate_researcher()
        self.validate_rubrics()
        self.validate_mechanisms(skill_names)
        self.validate_claims(skill_names)
        self.validate_corpus_index(skill_names)
        self.validate_activation_cases(skill_names)
        self.validate_benchmark_scenarios()
        self.validate_runs()
        self.validate_root_provenance()
        self.validate_source_evaluations()
        errors = sum(1 for f in self.findings if f.severity == "error")
        warnings = sum(1 for f in self.findings if f.severity == "warning")
        return {
            "ok": errors == 0,
            "summary": {
                "errors": errors,
                "warnings": warnings,
                "skill_count": len(skill_names),
            },
            "findings": [asdict(f) for f in self.findings],
        }

    def validate_skills(self) -> list[str]:
        skills_dir = self.root / "skills"
        if not skills_dir.exists():
            self.error(skills_dir, "skills directory missing")
            return []

        skill_names: list[str] = []
        for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                self.error(skill_file, "missing SKILL.md")
                continue

            text = skill_file.read_text(encoding="utf-8")
            lines = text.splitlines()
            frontmatter = self.parse_frontmatter(text, skill_file)
            name = str(frontmatter.get("name", "")).strip()
            description = str(frontmatter.get("description", "")).strip()
            skill_names.append(skill_dir.name)

            if not name:
                self.error(skill_file, "frontmatter missing name")
            elif name != skill_dir.name:
                self.error(skill_file, f"name '{name}' does not match directory '{skill_dir.name}'")
            if name and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
                self.error(skill_file, "name must be lowercase kebab-case without repeated hyphens")
            if not description:
                self.error(skill_file, "frontmatter missing description")
            elif len(description) > 1024:
                self.error(skill_file, "description exceeds 1024 characters")
            if re.search(r"\b(I can|Use me|You can use this)\b", description):
                self.warn(skill_file, "description may not be third person")
            if len(lines) > 500:
                self.error(skill_file, f"SKILL.md exceeds 500 lines ({len(lines)})")
            for section in [
                "## When to Activate",
                "## Core Concepts",
                "## Practical Guidance",
                "## Examples",
                "## Guidelines",
                "## Gotchas",
                "## Integration",
                "## References",
            ]:
                if section not in text:
                    self.error(skill_file, f"missing required section: {section}")
            if "Do not activate" not in text:
                self.warn(skill_file, "missing explicit non-activation boundary")

        return sorted(skill_names)

    def parse_frontmatter(self, text: str, path: Path) -> dict[str, str]:
        data, issues = parse_skill_frontmatter(text)
        for issue in issues:
            self.error(path, issue)
        return {key: str(value) for key, value in data.items()}

    def validate_manifests(self, skill_names: list[str]) -> None:
        marketplace_path = self.root / ".claude-plugin" / "marketplace.json"
        plugin_path = self.root / ".plugin" / "plugin.json"
        marketplace = self.load_json(marketplace_path)
        plugin = self.load_json(plugin_path)
        if not marketplace or not plugin:
            return

        try:
            plugins = marketplace["plugins"]
            if len(plugins) != 1:
                self.error(marketplace_path, "marketplace must contain exactly one bundled plugin")
                return
            plugin_entry = plugins[0]
            if plugin_entry.get("source") != "./":
                self.error(marketplace_path, "plugin source must be './'")
            manifest_paths = plugin_entry["skills"]
        except (KeyError, IndexError, TypeError):
            self.error(marketplace_path, "plugins[0].skills missing or invalid")
            return

        manifest_names = sorted(Path(p).name for p in manifest_paths)
        if len(manifest_paths) != len(set(manifest_paths)):
            self.error(marketplace_path, "duplicate skill paths in marketplace manifest")
        if manifest_names != sorted(skill_names):
            self.error(
                marketplace_path,
                f"manifest skills differ from skills directory: manifest={manifest_names} skills={skill_names}",
            )
        for raw_path in manifest_paths:
            if not str(raw_path).startswith("./"):
                self.error(marketplace_path, f"skill path must start with './': {raw_path}")
                continue
            if Path(raw_path).is_absolute() or ".." in Path(raw_path).parts:
                self.error(marketplace_path, f"skill path escapes repo: {raw_path}")
                continue
            path = self.root / raw_path
            if not path.exists():
                self.error(marketplace_path, f"skill path does not exist: {raw_path}")

        marketplace_version = str(marketplace.get("metadata", {}).get("version", ""))
        plugin_version = str(plugin.get("version", ""))
        if marketplace_version != plugin_version:
            self.warn(
                plugin_path,
                f"plugin version {plugin_version} differs from marketplace metadata {marketplace_version}",
            )
        plugin_name = str(plugin.get("name", ""))
        marketplace_plugin_name = str(plugin_entry.get("name", ""))
        if plugin_name != marketplace_plugin_name:
            self.error(
                plugin_path,
                f"plugin name {plugin_name!r} differs from marketplace plugin {marketplace_plugin_name!r}",
            )
        self.validate_open_plugin_manifest(plugin_path, plugin, skill_names)

    def validate_open_plugin_manifest(
        self,
        plugin_path: Path,
        plugin: dict[str, Any],
        skill_names: list[str],
    ) -> None:
        raw_skills = plugin.get("skills")
        if raw_skills is None:
            return
        if isinstance(raw_skills, str):
            skill_paths = [raw_skills]
        elif isinstance(raw_skills, list) and all(isinstance(item, str) for item in raw_skills):
            skill_paths = list(raw_skills)
        else:
            self.error(plugin_path, "Open Plugins 'skills' field must be a string or list of strings")
            return

        discovered: set[str] = set()
        for raw_path in skill_paths:
            path = Path(raw_path)
            if not raw_path.startswith("./"):
                self.error(plugin_path, f"Open Plugins skill path must start with './': {raw_path}")
                continue
            if path.is_absolute() or ".." in path.parts:
                self.error(plugin_path, f"Open Plugins skill path escapes repo: {raw_path}")
                continue
            full_path = self.root / raw_path
            if not full_path.exists():
                self.error(plugin_path, f"Open Plugins skill path does not exist: {raw_path}")
                continue
            if (full_path / "SKILL.md").exists():
                discovered.add(full_path.name)
                continue
            if full_path.is_dir():
                discovered.update(sorted(p.name for p in full_path.iterdir() if (p / "SKILL.md").exists()))
                continue
            self.error(plugin_path, f"Open Plugins skill path is not a skill directory: {raw_path}")

        if sorted(discovered) != sorted(skill_names):
            self.error(
                plugin_path,
                f"Open Plugins skills differ from skills directory: manifest={sorted(discovered)} skills={skill_names}",
            )
        plugin_metadata_dir = plugin_path.parent
        unexpected = sorted(p.name for p in plugin_metadata_dir.iterdir() if p.name != "plugin.json")
        if unexpected:
            self.error(plugin_path, f"Open Plugins metadata directory must contain only plugin.json: {unexpected}")

    def validate_docs(self, skill_names: list[str]) -> None:
        readme = self.root / "README.md"
        if not readme.exists():
            self.error(readme, "required doc missing")
        else:
            text = readme.read_text(encoding="utf-8")
            for skill in skill_names:
                if f"skills/{skill}/" not in text and f"`{skill}`" not in text:
                    self.error(readme, f"missing exact published skill mention: {skill}")

        root_skill = self.root / "SKILL.md"
        if not root_skill.exists():
            self.error(root_skill, "required doc missing")
        else:
            text = root_skill.read_text(encoding="utf-8")
            for skill in skill_names:
                if f"skills/{skill}/SKILL.md" not in text:
                    self.error(root_skill, f"missing exact internal skill path: {skill}")

        claude = self.root / "CLAUDE.md"
        if claude.exists():
            text = claude.read_text(encoding="utf-8")
            expected = f"{len(skill_names)} skill"
            if expected not in text:
                self.warn(claude, f"does not mention current skill count phrase '{expected}'")

    def validate_researcher(self) -> None:
        researcher = self.root / "researcher"
        for relative in REQUIRED_RESEARCHER_FILES:
            path = researcher / relative
            if not path.exists():
                self.error(path, "required researcher OS file missing")
        for relative in ["templates/source-evaluation.json"]:
            self.load_json(researcher / relative)

        content_rubric = researcher / "rubrics" / "content-curation.md"
        if content_rubric.exists():
            text = content_rubric.read_text(encoding="utf-8")
            if "any failed gate rejects" not in text.lower() and "any gate fails" not in text.lower():
                self.warn(content_rubric, "gate failure semantics are not explicit")

    def validate_rubrics(self) -> None:
        rubric_requirements = {
            "content-curation.md": ["G1", "G2", "G3", "G4", "O1", "O2", "O3", "O4", "1.4", "0.9"],
            "skill-change.md": ["S1", "S2", "S3", "S4", "S5", "1.4"],
            "harness-change.md": ["H1", "H2", "H3", "H4", "H5", "1.5"],
            "pairwise-skill-revision.md": ["Behavioral Improvement", "Evidence Fidelity", "Activation Clarity", "Corpus Fit", "Simplicity"],
        }
        rubric_dir = self.root / "researcher" / "rubrics"
        for filename, required_terms in rubric_requirements.items():
            path = rubric_dir / filename
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            for term in required_terms:
                if term not in text:
                    self.error(path, f"missing rubric term or threshold: {term}")

    def validate_mechanisms(self, skill_names: list[str]) -> None:
        path = self.root / "researcher" / "mechanisms" / "registry.jsonl"
        if not path.exists():
            return
        claim_ids = {
            entry.get("claim_id")
            for _, entry in self.load_jsonl(self.root / "researcher" / "claims" / "index.jsonl")
            if entry.get("claim_id")
        }
        seen: set[str] = set()
        required = {"mechanism_id", "owning_skill", "status", "activation_scenario", "behavior_change", "evidence", "failure_modes"}
        valid_status = {"accepted", "candidate", "deprecated", "rejected"}
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                self.error(path, f"line {line_number} invalid JSON: {exc}")
                continue
            missing = required - set(entry)
            if missing:
                self.error(path, f"line {line_number} missing fields: {sorted(missing)}")
            mechanism_id = entry.get("mechanism_id")
            if mechanism_id in seen:
                self.error(path, f"duplicate mechanism_id: {mechanism_id}")
            if isinstance(mechanism_id, str):
                seen.add(mechanism_id)
                if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", mechanism_id):
                    self.error(path, f"invalid mechanism_id: {mechanism_id}")
            if entry.get("status") not in valid_status:
                self.error(path, f"line {line_number} invalid status: {entry.get('status')}")
            if entry.get("owning_skill") not in skill_names:
                self.error(path, f"line {line_number} owning_skill is not published: {entry.get('owning_skill')}")
            for key in ["activation_scenario", "behavior_change"]:
                if not isinstance(entry.get(key), str) or not entry.get(key, "").strip():
                    self.error(path, f"line {line_number} {key} must be a non-empty string")
            if not isinstance(entry.get("evidence"), list) or not entry.get("evidence"):
                self.error(path, f"line {line_number} evidence must be a non-empty list")
            else:
                for evidence in entry["evidence"]:
                    if not isinstance(evidence, str):
                        self.error(path, f"line {line_number} evidence entries must be strings")
                        continue
                    if re.match(r"https?://", evidence):
                        continue
                    if evidence in claim_ids:
                        continue
                    if not (self.root / evidence).exists():
                        self.error(path, f"line {line_number} evidence path does not exist: {evidence}")
            if not isinstance(entry.get("failure_modes"), list) or not entry.get("failure_modes"):
                self.error(path, f"line {line_number} failure_modes must be a non-empty list")

        for ledger_name in ["accepted.jsonl", "rejected.jsonl"]:
            ledger_path = self.root / "researcher" / "mechanisms" / "ledgers" / ledger_name
            for line_number, entry in self.load_jsonl(ledger_path):
                if not entry.get("mechanism_id"):
                    self.error(ledger_path, f"line {line_number} missing mechanism_id")
                if not entry.get("rationale"):
                    self.error(ledger_path, f"line {line_number} missing rationale")

    def validate_claims(self, skill_names: list[str]) -> None:
        path = self.root / "researcher" / "claims" / "index.jsonl"
        seen: set[str] = set()
        valid_strength = {"primary", "secondary", "anecdotal", "derived"}
        valid_volatility = {"low", "medium", "high"}
        for line_number, entry in self.load_jsonl(path):
            claim_id = entry.get("claim_id")
            if not isinstance(claim_id, str) or not claim_id:
                self.error(path, f"line {line_number} missing claim_id")
            elif claim_id in seen:
                self.error(path, f"duplicate claim_id: {claim_id}")
            else:
                seen.add(claim_id)
            if entry.get("owning_skill") not in skill_names:
                self.error(path, f"line {line_number} owning_skill is not published: {entry.get('owning_skill')}")
            for key in ["claim_text", "section", "source_url", "retrieved_at", "last_reviewed"]:
                if not isinstance(entry.get(key), str) or not entry.get(key, "").strip():
                    self.error(path, f"line {line_number} {key} must be a non-empty string")
            source_url = entry.get("source_url")
            if isinstance(source_url, str) and not re.match(r"https?://", source_url):
                if not (self.root / source_url).exists():
                    self.error(path, f"line {line_number} source path does not exist: {source_url}")
            if entry.get("evidence_strength") not in valid_strength:
                self.error(path, f"line {line_number} invalid evidence_strength")
            if entry.get("volatility") not in valid_volatility:
                self.error(path, f"line {line_number} invalid volatility")

    def validate_corpus_index(self, skill_names: list[str]) -> None:
        path = self.root / "researcher" / "corpus" / "index.json"
        data = self.load_json(path)
        if not isinstance(data, dict):
            return
        skills = data.get("skills")
        if not isinstance(skills, list):
            self.error(path, "skills must be a list")
            return
        indexed_names = sorted(item.get("name") for item in skills if isinstance(item, dict))
        if indexed_names != sorted(skill_names):
            self.error(path, f"corpus skill index differs from skills directory: {indexed_names} != {skill_names}")
        claim_ids = {entry.get("claim_id") for _, entry in self.load_jsonl(self.root / "researcher" / "claims" / "index.jsonl")}
        mechanism_ids = {
            entry.get("mechanism_id")
            for _, entry in self.load_jsonl(self.root / "researcher" / "mechanisms" / "registry.jsonl")
        }
        for item in skills:
            if not isinstance(item, dict):
                self.error(path, "skill index entries must be objects")
                continue
            skill_path = item.get("path")
            if not isinstance(skill_path, str) or not (self.root / skill_path).exists():
                self.error(path, f"skill path missing: {skill_path}")
            for claim_id in item.get("claim_ids", []):
                if claim_id not in claim_ids:
                    self.error(path, f"unknown claim_id in corpus index: {claim_id}")
            for mechanism_id in item.get("mechanism_ids", []):
                if mechanism_id not in mechanism_ids:
                    self.error(path, f"unknown mechanism_id in corpus index: {mechanism_id}")

    def validate_activation_cases(self, skill_names: list[str]) -> None:
        path = self.root / "researcher" / "fixtures" / "activation-cases.jsonl"
        for line_number, entry in self.load_jsonl(path):
            expected = entry.get("expected_primary_skill")
            if expected not in skill_names:
                self.error(path, f"line {line_number} expected_primary_skill is not published: {expected}")
            for key in ["case_id", "prompt", "reason"]:
                if not isinstance(entry.get(key), str) or not entry.get(key, "").strip():
                    self.error(path, f"line {line_number} {key} must be a non-empty string")
            for key in ["acceptable_secondary_skills", "rejected_skills"]:
                values = entry.get(key)
                if not isinstance(values, list):
                    self.error(path, f"line {line_number} {key} must be a list")
                    continue
                for value in values:
                    if value not in skill_names:
                        self.error(path, f"line {line_number} unknown skill in {key}: {value}")

    def validate_benchmark_scenarios(self) -> None:
        scenario_dir = self.root / "researcher" / "benchmarks" / "scenarios"
        for path in sorted(scenario_dir.glob("*.jsonl")):
            for line_number, entry in self.load_jsonl(path):
                for key in ["scenario_id", "class", "description", "expected_gate", "deterministic_signal"]:
                    if not isinstance(entry.get(key), str) or not entry.get(key, "").strip():
                        self.error(path, f"line {line_number} {key} must be a non-empty string")

    def validate_runs(self) -> None:
        runs_dir = self.root / "researcher" / "runs"
        if not runs_dir.exists():
            return
        for run_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
            required_paths = [
                run_dir / "THREAD.md",
                run_dir / "run-state.json",
                run_dir / "sources" / "queue.jsonl",
                run_dir / "sources" / "evaluations",
                run_dir / "sources" / "evidence" / "raw",
                run_dir / "proposals",
                run_dir / "proposals" / "mechanism-proposal.jsonl",
            ]
            for path in required_paths:
                if not path.exists():
                    self.error(path, "run artifact missing")
            queue = run_dir / "sources" / "queue.jsonl"
            if queue.exists():
                for line_number, line in enumerate(queue.read_text(encoding="utf-8").splitlines(), start=1):
                    if not line.strip():
                        continue
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as exc:
                        self.error(queue, f"line {line_number} invalid JSONL: {exc}")
            report = run_dir / "reports" / "validation-report.json"
            if report.exists():
                data = self.load_json(report)
                if isinstance(data, dict) and data.get("ok") is not True:
                    self.error(report, "run validation report is not passing")
            state = run_dir / "run-state.json"
            if state.exists():
                data = self.load_json(state)
                if isinstance(data, dict):
                    if data.get("current_state") not in {
                        "initialized",
                        "retrieved",
                        "evaluated",
                        "proposed",
                        "novelty_checked",
                        "validated",
                        "pr_ready",
                        "closed",
                    }:
                        self.error(state, "invalid current_state")
                    if not isinstance(data.get("state_history"), list) or not data["state_history"]:
                        self.error(state, "state_history must be a non-empty list")

    def validate_root_provenance(self) -> None:
        for path in self.root.glob("autonomous-research-*.json"):
            self.error(
                path,
                "raw research artifact must live under researcher/runs/<run>/sources/evidence/raw or be excluded",
            )

    def validate_source_evaluations(self) -> None:
        candidates: list[Path] = []
        for base in [self.root / "researcher" / "runs", self.root / "researcher" / "fixtures"]:
            if base.exists():
                candidates.extend(base.rglob("*.json"))

        for path in candidates:
            data = self.load_json(path)
            if not isinstance(data, dict):
                continue
            if REQUIRED_SOURCE_EVAL_KEYS.issubset(data.keys()):
                if "draft" in path.stem:
                    continue
                self.validate_source_eval_shape(path, data)

    def validate_source_eval_shape(self, path: Path, data: dict[str, Any]) -> None:
        source = data.get("source", {})
        if source.get("retrieval_status") == "failed":
            decision = data.get("decision", {}).get("verdict")
            if decision != "REJECT":
                self.error(path, "failed retrieval must reject or reroute before evaluation")
        if source.get("retrieval_status") != "retrieved" and data.get("decision", {}).get("verdict") == "APPROVE":
            self.error(path, "only retrieved sources may receive APPROVE")

        gatekeeper = data.get("gatekeeper", {})
        gate_values = [
            gatekeeper.get("G1_mechanism_specificity", {}).get("pass"),
            gatekeeper.get("G2_implementable_artifacts", {}).get("pass"),
            gatekeeper.get("G3_beyond_basics", {}).get("pass"),
            gatekeeper.get("G4_source_verifiability", {}).get("pass"),
        ]
        if not all(isinstance(value, bool) for value in gate_values):
            self.error(path, "all gate pass values must be booleans")
            return
        expected_gatekeeper = "PASS" if all(gate_values) else "REJECT"
        if gatekeeper.get("verdict") != expected_gatekeeper:
            self.error(path, f"gatekeeper verdict must be {expected_gatekeeper}")

        scoring = data.get("scoring", {})
        score_keys = [
            "D1_technical_depth_actionability",
            "D2_repo_relevance",
            "D3_evidence_rigor",
            "D4_novelty_insight",
        ]
        scores: dict[str, float] = {}
        for key in score_keys:
            score = scoring.get(key, {}).get("score")
            if not isinstance(score, (int, float)) or score < 0 or score > 2:
                self.error(path, f"{key}.score must be a number from 0 to 2")
                return
            scores[key] = float(score)

        recomputed_total = (
            scores["D1_technical_depth_actionability"] * 0.35
            + scores["D2_repo_relevance"] * 0.30
            + scores["D3_evidence_rigor"] * 0.20
            + scores["D4_novelty_insight"] * 0.15
        )
        recorded_total = scoring.get("weighted_total")
        if not isinstance(recorded_total, (int, float)):
            self.error(path, "scoring.weighted_total must be numeric")
            return
        if abs(float(recorded_total) - recomputed_total) > 0.011:
            self.error(
                path,
                f"weighted_total {recorded_total} does not match recomputed {recomputed_total:.3f}",
            )

        expected_decision = self.expected_content_decision(all(gate_values), scores, recomputed_total)
        decision = data.get("decision", {})
        if decision.get("verdict") != expected_decision["verdict"]:
            self.error(
                path,
                f"decision verdict must be {expected_decision['verdict']} under content-curation rubric",
            )
        expected_override = expected_decision["override_triggered"]
        actual_override = decision.get("override_triggered")
        if actual_override == "null":
            actual_override = None
        if actual_override != expected_override:
            self.error(path, f"override_triggered must be {expected_override or 'null'}")

    def expected_content_decision(
        self,
        gates_pass: bool,
        scores: dict[str, float],
        total: float,
    ) -> dict[str, str | None]:
        if not gates_pass:
            return {"verdict": "REJECT", "override_triggered": None}
        if scores["D1_technical_depth_actionability"] == 0:
            return {"verdict": "REJECT", "override_triggered": "O1"}
        if scores["D2_repo_relevance"] == 0:
            return {"verdict": "REJECT", "override_triggered": "O2"}
        if scores["D3_evidence_rigor"] == 1 and total >= 1.4:
            return {"verdict": "HUMAN_REVIEW", "override_triggered": "O3"}
        if scores["D4_novelty_insight"] == 2 and total < 1.4:
            return {"verdict": "HUMAN_REVIEW", "override_triggered": "O4"}
        if total >= 1.4:
            return {"verdict": "APPROVE", "override_triggered": None}
        if total >= 0.9:
            return {"verdict": "HUMAN_REVIEW", "override_triggered": None}
        return {"verdict": "REJECT", "override_triggered": None}

    def load_json(self, path: Path) -> Any:
        if not path.exists():
            self.error(path, "JSON file missing")
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=self.reject_duplicate_keys(path))
        except json.JSONDecodeError as exc:
            self.error(path, f"invalid JSON: {exc}")
            return None

    def load_jsonl(self, path: Path) -> list[tuple[int, dict[str, Any]]]:
        if not path.exists():
            self.error(path, "JSONL file missing")
            return []
        entries: list[tuple[int, dict[str, Any]]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                data = json.loads(line, object_pairs_hook=self.reject_duplicate_keys(path))
            except json.JSONDecodeError as exc:
                self.error(path, f"line {line_number} invalid JSONL: {exc}")
                continue
            if not isinstance(data, dict):
                self.error(path, f"line {line_number} JSONL entry must be an object")
                continue
            entries.append((line_number, data))
        return entries

    def reject_duplicate_keys(self, path: Path):
        def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    self.error(path, f"duplicate JSON key: {key}")
                result[key] = value
            return result

        return hook


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate skill corpus and researcher harness")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = parser.parse_args()

    result = Validator(args.root).run()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        summary = result["summary"]
        print(
            f"Validation {'passed' if result['ok'] else 'failed'}: "
            f"{summary['errors']} errors, {summary['warnings']} warnings, "
            f"{summary['skill_count']} skills"
        )
        for finding in result["findings"]:
            print(f"[{finding['severity']}] {finding['path']}: {finding['message']}")

    if result["summary"]["errors"] > 0:
        return 1
    if args.strict and result["summary"]["warnings"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
