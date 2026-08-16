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
import re
from copy import deepcopy
from datetime import datetime, timezone
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

try:
    import yaml
except ImportError as exc:  # pragma: no cover - CI installs requirements-dev.txt
    raise RuntimeError("PyYAML is required to load governance/constitution.yaml") from exc


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONSTITUTION = ROOT / "governance" / "constitution.yaml"
# Compatibility name retained for callers that describe the currently active
# revision-1 policy. New parsers must use the complete supported-major set.
SUPPORTED_SCHEMA_MAJOR = 1
SUPPORTED_SCHEMA_MAJORS = frozenset({1, 2})
SUPPORTED_OPERATORS = frozenset({"equals", "not_equals", "in", "not_in", "present"})
SCHEMA_V2_OPERATORS = frozenset({"equals", "present", "less_than_or_equal"})
SCHEMA_V2_VALUE_TYPES = frozenset(
    {"boolean", "integer", "string", "sha256_digest", "utc_datetime"}
)
MAX_PORTABLE_INTEGER = 9_007_199_254_740_991
MAX_POLICY_STRING_LENGTH = 4096
MAX_POLICY_TOKEN_LENGTH = 128
MAX_PRINCIPAL_PAYLOAD_LENGTH = 128

_TOKEN_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_RULE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_REASON_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")
_PRINCIPAL_RE = re.compile(
    rf"^synthetic:[a-z][a-z0-9_]{{0,{MAX_PRINCIPAL_PAYLOAD_LENGTH - 1}}}$"
)
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_UTC_DATETIME_RE = re.compile(
    r"^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])"
    r"T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z$"
)
_SCHEMA_VERSION_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
)

_COMMON_ROOT_KEYS = frozenset({
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
})
_SCHEMA_V2_REQUIRED_ROOT_KEYS = _COMMON_ROOT_KEYS | {
    "identity_bindings",
    "separation_of_duty",
}
_SCHEMA_V2_OPTIONAL_ROOT_KEYS = frozenset({"non_constitutional_guidance"})
_SCHEMA_V2_RULE_REQUIRED_KEYS = frozenset({
    "rule_id",
    "effect",
    "actors",
    "actions",
    "resources",
    "reason_code",
})
_SCHEMA_V2_RULE_OPTIONAL_KEYS = frozenset({"conditions"})


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate and merge-shadowed keys."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key: {key!r}",
                key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


class ConstitutionError(ValueError):
    """Raised when the constitution is malformed or cannot be pinned safely."""


@dataclass(frozen=True)
class PolicyPredicate:
    """One validated schema-major-2 predicate over an authority scalar."""

    key: str
    operator: str
    value_type: str
    value: bool | int | str | None = None

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "key": self.key,
            "operator": self.operator,
            "value_type": self.value_type,
        }
        if self.operator != "present":
            payload["value"] = self.value
        return payload


@dataclass(frozen=True)
class SeparationOfDutyGroup:
    duty: str
    actor_classes: tuple[str, ...]


@dataclass(frozen=True)
class SeparationOfDutyRule:
    rule_id: str
    scope: str
    constraint: str
    groups: tuple[SeparationOfDutyGroup, ...]


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
    scope: str = "offline_class_policy_decision"
    runtime_authority: str = "none"

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


def _require_v2_token(value: Any, location: str) -> str:
    if (
        type(value) is not str
        or len(value) > MAX_POLICY_TOKEN_LENGTH
        or _TOKEN_RE.fullmatch(value) is None
    ):
        raise ConstitutionError(f"{location} must be a canonical lowercase token")
    return value


def _require_v2_rule_id(value: Any, location: str) -> str:
    if (
        type(value) is not str
        or len(value) > MAX_POLICY_TOKEN_LENGTH
        or _RULE_ID_RE.fullmatch(value) is None
    ):
        raise ConstitutionError(f"{location} must be a canonical rule identifier")
    return value


def _is_canonical_principal(value: Any) -> bool:
    if type(value) is not str or _PRINCIPAL_RE.fullmatch(value) is None:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _is_bounded_string(value: Any) -> bool:
    if type(value) is not str or not value or len(value) > MAX_POLICY_STRING_LENGTH:
        return False
    if value != value.strip() or any(
        ord(character) <= 0x1F or 0x7F <= ord(character) <= 0x9F
        for character in value
    ):
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _is_canonical_utc_datetime(value: Any) -> bool:
    if type(value) is not str or _UTC_DATETIME_RE.fullmatch(value) is None:
        return False
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return False
    canonical = (
        f"{parsed.year:04d}-{parsed.month:02d}-{parsed.day:02d}"
        f"T{parsed.hour:02d}:{parsed.minute:02d}:{parsed.second:02d}Z"
    )
    return canonical == value


def _authority_scalar_matches_type(value: Any, value_type: str) -> bool:
    if value_type == "boolean":
        return type(value) is bool
    if value_type == "integer":
        return (
            type(value) is int
            and 0 <= value <= MAX_PORTABLE_INTEGER
        )
    if value_type == "string":
        return _is_bounded_string(value)
    if value_type == "sha256_digest":
        return type(value) is str and _SHA256_RE.fullmatch(value) is not None
    if value_type == "utc_datetime":
        return _is_canonical_utc_datetime(value)
    return False


def _validate_authority_scalar(value: Any, value_type: str, location: str) -> None:
    if not _authority_scalar_matches_type(value, value_type):
        raise ConstitutionError(
            f"{location} must be a canonical {value_type} authority scalar"
        )


def parse_policy_predicate(value: Any, *, location: str) -> PolicyPredicate:
    """Parse the closed schema-major-2 predicate representation."""

    if not isinstance(value, dict):
        raise ConstitutionError(f"{location} must be a mapping")
    required_base = {"key", "operator", "value_type"}
    missing = required_base - set(value)
    if missing:
        raise ConstitutionError(f"{location} missing keys: {sorted(missing)}")

    key = _require_v2_token(value["key"], f"{location}.key")
    value_type = value["value_type"]
    if type(value_type) is not str or value_type not in SCHEMA_V2_VALUE_TYPES:
        raise ConstitutionError(f"{location}.value_type is unsupported")
    operator = value["operator"]
    if type(operator) is not str or operator not in SCHEMA_V2_OPERATORS:
        raise ConstitutionError(f"{location}.operator is unsupported")

    expected_keys = required_base if operator == "present" else required_base | {"value"}
    if set(value) != expected_keys:
        raise ConstitutionError(
            f"{location} fields do not match the {operator} predicate schema"
        )
    if operator == "present" and value_type == "boolean":
        raise ConstitutionError(
            f"{location}.present cannot be used for boolean authority predicates"
        )
    if operator == "less_than_or_equal" and value_type != "integer":
        raise ConstitutionError(
            f"{location}.less_than_or_equal requires value_type integer"
        )

    operand: bool | int | str | None = None
    if operator != "present":
        operand = value["value"]
        _validate_authority_scalar(operand, value_type, f"{location}.value")
    return PolicyPredicate(
        key=key,
        operator=operator,
        value_type=value_type,
        value=operand,
    )


def policy_predicate_matches(
    predicate: PolicyPredicate,
    context: Mapping[str, Any],
) -> bool:
    """Evaluate one typed predicate without Python scalar coercions."""

    if predicate.key not in context:
        return False
    actual = context[predicate.key]
    if not _authority_scalar_matches_type(actual, predicate.value_type):
        return False
    if predicate.operator == "present":
        return True
    if predicate.operator == "equals":
        return type(actual) is type(predicate.value) and actual == predicate.value
    if predicate.operator == "less_than_or_equal":
        return type(predicate.value) is int and actual <= predicate.value
    return False


def _exact_value_equal(actual: Any, expected: Any) -> bool:
    """Legacy equality that never aliases booleans, integers, or floats."""

    if type(actual) is not type(expected):
        return False
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(
            _exact_value_equal(left, right)
            for left, right in zip(actual, expected, strict=True)
        )
    if isinstance(actual, tuple):
        return len(actual) == len(expected) and all(
            _exact_value_equal(left, right)
            for left, right in zip(actual, expected, strict=True)
        )
    if isinstance(actual, dict):
        if len(actual) != len(expected):
            return False
        unmatched = list(expected.items())
        for actual_key, actual_value in actual.items():
            for index, (expected_key, expected_value) in enumerate(unmatched):
                if _exact_value_equal(actual_key, expected_key):
                    if not _exact_value_equal(actual_value, expected_value):
                        return False
                    unmatched.pop(index)
                    break
            else:
                return False
        return not unmatched
    try:
        equality = actual == expected
    except Exception:  # Fail closed for hostile context scalar implementations.
        return False
    return type(equality) is bool and equality


def _require_canonical_string_list(
    value: Any,
    location: str,
    *,
    allow_empty: bool,
    token_values: bool = False,
    principal_values: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, list) or (not allow_empty and not value):
        qualifier = "an array" if allow_empty else "a non-empty array"
        raise ConstitutionError(f"{location} must be {qualifier}")
    parsed: list[str] = []
    for index, item in enumerate(value):
        if token_values:
            parsed.append(_require_v2_token(item, f"{location}[{index}]"))
        elif principal_values:
            if not _is_canonical_principal(item):
                raise ConstitutionError(
                    f"{location}[{index}] must be a canonical synthetic offline principal"
                )
            parsed.append(item)
        elif not _is_bounded_string(item):
            raise ConstitutionError(
                f"{location}[{index}] must be a non-empty bounded string"
            )
        else:
            parsed.append(item)
    if parsed != sorted(set(parsed)):
        raise ConstitutionError(f"{location} must be sorted and duplicate-free")
    return tuple(parsed)


class Constitution:
    """Validated offline class-policy oracle.

    A positive decision is evidence about the loaded policy document only. It
    is not a runtime authorization, capability, authenticated identity, grant,
    fence, or permission to perform an external effect.
    """

    def __init__(self, document: Mapping[str, Any], digest: str, source: Path) -> None:
        self._document = deepcopy(dict(document))
        self.digest = digest
        self.source = source
        self.schema_major = -1
        self._rule_predicates: dict[str, tuple[PolicyPredicate, ...]] = {}
        self._identity_bindings: dict[str, tuple[str, ...]] = {}
        self._separation_of_duty_rules: tuple[SeparationOfDutyRule, ...] = ()
        self.version = _require_string(
            self._document.get("constitution_version"),
            "constitution_version",
        )
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
            document = yaml.load(
                resolved.read_text(encoding="utf-8"),
                Loader=_UniqueKeySafeLoader,
            )
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
        return tuple(self._document["actor_classes"])

    @property
    def actions(self) -> tuple[str, ...]:
        return tuple(self._document["actions"])

    @property
    def resource_classes(self) -> tuple[str, ...]:
        return tuple(self._document["resource_classes"])

    @property
    def document(self) -> dict[str, Any]:
        """Return a defensive snapshot of the validated authority document."""

        return deepcopy(self._document)

    @property
    def rules(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(self._document["rules"]))

    @property
    def identity_bindings(self) -> Mapping[str, tuple[str, ...]]:
        """Return validated schema-2 class-to-principal fixture bindings."""

        return dict(self._identity_bindings)

    @property
    def separation_of_duty_rules(self) -> tuple[SeparationOfDutyRule, ...]:
        return self._separation_of_duty_rules

    def predicates_for_rule(self, rule_id: str) -> tuple[PolicyPredicate, ...]:
        """Return parsed predicates for one schema-2 rule."""

        if self.schema_major != 2:
            raise ConstitutionError(
                "parsed policy predicates are available only for schema major 2"
            )
        try:
            return self._rule_predicates[rule_id]
        except KeyError as exc:
            raise ConstitutionError(f"unknown policy rule: {rule_id}") from exc

    def _validate(self) -> None:
        missing = _COMMON_ROOT_KEYS - self._document.keys()
        if missing:
            raise ConstitutionError(f"constitution missing keys: {sorted(missing)}")

        schema_version = _require_string(
            self._document["schema_version"], "schema_version"
        )
        match = _SCHEMA_VERSION_RE.fullmatch(schema_version)
        if match is None:
            raise ConstitutionError("schema_version must be a canonical semantic version")
        self.schema_major = int(match.group(1))
        if self.schema_major not in SUPPORTED_SCHEMA_MAJORS:
            raise ConstitutionError(
                "unsupported constitution schema major "
                f"{self.schema_major}; expected one of {sorted(SUPPORTED_SCHEMA_MAJORS)}"
            )
        if self.schema_major == 2:
            missing_v2 = _SCHEMA_V2_REQUIRED_ROOT_KEYS - self._document.keys()
            if missing_v2:
                raise ConstitutionError(
                    f"schema-2 constitution missing keys: {sorted(missing_v2)}"
                )
            allowed_v2 = _SCHEMA_V2_REQUIRED_ROOT_KEYS | _SCHEMA_V2_OPTIONAL_ROOT_KEYS
            unknown_v2 = set(self._document) - allowed_v2
            if unknown_v2:
                raise ConstitutionError(
                    f"schema-2 constitution has unknown keys: {sorted(unknown_v2)}"
                )
        if self._document["default_effect"] != "deny":
            raise ConstitutionError("default_effect must be deny")
        if self._document["promotion_event"] != "human_merged_commit":
            raise ConstitutionError("promotion_event must be human_merged_commit")
        if self._document["lifecycle_state"] not in {
            "draft",
            "reviewed",
            "merged",
            "effective",
            "superseded",
        }:
            raise ConstitutionError("invalid lifecycle_state")
        _require_string(self._document["effective_commit"], "effective_commit")
        if self.schema_major == 2:
            if _SCHEMA_VERSION_RE.fullmatch(self.version) is None:
                raise ConstitutionError(
                    "constitution_version must be a canonical semantic version"
                )
            if not _is_bounded_string(self._document["effective_commit"]):
                raise ConstitutionError(
                    "effective_commit must be a non-empty bounded string"
                )
            expected_emergency_controls = {
                "disable_changes_authority": False,
                "disable_mutates_history": False,
                "disable_stops_new_work": True,
            }
            if not _exact_value_equal(
                self._document["emergency_controls"],
                expected_emergency_controls,
            ):
                raise ConstitutionError(
                    "schema-2 emergency_controls must exactly preserve the "
                    "fail-safe control invariants"
                )
            expected_amendment_procedure = {
                "prior_versions_retained": True,
                "required_actor": "human_maintainer",
                "required_state_sequence": [
                    "draft",
                    "reviewed",
                    "merged",
                    "effective",
                ],
                "required_transport": "pull_request",
            }
            if not _exact_value_equal(
                self._document["amendment_procedure"],
                expected_amendment_procedure,
            ):
                raise ConstitutionError(
                    "schema-2 amendment_procedure must exactly preserve human review, "
                    "ordered promotion, and history retention"
                )
            guidance = self._document.get("non_constitutional_guidance")
            if guidance is not None:
                _require_canonical_string_list(
                    guidance,
                    "non_constitutional_guidance",
                    allow_empty=True,
                )

        actors = self._document["actor_classes"]
        if not isinstance(actors, dict) or not actors:
            raise ConstitutionError("actor_classes must be a non-empty mapping")
        for actor, descriptor in actors.items():
            if self.schema_major == 2:
                _require_v2_token(actor, "actor class")
            else:
                _require_string(actor, "actor class")
            if not isinstance(descriptor, dict):
                raise ConstitutionError(f"actor_classes.{actor} must be a mapping")
            if type(descriptor.get("automated")) is not bool:
                raise ConstitutionError(f"actor_classes.{actor}.automated must be boolean")
            if self.schema_major == 2:
                if set(descriptor) != {"automated"}:
                    raise ConstitutionError(
                        f"actor_classes.{actor} must contain only automated in schema 2"
                    )
            else:
                conflicts = descriptor.get("conflicts_with")
                if not isinstance(conflicts, list) or not all(
                    isinstance(item, str) for item in conflicts
                ):
                    raise ConstitutionError(
                        f"actor_classes.{actor}.conflicts_with must be a string list"
                    )
                unknown_conflicts = set(conflicts) - set(actors)
                if unknown_conflicts:
                    raise ConstitutionError(
                        f"actor_classes.{actor} has unknown conflicts: "
                        f"{sorted(unknown_conflicts)}"
                    )

        if self.schema_major == 2:
            self._validate_v2_identity_and_separation(actors)

        actions = _require_unique_strings(self._document["actions"], "actions")
        resources = _require_unique_strings(
            self._document["resource_classes"], "resource_classes"
        )
        protected_surfaces = _require_unique_strings(
            self._document["protected_surfaces"], "protected_surfaces"
        )
        if self.schema_major == 2:
            for index, action in enumerate(actions):
                _require_v2_token(action, f"actions[{index}]")
            for index, resource in enumerate(resources):
                _require_v2_token(resource, f"resource_classes[{index}]")
            for index, surface in enumerate(protected_surfaces):
                if not _is_bounded_string(surface):
                    raise ConstitutionError(
                        f"protected_surfaces[{index}] must be a non-empty bounded string"
                    )

        rules = self._document["rules"]
        if not isinstance(rules, list) or not rules:
            raise ConstitutionError("rules must be a non-empty list")
        seen_rules: set[str] = set()
        for index, rule in enumerate(rules):
            location = f"rules[{index}]"
            if not isinstance(rule, dict):
                raise ConstitutionError(f"{location} must be a mapping")
            if self.schema_major == 2:
                allowed_rule_keys = (
                    _SCHEMA_V2_RULE_REQUIRED_KEYS | _SCHEMA_V2_RULE_OPTIONAL_KEYS
                )
                missing_rule_keys = _SCHEMA_V2_RULE_REQUIRED_KEYS - set(rule)
                if missing_rule_keys:
                    raise ConstitutionError(
                        f"{location} missing keys: {sorted(missing_rule_keys)}"
                    )
                unknown_rule_keys = set(rule) - allowed_rule_keys
                if unknown_rule_keys:
                    raise ConstitutionError(
                        f"{location} has unknown keys: {sorted(unknown_rule_keys)}"
                    )
                rule_id = _require_v2_rule_id(
                    rule.get("rule_id"), f"{location}.rule_id"
                )
            else:
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
            if self.schema_major == 2:
                for field_name, values in (
                    ("actors", rule_actors),
                    ("actions", rule_actions),
                    ("resources", rule_resources),
                ):
                    for item_index, item in enumerate(values):
                        _require_v2_token(
                            item, f"{location}.{field_name}[{item_index}]"
                        )
                reason_code = rule.get("reason_code")
                if (
                    type(reason_code) is not str
                    or len(reason_code) > MAX_POLICY_TOKEN_LENGTH
                    or _REASON_CODE_RE.fullmatch(reason_code) is None
                ):
                    raise ConstitutionError(
                        f"{location}.reason_code must be a canonical reason code"
                    )
            else:
                _require_string(rule.get("reason_code"), f"{location}.reason_code")
            conditions = rule.get("conditions", [])
            if not isinstance(conditions, list):
                raise ConstitutionError(f"{location}.conditions must be a list")
            if self.schema_major == 2:
                parsed_predicates = tuple(
                    parse_policy_predicate(
                        condition,
                        location=f"{location}.conditions[{condition_index}]",
                    )
                    for condition_index, condition in enumerate(conditions)
                )
                predicate_keys = [predicate.key for predicate in parsed_predicates]
                if len(predicate_keys) != len(set(predicate_keys)):
                    raise ConstitutionError(
                        f"{location}.conditions contains duplicate predicate keys"
                    )
                if predicate_keys != sorted(predicate_keys):
                    raise ConstitutionError(
                        f"{location}.conditions must be sorted by key"
                    )
                self._rule_predicates[rule_id] = parsed_predicates
            else:
                for condition_index, condition in enumerate(conditions):
                    condition_location = f"{location}.conditions[{condition_index}]"
                    if not isinstance(condition, dict):
                        raise ConstitutionError(f"{condition_location} must be a mapping")
                    _require_string(condition.get("key"), f"{condition_location}.key")
                    operator = condition.get("operator")
                    if type(operator) is not str or operator not in SUPPORTED_OPERATORS:
                        raise ConstitutionError(f"{condition_location}.operator is unsupported")
                    if operator != "present" and "value" not in condition:
                        raise ConstitutionError(f"{condition_location}.value is required")

        if "human_maintainer" not in actors:
            raise ConstitutionError("human_maintainer actor class is required")
        for rule in rules:
            if rule["effect"] == "allow" and "merge" in rule["actions"]:
                if set(rule["actors"]) != {"human_maintainer"}:
                    raise ConstitutionError("only human_maintainer may have an allow rule for merge")

    def _validate_v2_identity_and_separation(
        self,
        actors: Mapping[str, Any],
    ) -> None:
        identity_bindings = self._document["identity_bindings"]
        if not isinstance(identity_bindings, dict):
            raise ConstitutionError("identity_bindings must be a mapping")
        if set(identity_bindings) != set(actors):
            raise ConstitutionError(
                "identity_bindings keys must exactly match actor_classes"
            )
        parsed_bindings: dict[str, tuple[str, ...]] = {}
        for actor in sorted(actors):
            parsed_bindings[actor] = _require_canonical_string_list(
                identity_bindings[actor],
                f"identity_bindings.{actor}",
                allow_empty=True,
                principal_values=True,
            )

        rules = self._document["separation_of_duty"]
        if not isinstance(rules, list) or not rules:
            raise ConstitutionError(
                "separation_of_duty must be a non-empty array in schema 2"
            )
        parsed_rules: list[SeparationOfDutyRule] = []
        seen_rule_ids: set[str] = set()
        for index, rule in enumerate(rules):
            location = f"separation_of_duty[{index}]"
            if not isinstance(rule, dict) or set(rule) != {
                "rule_id",
                "scope",
                "constraint",
                "groups",
            }:
                raise ConstitutionError(
                    f"{location} does not match the closed group-rule schema"
                )
            rule_id = _require_v2_rule_id(rule["rule_id"], f"{location}.rule_id")
            if rule_id in seen_rule_ids:
                raise ConstitutionError(f"duplicate separation-of-duty rule: {rule_id}")
            seen_rule_ids.add(rule_id)
            scope = _require_v2_token(rule["scope"], f"{location}.scope")
            if rule["constraint"] != "distinct_authenticated_principal_across_groups":
                raise ConstitutionError(f"{location}.constraint is unsupported")
            groups = rule["groups"]
            if not isinstance(groups, list) or len(groups) < 2:
                raise ConstitutionError(f"{location}.groups must contain at least two groups")

            parsed_groups: list[SeparationOfDutyGroup] = []
            seen_duties: set[str] = set()
            seen_group_actors: set[str] = set()
            for group_index, group in enumerate(groups):
                group_location = f"{location}.groups[{group_index}]"
                if not isinstance(group, dict) or set(group) != {
                    "duty",
                    "actor_classes",
                }:
                    raise ConstitutionError(
                        f"{group_location} does not match the closed group schema"
                    )
                duty = _require_v2_token(group["duty"], f"{group_location}.duty")
                if duty in seen_duties:
                    raise ConstitutionError(f"{location}.groups contains duplicate duties")
                seen_duties.add(duty)
                group_actors = _require_canonical_string_list(
                    group["actor_classes"],
                    f"{group_location}.actor_classes",
                    allow_empty=False,
                    token_values=True,
                )
                unknown_actors = set(group_actors) - set(actors)
                if unknown_actors:
                    raise ConstitutionError(
                        f"{group_location} references unknown actors: "
                        f"{sorted(unknown_actors)}"
                    )
                duplicated_actors = seen_group_actors & set(group_actors)
                if duplicated_actors:
                    raise ConstitutionError(
                        f"{location} assigns actors to more than one group: "
                        f"{sorted(duplicated_actors)}"
                    )
                seen_group_actors.update(group_actors)
                parsed_groups.append(
                    SeparationOfDutyGroup(duty=duty, actor_classes=group_actors)
                )
            if [group.duty for group in parsed_groups] != sorted(seen_duties):
                raise ConstitutionError(f"{location}.groups must be sorted by duty")

            principal_duties: dict[str, set[str]] = {}
            for group in parsed_groups:
                for actor in group.actor_classes:
                    for principal in parsed_bindings[actor]:
                        principal_duties.setdefault(principal, set()).add(group.duty)
            conflicts = sorted(
                principal
                for principal, duties in principal_duties.items()
                if len(duties) > 1
            )
            if conflicts:
                raise ConstitutionError(
                    f"{location} has principals assigned across protected groups: "
                    f"{conflicts}"
                )
            parsed_rules.append(
                SeparationOfDutyRule(
                    rule_id=rule_id,
                    scope=scope,
                    constraint=rule["constraint"],
                    groups=tuple(parsed_groups),
                )
            )

        if [rule.rule_id for rule in parsed_rules] != sorted(seen_rule_ids):
            raise ConstitutionError("separation_of_duty rules must be sorted by rule_id")
        self._identity_bindings = parsed_bindings
        self._separation_of_duty_rules = tuple(parsed_rules)

    def classify_path(self, path: str | Path) -> str:
        """Classify a repository-relative path without deriving authority from its name."""

        raw = PurePosixPath(str(path).replace("\\", "/")).as_posix()
        if raw.startswith("/") or ".." in PurePosixPath(raw).parts:
            raise ConstitutionError(f"path must be repository-relative: {path}")
        for pattern in self._document["protected_surfaces"]:
            if fnmatch.fnmatchcase(raw, pattern):
                return "protected_surface"
        return "public_repository"

    @staticmethod
    def _condition_matches(condition: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
        """Evaluate one legacy schema-1 condition with exact-type equality."""

        key = str(condition["key"])
        operator = condition["operator"]
        present = key in context
        actual = context.get(key)
        expected = condition.get("value")
        if operator == "present":
            return present
        if operator == "equals":
            return present and _exact_value_equal(actual, expected)
        if operator == "not_equals":
            return (
                present
                and type(actual) is type(expected)
                and not _exact_value_equal(actual, expected)
            )
        if operator == "in":
            return present and isinstance(expected, list) and any(
                _exact_value_equal(actual, candidate) for candidate in expected
            )
        if operator == "not_in":
            if not present or not isinstance(expected, list):
                return False
            comparable = [
                candidate for candidate in expected if type(candidate) is type(actual)
            ]
            return bool(comparable) and not any(
                _exact_value_equal(actual, candidate) for candidate in comparable
            )
        return False

    def _rule_matches(
        self,
        rule: Mapping[str, Any],
        actor: str,
        action: str,
        resource: str,
        context: Mapping[str, Any],
    ) -> bool:
        if (
            actor not in rule["actors"]
            or action not in rule["actions"]
            or resource not in rule["resources"]
        ):
            return False
        if self.schema_major == 2:
            return all(
                policy_predicate_matches(predicate, context)
                for predicate in self._rule_predicates[rule["rule_id"]]
            )
        return all(
            self._condition_matches(condition, context)
            for condition in rule.get("conditions", [])
        )

    def decide(
        self,
        actor: str,
        action: str,
        resource: str,
        context: Mapping[str, Any] | None = None,
    ) -> PolicyDecision:
        """Return an offline class-policy decision, never runtime authority."""

        if actor not in self.actor_classes:
            return self._decision(False, actor, action, resource, None, "UNKNOWN_ACTOR")
        if action not in self.actions:
            return self._decision(False, actor, action, resource, None, "UNKNOWN_ACTION")
        if resource not in self.resource_classes:
            return self._decision(False, actor, action, resource, None, "UNKNOWN_RESOURCE")
        if context is None:
            context = {}
        elif not isinstance(context, Mapping):
            return self._decision(False, actor, action, resource, None, "DEFAULT_DENY")
        try:
            context = dict(context)
        except (TypeError, ValueError):
            return self._decision(False, actor, action, resource, None, "DEFAULT_DENY")

        matches = sorted(
            (
                rule
                for rule in self._document["rules"]
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
