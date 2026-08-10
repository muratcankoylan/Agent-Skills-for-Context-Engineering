import { canonicalDigest } from "./canonicalize.js";
import { ContractError } from "./errors.js";
import type { JsonValue } from "./json.js";

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
