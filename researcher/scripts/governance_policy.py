#!/usr/bin/env python3
"""Deterministic policy evaluation for the program constitution.

The evaluator has deliberately small semantics: exact actor, action, and
resource-class matching plus explicit conditions. Deny rules override allow
rules and missing vocabulary fails closed. It performs no network access and
does not infer authority from prose, branch names, or chat messages.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

try:
    import yaml
except ImportError as exc:  # pragma: no cover - CI installs requirements-dev.txt
    raise RuntimeError("PyYAML is required to load governance/constitution.yaml") from exc


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONSTITUTION = ROOT / "governance" / "constitution.yaml"
SUPPORTED_SCHEMA_MAJOR = 1
SUPPORTED_OPERATORS = {"equals", "not_equals", "in", "not_in", "present"}


class ConstitutionError(ValueError):
    """Raised when the constitution is malformed or cannot be pinned safely."""


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    actor: str
    action: str
    resource: str
    constitution_version: str
    constitution_digest: str
    matched_rule: str | None
    reason_code: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConstitutionError(f"{location} must be a non-empty string")
    return value


def _require_unique_strings(value: Any, location: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ConstitutionError(f"{location} must be a non-empty list")
    if not all(isinstance(item, str) and item for item in value):
        raise ConstitutionError(f"{location} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise ConstitutionError(f"{location} contains duplicates")
    return list(value)


class Constitution:
    """Loaded, validated constitution with fail-closed decision semantics."""

    def __init__(self, document: Mapping[str, Any], digest: str, source: Path) -> None:
        self.document = dict(document)
        self.digest = digest
        self.source = source
        self.version = _require_string(document.get("constitution_version"), "constitution_version")
        self._validate()

    @classmethod
    def load(
        cls,
        path: Path = DEFAULT_CONSTITUTION,
        *,
        expected_digest: str | None = None,
    ) -> "Constitution":
        resolved = path.resolve()
        try:
            document = yaml.safe_load(resolved.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ConstitutionError(f"cannot load constitution: {exc}") from exc
        if not isinstance(document, dict):
            raise ConstitutionError("constitution root must be a mapping")
        digest = sha256_file(resolved)
        if expected_digest is not None and digest != expected_digest:
            raise ConstitutionError(
                f"constitution digest mismatch: expected {expected_digest}, loaded {digest}"
            )
        return cls(document, digest, resolved)

    @property
    def actor_classes(self) -> tuple[str, ...]:
        return tuple(self.document["actor_classes"])

    @property
    def actions(self) -> tuple[str, ...]:
        return tuple(self.document["actions"])

    @property
    def resource_classes(self) -> tuple[str, ...]:
        return tuple(self.document["resource_classes"])

    @property
    def rules(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.document["rules"])

    def _validate(self) -> None:
        required = {
            "schema_version",
            "constitution_version",
            "lifecycle_state",
            "effective_commit",
            "default_effect",
            "promotion_event",
            "actor_classes",
            "actions",
            "resource_classes",
            "protected_surfaces",
            "rules",
            "emergency_controls",
            "amendment_procedure",
        }
        missing = required - self.document.keys()
        if missing:
            raise ConstitutionError(f"constitution missing keys: {sorted(missing)}")

        schema_version = _require_string(self.document["schema_version"], "schema_version")
        try:
            schema_major = int(schema_version.split(".", maxsplit=1)[0])
        except ValueError as exc:
            raise ConstitutionError("schema_version must begin with an integer major version") from exc
        if schema_major != SUPPORTED_SCHEMA_MAJOR:
            raise ConstitutionError(
                f"unsupported constitution schema major {schema_major}; expected {SUPPORTED_SCHEMA_MAJOR}"
            )
        if self.document["default_effect"] != "deny":
            raise ConstitutionError("default_effect must be deny")
        if self.document["promotion_event"] != "human_merged_commit":
            raise ConstitutionError("promotion_event must be human_merged_commit")
        if self.document["lifecycle_state"] not in {
            "draft",
            "reviewed",
            "merged",
            "effective",
            "superseded",
        }:
            raise ConstitutionError("invalid lifecycle_state")
        _require_string(self.document["effective_commit"], "effective_commit")

        actors = self.document["actor_classes"]
        if not isinstance(actors, dict) or not actors:
            raise ConstitutionError("actor_classes must be a non-empty mapping")
        for actor, descriptor in actors.items():
            _require_string(actor, "actor class")
            if not isinstance(descriptor, dict):
                raise ConstitutionError(f"actor_classes.{actor} must be a mapping")
            if not isinstance(descriptor.get("automated"), bool):
                raise ConstitutionError(f"actor_classes.{actor}.automated must be boolean")
            conflicts = descriptor.get("conflicts_with")
            if not isinstance(conflicts, list) or not all(isinstance(item, str) for item in conflicts):
                raise ConstitutionError(f"actor_classes.{actor}.conflicts_with must be a string list")
            unknown_conflicts = set(conflicts) - set(actors)
            if unknown_conflicts:
                raise ConstitutionError(
                    f"actor_classes.{actor} has unknown conflicts: {sorted(unknown_conflicts)}"
                )

        actions = _require_unique_strings(self.document["actions"], "actions")
        resources = _require_unique_strings(self.document["resource_classes"], "resource_classes")
        _require_unique_strings(self.document["protected_surfaces"], "protected_surfaces")

        rules = self.document["rules"]
        if not isinstance(rules, list) or not rules:
            raise ConstitutionError("rules must be a non-empty list")
        seen_rules: set[str] = set()
        for index, rule in enumerate(rules):
            location = f"rules[{index}]"
            if not isinstance(rule, dict):
                raise ConstitutionError(f"{location} must be a mapping")
            rule_id = _require_string(rule.get("rule_id"), f"{location}.rule_id")
            if rule_id in seen_rules:
                raise ConstitutionError(f"duplicate rule_id: {rule_id}")
            seen_rules.add(rule_id)
            if rule.get("effect") not in {"allow", "deny"}:
                raise ConstitutionError(f"{location}.effect must be allow or deny")
            rule_actors = _require_unique_strings(rule.get("actors"), f"{location}.actors")
            rule_actions = _require_unique_strings(rule.get("actions"), f"{location}.actions")
            rule_resources = _require_unique_strings(rule.get("resources"), f"{location}.resources")
            if set(rule_actors) - set(actors):
                raise ConstitutionError(f"{location} references unknown actor")
            if set(rule_actions) - set(actions):
                raise ConstitutionError(f"{location} references unknown action")
            if set(rule_resources) - set(resources):
                raise ConstitutionError(f"{location} references unknown resource")
            _require_string(rule.get("reason_code"), f"{location}.reason_code")
            conditions = rule.get("conditions", [])
            if not isinstance(conditions, list):
                raise ConstitutionError(f"{location}.conditions must be a list")
            for condition_index, condition in enumerate(conditions):
                condition_location = f"{location}.conditions[{condition_index}]"
                if not isinstance(condition, dict):
                    raise ConstitutionError(f"{condition_location} must be a mapping")
                _require_string(condition.get("key"), f"{condition_location}.key")
                operator = condition.get("operator")
                if operator not in SUPPORTED_OPERATORS:
                    raise ConstitutionError(f"{condition_location}.operator is unsupported")
                if operator != "present" and "value" not in condition:
                    raise ConstitutionError(f"{condition_location}.value is required")

        if "human_maintainer" not in actors:
            raise ConstitutionError("human_maintainer actor class is required")
        for rule in rules:
            if rule["effect"] == "allow" and "merge" in rule["actions"]:
                if set(rule["actors"]) != {"human_maintainer"}:
                    raise ConstitutionError("only human_maintainer may have an allow rule for merge")

    def classify_path(self, path: str | Path) -> str:
        """Classify a repository-relative path without deriving authority from its name."""

        raw = PurePosixPath(str(path).replace("\\", "/")).as_posix()
        if raw.startswith("/") or ".." in PurePosixPath(raw).parts:
            raise ConstitutionError(f"path must be repository-relative: {path}")
        for pattern in self.document["protected_surfaces"]:
            if fnmatch.fnmatchcase(raw, pattern):
                return "protected_surface"
        return "public_repository"

    @staticmethod
    def _condition_matches(condition: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
        key = str(condition["key"])
        operator = condition["operator"]
        present = key in context
        actual = context.get(key)
        expected = condition.get("value")
        if operator == "present":
            return present
        if operator == "equals":
            return present and actual == expected
        if operator == "not_equals":
            return present and actual != expected
        if operator == "in":
            return present and isinstance(expected, list) and actual in expected
        if operator == "not_in":
            return present and isinstance(expected, list) and actual not in expected
        return False

    def _rule_matches(
        self,
        rule: Mapping[str, Any],
        actor: str,
        action: str,
        resource: str,
        context: Mapping[str, Any],
    ) -> bool:
        return (
            actor in rule["actors"]
            and action in rule["actions"]
            and resource in rule["resources"]
            and all(self._condition_matches(condition, context) for condition in rule.get("conditions", []))
        )

    def decide(
        self,
        actor: str,
        action: str,
        resource: str,
        context: Mapping[str, Any] | None = None,
    ) -> PolicyDecision:
        context = dict(context or {})
        if actor not in self.actor_classes:
            return self._decision(False, actor, action, resource, None, "UNKNOWN_ACTOR")
        if action not in self.actions:
            return self._decision(False, actor, action, resource, None, "UNKNOWN_ACTION")
        if resource not in self.resource_classes:
            return self._decision(False, actor, action, resource, None, "UNKNOWN_RESOURCE")

        matches = sorted(
            (
                rule
                for rule in self.rules
                if self._rule_matches(rule, actor, action, resource, context)
            ),
            key=lambda rule: rule["rule_id"],
        )
        denials = [rule for rule in matches if rule["effect"] == "deny"]
        if denials:
            rule = denials[0]
            return self._decision(False, actor, action, resource, rule["rule_id"], rule["reason_code"])
        allowances = [rule for rule in matches if rule["effect"] == "allow"]
        if allowances:
            rule = allowances[0]
            return self._decision(True, actor, action, resource, rule["rule_id"], rule["reason_code"])
        return self._decision(False, actor, action, resource, None, "DEFAULT_DENY")

    def _decision(
        self,
        allowed: bool,
        actor: str,
        action: str,
        resource: str,
        matched_rule: str | None,
        reason_code: str,
    ) -> PolicyDecision:
        return PolicyDecision(
            allowed=allowed,
            actor=actor,
            action=action,
            resource=resource,
            constitution_version=self.version,
            constitution_digest=self.digest,
            matched_rule=matched_rule,
            reason_code=reason_code,
        )


def canonical_decision_json(decision: PolicyDecision) -> str:
    return json.dumps(decision.to_dict(), sort_keys=True, separators=(",", ":"))
