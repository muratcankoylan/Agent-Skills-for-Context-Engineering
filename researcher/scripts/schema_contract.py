#!/usr/bin/env python3
"""Strict canonical records, typed identifiers, and schema-registry validation."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
import time
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import SchemaError, ValidationError
    from referencing import Registry, Resource
except ModuleNotFoundError as exc:  # pragma: no cover - dependency failure is explicit at startup.
    raise RuntimeError("Install requirements-dev.txt before using the schema contract") from exc


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / "researcher" / "schemas"
EXTERNAL_SCHEMA_ROOTS = (ROOT / "researcher" / "exports" / "schemas",)
DEFAULT_REGISTRY_PATH = SCHEMA_ROOT / "registry.json"
CANONICALIZATION_PROFILE = "jcs-rfc8785-integer-v1"
SAFE_INTEGER_MAX = (1 << 53) - 1
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
UUID_TEXT = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
TYPED_ID_PATTERN = re.compile(rf"^(?P<prefix>[a-z][a-z0-9]*)_(?P<uuid>{UUID_TEXT})$")
RFC3339_DATETIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LEGACY_ADAPTER_KEY_FIELDS = {
    "LegacyClaim": "claim_id",
    "LegacyMechanism": "mechanism_id",
    "LegacyQueueRecord": "id",
    "LegacyRunState": "run_id",
}


class ContractError(ValueError):
    """A stable, non-sensitive schema-contract failure."""

    def __init__(self, code: str, safe_message: str):
        super().__init__(f"[{code}] {safe_message}")
        self.code = code
        self.safe_message = safe_message


def sha256_bytes(body: bytes) -> str:
    return f"sha256:{hashlib.sha256(body).hexdigest()}"


def _reject_float(_: str) -> None:
    raise ContractError("UNSAFE_NUMBER", "canonical records do not admit floating-point numbers")


def _parse_integer(text: str) -> int:
    if text == "-0":
        raise ContractError("UNSAFE_NUMBER", "negative zero is not canonical")
    value = int(text)
    if abs(value) > SAFE_INTEGER_MAX:
        raise ContractError("UNSAFE_NUMBER", "integer is outside the interoperable safe range")
    return value


def _reject_constant(_: str) -> None:
    raise ContractError("UNSAFE_NUMBER", "non-finite numbers are not valid canonical JSON")


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("DUPLICATE_KEY", "JSON object contains a duplicate key")
        result[key] = value
    return result


def parse_json_strict(text: str) -> Any:
    """Parse the integer-only I-JSON profile without silent key or number coercion."""

    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_without_duplicates,
            parse_int=_parse_integer,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except ContractError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ContractError("INVALID_JSON", "record is not valid UTF-8 JSON") from exc


def _is_rfc3339_datetime(value: object) -> bool:
    if not isinstance(value, str) or not RFC3339_DATETIME_PATTERN.fullmatch(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _is_iso_date(value: object) -> bool:
    if not isinstance(value, str) or not ISO_DATE_PATTERN.fullmatch(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _validate_string(value: str) -> None:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ContractError("INVALID_UNICODE", "lone surrogate code points are not interoperable")


def utf16_sort_key(value: str) -> bytes:
    _validate_string(value)
    return value.encode("utf-16-be")


def validate_tree_path(value: str) -> None:
    if (
        not isinstance(value, str)
        or "\x00" in value
        or "\\" in value
        or unicodedata.normalize("NFC", value) != value
    ):
        raise ContractError("TREE_MANIFEST_INVALID", "freeze entry path is not normalized")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ContractError("TREE_MANIFEST_INVALID", "freeze entry path is unsafe")


def ascii_casefold_path(value: str) -> str:
    """Return the path key used by the portable case-collision profile."""

    return value.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"))


def canonicalize(value: Any) -> bytes:
    """Serialize the RFC 8785 subset used by durable organization records.

    The profile deliberately excludes floats and integers outside the exact
    ECMAScript range. Within that subset, output is RFC 8785 JCS bytes.
    """

    if value is None:
        return b"null"
    if value is True:
        return b"true"
    if value is False:
        return b"false"
    if isinstance(value, int):
        if abs(value) > SAFE_INTEGER_MAX:
            raise ContractError("UNSAFE_NUMBER", "integer is outside the interoperable safe range")
        return str(value).encode("ascii")
    if isinstance(value, float):
        raise ContractError("UNSAFE_NUMBER", "canonical records do not admit floating-point numbers")
    if isinstance(value, str):
        _validate_string(value)
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if isinstance(value, list):
        return b"[" + b",".join(canonicalize(item) for item in value) + b"]"
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ContractError("INVALID_JSON", "JSON object keys must be strings")
        keys = sorted(value, key=utf16_sort_key)
        parts = [canonicalize(key) + b":" + canonicalize(value[key]) for key in keys]
        return b"{" + b",".join(parts) + b"}"
    raise ContractError("INVALID_JSON", f"unsupported JSON value type: {type(value).__name__}")


def canonical_digest(value: Any, *, exclude_integrity_digest: bool = False) -> str:
    candidate = value
    if exclude_integrity_digest and isinstance(value, dict):
        candidate = dict(value)
        integrity = candidate.get("integrity")
        if isinstance(integrity, dict) and "digest" in integrity:
            candidate["integrity"] = {key: item for key, item in integrity.items() if key != "digest"}
    return sha256_bytes(canonicalize(candidate))


def uuid7_timestamp_ms(value: uuid.UUID) -> int:
    if value.version != 7 or value.variant != uuid.RFC_4122:
        raise ContractError("INVALID_ID", "identifier UUID is not RFC 9562 version 7")
    return value.int >> 80


class UUID7Generator:
    """Thread-safe RFC 9562 UUIDv7 generator with monotonic clock-regression handling."""

    def __init__(
        self,
        *,
        clock_ms: Callable[[], int] | None = None,
        random_bits: Callable[[int], int] | None = None,
    ) -> None:
        self._clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
        self._random_bits = random_bits or secrets.randbits
        self._lock = threading.Lock()
        self._last_ms = -1
        self._last_random = -1

    def new(self) -> uuid.UUID:
        with self._lock:
            timestamp_ms = self._clock_ms()
            if not isinstance(timestamp_ms, int) or timestamp_ms < 0 or timestamp_ms >= 1 << 48:
                raise ContractError("CLOCK_RANGE", "UUIDv7 clock is outside its 48-bit range")
            if timestamp_ms > self._last_ms:
                random_value = self._random_bits(74)
                if not 0 <= random_value < 1 << 74:
                    raise ContractError("ENTROPY_RANGE", "UUIDv7 entropy provider returned an invalid value")
            else:
                timestamp_ms = self._last_ms
                random_value = self._last_random + 1
                if random_value >= 1 << 74:
                    timestamp_ms += 1
                    random_value = 0
                    if timestamp_ms >= 1 << 48:
                        raise ContractError("CLOCK_RANGE", "UUIDv7 monotonic range exhausted")
            self._last_ms = timestamp_ms
            self._last_random = random_value
            rand_a = random_value >> 62
            rand_b = random_value & ((1 << 62) - 1)
            integer = (
                (timestamp_ms << 80)
                | (0x7 << 76)
                | (rand_a << 64)
                | (0b10 << 62)
                | rand_b
            )
            return uuid.UUID(int=integer)


DEFAULT_UUID7_GENERATOR = UUID7Generator()


def new_typed_id(prefix: str, *, generator: UUID7Generator = DEFAULT_UUID7_GENERATOR) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9]*", prefix):
        raise ContractError("INVALID_PREFIX", "typed ID prefix is invalid")
    return f"{prefix}_{generator.new()}"


def deterministic_import_id(prefix: str, namespace: uuid.UUID, legacy_key: str) -> str:
    if not legacy_key:
        raise ContractError("INVALID_ID", "legacy import key is empty")
    return f"{prefix}_{uuid.uuid5(namespace, legacy_key)}"


def validate_typed_id(
    value: str,
    *,
    expected_prefix: str,
    id_origin: str = "native",
) -> uuid.UUID:
    match = TYPED_ID_PATTERN.fullmatch(value)
    if not match or match.group("prefix") != expected_prefix:
        raise ContractError("PREFIX_KIND_MISMATCH", "identifier prefix does not match record kind")
    parsed = uuid.UUID(match.group("uuid"))
    expected_version = 5 if id_origin == "legacy_import" else 7
    if parsed.version != expected_version or parsed.variant != uuid.RFC_4122:
        raise ContractError("INVALID_ID", f"identifier must use UUIDv{expected_version}")
    return parsed


@dataclass(frozen=True)
class SchemaEntry:
    kind: str
    version: str
    schema_path: Path
    schema_id: str
    schema_digest: str
    owner_spec: str
    status: str
    compatibility: str
    canonicalization_profile: str
    classifications: tuple[str, ...]
    golden_paths: tuple[Path, ...]
    id_prefix: str | None


class SchemaRegistry:
    """Offline Draft 2020-12 registry with exact schema-file digest pins."""

    def __init__(self, path: Path, document: Mapping[str, Any], entries: Iterable[SchemaEntry]):
        self.path = path
        self.document = dict(document)
        self.entries = tuple(entries)
        self.by_key = {(entry.kind, entry.version): entry for entry in self.entries}
        self.by_kind = {entry.kind: entry for entry in self.entries if entry.status == "active"}
        self._schemas: dict[str, dict[str, Any]] = {}
        self._validators: dict[tuple[str, str], Draft202012Validator] = {}

    @classmethod
    def load(cls, path: Path = DEFAULT_REGISTRY_PATH) -> "SchemaRegistry":
        try:
            document = parse_json_strict(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ContractError("REGISTRY_MISSING", "schema registry could not be read") from exc
        except UnicodeError as exc:
            raise ContractError("REGISTRY_INVALID", "schema registry is not UTF-8") from exc
        if not isinstance(document, dict):
            raise ContractError("REGISTRY_INVALID", "schema registry must be an object")
        try:
            bootstrap_schema = parse_json_strict(
                (SCHEMA_ROOT / "registry.schema.json").read_text(encoding="utf-8")
            )
            if not isinstance(bootstrap_schema, dict):
                raise ContractError("SCHEMA_INVALID", "registry bootstrap schema is not an object")
            Draft202012Validator.check_schema(bootstrap_schema)
        except (OSError, UnicodeError, SchemaError) as exc:
            raise ContractError("SCHEMA_INVALID", "registry bootstrap schema is unavailable") from exc
        bootstrap_errors = sorted(
            Draft202012Validator(bootstrap_schema).iter_errors(document),
            key=str,
        )
        if bootstrap_errors:
            raise ContractError("REGISTRY_INVALID", "schema registry fails its bootstrap schema")
        expected = {
            "schema_version",
            "canonicalization_profile",
            "compatibility_policy",
            "id_prefixes",
            "entries",
        }
        if set(document) != expected:
            raise ContractError("REGISTRY_INVALID", "schema registry top-level fields differ")
        if document["canonicalization_profile"] != CANONICALIZATION_PROFILE:
            raise ContractError("PROFILE_MISMATCH", "unsupported canonicalization profile")
        prefix_map = document["id_prefixes"]
        if (
            not isinstance(prefix_map, dict)
            or not all(isinstance(key, str) and isinstance(value, str) for key, value in prefix_map.items())
            or len(set(prefix_map.values())) != len(prefix_map)
        ):
            raise ContractError("REGISTRY_INVALID", "typed ID prefix registry is invalid")
        entries: list[SchemaEntry] = []
        seen: set[tuple[str, str]] = set()
        seen_ids: dict[str, tuple[Path, str]] = {}
        for raw in document["entries"]:
            if not isinstance(raw, dict):
                raise ContractError("REGISTRY_INVALID", "schema entry must be an object")
            required = {
                "kind",
                "version",
                "schema_path",
                "schema_id",
                "schema_digest",
                "owner_spec",
                "status",
                "compatibility",
                "canonicalization_profile",
                "classifications",
                "golden_paths",
            }
            allowed = required | {"id_prefix"}
            if set(raw) - allowed or required - set(raw):
                raise ContractError("REGISTRY_INVALID", "schema entry fields differ from registry contract")
            key = (raw["kind"], raw["version"])
            if key in seen:
                raise ContractError("DUPLICATE_SCHEMA", "schema kind/version is duplicated")
            seen.add(key)
            relative = Path(raw["schema_path"])
            schema_path = (ROOT / relative).resolve()
            schema_roots = (SCHEMA_ROOT, *EXTERNAL_SCHEMA_ROOTS)
            if not any(
                schema_path == allowed.resolve() or allowed.resolve() in schema_path.parents
                for allowed in schema_roots
            ):
                raise ContractError("PATH_ESCAPE", "registered schema path escapes allowed schema roots")
            prior_resource = seen_ids.get(raw["schema_id"])
            current_resource = (schema_path, raw["schema_digest"])
            if prior_resource is not None and prior_resource != current_resource:
                raise ContractError("DUPLICATE_SCHEMA", "schema $id resolves to different resources")
            seen_ids[raw["schema_id"]] = current_resource
            golden_paths: list[Path] = []
            for golden in raw["golden_paths"]:
                resolved = (ROOT / golden).resolve()
                try:
                    resolved.relative_to(SCHEMA_ROOT.resolve())
                except ValueError as exc:
                    raise ContractError("PATH_ESCAPE", "registered golden path escapes schema root") from exc
                golden_paths.append(resolved)
            entries.append(
                SchemaEntry(
                    kind=raw["kind"],
                    version=raw["version"],
                    schema_path=schema_path,
                    schema_id=raw["schema_id"],
                    schema_digest=raw["schema_digest"],
                    owner_spec=raw["owner_spec"],
                    status=raw["status"],
                    compatibility=raw["compatibility"],
                    canonicalization_profile=raw["canonicalization_profile"],
                    classifications=tuple(raw["classifications"]),
                    golden_paths=tuple(golden_paths),
                    id_prefix=raw.get("id_prefix"),
                )
            )
        result = cls(path, document, entries)
        ordering = [(entry.kind, entry.version) for entry in result.entries]
        if ordering != sorted(ordering):
            raise ContractError("REGISTRY_INVALID", "schema entries must be sorted by kind and version")
        active_kinds = [entry.kind for entry in result.entries if entry.status == "active"]
        if len(active_kinds) != len(set(active_kinds)):
            raise ContractError("REGISTRY_INVALID", "schema kind has more than one active writer version")
        registered_prefixes = {
            entry.id_prefix: entry.kind for entry in result.entries if entry.id_prefix is not None
        }
        if registered_prefixes != prefix_map:
            raise ContractError("REGISTRY_INVALID", "typed ID prefixes disagree with schema entries")
        result._prepare_validators()
        result.validate(document, kind="SchemaRegistry", version="1.0.0")
        return result

    def _prepare_validators(self) -> None:
        resources_by_id: dict[str, Resource[Any]] = {}
        for entry in self.entries:
            try:
                body = entry.schema_path.read_bytes()
            except OSError as exc:
                raise ContractError("SCHEMA_MISSING", "registered schema file is missing") from exc
            if sha256_bytes(body) != entry.schema_digest:
                raise ContractError("SCHEMA_DIGEST_MISMATCH", "registered schema digest is stale")
            schema = parse_json_strict(body.decode("utf-8"))
            if not isinstance(schema, dict) or schema.get("$id") != entry.schema_id:
                raise ContractError("SCHEMA_ID_MISMATCH", "schema $id does not match registry")
            try:
                Draft202012Validator.check_schema(schema)
            except SchemaError as exc:
                raise ContractError("SCHEMA_INVALID", "registered schema fails meta-validation") from exc
            self._schemas[entry.schema_id] = schema
            resources_by_id[entry.schema_id] = Resource.from_contents(schema)
        registry: Registry[Any] = Registry().with_resources(resources_by_id.items())
        checker = FormatChecker()
        checker.checks("date-time")(_is_rfc3339_datetime)
        checker.checks("date")(_is_iso_date)
        for entry in self.entries:
            schema = self._schemas[entry.schema_id]
            self._validators[(entry.kind, entry.version)] = Draft202012Validator(
                schema,
                registry=registry,
                format_checker=checker,
            )

    def _resolve_exact(self, kind: str, version: str) -> SchemaEntry:
        entry = self.by_key.get((kind, version))
        if entry is None:
            if kind in {candidate.kind for candidate in self.entries}:
                raise ContractError("UNSUPPORTED_MAJOR", "record schema version is not registered")
            raise ContractError("UNKNOWN_KIND", "record kind is not registered")
        return entry

    def resolve_for_read(self, kind: str, version: str) -> SchemaEntry:
        entry = self._resolve_exact(kind, version)
        if entry.status not in {"active", "deprecated"}:
            raise ContractError("SCHEMA_INACTIVE", "record schema is not readable")
        return entry

    def resolve_for_write(self, kind: str, version: str) -> SchemaEntry:
        entry = self._resolve_exact(kind, version)
        if entry.status != "active":
            raise ContractError("SCHEMA_INACTIVE", "record schema is not writable")
        return entry

    def resolve(self, kind: str, version: str) -> SchemaEntry:
        """Backward-compatible read resolver; new producers use resolve_for_write()."""

        return self.resolve_for_read(kind, version)

    def validate(
        self,
        record: Mapping[str, Any],
        *,
        kind: str | None = None,
        version: str | None = None,
    ) -> SchemaEntry:
        # Mappings may arrive from in-process producers rather than the strict
        # JSON parser. Enforce the canonical value domain before schema logic.
        canonicalize(dict(record))
        actual_kind = kind if kind is not None else record.get("kind")
        actual_version = version if version is not None else record.get("schema_version")
        if not isinstance(actual_kind, str) or not isinstance(actual_version, str):
            raise ContractError("MISSING_DISCRIMINATOR", "record lacks kind or schema_version")
        entry = self.resolve_for_read(actual_kind, actual_version)
        if entry.compatibility != "legacy-adapter":
            embedded_version = record.get("schema_version")
            if embedded_version != actual_version:
                raise ContractError(
                    "DISCRIMINATOR_MISMATCH",
                    "explicit schema version differs from the record",
                )
            if entry.kind != "SchemaRegistry" and record.get("kind") != actual_kind:
                raise ContractError(
                    "DISCRIMINATOR_MISMATCH",
                    "explicit schema kind differs from the record",
                )
        errors = sorted(self._validators[(entry.kind, entry.version)].iter_errors(record), key=str)
        if errors:
            first: ValidationError = errors[0]
            location = "/".join(str(part) for part in first.absolute_path) or "$"
            raise ContractError("SCHEMA_VALIDATION", f"record fails {entry.kind} at {location}")
        classification = record.get("classification")
        if entry.classifications and classification not in entry.classifications:
            raise ContractError("CLASSIFICATION_MISMATCH", "record classification is not permitted")
        if entry.id_prefix and isinstance(record.get("id"), str):
            validate_typed_id(
                record["id"],
                expected_prefix=entry.id_prefix,
                id_origin=str(record.get("id_origin", "native")),
            )
        self._validate_semantics(record, entry)
        if entry.kind == "ArtifactEnvelope":
            self._validate_artifact_envelope(record)
        elif entry.kind == "ArtifactRef":
            target = self.resolve_for_read(
                str(record["artifact_kind"]),
                str(record["artifact_schema_version"]),
            )
            if target.id_prefix is None:
                raise ContractError(
                    "ARTIFACT_TARGET_INVALID",
                    "artifact reference target has no typed identity",
                )
            validate_typed_id(
                str(record["artifact_id"]),
                expected_prefix=target.id_prefix,
                id_origin=str(record["artifact_id_origin"]),
            )
        return entry

    def _validate_artifact_envelope(self, record: Mapping[str, Any]) -> None:
        target = self.resolve_for_read(
            str(record["artifact_kind"]),
            str(record["artifact_schema_version"]),
        )
        if target.kind == "ArtifactEnvelope":
            raise ContractError(
                "ENVELOPE_TARGET_INVALID",
                "artifact envelopes cannot recursively target themselves",
            )
        payload = record["payload"]
        if not isinstance(payload, Mapping):
            raise ContractError("ENVELOPE_PAYLOAD_INVALID", "artifact envelope payload is invalid")
        if record["id_origin"] != "legacy_import":
            if target.compatibility == "legacy-adapter":
                raise ContractError(
                    "ENVELOPE_TARGET_INVALID",
                    "legacy adapter targets require a declared legacy import",
                )
            self.validate(payload, kind=target.kind, version=target.version)
            return

        if target.compatibility != "legacy-adapter":
            raise ContractError(
                "ENVELOPE_TARGET_INVALID",
                "legacy imports must target a registered legacy adapter",
            )
        required = {"legacy_kind", "legacy_key", "source_digest", "source_record"}
        allowed = required | {"source_path"}
        if set(payload) - allowed or required - set(payload):
            raise ContractError(
                "ENVELOPE_PAYLOAD_INVALID",
                "legacy import payload fields differ from the contract",
            )
        legacy_kind = payload["legacy_kind"]
        legacy_key = payload["legacy_key"]
        source_record = payload["source_record"]
        source_path = payload.get("source_path")
        if (
            legacy_kind != target.kind
            or not isinstance(legacy_key, str)
            or not legacy_key
            or not isinstance(source_record, Mapping)
            or (source_path is not None and (not isinstance(source_path, str) or not source_path))
        ):
            raise ContractError(
                "ENVELOPE_PAYLOAD_INVALID",
                "legacy import payload metadata is inconsistent",
            )
        if target.kind == "LegacyQueueRecord" and source_path is None:
            raise ContractError(
                "ENVELOPE_PAYLOAD_INVALID",
                "legacy queue imports require source-path identity scope",
            )
        key_field = LEGACY_ADAPTER_KEY_FIELDS.get(target.kind)
        if key_field is None or source_record.get(key_field) != legacy_key:
            raise ContractError(
                "ENVELOPE_PAYLOAD_INVALID",
                "legacy import key disagrees with its source record",
            )
        source_digest = canonical_digest(dict(source_record))
        if payload["source_digest"] != source_digest:
            raise ContractError(
                "ENVELOPE_PAYLOAD_INVALID",
                "legacy import source digest is invalid",
            )
        if source_digest not in record["input_digests"] or legacy_key not in record["aliases"]:
            raise ContractError(
                "ENVELOPE_PAYLOAD_INVALID",
                "legacy import provenance does not bind its payload",
            )
        self.validate(source_record, kind=target.kind, version=target.version)

    @staticmethod
    def _validate_semantics(record: Mapping[str, Any], entry: SchemaEntry) -> None:
        if entry.kind == "ArtifactEnvelope":
            integrity = record["integrity"]
            if integrity["digest"] != canonical_digest(
                dict(record),
                exclude_integrity_digest=True,
            ):
                raise ContractError("INTEGRITY_MISMATCH", "artifact envelope integrity digest is invalid")
        elif entry.kind == "CapabilityGrantSpec":
            body = {key: value for key, value in record.items() if key != "grant_digest"}
            if record["grant_digest"] != canonical_digest(body):
                raise ContractError("GRANT_DIGEST_MISMATCH", "capability grant digest is invalid")
            issued_at = datetime.fromisoformat(str(record["issued_at"]).replace("Z", "+00:00"))
            expires_at = datetime.fromisoformat(str(record["expires_at"]).replace("Z", "+00:00"))
            if expires_at <= issued_at:
                raise ContractError("CAPABILITY_WINDOW", "capability expiry must follow issuance")
        elif entry.kind == "FreezeReceipt":
            entries = record["entries"]
            paths = [item["path"] for item in entries]
            for path in paths:
                validate_tree_path(path)
            if paths != sorted(paths, key=utf16_sort_key) or len(paths) != len(set(paths)):
                raise ContractError("TREE_MANIFEST_INVALID", "freeze entries must have unique sorted paths")
            collision_keys = [ascii_casefold_path(path) for path in paths]
            if len(collision_keys) != len(set(collision_keys)):
                raise ContractError(
                    "TREE_MANIFEST_INVALID",
                    "freeze entry paths collide under the portable path profile",
                )
            if record["file_count"] != len(entries):
                raise ContractError("TREE_MANIFEST_INVALID", "freeze file count disagrees with entries")
            if record["total_size_bytes"] != sum(item["size_bytes"] for item in entries):
                raise ContractError("TREE_MANIFEST_INVALID", "freeze byte count disagrees with entries")
            if record["tree_digest"] != canonical_digest(entries):
                raise ContractError("TREE_DIGEST_MISMATCH", "freeze tree digest is invalid")
        elif entry.kind == "CandidateArtifact":
            parent_ids = record["parent_candidate_ids"]
            if record["id"] in parent_ids:
                raise ContractError("CANDIDATE_CYCLE", "candidate cannot be its own parent")
            if "revision_of" in record and record["revision_of"] not in parent_ids:
                raise ContractError("CANDIDATE_PARENT_MISMATCH", "revision_of must also be a parent")
        elif entry.kind == "ExportApproval":
            expected = "approved" if record["decision"] == "approve" else "rejected"
            if record["state"] != expected:
                raise ContractError("EXPORT_DECISION_MISMATCH", "export approval state and decision differ")


def validate_digest(value: str) -> None:
    if not DIGEST_PATTERN.fullmatch(value):
        raise ContractError("INVALID_DIGEST", "SHA-256 digest has invalid form")


def stable_error(exc: Exception) -> dict[str, str]:
    if isinstance(exc, ContractError):
        return {"code": exc.code, "message": exc.safe_message}
    return {"code": "INTERNAL_ERROR", "message": exc.__class__.__name__}
