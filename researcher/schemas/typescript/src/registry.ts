import { existsSync, readFileSync, realpathSync } from "node:fs";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { Ajv2020, type AnySchema, type ValidateFunction } from "ajv/dist/2020.js";

import {
  CANONICALIZATION_PROFILE,
  canonicalDigest,
  canonicalize,
  sha256Bytes,
} from "./canonicalize.js";
import { ContractError } from "./errors.js";
import { parseJsonStrict, type JsonValue } from "./json.js";
import { validateRecordSemantics } from "./semantics.js";

export interface RegistryEntry {
  readonly canonicalization_profile: string;
  readonly classifications: readonly string[];
  readonly compatibility: string;
  readonly golden_paths: readonly string[];
  readonly id_prefix?: string;
  readonly kind: string;
  readonly owner_spec: string;
  readonly schema_digest: string;
  readonly schema_id: string;
  readonly schema_path: string;
  readonly status: string;
  readonly version: string;
}

export interface RegistryDocument {
  readonly canonicalization_profile: string;
  readonly compatibility_policy: Readonly<Record<string, JsonValue>>;
  readonly entries: readonly RegistryEntry[];
  readonly id_prefixes: Readonly<Record<string, string>>;
  readonly schema_version: string;
}

export interface RegistryValidationResult {
  readonly document: RegistryDocument;
  readonly goldenRecordCount: number;
  readonly registeredSchemaCount: number;
}

export interface ValidateRecordOptions {
  readonly kind?: string;
  readonly version?: string;
}

const LEGACY_ADAPTER_KEY_FIELDS: Readonly<Record<string, string>> = {
  LegacyClaim: "claim_id",
  LegacyMechanism: "mechanism_id",
  LegacyQueueRecord: "id",
  LegacyRunState: "run_id",
};

/** A digest-pinned runtime registry whose Ajv validators are compiled exactly once. */
export class LoadedRuntimeRegistry {
  readonly document: RegistryDocument;
  readonly entries: readonly RegistryEntry[];

  private readonly byKey = new Map<string, RegistryEntry>();
  private readonly activeByKind = new Map<string, RegistryEntry>();

  private constructor(
    document: RegistryDocument,
    private readonly validatorsByKey: ReadonlyMap<string, ValidateFunction>,
  ) {
    this.document = document;
    this.entries = document.entries;
    for (const entry of this.entries) {
      this.byKey.set(entryKey(entry.kind, entry.version), entry);
      if (entry.status === "active") {
        this.activeByKind.set(entry.kind, entry);
      }
    }
  }

  static load(
    repositoryRoot = repositoryRootFromModule(),
    registryPath?: string,
  ): LoadedRuntimeRegistry {
    const compiled = compileRegistry(repositoryRoot, registryPath);
    const registry = new LoadedRuntimeRegistry(compiled.document, compiled.validatorsByKey);
    registry.validateRecord(compiled.document as unknown as Record<string, JsonValue>, {
      kind: "SchemaRegistry",
      version: "1.0.0",
    });
    return registry;
  }

  resolveForRead(kind: string, version: string): RegistryEntry {
    const entry = this.resolveExact(kind, version);
    if (entry.status !== "active" && entry.status !== "deprecated") {
      throw new ContractError("SCHEMA_INACTIVE", "record schema is not readable");
    }
    return entry;
  }

  resolveForWrite(kind: string, version: string): RegistryEntry {
    const entry = this.resolveExact(kind, version);
    if (entry.status !== "active" || this.activeByKind.get(kind) !== entry) {
      throw new ContractError("SCHEMA_INACTIVE", "record schema is not writable");
    }
    return entry;
  }

  validateRecord(
    record: Record<string, JsonValue>,
    options: ValidateRecordOptions = {},
  ): RegistryEntry {
    // Runtime callers can supply in-process objects. Prove the complete value
    // is in the canonical JSON domain before trusting discriminators or Ajv.
    canonicalize(record);
    const actualKind = options.kind ?? record.kind;
    const actualVersion = options.version ?? record.schema_version;
    if (typeof actualKind !== "string" || typeof actualVersion !== "string") {
      throw new ContractError(
        "MISSING_DISCRIMINATOR",
        "record lacks kind or schema_version",
      );
    }
    const entry = this.resolveForRead(actualKind, actualVersion);
    if (entry.compatibility !== "legacy-adapter") {
      if (record.schema_version !== actualVersion) {
        throw new ContractError(
          "DISCRIMINATOR_MISMATCH",
          "explicit schema version differs from the record",
        );
      }
      if (entry.kind !== "SchemaRegistry" && record.kind !== actualKind) {
        throw new ContractError(
          "DISCRIMINATOR_MISMATCH",
          "explicit schema kind differs from the record",
        );
      }
    }
    const validator = this.validatorsByKey.get(entryKey(entry.kind, entry.version));
    if (validator === undefined) {
      throw new ContractError("SCHEMA_INVALID", "compiled schema validator is unavailable");
    }
    validateWithAjv(validator, record, `record fails ${entry.kind}`);
    validateClassification(record, entry);
    validateRecordTypedId(record, entry);
    validateRecordSemantics(record, entry.kind);
    if (entry.kind === "ArtifactEnvelope") {
      this.validateArtifactEnvelope(record);
    } else if (entry.kind === "ArtifactRef") {
      const target = this.resolveForRead(
        String(record.artifact_kind),
        String(record.artifact_schema_version),
      );
      if (target.id_prefix === undefined) {
        throw new ContractError(
          "ARTIFACT_TARGET_INVALID",
          "artifact reference target has no typed identity",
        );
      }
      validateTypedId(
        String(record.artifact_id),
        target.id_prefix,
        record.artifact_id_origin === "legacy_import" ? "legacy_import" : "native",
      );
    }
    return entry;
  }

  private validateArtifactEnvelope(record: Record<string, JsonValue>): void {
    const target = this.resolveForRead(
      String(record.artifact_kind),
      String(record.artifact_schema_version),
    );
    if (target.kind === "ArtifactEnvelope") {
      throw new ContractError(
        "ENVELOPE_TARGET_INVALID",
        "artifact envelopes cannot recursively target themselves",
      );
    }
    const payloadValue = record.payload;
    if (
      payloadValue === null ||
      Array.isArray(payloadValue) ||
      typeof payloadValue !== "object"
    ) {
      throw new ContractError(
        "ENVELOPE_PAYLOAD_INVALID",
        "artifact envelope payload is invalid",
      );
    }
    const payload = payloadValue;
    if (record.id_origin !== "legacy_import") {
      if (target.compatibility === "legacy-adapter") {
        throw new ContractError(
          "ENVELOPE_TARGET_INVALID",
          "legacy adapter targets require a declared legacy import",
        );
      }
      this.validateRecord(payload, { kind: target.kind, version: target.version });
      return;
    }

    if (target.compatibility !== "legacy-adapter") {
      throw new ContractError(
        "ENVELOPE_TARGET_INVALID",
        "legacy imports must target a registered legacy adapter",
      );
    }
    const required = ["legacy_key", "legacy_kind", "source_digest", "source_record"];
    const allowed = new Set([...required, "source_path"]);
    const payloadKeys = Object.keys(payload);
    if (
      payloadKeys.some((key) => !allowed.has(key)) ||
      required.some((key) => !payloadKeys.includes(key))
    ) {
      throw new ContractError(
        "ENVELOPE_PAYLOAD_INVALID",
        "legacy import payload fields differ from the contract",
      );
    }
    const legacyKey = payload.legacy_key;
    const sourceRecordValue = payload.source_record;
    const sourcePath = payload.source_path;
    if (
      payload.legacy_kind !== target.kind ||
      typeof legacyKey !== "string" ||
      legacyKey.length === 0 ||
      sourceRecordValue === null ||
      Array.isArray(sourceRecordValue) ||
      typeof sourceRecordValue !== "object" ||
      (sourcePath !== undefined && (typeof sourcePath !== "string" || sourcePath.length === 0))
    ) {
      throw new ContractError(
        "ENVELOPE_PAYLOAD_INVALID",
        "legacy import payload metadata is inconsistent",
      );
    }
    if (target.kind === "LegacyQueueRecord" && sourcePath === undefined) {
      throw new ContractError(
        "ENVELOPE_PAYLOAD_INVALID",
        "legacy queue imports require source-path identity scope",
      );
    }
    const sourceRecord = sourceRecordValue;
    const keyField = LEGACY_ADAPTER_KEY_FIELDS[target.kind];
    if (keyField === undefined || sourceRecord[keyField] !== legacyKey) {
      throw new ContractError(
        "ENVELOPE_PAYLOAD_INVALID",
        "legacy import key disagrees with its source record",
      );
    }
    const sourceDigest = canonicalDigest(sourceRecord);
    if (payload.source_digest !== sourceDigest) {
      throw new ContractError(
        "ENVELOPE_PAYLOAD_INVALID",
        "legacy import source digest is invalid",
      );
    }
    if (
      !Array.isArray(record.input_digests) ||
      !record.input_digests.includes(sourceDigest) ||
      !Array.isArray(record.aliases) ||
      !record.aliases.includes(legacyKey)
    ) {
      throw new ContractError(
        "ENVELOPE_PAYLOAD_INVALID",
        "legacy import provenance does not bind its payload",
      );
    }
    this.validateRecord(sourceRecord, { kind: target.kind, version: target.version });
  }

  private resolveExact(kind: string, version: string): RegistryEntry {
    const entry = this.byKey.get(entryKey(kind, version));
    if (entry !== undefined) {
      return entry;
    }
    if (this.entries.some((candidate) => candidate.kind === kind)) {
      throw new ContractError(
        "UNSUPPORTED_MAJOR",
        "record schema version is not registered",
      );
    }
    throw new ContractError("UNKNOWN_KIND", "record kind is not registered");
  }
}

export function repositoryRootFromModule(): string {
  let candidate = dirname(fileURLToPath(import.meta.url));
  for (let depth = 0; depth < 8; depth += 1) {
    if (existsSync(resolve(candidate, "researcher/schemas/registry.json"))) {
      return candidate;
    }
    const parent = dirname(candidate);
    if (parent === candidate) {
      break;
    }
    candidate = parent;
  }
  throw new ContractError("SCHEMA_MISSING", "repository schema root could not be located");
}

/** Validate registry shape, raw schema digest pins, schema IDs, and every golden record. */
export function validateRegistryAndGoldens(
  repositoryRoot = repositoryRootFromModule(),
): RegistryValidationResult {
  const registry = loadRuntimeRegistry(repositoryRoot);
  const root = realpathSync(repositoryRoot);
  const schemaRoot = realpathSync(resolve(root, "researcher/schemas"));
  let goldenRecordCount = 0;
  for (const entry of registry.entries) {
    for (const goldenPathText of entry.golden_paths) {
      const goldenPath = resolveContainedFile(root, goldenPathText, [schemaRoot]);
      const record = expectObject(parseFile(goldenPath), "registered golden is not an object");
      registry.validateRecord(record, { kind: entry.kind, version: entry.version });
      goldenRecordCount += 1;
    }
  }

  return {
    document: registry.document,
    goldenRecordCount,
    registeredSchemaCount: registry.entries.length,
  };
}

export function loadRuntimeRegistry(
  repositoryRoot = repositoryRootFromModule(),
  registryPath?: string,
): LoadedRuntimeRegistry {
  return LoadedRuntimeRegistry.load(repositoryRoot, registryPath);
}

interface CompiledRegistry {
  readonly document: RegistryDocument;
  readonly validatorsByKey: ReadonlyMap<string, ValidateFunction>;
}

function compileRegistry(repositoryRoot: string, registryPathOverride?: string): CompiledRegistry {
  const root = realpathSync(repositoryRoot);
  const schemaRoot = realpathSync(resolve(root, "researcher/schemas"));
  const exportSchemaRoot = realpathSync(resolve(root, "researcher/exports/schemas"));
  const registryPath = registryPathOverride ?? resolve(schemaRoot, "registry.json");
  const registrySchemaPath = resolve(schemaRoot, "registry.schema.json");
  const registryValue = parseFile(registryPath);
  const registrySchemaValue = parseFile(registrySchemaPath);
  const registryObject = expectObject(registryValue, "schema registry must be an object");
  const registrySchema = expectSchema(registrySchemaValue);

  const ajv = createAjv();
  addSchema(ajv, registrySchema);
  const registryValidator = getValidator(ajv, schemaId(registrySchema));
  validateWithAjv(registryValidator, registryObject, "schema registry fails its schema");
  const document = registryObject as unknown as RegistryDocument;
  validateRegistrySemantics(document);

  const resourcesById = new Map<string, { readonly path: string; readonly digest: string }>();
  const validatorsById = new Map<string, ValidateFunction>();
  const entriesByKey = new Set<string>();

  for (const entry of document.entries) {
    const key = `${entry.kind}\u0000${entry.version}`;
    if (entriesByKey.has(key)) {
      throw new ContractError("DUPLICATE_SCHEMA", "schema kind/version is duplicated");
    }
    entriesByKey.add(key);
    if (entry.canonicalization_profile !== CANONICALIZATION_PROFILE) {
      throw new ContractError("PROFILE_MISMATCH", "schema entry uses an unsupported profile");
    }

    const schemaPath = resolveContainedFile(root, entry.schema_path, [schemaRoot, exportSchemaRoot]);
    const schemaBody = readFileSync(schemaPath);
    if (sha256Bytes(schemaBody) !== entry.schema_digest) {
      throw new ContractError("SCHEMA_DIGEST_MISMATCH", "registered schema digest is stale");
    }
    const schema = expectSchema(parseJsonStrict(schemaBody.toString("utf8")));
    if (schemaId(schema) !== entry.schema_id) {
      throw new ContractError("SCHEMA_ID_MISMATCH", "schema $id does not match registry");
    }

    const prior = resourcesById.get(entry.schema_id);
    if (prior !== undefined) {
      if (prior.path !== schemaPath || prior.digest !== entry.schema_digest) {
        throw new ContractError(
          "DUPLICATE_SCHEMA",
          "schema $id resolves to different resources",
        );
      }
    } else {
      resourcesById.set(entry.schema_id, { path: schemaPath, digest: entry.schema_digest });
      if (entry.schema_id !== schemaId(registrySchema)) {
        addSchema(ajv, schema);
      }
    }
  }

  for (const entry of document.entries) {
    if (!validatorsById.has(entry.schema_id)) {
      validatorsById.set(entry.schema_id, getValidator(ajv, entry.schema_id));
    }
  }

  const validatorsByKey = new Map<string, ValidateFunction>();
  for (const entry of document.entries) {
    validatorsByKey.set(
      entryKey(entry.kind, entry.version),
      validatorsById.get(entry.schema_id) as ValidateFunction,
    );
  }

  return { document, validatorsByKey };
}

function createAjv(): Ajv2020 {
  const ajv = new Ajv2020({
    allErrors: true,
    allowUnionTypes: true,
    strict: true,
    unicodeRegExp: true,
    validateFormats: true,
  });
  ajv.addFormat("date", {
    type: "string",
    validate: (value: string) => isDate(value),
  });
  ajv.addFormat("date-time", {
    type: "string",
    validate: (value: string) => isDateTime(value),
  });
  ajv.addFormat("uri", {
    type: "string",
    validate: (value: string) => isUri(value),
  });
  return ajv;
}

function addSchema(ajv: Ajv2020, schema: AnySchema): void {
  if (!ajv.validateSchema(schema)) {
    throw new ContractError("SCHEMA_INVALID", "registered schema fails meta-validation");
  }
  try {
    ajv.addSchema(schema);
  } catch {
    throw new ContractError("SCHEMA_INVALID", "registered schema cannot be compiled");
  }
}

function getValidator(ajv: Ajv2020, id: string): ValidateFunction {
  try {
    const validator = ajv.getSchema(id);
    if (validator !== undefined) {
      return validator;
    }
  } catch {
    // Collapse compiler details to the stable contract error below.
  }
  throw new ContractError("SCHEMA_INVALID", "registered schema cannot be compiled");
}

function validateWithAjv(
  validator: ValidateFunction,
  value: JsonValue,
  safeMessage: string,
): void {
  if (!validator(value)) {
    throw new ContractError("SCHEMA_VALIDATION", safeMessage);
  }
}

function validateRegistrySemantics(document: RegistryDocument): void {
  if (document.canonicalization_profile !== CANONICALIZATION_PROFILE) {
    throw new ContractError("PROFILE_MISMATCH", "unsupported canonicalization profile");
  }
  const entryKeys = document.entries.map((entry) => `${entry.kind}\u0000${entry.version}`);
  if (!sameStrings(entryKeys, [...entryKeys].sort())) {
    throw new ContractError(
      "REGISTRY_INVALID",
      "schema entries must be sorted by kind and version",
    );
  }
  const activeKinds = new Set<string>();
  for (const entry of document.entries) {
    if (entry.status === "active") {
      if (activeKinds.has(entry.kind)) {
        throw new ContractError(
          "REGISTRY_INVALID",
          "schema kind has more than one active writer version",
        );
      }
      activeKinds.add(entry.kind);
    }
  }
  const registeredPrefixes: Record<string, string> = {};
  for (const entry of document.entries) {
    if (entry.id_prefix !== undefined) {
      if (registeredPrefixes[entry.id_prefix] !== undefined) {
        throw new ContractError("REGISTRY_INVALID", "typed ID prefix is duplicated");
      }
      registeredPrefixes[entry.id_prefix] = entry.kind;
    }
  }
  if (!sameStringMap(registeredPrefixes, document.id_prefixes)) {
    throw new ContractError(
      "REGISTRY_INVALID",
      "typed ID prefixes disagree with schema entries",
    );
  }
}

function entryKey(kind: string, version: string): string {
  return `${kind}\u0000${version}`;
}

function validateClassification(
  record: Record<string, JsonValue>,
  entry: RegistryEntry,
): void {
  if (
    entry.classifications.length > 0 &&
    !entry.classifications.includes(String(record.classification))
  ) {
    throw new ContractError(
      "CLASSIFICATION_MISMATCH",
      "record classification is not permitted",
    );
  }
}

function validateRecordTypedId(record: Record<string, JsonValue>, entry: RegistryEntry): void {
  if (entry.id_prefix === undefined || typeof record.id !== "string") {
    return;
  }
  validateTypedId(
    record.id,
    entry.id_prefix,
    record.id_origin === "legacy_import" ? "legacy_import" : "native",
  );
}

/** Validate the prefix, RFC 4122 variant, and origin-specific UUID version of a typed ID. */
export function validateTypedId(
  value: string,
  expectedPrefix: string,
  idOrigin: "legacy_import" | "native" = "native",
): void {
  const match = /^([a-z][a-z0-9]*)_[0-9a-f]{8}-[0-9a-f]{4}-([0-9a-f])[0-9a-f]{3}-([89ab])[0-9a-f]{3}-[0-9a-f]{12}$/.exec(
    value,
  );
  if (match === null || match[1] !== expectedPrefix) {
    throw new ContractError(
      "PREFIX_KIND_MISMATCH",
      "identifier prefix does not match record kind",
    );
  }
  const expectedVersion = idOrigin === "legacy_import" ? "5" : "7";
  if (match[2] !== expectedVersion || match[3] === undefined) {
    throw new ContractError("INVALID_ID", `identifier must use UUIDv${expectedVersion}`);
  }
}

function parseFile(path: string): JsonValue {
  try {
    return parseJsonStrict(readFileSync(path, "utf8"));
  } catch (error) {
    if (error instanceof ContractError) {
      throw error;
    }
    throw new ContractError("SCHEMA_MISSING", "registered contract file could not be read");
  }
}

function resolveContainedFile(root: string, pathText: string, allowedRoots: readonly string[]): string {
  if (isAbsolute(pathText)) {
    throw new ContractError("PATH_ESCAPE", "registered path must be repository-relative");
  }
  let target: string;
  try {
    target = realpathSync(resolve(root, pathText));
  } catch {
    throw new ContractError("SCHEMA_MISSING", "registered contract file is missing");
  }
  if (!allowedRoots.some((allowedRoot) => isWithin(allowedRoot, target))) {
    throw new ContractError("PATH_ESCAPE", "registered path escapes its allowed roots");
  }
  return target;
}

function isWithin(root: string, target: string): boolean {
  const path = relative(root, target);
  return path === "" || (!path.startsWith("..") && !isAbsolute(path));
}

function expectObject(value: JsonValue, message: string): Record<string, JsonValue> {
  if (value === null || Array.isArray(value) || typeof value !== "object") {
    throw new ContractError("REGISTRY_INVALID", message);
  }
  return value;
}

function expectSchema(value: JsonValue): AnySchema {
  const object = expectObject(value, "registered schema is not an object");
  if (typeof object.$id !== "string") {
    throw new ContractError("SCHEMA_ID_MISMATCH", "registered schema has no string $id");
  }
  return object as AnySchema;
}

function schemaId(schema: AnySchema): string {
  const id = (schema as Record<string, unknown>).$id;
  if (typeof id !== "string") {
    throw new ContractError("SCHEMA_ID_MISMATCH", "registered schema has no string $id");
  }
  return id;
}

function sameStringMap(
  left: Readonly<Record<string, string>>,
  right: Readonly<Record<string, string>>,
): boolean {
  const leftKeys = Object.keys(left).sort();
  const rightKeys = Object.keys(right).sort();
  return (
    leftKeys.length === rightKeys.length &&
    leftKeys.every((key, index) => key === rightKeys[index] && left[key] === right[key])
  );
}

function sameStrings(left: readonly string[], right: readonly string[]): boolean {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

function isDate(value: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (match === null) {
    return false;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (year < 1 || month < 1 || month > 12 || day < 1) {
    return false;
  }
  const daysPerMonth = [31, isLeapYear(year) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return day <= (daysPerMonth[month - 1] as number);
}

function isDateTime(value: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|([+-])(\d{2}):(\d{2}))$/.exec(
    value,
  );
  if (match === null || !isDate(`${match[1]}-${match[2]}-${match[3]}`)) {
    return false;
  }
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const second = Number(match[6]);
  const offsetHour = match[8] === undefined ? 0 : Number(match[8]);
  const offsetMinute = match[9] === undefined ? 0 : Number(match[9]);
  return (
    hour <= 23 &&
    minute <= 59 &&
    second <= 59 &&
    offsetHour <= 23 &&
    offsetMinute <= 59 &&
    Number.isFinite(Date.parse(value))
  );
}

function isUri(value: string): boolean {
  try {
    const parsed = new URL(value);
    return parsed.protocol.length > 1;
  } catch {
    return false;
  }
}

function isLeapYear(year: number): boolean {
  return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
}
