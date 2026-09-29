import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { test } from "node:test";

import {
  canonicalDigest,
  ContractError,
  deterministicRunEventId,
  deterministicRunEventIdempotencyDigest,
  loadRuntimeRegistry,
  parseJsonStrict,
  repositoryRootFromModule,
  type JsonValue,
  type LoadedRuntimeRegistry,
  type RegistryDocument,
  type RegistryEntry,
} from "../src/index.js";

type MutableRegistryEntry = {
  -readonly [Key in keyof RegistryEntry]: RegistryEntry[Key];
};

interface MutableRegistryDocument extends Omit<RegistryDocument, "entries"> {
  entries: MutableRegistryEntry[];
}

const repositoryRoot = repositoryRootFromModule();

function assertContractCode(source: () => unknown, code: string): void {
  assert.throws(source, (error: unknown) => error instanceof ContractError && error.code === code);
}

function fixture(name: string): Record<string, JsonValue> {
  const value = parseJsonStrict(
    readFileSync(
      resolve(repositoryRoot, "researcher/schemas/fixtures/records", name),
      "utf8",
    ),
  );
  assert(value !== null && !Array.isArray(value) && typeof value === "object");
  return value;
}

function bindEnvelopeDigest(envelope: Record<string, JsonValue>): void {
  const body = structuredClone(envelope);
  const bodyIntegrity = body.integrity;
  const envelopeIntegrity = envelope.integrity;
  assert(
    bodyIntegrity !== null &&
      !Array.isArray(bodyIntegrity) &&
      typeof bodyIntegrity === "object" &&
      envelopeIntegrity !== null &&
      !Array.isArray(envelopeIntegrity) &&
      typeof envelopeIntegrity === "object",
  );
  delete bodyIntegrity.digest;
  envelopeIntegrity.digest = canonicalDigest(body);
}

function loadModifiedRegistry(
  mutate: (document: MutableRegistryDocument) => void,
): LoadedRuntimeRegistry {
  const source = loadRuntimeRegistry(repositoryRoot).document;
  const document = structuredClone(source) as MutableRegistryDocument;
  mutate(document);
  const temporary = mkdtempSync(join(tmpdir(), "typescript-schema-registry-"));
  const registryPath = join(temporary, "registry.json");
  try {
    writeFileSync(registryPath, `${JSON.stringify(document, null, 2)}\n`, "utf8");
    return loadRuntimeRegistry(repositoryRoot, registryPath);
  } finally {
    rmSync(temporary, { force: true, recursive: true });
  }
}

function entry(document: MutableRegistryDocument, kind: string): MutableRegistryEntry {
  const found = document.entries.find((candidate) => candidate.kind === kind);
  assert(found !== undefined);
  return found;
}

test("loaded runtime registry reuses validators for valid and rejected records", () => {
  const registry = loadRuntimeRegistry(repositoryRoot);
  const artifactRef = fixture("artifact-ref.json");

  assert.equal(registry.validateRecord(artifactRef).kind, "ArtifactRef");
  assert.equal(registry.resolveForRead("ArtifactRef", "1.0.0").status, "active");
  assert.equal(registry.resolveForWrite("ArtifactRef", "1.0.0").status, "active");

  artifactRef.private_locator = "/private/example";
  assertContractCode(() => registry.validateRecord(artifactRef), "SCHEMA_VALIDATION");
  delete artifactRef.private_locator;
  artifactRef.size_bytes = 1.5;
  assertContractCode(() => registry.validateRecord(artifactRef), "UNSAFE_NUMBER");
  assertContractCode(
    () => registry.validateRecord({}, { kind: "UnknownThing", version: "1.0.0" }),
    "UNKNOWN_KIND",
  );
  assertContractCode(
    () => registry.resolveForRead("ArtifactRef", "2.0.0"),
    "UNSUPPORTED_MAJOR",
  );
  assertContractCode(() => registry.validateRecord({}), "MISSING_DISCRIMINATOR");
});

test("explicit discriminators cannot route a record through a sibling schema", () => {
  const registry = loadRuntimeRegistry(repositoryRoot);
  const manifest = fixture("export-manifest.json");
  assertContractCode(
    () => registry.validateRecord(manifest, { kind: "ExportValidation", version: "1.0.0" }),
    "DISCRIMINATOR_MISMATCH",
  );

  const artifactRef = fixture("artifact-ref.json");
  artifactRef.schema_version = "9.0.0";
  assertContractCode(
    () => registry.validateRecord(artifactRef, { kind: "ArtifactRef", version: "1.0.0" }),
    "DISCRIMINATOR_MISMATCH",
  );
});

test("artifact references resolve their target kind, version, prefix, and origin", () => {
  const registry = loadRuntimeRegistry(repositoryRoot);
  const mismatched = fixture("artifact-ref.json");
  mismatched.artifact_id = fixture("capability-grant-spec.json").id as JsonValue;
  assertContractCode(() => registry.validateRecord(mismatched), "PREFIX_KIND_MISMATCH");

  const wrongOrigin = fixture("artifact-ref.json");
  wrongOrigin.artifact_id_origin = "legacy_import";
  wrongOrigin.artifact_id = "cand_abd043a6-b030-521d-bb61-1bbc791062c4";
  assertContractCode(() => registry.validateRecord(wrongOrigin), "ARTIFACT_TARGET_INVALID");

  const unknown = fixture("artifact-ref.json");
  unknown.artifact_kind = "UnknownArtifact";
  assertContractCode(() => registry.validateRecord(unknown), "UNKNOWN_KIND");

  const unsupported = fixture("artifact-ref.json");
  unsupported.artifact_schema_version = "2.0.0";
  assertContractCode(() => registry.validateRecord(unsupported), "UNSUPPORTED_MAJOR");
});

test("artifact envelopes resolve and validate their declared payload contract", () => {
  const registry = loadRuntimeRegistry(repositoryRoot);
  const unknown = fixture("artifact-envelope.json");
  unknown.artifact_kind = "UnknownArtifact";
  bindEnvelopeDigest(unknown);
  assertContractCode(() => registry.validateRecord(unknown), "UNKNOWN_KIND");

  const unsupported = fixture("artifact-envelope.json");
  unsupported.artifact_schema_version = "2.0.0";
  bindEnvelopeDigest(unsupported);
  assertContractCode(() => registry.validateRecord(unsupported), "UNSUPPORTED_MAJOR");

  const mismatchedKind = fixture("artifact-envelope.json");
  const mismatchedPayload = mismatchedKind.payload;
  assert(
    mismatchedPayload !== null &&
      !Array.isArray(mismatchedPayload) &&
      typeof mismatchedPayload === "object",
  );
  mismatchedPayload.legacy_kind = "LegacyMechanism";
  bindEnvelopeDigest(mismatchedKind);
  assertContractCode(
    () => registry.validateRecord(mismatchedKind),
    "ENVELOPE_PAYLOAD_INVALID",
  );

  const invalidSource = fixture("artifact-envelope.json");
  const invalidPayload = invalidSource.payload;
  assert(
    invalidPayload !== null &&
      !Array.isArray(invalidPayload) &&
      typeof invalidPayload === "object",
  );
  const sourceRecord = invalidPayload.source_record;
  assert(sourceRecord !== null && !Array.isArray(sourceRecord) && typeof sourceRecord === "object");
  delete sourceRecord.claim_text;
  const sourceDigest = canonicalDigest(sourceRecord);
  invalidPayload.source_digest = sourceDigest;
  invalidSource.input_digests = [sourceDigest];
  bindEnvelopeDigest(invalidSource);
  assertContractCode(() => registry.validateRecord(invalidSource), "SCHEMA_VALIDATION");

  const candidate = fixture("candidate-artifact.json");
  const native: Record<string, JsonValue> = {
    aliases: [candidate.id as JsonValue],
    artifact_kind: "CandidateArtifact",
    artifact_schema_version: "1.0.0",
    classification: "private_operational",
    created_at: "2026-08-10T12:00:00Z",
    id: "rec_018f3e40-7b80-7a21-8000-000000000001",
    id_origin: "native",
    input_digests: [canonicalDigest(candidate)],
    integrity: {
      algorithm: "sha256",
      canonicalization_profile: "jcs-rfc8785-integer-v1",
      digest: `sha256:${"0".repeat(64)}`,
    },
    kind: "ArtifactEnvelope",
    payload: candidate,
    producer_actor_id: "platform_steward",
    retention: "durable",
    schema_version: "1.0.0",
  };
  bindEnvelopeDigest(native);
  assert.equal(registry.validateRecord(native).kind, "ArtifactEnvelope");

  native.artifact_kind = "ArtifactEnvelope";
  bindEnvelopeDigest(native);
  assertContractCode(() => registry.validateRecord(native), "ENVELOPE_TARGET_INVALID");
});

test("organization events bind payload, routing, provenance, authority, and causation", () => {
  const registry = loadRuntimeRegistry(repositoryRoot);
  const valid = fixture("organization-event.json");
  assert.equal(registry.validateRecord(valid).kind, "OrganizationEvent");

  const tampered = structuredClone(valid);
  const tamperedPayload = tampered.payload as Record<string, JsonValue>;
  tamperedPayload.reason = "different";
  assertContractCode(
    () => registry.validateRecord(tampered),
    "EVENT_PAYLOAD_DIGEST_MISMATCH",
  );

  const mismatched = structuredClone(valid);
  const mismatchedSubject = mismatched.subject as Record<string, JsonValue>;
  mismatchedSubject.id = "20260810-120000-different-run";
  assertContractCode(() => registry.validateRecord(mismatched), "EVENT_PAYLOAD_MISMATCH");

  const invalidTransition = structuredClone(valid);
  const invalidPayload = invalidTransition.payload as Record<string, JsonValue>;
  invalidPayload.from_state = "retrieved";
  invalidTransition.payload_digest = canonicalDigest(invalidPayload);
  assertContractCode(
    () => registry.validateRecord(invalidTransition),
    "RUN_EVENT_TRANSITION_INVALID",
  );

  const overlapping = structuredClone(valid);
  const overlappingPayload = overlapping.payload as Record<string, JsonValue>;
  const initialization = overlappingPayload.initialization as Record<string, JsonValue>;
  const lockedSurfaces = initialization.locked_surfaces as JsonValue[];
  const editableSurfaces = initialization.editable_surfaces as JsonValue[];
  editableSurfaces.push(lockedSurfaces[0] as JsonValue);
  overlapping.payload_digest = canonicalDigest(overlappingPayload);
  assertContractCode(
    () => registry.validateRecord(overlapping),
    "RUN_EVENT_TRANSITION_INVALID",
  );

  const nondeterministic = structuredClone(valid);
  const nondeterministicPayload = nondeterministic.payload as Record<string, JsonValue>;
  nondeterministicPayload.transition_source = "file_state_history";
  nondeterministic.payload_digest = canonicalDigest(nondeterministicPayload);
  assertContractCode(
    () => registry.validateRecord(nondeterministic),
    "RUN_EVENT_ORIGIN_MISMATCH",
  );

  const imported = structuredClone(valid);
  const importedPayload = imported.payload as Record<string, JsonValue>;
  const importedRunId = String(importedPayload.run_id);
  assert.equal(
    deterministicRunEventId(importedRunId, 0),
    "evt_abd043a6-b030-521d-bb61-1bbc791062c4",
  );
  assert.equal(
    deterministicRunEventId(importedRunId, 1),
    "evt_d5470156-e488-5501-a212-0245f8368d7b",
  );
  assert.equal(
    deterministicRunEventIdempotencyDigest(importedRunId, 0),
    "sha256:fb097c8c85a97fd9946728a20b842a890491aeff75a68cd4b9be2bb5806af62b",
  );
  assertContractCode(
    () => deterministicRunEventId(importedRunId, 2 ** 53),
    "INVALID_ID",
  );
  importedPayload.transition_source = "file_state_history";
  imported.id = deterministicRunEventId(importedRunId, 0);
  imported.id_origin = "legacy_import";
  imported.correlation_event_id = imported.id as JsonValue;
  imported.causation_event_id = null;
  imported.idempotency = {
    scope: "research_loop_file_shadow",
    key_digest: deterministicRunEventIdempotencyDigest(importedRunId, 0),
  };
  imported.actor = {
    id: "research-loop-file-shadow",
    class: "legacy_file_bridge",
  };
  imported.authority = {
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
  imported.repository = { commit_sha: null, pull_request: null };
  imported.payload_digest = canonicalDigest(importedPayload);
  assert.equal(registry.validateRecord(imported).kind, "OrganizationEvent");

  const importedMutations: Array<(event: Record<string, JsonValue>) => void> = [
    (event) => {
      event.id = deterministicRunEventId(importedRunId, 1);
    },
    (event) => {
      const idempotency = event.idempotency as Record<string, JsonValue>;
      idempotency.scope = "research_loop";
    },
    (event) => {
      const changedActor = event.actor as Record<string, JsonValue>;
      changedActor.id = "different-bridge";
    },
    (event) => {
      const changedAuthority = event.authority as Record<string, JsonValue>;
      changedAuthority.action = "research";
    },
  ];
  for (const mutate of importedMutations) {
    const changed = structuredClone(imported);
    mutate(changed);
    assertContractCode(
      () => registry.validateRecord(changed),
      "RUN_EVENT_ORIGIN_MISMATCH",
    );
  }

  const wrongActor = structuredClone(valid);
  const actor = wrongActor.actor as Record<string, JsonValue>;
  actor.class = "runtime_operator";
  assertContractCode(
    () => registry.validateRecord(wrongActor),
    "EVENT_AUTHORITY_MISMATCH",
  );

  const reservedScope = structuredClone(valid);
  const reservedIdempotency = reservedScope.idempotency as Record<string, JsonValue>;
  reservedIdempotency.scope = "research_loop_file_shadow";
  assertContractCode(
    () => registry.validateRecord(reservedScope),
    "RUN_EVENT_ORIGIN_MISMATCH",
  );

  const selfCaused = structuredClone(valid);
  selfCaused.causation_event_id = selfCaused.id as JsonValue;
  assertContractCode(
    () => registry.validateRecord(selfCaused),
    "EVENT_CAUSATION_INVALID",
  );
});

test("organization event detail references resolve target identity and classification", () => {
  const registry = loadRuntimeRegistry(repositoryRoot);
  const event = fixture("organization-event.json");
  const candidate = fixture("candidate-artifact.json");
  event.detail_ref = {
    artifact_id: candidate.id as JsonValue,
    artifact_id_origin: "native",
    artifact_kind: "CandidateArtifact",
    artifact_schema_version: "1.0.0",
    classification: "private_operational",
    digest: canonicalDigest(candidate),
  };
  assert.equal(registry.validateRecord(event).kind, "OrganizationEvent");

  const wrongPrefix = structuredClone(event);
  const wrongDetail = wrongPrefix.detail_ref as Record<string, JsonValue>;
  wrongDetail.artifact_id = fixture("capability-grant-spec.json").id as JsonValue;
  assertContractCode(() => registry.validateRecord(wrongPrefix), "PREFIX_KIND_MISMATCH");

  const unknown = structuredClone(event);
  const unknownDetail = unknown.detail_ref as Record<string, JsonValue>;
  unknownDetail.artifact_kind = "UnknownArtifact";
  assertContractCode(() => registry.validateRecord(unknown), "UNKNOWN_KIND");

  const classification = structuredClone(event);
  const classifiedDetail = classification.detail_ref as Record<string, JsonValue>;
  classifiedDetail.classification = "public";
  assertContractCode(
    () => registry.validateRecord(classification),
    "EVENT_DETAIL_REF_INVALID",
  );

  const storage = fixture("storage-binding.json");
  const disallowedTargetClassification = structuredClone(event);
  const publicPayload = disallowedTargetClassification.payload as Record<string, JsonValue>;
  disallowedTargetClassification.classification = "public";
  publicPayload.classification = "public";
  disallowedTargetClassification.payload_digest = canonicalDigest(publicPayload);
  disallowedTargetClassification.detail_ref = {
    artifact_id: storage.id as JsonValue,
    artifact_id_origin: "native",
    artifact_kind: "StorageBinding",
    artifact_schema_version: "1.0.0",
    classification: "public",
    digest: canonicalDigest(storage),
  };
  assertContractCode(
    () => registry.validateRecord(disallowedTargetClassification),
    "CLASSIFICATION_MISMATCH",
  );

  const selfTarget = structuredClone(event);
  selfTarget.detail_ref = {
    artifact_id: selfTarget.id as JsonValue,
    artifact_id_origin: selfTarget.id_origin as JsonValue,
    artifact_kind: "OrganizationEvent",
    artifact_schema_version: "1.0.0",
    classification: selfTarget.classification as JsonValue,
    digest: `sha256:${"0".repeat(64)}`,
  };
  assertContractCode(
    () => registry.validateRecord(selfTarget),
    "EVENT_DETAIL_REF_INVALID",
  );

  const impossibleLegacyTarget = structuredClone(event);
  const impossibleDetail = impossibleLegacyTarget.detail_ref as Record<string, JsonValue>;
  impossibleDetail.artifact_id_origin = "legacy_import";
  impossibleDetail.artifact_id = "cand_abd043a6-b030-521d-bb61-1bbc791062c4";
  assertContractCode(
    () => registry.validateRecord(impossibleLegacyTarget),
    "ARTIFACT_TARGET_INVALID",
  );
});

test("freeze paths reject portable ASCII case collisions", () => {
  const registry = loadRuntimeRegistry(repositoryRoot);
  const receipt = fixture("freeze-receipt.json");
  const original = receipt.entries;
  assert(Array.isArray(original) && original.length === 1);
  const first: Record<string, JsonValue> = {
    ...(original[0] as Record<string, JsonValue>),
    path: "A.txt",
  };
  const second: Record<string, JsonValue> = {
    ...(original[0] as Record<string, JsonValue>),
    path: "a.txt",
  };
  receipt.entries = [first, second];
  receipt.file_count = 2;
  receipt.total_size_bytes = Number(first.size_bytes) + Number(second.size_bytes);
  receipt.tree_digest = canonicalDigest(receipt.entries);
  assertContractCode(() => registry.validateRecord(receipt), "TREE_MANIFEST_INVALID");
});

test("date-time formats reject impossible calendar instants", () => {
  const registry = loadRuntimeRegistry(repositoryRoot);
  const artifactRef = fixture("artifact-ref.json");
  artifactRef.created_at = "2024-02-29T00:00:00Z";
  assert.doesNotThrow(() => registry.validateRecord(artifactRef));
  artifactRef.created_at = "2026-02-30T00:00:00Z";
  assertContractCode(() => registry.validateRecord(artifactRef), "SCHEMA_VALIDATION");
});

test("read and write resolution enforce inactive-version policy", () => {
  const deprecated = loadModifiedRegistry((document) => {
    entry(document, "ArtifactRef").status = "deprecated";
  });
  assert.equal(deprecated.resolveForRead("ArtifactRef", "1.0.0").status, "deprecated");
  assertContractCode(
    () => deprecated.resolveForWrite("ArtifactRef", "1.0.0"),
    "SCHEMA_INACTIVE",
  );
  assert.equal(deprecated.validateRecord(fixture("artifact-ref.json")).kind, "ArtifactRef");

  const retired = loadModifiedRegistry((document) => {
    entry(document, "ArtifactRef").status = "retired";
  });
  assertContractCode(
    () => retired.resolveForRead("ArtifactRef", "1.0.0"),
    "SCHEMA_INACTIVE",
  );
  assertContractCode(
    () => retired.resolveForWrite("ArtifactRef", "1.0.0"),
    "SCHEMA_INACTIVE",
  );
  assertContractCode(
    () => retired.validateRecord(fixture("artifact-ref.json")),
    "SCHEMA_INACTIVE",
  );
});

test("runtime validation applies classification and semantic checks after Ajv", () => {
  const narrowed = loadModifiedRegistry((document) => {
    entry(document, "ArtifactRef").classifications = ["private_operational"];
  });
  const artifactRef = fixture("artifact-ref.json");
  artifactRef.classification = "public";
  assertContractCode(
    () => narrowed.validateRecord(artifactRef),
    "CLASSIFICATION_MISMATCH",
  );

  const envelope = fixture("artifact-envelope.json");
  const payload = envelope.payload;
  assert(payload !== null && !Array.isArray(payload) && typeof payload === "object");
  payload.claim_id = "tampered";
  assertContractCode(
    () => loadRuntimeRegistry(repositoryRoot).validateRecord(envelope),
    "INTEGRITY_MISMATCH",
  );
});

test("registry entries must remain sorted by kind and version", () => {
  assertContractCode(
    () =>
      loadModifiedRegistry((document) => {
        const first = document.entries[0] as MutableRegistryEntry;
        document.entries[0] = document.entries[1] as MutableRegistryEntry;
        document.entries[1] = first;
      }),
    "REGISTRY_INVALID",
  );
});

test("a kind cannot register multiple active writer versions", () => {
  assertContractCode(
    () =>
      loadModifiedRegistry((document) => {
        const original = entry(document, "ArtifactEnvelope");
        const second = structuredClone(original);
        second.version = "1.1.0";
        delete second.id_prefix;
        document.entries.splice(1, 0, second);
      }),
    "REGISTRY_INVALID",
  );
});
