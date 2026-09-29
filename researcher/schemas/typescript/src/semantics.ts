import { createHash } from "node:crypto";

import { canonicalDigest } from "./canonicalize.js";
import { ContractError } from "./errors.js";
import type { JsonValue } from "./json.js";

const RUN_EVENT_IMPORT_NAMESPACE = "b5a8ef43-d10b-5dd9-9406-31c558426e6d";
const RUN_EVENT_IMPORT_IDEMPOTENCY_SCOPE = "research_loop_file_shadow";
const RUN_EVENT_IMPORT_ACTOR: Record<string, JsonValue> = {
  id: "research-loop-file-shadow",
  class: "legacy_file_bridge",
};
const RUN_EVENT_IMPORT_AUTHORITY: Record<string, JsonValue> = {
  outcome: "legacy_authority_not_recorded",
  actor_class: "legacy_file_bridge",
  action: "mirror_legacy_state",
  resource: "research_run",
  reason_code: "LEGACY_AUTHORITY_NOT_RECORDED",
  constitution_version: null,
  constitution_digest: null,
  context_digest: null,
  matched_rule: null,
};

export function deterministicRunEventId(runId: string, historyIndex: number): string {
  validateRunEventImportInputs(runId, historyIndex, "INVALID_ID");
  const key = `research-run-transition/v1:${runId}:${historyIndex}`;
  return `evt_${uuidV5(RUN_EVENT_IMPORT_NAMESPACE, key)}`;
}

export function deterministicRunEventIdempotencyDigest(
  runId: string,
  historyIndex: number,
): string {
  validateRunEventImportInputs(runId, historyIndex, "INVALID_DIGEST");
  const key = `research-run-transition-idempotency/v1:${runId}:${historyIndex}`;
  return `sha256:${createHash("sha256").update(key, "utf8").digest("hex")}`;
}

function validateRunEventImportInputs(
  runId: string,
  historyIndex: number,
  code: "INVALID_ID" | "INVALID_DIGEST",
): void {
  if (
    runId.length === 0 ||
    !Number.isSafeInteger(historyIndex) ||
    historyIndex < 0 ||
    historyIndex >= Number.MAX_SAFE_INTEGER
  ) {
    throw new ContractError(code, "run-event import identity inputs are invalid");
  }
}

function uuidV5(namespace: string, name: string): string {
  const namespaceBytes = Buffer.from(namespace.replaceAll("-", ""), "hex");
  if (namespaceBytes.length !== 16) {
    throw new ContractError("INVALID_ID", "run-event namespace is invalid");
  }
  const bytes = createHash("sha1")
    .update(namespaceBytes)
    .update(name, "utf8")
    .digest()
    .subarray(0, 16);
  bytes[6] = (bytes[6]! & 0x0f) | 0x50;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  const hex = bytes.toString("hex");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/** Apply the invariants that JSON Schema cannot express for registered records. */
export function validateRecordSemantics(
  record: Record<string, JsonValue>,
  kind: string,
): void {
  switch (kind) {
    case "ArtifactEnvelope":
      validateArtifactEnvelope(record);
      return;
    case "CapabilityGrantSpec":
      validateCapabilityGrant(record);
      return;
    case "FreezeReceipt":
      validateFreezeReceipt(record);
      return;
    case "CandidateArtifact":
      validateCandidateArtifact(record);
      return;
    case "ResearchRunTransition":
      validateResearchRunTransition(record);
      return;
    case "OrganizationEvent":
      validateOrganizationEvent(record);
      return;
    case "ExportApproval":
      validateExportApproval(record);
      return;
    default:
      return;
  }
}

function validateArtifactEnvelope(record: Record<string, JsonValue>): void {
  const integrity = objectField(record, "integrity");
  const digest = stringField(integrity, "digest");
  const integrityBody = omit(integrity, "digest");
  const body: Record<string, JsonValue> = { ...record, integrity: integrityBody };
  if (digest !== canonicalDigest(body)) {
    throw new ContractError(
      "INTEGRITY_MISMATCH",
      "artifact envelope integrity digest is invalid",
    );
  }
}

function validateCapabilityGrant(record: Record<string, JsonValue>): void {
  const digest = stringField(record, "grant_digest");
  if (digest !== canonicalDigest(omit(record, "grant_digest"))) {
    throw new ContractError("GRANT_DIGEST_MISMATCH", "capability grant digest is invalid");
  }
  const issuedAt = Date.parse(stringField(record, "issued_at"));
  const expiresAt = Date.parse(stringField(record, "expires_at"));
  if (!Number.isFinite(issuedAt) || !Number.isFinite(expiresAt) || expiresAt <= issuedAt) {
    throw new ContractError("CAPABILITY_WINDOW", "capability expiry must follow issuance");
  }
}

function validateFreezeReceipt(record: Record<string, JsonValue>): void {
  const entriesValue = record.entries;
  if (!Array.isArray(entriesValue)) {
    schemaAssumption("freeze entries are not an array");
  }
  const entries = entriesValue.map((entry) => objectValue(entry, "freeze entry is not an object"));
  const paths = entries.map((entry) => stringField(entry, "path"));
  for (const path of paths) {
    validateTreePath(path);
  }
  // ECMAScript's default string ordering compares UTF-16 code units. That is
  // the ordering required by the repository's RFC 8785-compatible profile.
  const sortedPaths = [...paths].sort();
  if (!sameStrings(paths, sortedPaths) || new Set(paths).size !== paths.length) {
    throw new ContractError(
      "TREE_MANIFEST_INVALID",
      "freeze entries must have unique sorted paths",
    );
  }
  const collisionKeys = paths.map(asciiCasefoldPath);
  if (new Set(collisionKeys).size !== collisionKeys.length) {
    throw new ContractError(
      "TREE_MANIFEST_INVALID",
      "freeze entry paths collide under the portable path profile",
    );
  }
  if (numberField(record, "file_count") !== entries.length) {
    throw new ContractError(
      "TREE_MANIFEST_INVALID",
      "freeze file count disagrees with entries",
    );
  }
  const totalSize = entries.reduce(
    (total, entry) => total + BigInt(numberField(entry, "size_bytes")),
    0n,
  );
  if (BigInt(numberField(record, "total_size_bytes")) !== totalSize) {
    throw new ContractError(
      "TREE_MANIFEST_INVALID",
      "freeze byte count disagrees with entries",
    );
  }
  if (stringField(record, "tree_digest") !== canonicalDigest(entriesValue)) {
    throw new ContractError("TREE_DIGEST_MISMATCH", "freeze tree digest is invalid");
  }
}

function validateCandidateArtifact(record: Record<string, JsonValue>): void {
  const id = stringField(record, "id");
  const parentValue = record.parent_candidate_ids;
  if (!Array.isArray(parentValue) || !parentValue.every((value) => typeof value === "string")) {
    schemaAssumption("candidate parent IDs are invalid");
  }
  const parentIds = parentValue as string[];
  if (parentIds.includes(id)) {
    throw new ContractError("CANDIDATE_CYCLE", "candidate cannot be its own parent");
  }
  if (record.revision_of !== undefined) {
    const revisionOf = stringField(record, "revision_of");
    if (!parentIds.includes(revisionOf)) {
      throw new ContractError(
        "CANDIDATE_PARENT_MISMATCH",
        "revision_of must also be a parent",
      );
    }
  }
}

function validateResearchRunTransition(record: Record<string, JsonValue>): void {
  const historyIndex = numberField(record, "history_index");
  const fromState = record.from_state;
  const toState = stringField(record, "to_state");
  const initialization = record.initialization;
  const closure = record.closure;
  if (historyIndex === 0) {
    if (fromState !== null || toState !== "initialized" || initialization === null) {
      throw new ContractError(
        "RUN_EVENT_TRANSITION_INVALID",
        "first run transition must initialize the subject",
      );
    }
  } else if (
    typeof fromState !== "string" ||
    toState === "initialized" ||
    fromState === toState
  ) {
    throw new ContractError(
      "RUN_EVENT_TRANSITION_INVALID",
      "later run transition has inconsistent states",
    );
  }
  if ((toState === "initialized") !== (initialization !== null)) {
    throw new ContractError(
      "RUN_EVENT_TRANSITION_INVALID",
      "run initialization metadata disagrees with the target state",
    );
  }
  if (initialization !== null) {
    const initializationRecord = objectValue(
      initialization,
      "run initialization is not an object",
    );
    const locked = stringArrayField(initializationRecord, "locked_surfaces");
    const editable = new Set(stringArrayField(initializationRecord, "editable_surfaces"));
    if (locked.some((surface) => editable.has(surface))) {
      throw new ContractError(
        "RUN_EVENT_TRANSITION_INVALID",
        "run initialization surfaces cannot be both locked and editable",
      );
    }
  }
  if ((toState === "closed") !== (closure !== null)) {
    throw new ContractError(
      "RUN_EVENT_TRANSITION_INVALID",
      "run closure metadata disagrees with the target state",
    );
  }
  if (closure !== null) {
    const closureRecord = objectValue(closure, "run closure is not an object");
    if (stringField(closureRecord, "reason") !== stringField(record, "reason")) {
      throw new ContractError(
        "RUN_EVENT_TRANSITION_INVALID",
        "run closure reason disagrees with the transition",
      );
    }
  }
}

function validateOrganizationEvent(record: Record<string, JsonValue>): void {
  const payload = objectField(record, "payload");
  if (stringField(record, "payload_digest") !== canonicalDigest(payload)) {
    throw new ContractError(
      "EVENT_PAYLOAD_DIGEST_MISMATCH",
      "event payload digest is invalid",
    );
  }
  const subject = objectField(record, "subject");
  const eventType = `research_run.${stringField(payload, "to_state")}`;
  if (
    stringField(record, "event_type") !== eventType ||
    stringField(subject, "id") !== stringField(payload, "run_id") ||
    numberField(subject, "version") !== numberField(payload, "history_index") + 1 ||
    stringField(record, "classification") !== stringField(payload, "classification")
  ) {
    throw new ContractError(
      "EVENT_PAYLOAD_MISMATCH",
      "event routing fields disagree with the run transition",
    );
  }
  const actor = objectField(record, "actor");
  const authority = objectField(record, "authority");
  if (stringField(actor, "class") !== stringField(authority, "actor_class")) {
    throw new ContractError(
      "EVENT_AUTHORITY_MISMATCH",
      "event actor disagrees with its authority decision",
    );
  }
  const source = stringField(payload, "transition_source");
  const imported = source === "file_state_history";
  const repository = objectField(record, "repository");
  if (imported) {
    const runId = stringField(payload, "run_id");
    const historyIndex = numberField(payload, "history_index");
    const expectedId = deterministicRunEventId(runId, historyIndex);
    const expectedCorrelation = deterministicRunEventId(runId, 0);
    const expectedCausation =
      historyIndex === 0 ? null : deterministicRunEventId(runId, historyIndex - 1);
    const idempotency = objectField(record, "idempotency");
    const deterministic =
      record.id_origin === "legacy_import" &&
      record.id === expectedId &&
      record.correlation_event_id === expectedCorrelation &&
      record.causation_event_id === expectedCausation &&
      idempotency.scope === RUN_EVENT_IMPORT_IDEMPOTENCY_SCOPE &&
      idempotency.key_digest === deterministicRunEventIdempotencyDigest(runId, historyIndex) &&
      canonicalDigest(actor) === canonicalDigest(RUN_EVENT_IMPORT_ACTOR) &&
      canonicalDigest(authority) === canonicalDigest(RUN_EVENT_IMPORT_AUTHORITY) &&
      repository.commit_sha === null &&
      repository.pull_request === null &&
      record.classification === "private_operational" &&
      payload.classification === "private_operational" &&
      record.detail_ref === null;
    if (!deterministic) {
      throw new ContractError(
        "RUN_EVENT_ORIGIN_MISMATCH",
        "file-shadow event provenance is not deterministic",
      );
    }
  } else {
    const authorized =
      record.id_origin === "native" &&
      objectField(record, "idempotency").scope !== RUN_EVENT_IMPORT_IDEMPOTENCY_SCOPE &&
      authority.outcome === "allowed" &&
      typeof authority.constitution_version === "string" &&
      typeof authority.constitution_digest === "string" &&
      typeof authority.context_digest === "string" &&
      typeof authority.matched_rule === "string";
    if (!authorized) {
      throw new ContractError(
        "RUN_EVENT_ORIGIN_MISMATCH",
        "native run event lacks an allowed authority decision",
      );
    }
  }
  const toState = stringField(payload, "to_state");
  if (toState === "initialized") {
    const initialization = objectValue(
      payload.initialization,
      "run initialization is not an object",
    );
    if (stringField(initialization, "created_at") !== stringField(record, "occurred_at")) {
      throw new ContractError(
        "EVENT_PAYLOAD_MISMATCH",
        "initialization time disagrees with the event",
      );
    }
  }
  if (toState === "closed") {
    const closure = objectValue(payload.closure, "run closure is not an object");
    if (stringField(closure, "closed_at") !== stringField(record, "occurred_at")) {
      throw new ContractError(
        "EVENT_PAYLOAD_MISMATCH",
        "closure time disagrees with the event",
      );
    }
  }
  const eventId = stringField(record, "id");
  const subjectVersion = numberField(subject, "version");
  const causation = record.causation_event_id;
  const validCausation =
    subjectVersion === 1
      ? causation === null && record.correlation_event_id === eventId
      : typeof causation === "string" && causation !== eventId;
  if (!validCausation) {
    throw new ContractError(
      "EVENT_CAUSATION_INVALID",
      "event correlation or causation is inconsistent",
    );
  }
  if (record.detail_ref !== null) {
    const detailRef = objectValue(record.detail_ref, "event detail reference is not an object");
    if (detailRef.classification !== record.classification) {
      throw new ContractError(
        "EVENT_DETAIL_REF_INVALID",
        "event detail classification disagrees with the event",
      );
    }
  }
}

function validateExportApproval(record: Record<string, JsonValue>): void {
  const expected = stringField(record, "decision") === "approve" ? "approved" : "rejected";
  if (record.state !== expected) {
    throw new ContractError(
      "EXPORT_DECISION_MISMATCH",
      "export approval state and decision differ",
    );
  }
}

function omit(record: Record<string, JsonValue>, keyToOmit: string): Record<string, JsonValue> {
  return Object.fromEntries(
    Object.entries(record).filter(([key]) => key !== keyToOmit),
  ) as Record<string, JsonValue>;
}

function objectField(
  record: Record<string, JsonValue>,
  key: string,
): Record<string, JsonValue> {
  return objectValue(record[key], `field ${key} is not an object`);
}

function stringArrayField(record: Record<string, JsonValue>, key: string): string[] {
  const value = record[key];
  if (!Array.isArray(value) || !value.every((item) => typeof item === "string")) {
    schemaAssumption(`${key} is not a string array`);
  }
  return value as string[];
}

function objectValue(value: JsonValue | undefined, message: string): Record<string, JsonValue> {
  if (value === undefined || value === null || Array.isArray(value) || typeof value !== "object") {
    schemaAssumption(message);
  }
  return value;
}

function stringField(record: Record<string, JsonValue>, key: string): string {
  const value = record[key];
  if (typeof value !== "string") {
    schemaAssumption(`field ${key} is not a string`);
  }
  return value;
}

function numberField(record: Record<string, JsonValue>, key: string): number {
  const value = record[key];
  if (typeof value !== "number" || !Number.isSafeInteger(value)) {
    schemaAssumption(`field ${key} is not a safe integer`);
  }
  return value;
}

function sameStrings(left: readonly string[], right: readonly string[]): boolean {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

function validateTreePath(path: string): void {
  const parts = path.split("/");
  if (
    path.length === 0 ||
    path.startsWith("/") ||
    path.includes("\\") ||
    path.includes("\u0000") ||
    path.normalize("NFC") !== path ||
    parts.some((part) => part === "" || part === "." || part === "..")
  ) {
    throw new ContractError("TREE_MANIFEST_INVALID", "freeze entry path is unsafe");
  }
}

function asciiCasefoldPath(path: string): string {
  return path.replace(/[A-Z]/g, (character) => character.toLowerCase());
}

function schemaAssumption(message: string): never {
  throw new ContractError("SCHEMA_VALIDATION", message);
}
