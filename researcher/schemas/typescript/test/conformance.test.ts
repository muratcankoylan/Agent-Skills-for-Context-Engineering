import assert from "node:assert/strict";
import { test } from "node:test";

import {
  ContractError,
  canonicalDigest,
  canonicalize,
  parseJsonStrict,
  runRepositoryConformance,
  validateRecordSemantics,
  validateTypedId,
} from "../src/index.js";
import type { JsonValue } from "../src/index.js";

function assertContractCode(source: () => unknown, code: string): void {
  assert.throws(source, (error: unknown) => error instanceof ContractError && error.code === code);
}

test("matches every generated canonicalization result and registered golden count", () => {
  const result = runRepositoryConformance();
  assert.equal(result.registeredSchemaCount, 20);
  assert.equal(result.goldenRecordCount, 21);
  assert.equal(result.canonicalizationCases.length, 12);
  assert.equal(
    result.suiteDigest,
    "sha256:f85913b47745ef1e028a1f36988ce33419658bdcdb382402f76e316386244091",
  );
});

test("strict parser rejects literal and escape-equivalent duplicate keys", () => {
  assertContractCode(() => parseJsonStrict('{"a":1,"a":2}'), "DUPLICATE_KEY");
  assertContractCode(() => parseJsonStrict('{"a":1,"\\u0061":2}'), "DUPLICATE_KEY");
  const prototypeKey = parseJsonStrict('{"__proto__":1}') as Record<string, JsonValue>;
  assert.equal(prototypeKey.__proto__, 1);
  assert.equal(Object.getPrototypeOf(prototypeKey), Object.prototype);
});

test("strict parser accepts only safe, non-negative-zero integers", () => {
  assert.deepEqual(
    parseJsonStrict("[-9007199254740991,0,9007199254740991]"),
    [-9_007_199_254_740_991, 0, 9_007_199_254_740_991],
  );
  for (const source of ["1.5", "1e0", "-0", "9007199254740992", "NaN", "Infinity", "-Infinity"]) {
    assertContractCode(() => parseJsonStrict(source), "UNSAFE_NUMBER");
  }
});

test("strict parser and canonicalizer reject lone surrogates", () => {
  assertContractCode(() => parseJsonStrict('{"value":"\\ud800"}'), "INVALID_UNICODE");
  assertContractCode(() => canonicalize("\ud800"), "INVALID_UNICODE");
});

test("canonicalization uses UTF-16 key order without Unicode normalization", () => {
  const value = parseJsonStrict('{"":1,"😀":2,"é":"NFC","é":"NFD"}');
  assert.equal(canonicalize(value), '{"é":"NFD","é":"NFC","😀":2,"":1}');
  assert.equal(
    canonicalize(parseJsonStrict('{"line":"a b","control":"\\u0001"}')),
    '{"control":"\\u0001","line":"a b"}',
  );
});

test("canonical digest is SHA-256 over UTF-8 canonical bytes", () => {
  assert.equal(
    canonicalDigest(parseJsonStrict('{"z":1,"a":"é"}')),
    "sha256:fb64e573f7cde5b7efeda52ffc4bdd57572055b0b7e64a70172606c82c6c7eac",
  );
  assertContractCode(() => canonicalize(1.5), "UNSAFE_NUMBER");
  assertContractCode(() => canonicalize(-0), "UNSAFE_NUMBER");
});

test("semantic checks verify artifact and capability digests", () => {
  const envelope: Record<string, JsonValue> = {
    id: "rec_example",
    integrity: {
      algorithm: "sha256",
      canonicalization_profile: "jcs-rfc8785-integer-v1",
      digest: "sha256:bad",
    },
  };
  assertContractCode(
    () => validateRecordSemantics(envelope, "ArtifactEnvelope"),
    "INTEGRITY_MISMATCH",
  );

  const grant: Record<string, JsonValue> = {
    expires_at: "2026-08-10T12:00:00Z",
    grant_digest: "",
    issued_at: "2026-08-10T12:00:00Z",
  };
  grant.grant_digest = canonicalDigest({
    expires_at: grant.expires_at as string,
    issued_at: grant.issued_at as string,
  });
  assertContractCode(
    () => validateRecordSemantics(grant, "CapabilityGrantSpec"),
    "CAPABILITY_WINDOW",
  );
  grant.grant_digest = "sha256:bad";
  assertContractCode(
    () => validateRecordSemantics(grant, "CapabilityGrantSpec"),
    "GRANT_DIGEST_MISMATCH",
  );
});

test("semantic checks verify freeze manifests and tree digests", () => {
  const entries: JsonValue[] = [
    { path: "b", size_bytes: 1 },
    { path: "a", size_bytes: 2 },
  ];
  const freeze: Record<string, JsonValue> = {
    entries,
    file_count: 2,
    total_size_bytes: 3,
    tree_digest: canonicalDigest(entries),
  };
  assertContractCode(
    () => validateRecordSemantics(freeze, "FreezeReceipt"),
    "TREE_MANIFEST_INVALID",
  );
  freeze.entries = [entries[1] as JsonValue, entries[0] as JsonValue];
  freeze.tree_digest = "sha256:bad";
  assertContractCode(
    () => validateRecordSemantics(freeze, "FreezeReceipt"),
    "TREE_DIGEST_MISMATCH",
  );

  const utf16Entries: JsonValue[] = [
    { path: "😀", size_bytes: 1 },
    { path: "", size_bytes: 1 },
  ];
  assert.doesNotThrow(() =>
    validateRecordSemantics(
      {
        entries: utf16Entries,
        file_count: 2,
        total_size_bytes: 2,
        tree_digest: canonicalDigest(utf16Entries),
      },
      "FreezeReceipt",
    ),
  );

  const unsafeEntries: JsonValue[] = [{ path: "../escape", size_bytes: 1 }];
  assertContractCode(
    () =>
      validateRecordSemantics(
        {
          entries: unsafeEntries,
          file_count: 1,
          total_size_bytes: 1,
          tree_digest: canonicalDigest(unsafeEntries),
        },
        "FreezeReceipt",
      ),
    "TREE_MANIFEST_INVALID",
  );
});

test("semantic checks verify candidate ancestry and export decisions", () => {
  assertContractCode(
    () =>
      validateRecordSemantics(
        { id: "cand_a", parent_candidate_ids: ["cand_a"] },
        "CandidateArtifact",
      ),
    "CANDIDATE_CYCLE",
  );
  assertContractCode(
    () =>
      validateRecordSemantics(
        { id: "cand_a", parent_candidate_ids: [], revision_of: "cand_b" },
        "CandidateArtifact",
      ),
    "CANDIDATE_PARENT_MISMATCH",
  );
  assertContractCode(
    () =>
      validateRecordSemantics(
        { decision: "approve", state: "rejected" },
        "ExportApproval",
      ),
    "EXPORT_DECISION_MISMATCH",
  );
});

test("typed IDs enforce registered prefixes and origin-specific UUID versions", () => {
  assert.doesNotThrow(() =>
    validateTypedId("rec_018f3e40-7b80-7a21-8000-000000000001", "rec"),
  );
  assert.doesNotThrow(() =>
    validateTypedId(
      "rec_018f3e40-7b80-5a21-8000-000000000001",
      "rec",
      "legacy_import",
    ),
  );
  assertContractCode(
    () => validateTypedId("cand_018f3e40-7b80-7a21-8000-000000000001", "rec"),
    "PREFIX_KIND_MISMATCH",
  );
  assertContractCode(
    () => validateTypedId("rec_018f3e40-7b80-5a21-8000-000000000001", "rec"),
    "INVALID_ID",
  );
});
