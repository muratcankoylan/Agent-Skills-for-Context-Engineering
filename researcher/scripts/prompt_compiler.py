#!/usr/bin/env python3
"""Deterministic, non-authoritative prompt compilation for pre-acceptance tests.

This module turns frozen, typed prompt inputs into exact model-visible bytes and a
separately identified safe launch projection.  It deliberately has no provider,
model, tool, credential-resolution, process-launch, or external-effect API.  A
successful compilation proves only that the supplied public inputs are internally
consistent; it grants no execution authority.
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, ClassVar, Mapping, Sequence

try:
    from schema_contract import SAFE_INTEGER_MAX, canonicalize, sha256_bytes
except ModuleNotFoundError:  # Package import from the repository root.
    from researcher.scripts.schema_contract import (
        SAFE_INTEGER_MAX,
        canonicalize,
        sha256_bytes,
    )


SCHEMA_VERSION = "1.0.0"
COMPILER_PROFILE = "pre-accept-prompt-compiler-v1"
EXECUTION_AUTHORITY = "none"
MAX_TEMPLATE_BYTES = 128 * 1024
MAX_PROMPT_BYTES = 256 * 1024
MAX_SUBSTITUTION_BYTES = 64 * 1024
MAX_PRIVATE_VALUE_BYTES = 64 * 1024
MAX_TOOLS = 64
MAX_TOOL_OPERATIONS = 32
MAX_EDITABLE_SURFACES = 128
MAX_SOURCE_ARTIFACTS = 256

DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+/-]{0,191}$")
CANONICAL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
PLACEHOLDER_PATTERN = re.compile(r"{{([a-z][a-z0-9_]{0,63})}}")
OPERATION_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
CREDENTIAL_REF_PATTERN = re.compile(r"^cred_[A-Za-z0-9][A-Za-z0-9._:-]{0,126}$")
CONTENT_ID_PATTERN = re.compile(r"^(?:pinst|launch)_[0-9a-f]{64}$")

PRIVATE_NAME_PARTS = frozenset(
    {
        "api_key",
        "capability",
        "credential",
        "locator",
        "password",
        "private",
        "secret",
        "token",
    }
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(
        r"(?i)\b(?:authorization|api[_-]?key|access[_-]?token|password|secret)"
        r"\s*[:=]\s*[^\s,;]+"
    ),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{8,}"),
    re.compile(
        r"\b(?:AKIA[0-9A-Z]{16}|github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,})\b"
    ),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|xox[baprs]-[A-Za-z0-9-]{10,})\b"),
    re.compile(r"(?:/Users/[^/\s]+/|/home/[^/\s]+/|[A-Za-z]:\\Users\\[^\\\s]+\\)"),
)


class PromptCompileError(ValueError):
    """Stable, non-sensitive compiler failure."""

    def __init__(self, code: str, safe_message: str):
        super().__init__(f"[{code}] {safe_message}")
        self.code = code
        self.safe_message = safe_message


def _require_exact_keys(
    record: Mapping[str, Any], expected: frozenset[str], label: str
) -> None:
    if not isinstance(record, Mapping):
        raise PromptCompileError("INVALID_TYPE", f"{label} must be an object")
    if not all(isinstance(key, str) for key in record):
        raise PromptCompileError("INVALID_TYPE", f"{label} keys must be strings")
    actual = set(record)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        raise PromptCompileError(
            "CLOSED_RECORD",
            f"{label} has missing or unknown fields",
        )


def _require_string(value: object, label: str, *, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value:
        raise PromptCompileError("INVALID_TYPE", f"{label} must be a non-empty string")
    if "\x00" in value or any(
        0xD800 <= ord(character) <= 0xDFFF for character in value
    ):
        raise PromptCompileError("INVALID_UNICODE", f"{label} contains unsafe Unicode")
    if unicodedata.normalize("NFC", value) != value:
        raise PromptCompileError(
            "INVALID_UNICODE", f"{label} must use NFC normalization"
        )
    if len(value.encode("utf-8")) > maximum:
        raise PromptCompileError("SIZE_LIMIT", f"{label} exceeds its UTF-8 byte limit")
    return value


def _require_token(value: object, label: str) -> str:
    candidate = _require_string(value, label, maximum=192)
    if not TOKEN_PATTERN.fullmatch(candidate):
        raise PromptCompileError("INVALID_TOKEN", f"{label} is not a canonical token")
    return candidate


def _require_digest(value: object, label: str) -> str:
    if not isinstance(value, str) or not DIGEST_PATTERN.fullmatch(value):
        raise PromptCompileError("INVALID_DIGEST", f"{label} must be a SHA-256 digest")
    return value


def _require_integer(value: object, label: str, *, minimum: int = 0) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > SAFE_INTEGER_MAX
    ):
        raise PromptCompileError(
            "INVALID_BUDGET", f"{label} must be an integer in the accepted range"
        )
    return value


def _require_string_tuple(
    value: object,
    label: str,
    *,
    maximum_items: int,
    item_validator: Any = _require_token,
    require_nonempty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise PromptCompileError("INVALID_TYPE", f"{label} must be a tuple")
    if len(value) > maximum_items or (require_nonempty and not value):
        raise PromptCompileError("SIZE_LIMIT", f"{label} has an invalid item count")
    checked = tuple(item_validator(item, f"{label} item") for item in value)
    if len(set(checked)) != len(checked):
        raise PromptCompileError("DUPLICATE_VALUE", f"{label} contains duplicates")
    return checked


def _reject_secret_material(value: str, label: str) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(value):
            raise PromptCompileError(
                "SECRET_VALUE", f"{label} contains private or secret material"
            )


def _content_id(prefix: str, domain: str, body: Mapping[str, Any]) -> str:
    payload = domain.encode("ascii") + b"\x00" + canonicalize(dict(body))
    return f"{prefix}_{hashlib.sha256(payload).hexdigest()}"


def _canonical_json_bytes(record: Mapping[str, Any]) -> bytes:
    return canonicalize(dict(record)) + b"\n"


def _validate_surface(value: object, label: str) -> str:
    candidate = _require_string(value, label, maximum=512)
    if "\\" in candidate or candidate.startswith("/") or candidate.endswith("/"):
        raise PromptCompileError(
            "INVALID_SURFACE", f"{label} is not a canonical relative path"
        )
    path = PurePosixPath(candidate)
    if path.as_posix() != candidate or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        raise PromptCompileError(
            "INVALID_SURFACE", f"{label} is not a canonical relative path"
        )
    return candidate


def _private_placeholder_name(name: str) -> bool:
    return any(part in name for part in PRIVATE_NAME_PARTS)


@dataclass(frozen=True, slots=True)
class BudgetEnvelope:
    max_tokens: int
    max_tool_calls: int
    max_paid_calls: int
    max_external_calls: int
    max_cost_micros: int
    currency: str
    max_output_bytes: int

    RECORD_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "max_tokens",
            "max_tool_calls",
            "max_paid_calls",
            "max_external_calls",
            "max_cost_micros",
            "currency",
            "max_output_bytes",
        }
    )

    def __post_init__(self) -> None:
        for name in (
            "max_tokens",
            "max_tool_calls",
            "max_paid_calls",
            "max_external_calls",
            "max_cost_micros",
        ):
            _require_integer(getattr(self, name), f"budget.{name}")
        _require_integer(self.max_output_bytes, "budget.max_output_bytes", minimum=1)
        if not isinstance(self.currency, str) or not re.fullmatch(
            r"[A-Z]{3}", self.currency
        ):
            raise PromptCompileError(
                "INVALID_BUDGET", "budget.currency must be an ISO-style code"
            )
        if self.max_paid_calls == 0 and self.max_cost_micros != 0:
            raise PromptCompileError(
                "INVALID_BUDGET",
                "a zero-paid-call budget must have zero monetary budget",
            )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> BudgetEnvelope:
        _require_exact_keys(record, cls.RECORD_KEYS, "BudgetEnvelope")
        return cls(**record)

    def to_record(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in sorted(self.RECORD_KEYS)}


@dataclass(frozen=True, slots=True)
class ToolGrant:
    grant_id: str
    tool_id: str
    operations: tuple[str, ...]
    audience_attempt_id: str
    credential_ref: str | None

    RECORD_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "binding_class",
            "grant_id",
            "tool_id",
            "operations",
            "audience_attempt_id",
            "credential_ref",
        }
    )

    def __post_init__(self) -> None:
        _require_token(self.grant_id, "tool grant id")
        _require_token(self.tool_id, "tool id")
        _require_token(self.audience_attempt_id, "tool audience attempt id")
        operations = _require_string_tuple(
            self.operations,
            "tool operations",
            maximum_items=MAX_TOOL_OPERATIONS,
            item_validator=lambda item, label: (
                _require_string(item, label, maximum=64)
                if isinstance(item, str) and OPERATION_PATTERN.fullmatch(item)
                else (_raise("INVALID_OPERATION", f"{label} is invalid"))
            ),
            require_nonempty=True,
        )
        if tuple(sorted(operations)) != operations:
            raise PromptCompileError(
                "NONCANONICAL_ORDER", "tool operations must be sorted"
            )
        if self.credential_ref is not None:
            if not isinstance(
                self.credential_ref, str
            ) or not CREDENTIAL_REF_PATTERN.fullmatch(self.credential_ref):
                raise PromptCompileError(
                    "INVALID_CREDENTIAL_REF",
                    "credential reference must be opaque and canonical",
                )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> ToolGrant:
        _require_exact_keys(record, cls.RECORD_KEYS, "ToolGrant")
        if record["binding_class"] != "pre_accept_only":
            raise PromptCompileError(
                "AUTHORITY_FORBIDDEN", "tool binding is not pre-accept-only"
            )
        operations = record["operations"]
        if not isinstance(operations, list):
            raise PromptCompileError(
                "INVALID_TYPE", "ToolGrant.operations must be an array"
            )
        return cls(
            grant_id=record["grant_id"],
            tool_id=record["tool_id"],
            operations=tuple(operations),
            audience_attempt_id=record["audience_attempt_id"],
            credential_ref=record["credential_ref"],
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "binding_class": "pre_accept_only",
            "grant_id": self.grant_id,
            "tool_id": self.tool_id,
            "operations": list(self.operations),
            "audience_attempt_id": self.audience_attempt_id,
            "credential_ref": self.credential_ref,
        }

    def safe_record(self) -> dict[str, Any]:
        return {"tool_id": self.tool_id, "operations": list(self.operations)}


def _raise(code: str, message: str) -> Any:
    raise PromptCompileError(code, message)


@dataclass(frozen=True, slots=True)
class RolePackage:
    package_id: str
    version: int
    role: str
    principal_id: str
    attempt_id: str
    context_digest: str
    allowed_tool_ids: tuple[str, ...]
    source_builder_principal_id: str | None
    source_builder_attempt_id: str | None
    source_builder_context_digest: str | None
    frozen_candidate_digest: str | None
    independence_receipt_digest: str | None

    RECORD_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "package_id",
            "version",
            "role",
            "principal_id",
            "attempt_id",
            "context_digest",
            "allowed_tool_ids",
            "source_builder_principal_id",
            "source_builder_attempt_id",
            "source_builder_context_digest",
            "frozen_candidate_digest",
            "independence_receipt_digest",
        }
    )

    def __post_init__(self) -> None:
        _require_token(self.package_id, "role package id")
        _require_integer(self.version, "role package version", minimum=1)
        if self.role not in {"builder", "verifier"}:
            raise PromptCompileError("INVALID_ROLE", "role must be builder or verifier")
        _require_token(self.principal_id, "principal id")
        _require_token(self.attempt_id, "attempt id")
        _require_digest(self.context_digest, "context digest")
        tool_ids = _require_string_tuple(
            self.allowed_tool_ids,
            "allowed tool ids",
            maximum_items=MAX_TOOLS,
            require_nonempty=False,
        )
        if tuple(sorted(tool_ids)) != tool_ids:
            raise PromptCompileError(
                "NONCANONICAL_ORDER", "allowed tool ids must be sorted"
            )

        verifier_values = (
            self.source_builder_principal_id,
            self.source_builder_attempt_id,
            self.source_builder_context_digest,
            self.frozen_candidate_digest,
            self.independence_receipt_digest,
        )
        if self.role == "builder":
            if any(value is not None for value in verifier_values):
                raise PromptCompileError(
                    "ROLE_SEPARATION",
                    "builder role cannot carry verifier-source bindings",
                )
            return

        if any(value is None for value in verifier_values):
            raise PromptCompileError(
                "ROLE_SEPARATION",
                "verifier role requires complete independent-source bindings",
            )
        _require_token(self.source_builder_principal_id, "source builder principal id")
        _require_token(self.source_builder_attempt_id, "source builder attempt id")
        _require_digest(
            self.source_builder_context_digest, "source builder context digest"
        )
        _require_digest(self.frozen_candidate_digest, "frozen candidate digest")
        _require_digest(self.independence_receipt_digest, "independence receipt digest")
        if self.principal_id == self.source_builder_principal_id:
            raise PromptCompileError(
                "ROLE_SEPARATION", "verifier principal must differ from builder"
            )
        if self.attempt_id == self.source_builder_attempt_id:
            raise PromptCompileError(
                "ROLE_SEPARATION", "verifier attempt must differ from builder"
            )
        if self.context_digest == self.source_builder_context_digest:
            raise PromptCompileError(
                "ROLE_SEPARATION", "verifier context must differ from builder"
            )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> RolePackage:
        _require_exact_keys(record, cls.RECORD_KEYS, "RolePackage")
        if record["schema_version"] != SCHEMA_VERSION:
            raise PromptCompileError(
                "SCHEMA_VERSION", "RolePackage schema version is unsupported"
            )
        tool_ids = record["allowed_tool_ids"]
        if not isinstance(tool_ids, list):
            raise PromptCompileError(
                "INVALID_TYPE", "allowed_tool_ids must be an array"
            )
        return cls(
            package_id=record["package_id"],
            version=record["version"],
            role=record["role"],
            principal_id=record["principal_id"],
            attempt_id=record["attempt_id"],
            context_digest=record["context_digest"],
            allowed_tool_ids=tuple(tool_ids),
            source_builder_principal_id=record["source_builder_principal_id"],
            source_builder_attempt_id=record["source_builder_attempt_id"],
            source_builder_context_digest=record["source_builder_context_digest"],
            frozen_candidate_digest=record["frozen_candidate_digest"],
            independence_receipt_digest=record["independence_receipt_digest"],
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "package_id": self.package_id,
            "version": self.version,
            "role": self.role,
            "principal_id": self.principal_id,
            "attempt_id": self.attempt_id,
            "context_digest": self.context_digest,
            "allowed_tool_ids": list(self.allowed_tool_ids),
            "source_builder_principal_id": self.source_builder_principal_id,
            "source_builder_attempt_id": self.source_builder_attempt_id,
            "source_builder_context_digest": self.source_builder_context_digest,
            "frozen_candidate_digest": self.frozen_candidate_digest,
            "independence_receipt_digest": self.independence_receipt_digest,
        }

    @property
    def digest(self) -> str:
        return sha256_bytes(canonicalize(self.to_record()))


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    template_id: str
    version: int
    role: str
    text: str
    declared_placeholders: tuple[str, ...]
    source_digest: str

    RECORD_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "template_id",
            "version",
            "role",
            "text",
            "declared_placeholders",
            "source_digest",
        }
    )

    def __post_init__(self) -> None:
        _require_token(self.template_id, "template id")
        _require_integer(self.version, "template version", minimum=1)
        if self.role not in {"builder", "verifier"}:
            raise PromptCompileError(
                "INVALID_ROLE", "template role must be builder or verifier"
            )
        if not isinstance(self.text, str) or not self.text:
            raise PromptCompileError("INVALID_TYPE", "template text must be non-empty")
        if "\r" in self.text or "\ufeff" in self.text:
            raise PromptCompileError(
                "NONCANONICAL_TEXT", "template must be BOM-free LF text"
            )
        _require_string(self.text, "template text", maximum=MAX_TEMPLATE_BYTES)
        _reject_secret_material(self.text, "template text")
        placeholders = _require_string_tuple(
            self.declared_placeholders,
            "declared placeholders",
            maximum_items=256,
            item_validator=lambda item, label: (
                _require_string(item, label, maximum=64)
                if isinstance(item, str) and CANONICAL_NAME_PATTERN.fullmatch(item)
                else _raise("INVALID_PLACEHOLDER", f"{label} is invalid")
            ),
        )
        for name in placeholders:
            if _private_placeholder_name(name):
                raise PromptCompileError(
                    "PRIVATE_MARKER", "private or credential placeholders are forbidden"
                )

        markers = PLACEHOLDER_PATTERN.findall(self.text)
        stripped = PLACEHOLDER_PATTERN.sub("", self.text)
        if "{{" in stripped or "}}" in stripped:
            raise PromptCompileError(
                "MALFORMED_MARKER", "template contains a malformed marker"
            )
        if len(markers) != len(set(markers)):
            raise PromptCompileError(
                "DUPLICATE_MARKER", "template repeats a placeholder marker"
            )
        if tuple(markers) != placeholders:
            raise PromptCompileError(
                "PLACEHOLDER_CONTRACT",
                "declared placeholders must exactly match marker order",
            )
        _require_digest(self.source_digest, "template source digest")
        if self.source_digest != sha256_bytes(self.text.encode("utf-8")):
            raise PromptCompileError(
                "STALE_SOURCE", "template source digest does not match bytes"
            )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> PromptTemplate:
        _require_exact_keys(record, cls.RECORD_KEYS, "PromptTemplate")
        if record["schema_version"] != SCHEMA_VERSION:
            raise PromptCompileError(
                "SCHEMA_VERSION", "PromptTemplate schema version is unsupported"
            )
        placeholders = record["declared_placeholders"]
        if not isinstance(placeholders, list):
            raise PromptCompileError(
                "INVALID_TYPE", "declared_placeholders must be an array"
            )
        return cls(
            template_id=record["template_id"],
            version=record["version"],
            role=record["role"],
            text=record["text"],
            declared_placeholders=tuple(placeholders),
            source_digest=record["source_digest"],
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "template_id": self.template_id,
            "version": self.version,
            "role": self.role,
            "text": self.text,
            "declared_placeholders": list(self.declared_placeholders),
            "source_digest": self.source_digest,
        }


@dataclass(frozen=True, slots=True)
class PromptInstance:
    instance_id: str
    role_package: RolePackage
    template: PromptTemplate
    rendered_prompt: str
    prompt_digest: str
    model_id: str
    tool_grants: tuple[ToolGrant, ...]
    authority_projection_id: str
    authority_projection_digest: str
    budget: BudgetEnvelope
    editable_surfaces: tuple[str, ...]
    source_artifact_digests: tuple[tuple[str, str], ...]

    RECORD_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "compiler_profile",
            "instance_id",
            "role_package",
            "template",
            "rendered_prompt",
            "prompt_digest",
            "model_id",
            "tool_grants",
            "authority_projection_id",
            "authority_projection_digest",
            "budget",
            "editable_surfaces",
            "source_artifact_digests",
            "execution_authority",
        }
    )

    def __post_init__(self) -> None:
        if not CONTENT_ID_PATTERN.fullmatch(self.instance_id):
            raise PromptCompileError("INVALID_ID", "prompt instance id is invalid")
        if not isinstance(self.role_package, RolePackage) or not isinstance(
            self.template, PromptTemplate
        ):
            raise PromptCompileError(
                "INVALID_TYPE", "prompt instance bindings are invalid"
            )
        if self.role_package.role != self.template.role:
            raise PromptCompileError(
                "ROLE_MISMATCH", "prompt instance roles do not match"
            )
        _require_string(
            self.rendered_prompt, "rendered prompt", maximum=MAX_PROMPT_BYTES
        )
        if "\r" in self.rendered_prompt or "\ufeff" in self.rendered_prompt:
            raise PromptCompileError(
                "NONCANONICAL_TEXT", "rendered prompt must be BOM-free LF text"
            )
        if "{{" in self.rendered_prompt or "}}" in self.rendered_prompt:
            raise PromptCompileError(
                "UNRESOLVED_MARKER", "rendered prompt contains a marker"
            )
        prompt_bytes = self.rendered_prompt.encode("utf-8")
        _reject_secret_material(self.rendered_prompt, "rendered prompt")
        _require_digest(self.prompt_digest, "prompt digest")
        if self.prompt_digest != sha256_bytes(prompt_bytes):
            raise PromptCompileError(
                "DIGEST_MISMATCH", "prompt digest does not match prompt bytes"
            )
        _require_token(self.model_id, "model id")
        _require_token(self.authority_projection_id, "authority projection id")
        _require_digest(self.authority_projection_digest, "authority projection digest")
        if not isinstance(self.budget, BudgetEnvelope):
            raise PromptCompileError("INVALID_TYPE", "budget binding is invalid")
        if not isinstance(self.tool_grants, tuple):
            raise PromptCompileError("INVALID_TYPE", "tool grants must be a tuple")
        if (
            _normalized_tool_grants(self.tool_grants, self.role_package)
            != self.tool_grants
        ):
            raise PromptCompileError("NONCANONICAL_ORDER", "tool grants must be sorted")
        private_bindings = (
            self.role_package.principal_id,
            self.role_package.attempt_id,
            self.role_package.context_digest,
            self.role_package.source_builder_principal_id,
            self.role_package.source_builder_attempt_id,
            self.role_package.source_builder_context_digest,
            *(grant.credential_ref for grant in self.tool_grants),
        )
        if any(value and value in self.rendered_prompt for value in private_bindings):
            raise PromptCompileError(
                "PRIVATE_VALUE_LEAK", "rendered prompt contains a private binding"
            )
        if _validated_surfaces(self.editable_surfaces) != self.editable_surfaces:
            raise PromptCompileError(
                "NONCANONICAL_ORDER", "editable surfaces must be sorted"
            )
        if (
            _validated_artifact_pairs(self.source_artifact_digests)
            != self.source_artifact_digests
        ):
            raise PromptCompileError(
                "NONCANONICAL_ORDER", "source artifacts must be sorted"
            )
        if self.instance_id != _content_id(
            "pinst", "prompt-instance/v1", self.identity_record()
        ):
            raise PromptCompileError(
                "IDENTITY_MISMATCH", "prompt instance identity is stale"
            )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> PromptInstance:
        _require_exact_keys(record, cls.RECORD_KEYS, "PromptInstance")
        if record["schema_version"] != SCHEMA_VERSION:
            raise PromptCompileError(
                "SCHEMA_VERSION", "PromptInstance schema version is unsupported"
            )
        if record["compiler_profile"] != COMPILER_PROFILE:
            raise PromptCompileError(
                "COMPILER_PROFILE", "PromptInstance compiler profile is unsupported"
            )
        if record["execution_authority"] != EXECUTION_AUTHORITY:
            raise PromptCompileError(
                "AUTHORITY_FORBIDDEN", "prompt instance cannot grant authority"
            )
        grants = record["tool_grants"]
        surfaces = record["editable_surfaces"]
        if not isinstance(grants, list):
            raise PromptCompileError("INVALID_TYPE", "tool_grants must be an array")
        if not isinstance(surfaces, list):
            raise PromptCompileError(
                "INVALID_TYPE", "editable_surfaces must be an array"
            )
        return cls(
            instance_id=record["instance_id"],
            role_package=RolePackage.from_record(record["role_package"]),
            template=PromptTemplate.from_record(record["template"]),
            rendered_prompt=record["rendered_prompt"],
            prompt_digest=record["prompt_digest"],
            model_id=record["model_id"],
            tool_grants=tuple(ToolGrant.from_record(grant) for grant in grants),
            authority_projection_id=record["authority_projection_id"],
            authority_projection_digest=record["authority_projection_digest"],
            budget=BudgetEnvelope.from_record(record["budget"]),
            editable_surfaces=tuple(surfaces),
            source_artifact_digests=_artifact_pairs_from_records(
                record["source_artifact_digests"]
            ),
        )

    def identity_record(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "compiler_profile": COMPILER_PROFILE,
            "role_package": self.role_package.to_record(),
            "template": self.template.to_record(),
            "rendered_prompt": self.rendered_prompt,
            "prompt_digest": self.prompt_digest,
            "model_id": self.model_id,
            "tool_grants": [grant.to_record() for grant in self.tool_grants],
            "authority_projection_id": self.authority_projection_id,
            "authority_projection_digest": self.authority_projection_digest,
            "budget": self.budget.to_record(),
            "editable_surfaces": list(self.editable_surfaces),
            "source_artifact_digests": [
                {"artifact_id": artifact_id, "digest": digest}
                for artifact_id, digest in self.source_artifact_digests
            ],
            "execution_authority": EXECUTION_AUTHORITY,
        }

    def to_record(self) -> dict[str, Any]:
        return {"instance_id": self.instance_id, **self.identity_record()}

    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(self.to_record())

    def prompt_bytes(self) -> bytes:
        return self.rendered_prompt.encode("utf-8")


@dataclass(frozen=True, slots=True)
class LaunchProjection:
    projection_id: str
    role: str
    model_id: str
    prompt_digest: str
    template_id: str
    template_version: int
    tool_bindings: tuple[tuple[str, tuple[str, ...]], ...]
    authority_projection_id: str
    authority_projection_digest: str
    budget: BudgetEnvelope
    editable_surfaces: tuple[str, ...]
    source_artifact_digests: tuple[tuple[str, str], ...]
    frozen_candidate_digest: str | None
    independence_receipt_digest: str | None

    RECORD_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "compiler_profile",
            "projection_id",
            "role",
            "model_id",
            "prompt_digest",
            "template_id",
            "template_version",
            "tool_bindings",
            "authority_projection_id",
            "authority_projection_digest",
            "budget",
            "editable_surfaces",
            "source_artifact_digests",
            "frozen_candidate_digest",
            "independence_receipt_digest",
            "execution_authority",
        }
    )

    def __post_init__(self) -> None:
        if not CONTENT_ID_PATTERN.fullmatch(self.projection_id):
            raise PromptCompileError("INVALID_ID", "launch projection id is invalid")
        if self.role not in {"builder", "verifier"}:
            raise PromptCompileError("INVALID_ROLE", "launch role is invalid")
        _require_token(self.model_id, "model id")
        _require_digest(self.prompt_digest, "prompt digest")
        _require_token(self.template_id, "template id")
        _require_integer(self.template_version, "template version", minimum=1)
        _require_token(self.authority_projection_id, "authority projection id")
        _require_digest(self.authority_projection_digest, "authority projection digest")
        if not isinstance(self.budget, BudgetEnvelope):
            raise PromptCompileError("INVALID_TYPE", "projection budget is invalid")
        if _validated_tool_bindings(self.tool_bindings) != self.tool_bindings:
            raise PromptCompileError(
                "NONCANONICAL_ORDER", "tool bindings must be sorted"
            )
        if _validated_surfaces(self.editable_surfaces) != self.editable_surfaces:
            raise PromptCompileError(
                "NONCANONICAL_ORDER", "editable surfaces must be sorted"
            )
        if (
            _validated_artifact_pairs(self.source_artifact_digests)
            != self.source_artifact_digests
        ):
            raise PromptCompileError(
                "NONCANONICAL_ORDER", "source artifacts must be sorted"
            )
        if self.role == "builder":
            if (
                self.frozen_candidate_digest is not None
                or self.independence_receipt_digest is not None
            ):
                raise PromptCompileError(
                    "ROLE_SEPARATION", "builder projection has verifier fields"
                )
        else:
            _require_digest(self.frozen_candidate_digest, "frozen candidate digest")
            _require_digest(
                self.independence_receipt_digest, "independence receipt digest"
            )
        if self.projection_id != _content_id(
            "launch", "launch-projection/v1", self.identity_record()
        ):
            raise PromptCompileError(
                "IDENTITY_MISMATCH", "launch projection identity is stale"
            )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> LaunchProjection:
        _require_exact_keys(record, cls.RECORD_KEYS, "LaunchProjection")
        if record["schema_version"] != SCHEMA_VERSION:
            raise PromptCompileError(
                "SCHEMA_VERSION", "LaunchProjection schema version is unsupported"
            )
        if record["compiler_profile"] != COMPILER_PROFILE:
            raise PromptCompileError(
                "COMPILER_PROFILE", "LaunchProjection compiler profile is unsupported"
            )
        if record["execution_authority"] != EXECUTION_AUTHORITY:
            raise PromptCompileError(
                "AUTHORITY_FORBIDDEN", "launch projection cannot grant authority"
            )
        surfaces = record["editable_surfaces"]
        if not isinstance(surfaces, list):
            raise PromptCompileError(
                "INVALID_TYPE", "editable_surfaces must be an array"
            )
        return cls(
            projection_id=record["projection_id"],
            role=record["role"],
            model_id=record["model_id"],
            prompt_digest=record["prompt_digest"],
            template_id=record["template_id"],
            template_version=record["template_version"],
            tool_bindings=_tool_bindings_from_records(record["tool_bindings"]),
            authority_projection_id=record["authority_projection_id"],
            authority_projection_digest=record["authority_projection_digest"],
            budget=BudgetEnvelope.from_record(record["budget"]),
            editable_surfaces=tuple(surfaces),
            source_artifact_digests=_artifact_pairs_from_records(
                record["source_artifact_digests"]
            ),
            frozen_candidate_digest=record["frozen_candidate_digest"],
            independence_receipt_digest=record["independence_receipt_digest"],
        )

    def identity_record(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "compiler_profile": COMPILER_PROFILE,
            "role": self.role,
            "model_id": self.model_id,
            "prompt_digest": self.prompt_digest,
            "template_id": self.template_id,
            "template_version": self.template_version,
            "tool_bindings": [
                {"tool_id": tool_id, "operations": list(operations)}
                for tool_id, operations in self.tool_bindings
            ],
            "authority_projection_id": self.authority_projection_id,
            "authority_projection_digest": self.authority_projection_digest,
            "budget": self.budget.to_record(),
            "editable_surfaces": list(self.editable_surfaces),
            "source_artifact_digests": [
                {"artifact_id": artifact_id, "digest": digest}
                for artifact_id, digest in self.source_artifact_digests
            ],
            "frozen_candidate_digest": self.frozen_candidate_digest,
            "independence_receipt_digest": self.independence_receipt_digest,
            "execution_authority": EXECUTION_AUTHORITY,
        }

    def to_record(self) -> dict[str, Any]:
        return {"projection_id": self.projection_id, **self.identity_record()}

    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(self.to_record())


def _validated_surfaces(values: object) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise PromptCompileError("INVALID_TYPE", "editable surfaces must be a tuple")
    return _normalized_surfaces(values)


def _validated_artifact_pairs(values: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(values, tuple):
        raise PromptCompileError("INVALID_TYPE", "source artifacts must be a tuple")
    if not values or len(values) > MAX_SOURCE_ARTIFACTS:
        raise PromptCompileError(
            "SIZE_LIMIT", "source artifacts have an invalid item count"
        )
    checked: list[tuple[str, str]] = []
    for item in values:
        if not isinstance(item, tuple) or len(item) != 2:
            raise PromptCompileError(
                "INVALID_TYPE", "source artifact entries must be pairs"
            )
        artifact_id, digest = item
        checked.append(
            (
                _require_token(artifact_id, "source artifact id"),
                _require_digest(digest, "source artifact digest"),
            )
        )
    if len({artifact_id for artifact_id, _ in checked}) != len(checked):
        raise PromptCompileError(
            "DUPLICATE_VALUE", "source artifact ids contain duplicates"
        )
    return tuple(sorted(checked))


def _artifact_pairs_from_records(value: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list):
        raise PromptCompileError(
            "INVALID_TYPE", "source_artifact_digests must be an array"
        )
    pairs: list[tuple[str, str]] = []
    keys = frozenset({"artifact_id", "digest"})
    for item in value:
        _require_exact_keys(item, keys, "source artifact binding")
        pairs.append((item["artifact_id"], item["digest"]))
    parsed = tuple(pairs)
    _validated_artifact_pairs(parsed)
    return parsed


def _validated_tool_bindings(
    values: object,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if not isinstance(values, tuple):
        raise PromptCompileError("INVALID_TYPE", "tool bindings must be a tuple")
    if len(values) > MAX_TOOLS:
        raise PromptCompileError("SIZE_LIMIT", "too many tool bindings")
    checked: list[tuple[str, tuple[str, ...]]] = []
    for item in values:
        if not isinstance(item, tuple) or len(item) != 2:
            raise PromptCompileError("INVALID_TYPE", "tool bindings must contain pairs")
        tool_id, operations_value = item
        operations = _require_string_tuple(
            operations_value,
            "tool operations",
            maximum_items=MAX_TOOL_OPERATIONS,
            item_validator=lambda operation, label: (
                _require_string(operation, label, maximum=64)
                if isinstance(operation, str) and OPERATION_PATTERN.fullmatch(operation)
                else _raise("INVALID_OPERATION", f"{label} is invalid")
            ),
            require_nonempty=True,
        )
        if tuple(sorted(operations)) != operations:
            raise PromptCompileError(
                "NONCANONICAL_ORDER", "tool operations must be sorted"
            )
        checked.append((_require_token(tool_id, "tool id"), operations))
    if len({tool_id for tool_id, _ in checked}) != len(checked):
        raise PromptCompileError(
            "DUPLICATE_VALUE", "tool bindings contain duplicate tools"
        )
    return tuple(sorted(checked))


def _tool_bindings_from_records(
    value: object,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if not isinstance(value, list):
        raise PromptCompileError("INVALID_TYPE", "tool_bindings must be an array")
    bindings: list[tuple[str, tuple[str, ...]]] = []
    keys = frozenset({"tool_id", "operations"})
    for item in value:
        _require_exact_keys(item, keys, "tool binding")
        operations = item["operations"]
        if not isinstance(operations, list):
            raise PromptCompileError(
                "INVALID_TYPE", "tool binding operations must be an array"
            )
        bindings.append((item["tool_id"], tuple(operations)))
    parsed = tuple(bindings)
    _validated_tool_bindings(parsed)
    return parsed


def _normalized_tool_grants(
    values: Sequence[ToolGrant], role_package: RolePackage
) -> tuple[ToolGrant, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise PromptCompileError("INVALID_TYPE", "tool grants must be a sequence")
    if len(values) > MAX_TOOLS:
        raise PromptCompileError("SIZE_LIMIT", "too many tool grants")
    grants = tuple(values)
    if any(not isinstance(grant, ToolGrant) for grant in grants):
        raise PromptCompileError("INVALID_TYPE", "tool grants contain an invalid value")
    if any(grant.audience_attempt_id != role_package.attempt_id for grant in grants):
        raise PromptCompileError(
            "AUDIENCE_MISMATCH", "tool grant audience does not match attempt"
        )
    ids = [grant.tool_id for grant in grants]
    if len(ids) != len(set(ids)):
        raise PromptCompileError("DUPLICATE_VALUE", "tool ids must be unique")
    if set(ids) != set(role_package.allowed_tool_ids):
        raise PromptCompileError(
            "TOOL_SCOPE_MISMATCH", "tool grants do not match role package"
        )
    return tuple(sorted(grants, key=lambda grant: grant.tool_id))


def _normalized_surfaces(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise PromptCompileError("INVALID_TYPE", "editable surfaces must be a sequence")
    if len(values) > MAX_EDITABLE_SURFACES:
        raise PromptCompileError("SIZE_LIMIT", "too many editable surfaces")
    surfaces = tuple(_validate_surface(value, "editable surface") for value in values)
    if len(surfaces) != len(set(surfaces)):
        raise PromptCompileError(
            "DUPLICATE_VALUE", "editable surfaces contain duplicates"
        )
    return tuple(sorted(surfaces))


def _normalized_artifacts(values: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    if not isinstance(values, Mapping):
        raise PromptCompileError("INVALID_TYPE", "source artifacts must be an object")
    if not values or len(values) > MAX_SOURCE_ARTIFACTS:
        raise PromptCompileError(
            "SIZE_LIMIT", "source artifacts have an invalid item count"
        )
    artifacts: list[tuple[str, str]] = []
    for artifact_id, digest in values.items():
        artifacts.append(
            (
                _require_token(artifact_id, "source artifact id"),
                _require_digest(digest, "source artifact digest"),
            )
        )
    if len({artifact_id for artifact_id, _ in artifacts}) != len(artifacts):
        raise PromptCompileError(
            "DUPLICATE_VALUE", "source artifact ids contain duplicates"
        )
    return tuple(sorted(artifacts))


def _render_prompt(template: PromptTemplate, substitutions: Mapping[str, str]) -> str:
    if not isinstance(substitutions, Mapping):
        raise PromptCompileError("INVALID_TYPE", "substitutions must be an object")
    expected = set(template.declared_placeholders)
    actual = set(substitutions)
    if expected != actual:
        raise PromptCompileError(
            "SUBSTITUTION_CONTRACT",
            "substitution names do not match the declared placeholder contract",
        )
    detached: dict[str, str] = {}
    for name in template.declared_placeholders:
        if _private_placeholder_name(name):
            raise PromptCompileError(
                "PRIVATE_MARKER", "private substitution name is forbidden"
            )
        value = substitutions[name]
        if not isinstance(value, str):
            raise PromptCompileError(
                "INVALID_TYPE", "substitution values must be strings"
            )
        _require_string(value, f"substitution {name}", maximum=MAX_SUBSTITUTION_BYTES)
        if "\r" in value or "\ufeff" in value:
            raise PromptCompileError(
                "NONCANONICAL_TEXT", "substitution values must be BOM-free LF text"
            )
        if "{{" in value or "}}" in value:
            raise PromptCompileError(
                "MARKER_INJECTION",
                "substitution values cannot introduce template markers",
            )
        _reject_secret_material(value, f"substitution {name}")
        detached[name] = value

    rendered = PLACEHOLDER_PATTERN.sub(
        lambda match: detached[match.group(1)], template.text
    )
    if "{{" in rendered or "}}" in rendered:
        raise PromptCompileError(
            "UNRESOLVED_MARKER", "rendered prompt contains a marker"
        )
    if len(rendered.encode("utf-8")) > MAX_PROMPT_BYTES:
        raise PromptCompileError("SIZE_LIMIT", "rendered prompt exceeds byte limit")
    return rendered


def compile_prompt(
    *,
    role_package: RolePackage,
    template: PromptTemplate,
    substitutions: Mapping[str, str],
    model_id: str,
    tool_grants: Sequence[ToolGrant],
    authority_projection_id: str,
    authority_projection_digest: str,
    budget: BudgetEnvelope,
    editable_surfaces: Sequence[str],
    source_artifact_digests: Mapping[str, str],
    private_values: Sequence[str] = (),
) -> tuple[PromptInstance, LaunchProjection]:
    """Compile exact prompt bytes and a safe, non-authorizing launch projection."""

    if not isinstance(role_package, RolePackage) or not isinstance(
        template, PromptTemplate
    ):
        raise PromptCompileError(
            "INVALID_TYPE", "role package and template must be typed"
        )
    if template.role != role_package.role:
        raise PromptCompileError(
            "ROLE_MISMATCH", "template role does not match role package"
        )
    if not isinstance(budget, BudgetEnvelope):
        raise PromptCompileError("INVALID_TYPE", "budget must be typed")
    model = _require_token(model_id, "model id")
    authority_id = _require_token(authority_projection_id, "authority projection id")
    authority_digest = _require_digest(
        authority_projection_digest, "authority projection digest"
    )
    grants = _normalized_tool_grants(tool_grants, role_package)
    surfaces = _normalized_surfaces(editable_surfaces)
    artifacts = _normalized_artifacts(source_artifact_digests)
    rendered = _render_prompt(template, substitutions)

    if isinstance(private_values, (str, bytes)) or not isinstance(
        private_values, Sequence
    ):
        raise PromptCompileError("INVALID_TYPE", "private values must be a sequence")
    forbidden: list[str] = [
        role_package.principal_id,
        role_package.attempt_id,
        role_package.context_digest,
        *(
            value
            for value in (
                role_package.source_builder_principal_id,
                role_package.source_builder_attempt_id,
                role_package.source_builder_context_digest,
            )
            if value is not None
        ),
    ]
    for value in private_values:
        if not isinstance(value, str) or not value:
            raise PromptCompileError(
                "PRIVATE_VALUE_INVALID", "private value is invalid"
            )
        if (
            "\x00" in value
            or any(0xD800 <= ord(character) <= 0xDFFF for character in value)
            or unicodedata.normalize("NFC", value) != value
            or len(value.encode("utf-8")) > MAX_PRIVATE_VALUE_BYTES
        ):
            raise PromptCompileError(
                "PRIVATE_VALUE_INVALID", "private value is invalid"
            )
        if len(value) < 4:
            raise PromptCompileError(
                "PRIVATE_VALUE_INVALID",
                "private values must be long enough for safe leak scanning",
            )
        forbidden.append(value)
    forbidden.extend(
        grant.credential_ref for grant in grants if grant.credential_ref is not None
    )
    if any(value in rendered for value in forbidden):
        raise PromptCompileError(
            "PRIVATE_VALUE_LEAK", "rendered prompt contains a private value"
        )

    prompt_digest = sha256_bytes(rendered.encode("utf-8"))
    temporary = PromptInstance.__new__(PromptInstance)
    instance_values = {
        "role_package": role_package,
        "template": template,
        "rendered_prompt": rendered,
        "prompt_digest": prompt_digest,
        "model_id": model,
        "tool_grants": grants,
        "authority_projection_id": authority_id,
        "authority_projection_digest": authority_digest,
        "budget": budget,
        "editable_surfaces": surfaces,
        "source_artifact_digests": artifacts,
    }
    for name, value in instance_values.items():
        object.__setattr__(temporary, name, value)
    instance_id = _content_id(
        "pinst", "prompt-instance/v1", temporary.identity_record()
    )
    instance = PromptInstance(instance_id=instance_id, **instance_values)

    tool_bindings = tuple((grant.tool_id, grant.operations) for grant in grants)
    projection_values = {
        "role": role_package.role,
        "model_id": model,
        "prompt_digest": prompt_digest,
        "template_id": template.template_id,
        "template_version": template.version,
        "tool_bindings": tool_bindings,
        "authority_projection_id": authority_id,
        "authority_projection_digest": authority_digest,
        "budget": budget,
        "editable_surfaces": surfaces,
        "source_artifact_digests": artifacts,
        "frozen_candidate_digest": role_package.frozen_candidate_digest,
        "independence_receipt_digest": role_package.independence_receipt_digest,
    }
    projection_temporary = LaunchProjection.__new__(LaunchProjection)
    for name, value in projection_values.items():
        object.__setattr__(projection_temporary, name, value)
    projection_id = _content_id(
        "launch", "launch-projection/v1", projection_temporary.identity_record()
    )
    projection = LaunchProjection(projection_id=projection_id, **projection_values)

    projection_bytes = projection.canonical_bytes()
    forbidden_projection_terms = [
        role_package.principal_id,
        role_package.attempt_id,
        role_package.context_digest,
        role_package.package_id,
        role_package.digest,
        instance.instance_id,
        *(
            value
            for value in (
                role_package.source_builder_principal_id,
                role_package.source_builder_attempt_id,
                role_package.source_builder_context_digest,
            )
            if value is not None
        ),
        *(grant.grant_id for grant in grants),
        *(value for value in forbidden if value),
    ]
    if any(
        value.encode("utf-8") in projection_bytes
        for value in forbidden_projection_terms
    ):
        raise PromptCompileError(
            "PRIVATE_PROJECTION_LEAK", "launch projection contains a private binding"
        )
    if projection.projection_id == instance.instance_id:
        raise PromptCompileError(
            "IDENTITY_ALIAS", "safe projection must have a new identity"
        )
    return instance, projection


def reject_nonfinite_budget_record(record: Mapping[str, Any]) -> BudgetEnvelope:
    """Parse a JSON-like budget while rejecting NaN and infinities explicitly.

    Python's runtime permits non-finite floats even though canonical JSON does not.
    This narrow helper makes that rejection available to callers before dataclass
    construction.
    """

    for value in record.values() if isinstance(record, Mapping) else ():
        if isinstance(value, float) and not math.isfinite(value):
            raise PromptCompileError(
                "INVALID_BUDGET", "budget contains a non-finite number"
            )
    return BudgetEnvelope.from_record(record)


__all__ = [
    "BudgetEnvelope",
    "COMPILER_PROFILE",
    "EXECUTION_AUTHORITY",
    "LaunchProjection",
    "MAX_PROMPT_BYTES",
    "MAX_TEMPLATE_BYTES",
    "PromptCompileError",
    "PromptInstance",
    "PromptTemplate",
    "RolePackage",
    "ToolGrant",
    "compile_prompt",
    "reject_nonfinite_budget_record",
]
