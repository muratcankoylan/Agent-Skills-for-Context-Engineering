/** Crash-safe, manifest-bound state for the pre-activation router runner. */

import { randomBytes } from "node:crypto";
import { join, resolve } from "node:path";

import {
  assertSha256Digest,
  canonicalFileBytes,
  canonicalJsonBytes,
  domainSeparatedDigest,
  parseCanonicalFile,
  sha256Bytes,
  type JsonValue,
  type Sha256Digest,
} from "./durableJson.ts";
import {
  DurableFsError,
  NodeDurableFileSystem,
  type DurableFileSystem,
} from "./durableFs.ts";
import {
  parseRouterRunManifestFile,
  type BuiltRouterRunManifest,
  type RouterPlanItem,
} from "./routerManifest.ts";

export const ROUTER_CLAIM_SCHEMA = "router-inflight-claim/v1" as const;
export const ROUTER_OUTCOME_SCHEMA = "router-attempt-outcome/v1" as const;
export const ROUTER_TERMINAL_SCHEMA = "router-terminal-record/v1" as const;

const STORE_NAMESPACE = "router-run-manifest-v1";
const CLAIMS_DIR = "attempt-claims";
const OUTCOMES_DIR = "attempt-outcomes";
const TERMINALS_DIR = "results";
const MANIFEST_FILE = "manifest.json";
const PLAN_FILE = "plan.json";
const LOCK_FILE = "run.lock";
const MAX_ADMIN_BYTES = 64 * 1024 * 1024;
const MAX_RECORD_BYTES = 16 * 1024 * 1024;
const MAX_RAW_TEXT_BYTES = 8 * 1024 * 1024;
const MAX_MESSAGE_BYTES = 64 * 1024;
const MAX_TOKEN_BYTES = 4 * 1024;
const DIGEST_FILE = /^[0-9a-f]{64}\.json$/;
const UTC_SECOND = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z$/;
const OWNER_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const LOCK_GENERATION = /^[0-9a-f]{64}$/;

export type RouterRunStoreErrorCode =
  | "BUDGET_EXHAUSTED"
  | "DUPLICATE_STATE"
  | "FOREIGN_STATE"
  | "INITIALIZATION_INCOMPLETE"
  | "INVALID_RECORD"
  | "RECONCILIATION_REQUIRED"
  | "RESULT_CONFLICT"
  | "RUN_LOCKED"
  | "RUN_NOT_INITIALIZED"
  | "UNEXPECTED_STATE_ENTRY";

export class RouterRunStoreError extends Error {
  readonly code: RouterRunStoreErrorCode;

  constructor(code: RouterRunStoreErrorCode, message: string, options?: ErrorOptions) {
    super(`[${code}] ${message}`, options);
    this.name = "RouterRunStoreError";
    this.code = code;
  }
}

export interface RouterRunLease {
  readonly manifest_digest: Sha256Digest;
  readonly owner_id: string;
  readonly acquired_at: string;
  readonly lock_generation: string;
  readonly run_directory: string;
  readonly lock_body: Uint8Array;
}

export interface RouterInflightClaim {
  readonly schema: typeof ROUTER_CLAIM_SCHEMA;
  readonly manifest_digest: Sha256Digest;
  readonly item_id: Sha256Digest;
  readonly attempt: number;
  readonly owner_id: string;
  readonly lock_generation: string;
  readonly claimed_at: string;
  readonly estimated_cost_microusd: number;
}

export interface RouterUsage {
  readonly input_tokens: number;
  readonly output_tokens: number;
  readonly cache_read_tokens: number;
  readonly cache_write_tokens: number;
  readonly total_tokens: number;
  readonly reasoning_tokens: number;
}

export type RouterAttemptStatus =
  | "finished"
  | "format_failure"
  | "provider_error"
  | "cancelled"
  | "model_unavailable";

export interface RouterAttemptSettlement {
  readonly status: RouterAttemptStatus;
  readonly finished_at: string;
  readonly duration_ms: number;
  readonly request_id?: string;
  readonly resolved_model_id?: string;
  readonly raw_text?: string;
  readonly ranking?: readonly string[];
  readonly confidence_millionths?: number;
  readonly rationale?: string;
  readonly error_code?: string;
  readonly error_message?: string;
  readonly usage?: RouterUsage;
}

export interface RouterAttemptOutcome {
  readonly schema: typeof ROUTER_OUTCOME_SCHEMA;
  readonly manifest_digest: Sha256Digest;
  readonly item_id: Sha256Digest;
  readonly attempt: number;
  readonly claim_digest: Sha256Digest;
  readonly status: RouterAttemptStatus;
  readonly finished_at: string;
  readonly duration_ms: number;
  readonly request_id: string | null;
  readonly resolved_model_id: string | null;
  readonly raw_text: string | null;
  readonly ranking: readonly string[];
  readonly confidence_millionths: number | null;
  readonly rationale: string | null;
  readonly error_code: string | null;
  readonly error_message: string | null;
  readonly usage: RouterUsage | null;
}

export type RouterTerminalStatus =
  | "finished"
  | "format_failure"
  | "provider_error"
  | "cancelled"
  | "model_unavailable";

export interface RouterTerminalRecord {
  readonly schema: typeof ROUTER_TERMINAL_SCHEMA;
  readonly manifest_digest: Sha256Digest;
  readonly item_id: Sha256Digest;
  readonly prompt_id: string;
  readonly model_id: string;
  readonly rep: number;
  readonly shuffle_seed: number;
  readonly outcome_digests: readonly Sha256Digest[];
  readonly status: RouterTerminalStatus;
  readonly completed_at: string;
  readonly total_duration_ms: number;
  readonly ranking: readonly string[];
  readonly confidence_millionths: number | null;
  readonly rationale: string | null;
}

export interface RouterPendingItem {
  readonly item: RouterPlanItem;
  readonly next_attempt: number;
}

export interface RouterResumeState {
  readonly pending: readonly RouterPendingItem[];
  readonly terminal_pending: readonly RouterPlanItem[];
  readonly completed_item_ids: readonly Sha256Digest[];
  readonly claimed_invocations: number;
  readonly claimed_cost_microusd: number;
}

interface ScannedAttempt {
  readonly claim: RouterInflightClaim;
  readonly claimBytes: Buffer;
  readonly outcome?: RouterAttemptOutcome;
  readonly outcomeBytes?: Buffer;
}

interface ScannedState extends RouterResumeState {
  readonly attemptsByItem: ReadonlyMap<Sha256Digest, readonly ScannedAttempt[]>;
  readonly latestFinishedAt: string | null;
}

interface LeaseAuthority {
  readonly manifestDigest: Sha256Digest;
  readonly ownerId: string;
  readonly acquiredAt: string;
  readonly lockGeneration: string;
  readonly runDirectory: string;
  readonly lockBody: Buffer;
}

/**
 * Cooperative same-UID state store. A process with the same UID can still
 * tamper between syscalls; every detected ambiguity therefore blocks calls.
 */
export class RouterRunStore {
  readonly resultsRoot: string;
  readonly namespaceRoot: string;
  readonly runDirectory: string;
  readonly fileSystem: DurableFileSystem;

  readonly #authorityManifest: BuiltRouterRunManifest;
  readonly #authorityPlanBytes: Buffer;
  private readonly itemsById: ReadonlyMap<Sha256Digest, RouterPlanItem>;
  private readonly leaseAuthorities = new WeakMap<object, LeaseAuthority>();
  private readonly activeClaims = new WeakMap<object, RouterRunLease>();

  constructor(
    resultsRoot: string,
    manifest: BuiltRouterRunManifest,
    fileSystem?: DurableFileSystem,
  ) {
    const reparsed = parseRouterRunManifestFile(manifest.canonicalBytes);
    if (reparsed.digest !== manifest.digest) {
      throw new RouterRunStoreError("FOREIGN_STATE", "manifest bytes and digest disagree");
    }
    this.#authorityManifest = Object.freeze({
      manifest: reparsed.manifest,
      canonicalBytes: Buffer.from(reparsed.canonicalBytes),
      digest: reparsed.digest,
    });
    this.resultsRoot = resolve(resultsRoot);
    this.namespaceRoot = join(this.resultsRoot, STORE_NAMESPACE);
    this.runDirectory = join(this.namespaceRoot, digestHex(reparsed.digest));
    this.#authorityPlanBytes = canonicalFileBytes(reparsed.manifest.plan as unknown as JsonValue);
    if (
      this.#authorityManifest.canonicalBytes.byteLength > MAX_ADMIN_BYTES ||
      this.#authorityPlanBytes.byteLength > MAX_ADMIN_BYTES
    ) {
      throw new RouterRunStoreError("INVALID_RECORD", "manifest or plan exceeds the durable admin limit");
    }
    this.fileSystem = fileSystem ?? new NodeDurableFileSystem(this.resultsRoot);
    this.itemsById = new Map(
      reparsed.manifest.plan.items.map((item) => [item.item_id, item]),
    );
    Object.freeze(this);
  }

  /** Defensive snapshot; mutating it cannot change store authority. */
  get manifest(): BuiltRouterRunManifest {
    return parseRouterRunManifestFile(this.#authorityManifest.canonicalBytes);
  }

  /** Defensive plan bytes; mutating them cannot change store authority. */
  get planBytes(): Buffer {
    return Buffer.from(this.#authorityPlanBytes);
  }

  async acquire(ownerId: string, acquiredAt: string): Promise<RouterRunLease> {
    requireOwner(ownerId);
    requireTimestamp(acquiredAt, "acquired_at");
    await this.fileSystem.ensurePrivateDirectory(this.runDirectory);
    const lockGeneration = randomBytes(32).toString("hex");
    requireLockGeneration(lockGeneration);
    const lock = {
      acquired_at: acquiredAt,
      lock_generation: lockGeneration,
      manifest_digest: this.#authorityManifest.digest,
      owner_id: ownerId,
      schema: "router-run-lock/v1",
    } satisfies JsonValue;
    const lockBody = canonicalFileBytes(lock);
    try {
      await this.fileSystem.writeExclusiveDurable(join(this.runDirectory, LOCK_FILE), lockBody);
    } catch (error) {
      if (error instanceof DurableFsError && error.code === "EXCLUSIVE_TARGET_EXISTS") {
        throw new RouterRunStoreError("RUN_LOCKED", "router run already has an active or stale lock", {
          cause: error,
        });
      }
      throw error;
    }
    const lease: RouterRunLease = Object.freeze({
      manifest_digest: this.#authorityManifest.digest,
      owner_id: ownerId,
      acquired_at: acquiredAt,
      lock_generation: lockGeneration,
      run_directory: this.runDirectory,
      lock_body: Buffer.from(lockBody),
    });
    this.leaseAuthorities.set(lease, {
      manifestDigest: this.#authorityManifest.digest,
      ownerId,
      acquiredAt,
      lockGeneration,
      runDirectory: this.runDirectory,
      lockBody: Buffer.from(lockBody),
    });
    return lease;
  }

  async release(lease: RouterRunLease): Promise<void> {
    const authority = this.requireLease(lease);
    await this.fileSystem.removeExactDurable(join(this.runDirectory, LOCK_FILE), authority.lockBody);
    this.leaseAuthorities.delete(lease);
  }

  async initialize(lease: RouterRunLease): Promise<void> {
    this.requireLease(lease);
    await this.assertLeaseFile(lease);
    await this.assertRootEntries(true);
    for (const name of [CLAIMS_DIR, OUTCOMES_DIR, TERMINALS_DIR]) {
      await this.fileSystem.ensurePrivateDirectory(join(this.runDirectory, name));
    }
    await this.ensureExactFile(MANIFEST_FILE, this.#authorityManifest.canonicalBytes);
    await this.ensureExactFile(PLAN_FILE, this.#authorityPlanBytes);
    await this.assertRootEntries(false);
  }

  async preflight(lease: RouterRunLease): Promise<RouterResumeState> {
    const state = await this.scan(lease);
    return publicState(state);
  }

  async claim(
    lease: RouterRunLease,
    itemId: Sha256Digest,
    claimedAt: string,
  ): Promise<RouterInflightClaim> {
    assertSha256Digest(itemId, "item_id");
    requireTimestamp(claimedAt, "claimed_at");
    const state = await this.scan(lease);
    const pending = state.pending[0];
    if (!pending || pending.item.item_id !== itemId) {
      throw new RouterRunStoreError(
        "RESULT_CONFLICT",
        "only the next canonical plan item is eligible for another attempt",
      );
    }
    const unit = this.#authorityManifest.manifest.cost.estimated_micro_usd_per_sdk_attempt;
    if (
      state.claimed_invocations + 1 > this.#authorityManifest.manifest.cost.max_sdk_invocations ||
      state.claimed_cost_microusd + unit > this.#authorityManifest.manifest.cost.cap_micro_usd
    ) {
      throw new RouterRunStoreError("BUDGET_EXHAUSTED", "attempt would exceed a manifest cost cap");
    }
    const authority = this.requireLease(lease);
    requireNotBefore(claimedAt, authority.acquiredAt, "claim precedes the active lease");
    if (state.latestFinishedAt !== null) {
      requireNotBefore(
        claimedAt,
        state.latestFinishedAt,
        "claim precedes the latest settled plan outcome",
      );
    }
    const priorOutcome = state.attemptsByItem.get(itemId)?.at(-1)?.outcome;
    if (priorOutcome) {
      requireNotBefore(claimedAt, priorOutcome.finished_at, "claim precedes the prior outcome");
    }
    const claim: RouterInflightClaim = {
      schema: ROUTER_CLAIM_SCHEMA,
      manifest_digest: this.#authorityManifest.digest,
      item_id: itemId,
      attempt: pending.next_attempt,
      owner_id: authority.ownerId,
      lock_generation: authority.lockGeneration,
      claimed_at: claimedAt,
      estimated_cost_microusd: unit,
    };
    const body = canonicalFileBytes(claim as unknown as JsonValue);
    await this.writeExclusive(
      join(this.runDirectory, CLAIMS_DIR, attemptFileName(this.#authorityManifest.digest, itemId, claim.attempt)),
      body,
    );
    this.activeClaims.set(claim, lease);
    return claim;
  }

  async settle(
    lease: RouterRunLease,
    claim: RouterInflightClaim,
    settlement: RouterAttemptSettlement,
  ): Promise<RouterAttemptOutcome> {
    this.requireLease(lease);
    if (this.activeClaims.get(claim) !== lease) {
      throw new RouterRunStoreError(
        "RECONCILIATION_REQUIRED",
        "ordinary settlement requires the exact claim minted by this active lease",
      );
    }
    // Consume in-process settlement authority before any operation that can
    // fail ambiguously. This revision leaves any unmatched claim permanently
    // blocked rather than inferring whether a prior write or effect landed.
    this.activeClaims.delete(claim);
    const state = await this.scan(lease, attemptKey(claim.item_id, claim.attempt));
    const attempts = state.attemptsByItem.get(claim.item_id) ?? [];
    const stored = attempts.find((entry) => entry.claim.attempt === claim.attempt);
    if (!stored || canonicalFileBytes(claim as unknown as JsonValue).compare(stored.claimBytes) !== 0) {
      throw new RouterRunStoreError("FOREIGN_STATE", "settlement claim does not match durable state");
    }
    if (stored.outcome) {
      throw new RouterRunStoreError("RESULT_CONFLICT", "attempt is already settled");
    }
    requireNotBefore(
      settlement.finished_at,
      stored.claim.claimed_at,
      "outcome precedes its claim",
    );
    const outcome = buildOutcome(
      claim,
      sha256Bytes(stored.claimBytes),
      settlement,
      this.#authorityManifest,
    );
    const body = canonicalFileBytes(outcome as unknown as JsonValue);
    await this.writeExclusive(
      join(
        this.runDirectory,
        OUTCOMES_DIR,
        attemptFileName(this.#authorityManifest.digest, claim.item_id, claim.attempt),
      ),
      body,
    );
    return outcome;
  }

  async writeTerminal(
    lease: RouterRunLease,
    itemId: Sha256Digest,
    completedAt?: string,
  ): Promise<RouterTerminalRecord> {
    const state = await this.scan(lease);
    const item = state.terminal_pending.find((candidate) => candidate.item_id === itemId);
    if (!item) {
      throw new RouterRunStoreError("RESULT_CONFLICT", "item has no settled terminal outcome to record");
    }
    const attempts = state.attemptsByItem.get(itemId) ?? [];
    const outcomes = attempts.map((attempt) => attempt.outcome as RouterAttemptOutcome);
    const last = outcomes[outcomes.length - 1] as RouterAttemptOutcome;
    const completion = completedAt ?? last.finished_at;
    requireTimestamp(completion, "completed_at");
    if (completion !== last.finished_at) {
      throw new RouterRunStoreError("INVALID_RECORD", "terminal time must equal the final outcome time");
    }
    const totalDuration = safeSum(outcomes.map((outcome) => outcome.duration_ms), "total duration");
    const record: RouterTerminalRecord = {
      schema: ROUTER_TERMINAL_SCHEMA,
      manifest_digest: this.#authorityManifest.digest,
      item_id: item.item_id,
      prompt_id: item.prompt_id,
      model_id: item.model_id,
      rep: item.rep,
      shuffle_seed: item.shuffle_seed,
      outcome_digests: attempts.map((attempt) => sha256Bytes(attempt.outcomeBytes as Buffer)),
      status: last.status,
      completed_at: completion,
      total_duration_ms: totalDuration,
      ranking: last.status === "finished" ? [...last.ranking] : [],
      confidence_millionths: last.status === "finished" ? last.confidence_millionths : null,
      rationale: last.status === "finished" ? last.rationale : null,
    };
    await this.writeExclusive(
      join(this.runDirectory, TERMINALS_DIR, terminalFileName(this.#authorityManifest.digest, itemId)),
      canonicalFileBytes(record as unknown as JsonValue),
    );
    return record;
  }

  private async scan(lease: RouterRunLease, allowedUnsettled?: string): Promise<ScannedState> {
    this.requireLease(lease);
    await this.assertLeaseFile(lease);
    await this.assertRootEntries(false);
    await this.assertExactFile(MANIFEST_FILE, this.#authorityManifest.canonicalBytes, MAX_ADMIN_BYTES);
    await this.assertExactFile(PLAN_FILE, this.#authorityPlanBytes, MAX_ADMIN_BYTES);

    const claims = await this.readClaims();
    const outcomes = await this.readOutcomes();
    const terminals = await this.readTerminals();
    const attemptsByItem = new Map<Sha256Digest, ScannedAttempt[]>();
    let claimedCost = 0n;

    for (const [key, entry] of claims) {
      const outcome = outcomes.get(key);
      if (outcome && outcome.record.claim_digest !== sha256Bytes(entry.bytes)) {
        throw new RouterRunStoreError("FOREIGN_STATE", "attempt outcome binds the wrong claim bytes");
      }
      const itemAttempts = attemptsByItem.get(entry.record.item_id) ?? [];
      itemAttempts.push({
        claim: entry.record,
        claimBytes: entry.bytes,
        ...(outcome ? { outcome: outcome.record, outcomeBytes: outcome.bytes } : {}),
      });
      attemptsByItem.set(entry.record.item_id, itemAttempts);
      claimedCost += BigInt(entry.record.estimated_cost_microusd);
    }
    for (const key of outcomes.keys()) {
      if (!claims.has(key)) {
        throw new RouterRunStoreError("FOREIGN_STATE", "attempt outcome has no matching claim");
      }
    }
    if (
      claims.size > this.#authorityManifest.manifest.cost.max_sdk_invocations ||
      claimedCost > BigInt(this.#authorityManifest.manifest.cost.cap_micro_usd)
    ) {
      throw new RouterRunStoreError("BUDGET_EXHAUSTED", "durable claims exceed manifest caps");
    }

    const pending: RouterPendingItem[] = [];
    const terminalPending: RouterPlanItem[] = [];
    const completed: Sha256Digest[] = [];
    const unresolved: string[] = [];
    let latestFinishedAt: string | null = null;

    for (const item of this.#authorityManifest.manifest.plan.items) {
      const attempts = attemptsByItem.get(item.item_id) ?? [];
      attempts.sort((left, right) => left.claim.attempt - right.claim.attempt);
      for (let index = 0; index < attempts.length; index += 1) {
        const attempt = attempts[index] as ScannedAttempt;
        if (attempt.claim.attempt !== index + 1) {
          throw new RouterRunStoreError("FOREIGN_STATE", "attempt sequence contains a gap");
        }
        const prior = attempts[index - 1]?.outcome;
        if (index > 0 && (prior === undefined || prior.status !== "format_failure")) {
          throw new RouterRunStoreError(
            "FOREIGN_STATE",
            "only a settled format failure can authorize the next attempt",
          );
        }
        if (prior) {
          requireNotBefore(
            attempt.claim.claimed_at,
            prior.finished_at,
            "claim precedes the prior outcome",
          );
        }
        if (latestFinishedAt !== null) {
          requireNotBefore(
            attempt.claim.claimed_at,
            latestFinishedAt,
            "claim precedes the latest settled plan outcome",
          );
        }
        if (attempt.outcome) {
          requireNotBefore(
            attempt.outcome.finished_at,
            attempt.claim.claimed_at,
            "outcome precedes its claim",
          );
          latestFinishedAt = attempt.outcome.finished_at;
        } else {
          unresolved.push(attemptKey(item.item_id, index + 1));
        }
      }
      if (attempts.length > this.#authorityManifest.manifest.plan.max_format_attempts) {
        throw new RouterRunStoreError("FOREIGN_STATE", "attempt sequence exceeds manifest maximum");
      }
      const last = attempts.at(-1)?.outcome;
      const terminal = last ? isTerminal(last, this.#authorityManifest.manifest.plan.max_format_attempts) : false;
      const existingTerminal = terminals.get(item.item_id);
      if (terminal) {
        if (existingTerminal) {
          validateTerminalAgainstState(existingTerminal.record, item, attempts, this.#authorityManifest.digest);
          completed.push(item.item_id);
        } else {
          terminalPending.push(item);
        }
      } else {
        if (existingTerminal) {
          throw new RouterRunStoreError("RESULT_CONFLICT", "terminal record exists for nonterminal item");
        }
        if (attempts.length === 0 || last?.status === "format_failure") {
          pending.push({ item, next_attempt: attempts.length + 1 });
        }
      }
    }
    for (const itemId of terminals.keys()) {
      if (!this.itemsById.has(itemId)) {
        throw new RouterRunStoreError("FOREIGN_STATE", "terminal record names a foreign plan item");
      }
    }
    const foreignUnresolved = unresolved.filter((key) => key !== allowedUnsettled);
    if (foreignUnresolved.length > 0) {
      throw new RouterRunStoreError(
        "RECONCILIATION_REQUIRED",
        "one or more attempt claims have no durable outcome",
      );
    }
    return {
      pending,
      terminal_pending: terminalPending,
      completed_item_ids: completed,
      claimed_invocations: claims.size,
      claimed_cost_microusd: Number(claimedCost),
      attemptsByItem,
      latestFinishedAt,
    };
  }

  private async readClaims(): Promise<Map<string, { record: RouterInflightClaim; bytes: Buffer }>> {
    const result = new Map<string, { record: RouterInflightClaim; bytes: Buffer }>();
    for (const { name, bytes, value } of await this.readRecordDirectory(CLAIMS_DIR)) {
      const record = validateClaim(value, this.#authorityManifest);
      const expected = attemptFileName(this.#authorityManifest.digest, record.item_id, record.attempt);
      if (name !== expected) wrongFilename(name);
      const key = attemptKey(record.item_id, record.attempt);
      if (result.has(key)) duplicateState();
      result.set(key, { record, bytes });
    }
    return result;
  }

  private async readOutcomes(): Promise<Map<string, { record: RouterAttemptOutcome; bytes: Buffer }>> {
    const result = new Map<string, { record: RouterAttemptOutcome; bytes: Buffer }>();
    for (const { name, bytes, value } of await this.readRecordDirectory(OUTCOMES_DIR)) {
      const record = validateOutcome(value, this.#authorityManifest);
      const expected = attemptFileName(this.#authorityManifest.digest, record.item_id, record.attempt);
      if (name !== expected) wrongFilename(name);
      const key = attemptKey(record.item_id, record.attempt);
      if (result.has(key)) duplicateState();
      result.set(key, { record, bytes });
    }
    return result;
  }

  private async readTerminals(): Promise<Map<Sha256Digest, { record: RouterTerminalRecord; bytes: Buffer }>> {
    const result = new Map<Sha256Digest, { record: RouterTerminalRecord; bytes: Buffer }>();
    for (const { name, bytes, value } of await this.readRecordDirectory(TERMINALS_DIR)) {
      const record = validateTerminal(value, this.#authorityManifest);
      const expected = terminalFileName(this.#authorityManifest.digest, record.item_id);
      if (name !== expected) wrongFilename(name);
      if (result.has(record.item_id)) duplicateState();
      result.set(record.item_id, { record, bytes });
    }
    return result;
  }

  private async readRecordDirectory(
    name: string,
  ): Promise<Array<{ name: string; bytes: Buffer; value: JsonValue }>> {
    const directory = join(this.runDirectory, name);
    const records: Array<{ name: string; bytes: Buffer; value: JsonValue }> = [];
    for (const entry of await this.fileSystem.listDirectory(directory)) {
      if (entry.kind !== "file" || !DIGEST_FILE.test(entry.name)) {
        throw new RouterRunStoreError(
          "UNEXPECTED_STATE_ENTRY",
          `unexpected ${name} entry ${entry.name}`,
        );
      }
      const bytes = Buffer.from(
        await this.fileSystem.readRegularNoFollow(join(directory, entry.name), MAX_RECORD_BYTES),
      );
      let value: JsonValue;
      try {
        value = parseCanonicalFile(bytes);
      } catch (error) {
        throw new RouterRunStoreError("INVALID_RECORD", `invalid canonical record ${entry.name}`, {
          cause: error,
        });
      }
      records.push({ name: entry.name, bytes, value });
    }
    return records;
  }

  private async assertRootEntries(allowMissing: boolean): Promise<void> {
    const expected = new Map<string, "file" | "directory">([
      [LOCK_FILE, "file"],
      [MANIFEST_FILE, "file"],
      [PLAN_FILE, "file"],
      [CLAIMS_DIR, "directory"],
      [OUTCOMES_DIR, "directory"],
      [TERMINALS_DIR, "directory"],
    ]);
    const seen = new Set<string>();
    for (const entry of await this.fileSystem.listDirectory(this.runDirectory)) {
      const kind = expected.get(entry.name);
      if (!kind || kind !== entry.kind) {
        throw new RouterRunStoreError(
          "UNEXPECTED_STATE_ENTRY",
          `unexpected run-state entry ${entry.name}`,
        );
      }
      seen.add(entry.name);
    }
    if (!allowMissing) {
      for (const name of expected.keys()) {
        if (!seen.has(name)) {
          throw new RouterRunStoreError("INITIALIZATION_INCOMPLETE", `missing run-state entry ${name}`);
        }
      }
    }
  }

  private async ensureExactFile(name: string, expected: Uint8Array): Promise<void> {
    const path = join(this.runDirectory, name);
    const info = await this.fileSystem.statPath(path);
    if (info === null) {
      await this.writeExclusive(path, expected, MAX_ADMIN_BYTES);
      return;
    }
    await this.assertExactFile(name, expected, MAX_ADMIN_BYTES);
  }

  private async assertExactFile(name: string, expected: Uint8Array, maximum: number): Promise<void> {
    const actual = Buffer.from(
      await this.fileSystem.readRegularNoFollow(join(this.runDirectory, name), maximum),
    );
    if (!actual.equals(Buffer.from(expected))) {
      throw new RouterRunStoreError("FOREIGN_STATE", `${name} does not match the selected manifest`);
    }
  }

  private async assertLeaseFile(lease: RouterRunLease): Promise<void> {
    const authority = this.requireLease(lease);
    await this.assertExactFile(LOCK_FILE, authority.lockBody, MAX_RECORD_BYTES);
  }

  private async writeExclusive(
    path: string,
    body: Uint8Array,
    maximum = MAX_RECORD_BYTES,
  ): Promise<void> {
    if (body.byteLength > maximum) {
      throw new RouterRunStoreError(
        "INVALID_RECORD",
        `durable record exceeds the ${maximum}-byte limit`,
      );
    }
    try {
      await this.fileSystem.writeExclusiveDurable(path, body);
    } catch (error) {
      if (error instanceof DurableFsError && error.code === "EXCLUSIVE_TARGET_EXISTS") {
        throw new RouterRunStoreError("RESULT_CONFLICT", "durable record already exists", {
          cause: error,
        });
      }
      throw error;
    }
  }

  private requireLease(lease: RouterRunLease): LeaseAuthority {
    const authority = this.leaseAuthorities.get(lease);
    let bodyMatches = false;
    try {
      bodyMatches = authority !== undefined &&
        Buffer.from(lease.lock_body).equals(authority.lockBody);
    } catch {
      bodyMatches = false;
    }
    if (
      authority === undefined ||
      lease.manifest_digest !== authority.manifestDigest ||
      lease.owner_id !== authority.ownerId ||
      lease.acquired_at !== authority.acquiredAt ||
      lease.lock_generation !== authority.lockGeneration ||
      lease.run_directory !== authority.runDirectory ||
      authority.manifestDigest !== this.#authorityManifest.digest ||
      authority.runDirectory !== this.runDirectory ||
      !LOCK_GENERATION.test(authority.lockGeneration) ||
      !bodyMatches
    ) {
      throw new RouterRunStoreError("RUN_LOCKED", "operation requires this store's active run lease");
    }
    return authority;
  }
}

function validateClaim(value: JsonValue, manifest: BuiltRouterRunManifest): RouterInflightClaim {
  const record = closed(value, [
    "schema", "manifest_digest", "item_id", "attempt", "owner_id", "lock_generation", "claimed_at",
    "estimated_cost_microusd",
  ]);
  literal(record.schema, ROUTER_CLAIM_SCHEMA);
  binding(record, manifest);
  const attempt = positiveInteger(record.attempt, "attempt");
  if (attempt > manifest.manifest.plan.max_format_attempts) invalid("attempt exceeds manifest maximum");
  const owner = nonempty(record.owner_id, "owner_id");
  requireOwner(owner);
  const lockGeneration = nonempty(record.lock_generation, "lock_generation");
  requireLockGeneration(lockGeneration);
  const claimedAt = nonempty(record.claimed_at, "claimed_at");
  requireTimestamp(claimedAt, "claimed_at");
  const cost = positiveInteger(record.estimated_cost_microusd, "estimated_cost_microusd");
  if (cost !== manifest.manifest.cost.estimated_micro_usd_per_sdk_attempt) {
    invalid("claim cost differs from manifest unit forecast");
  }
  return {
    schema: ROUTER_CLAIM_SCHEMA,
    manifest_digest: record.manifest_digest as Sha256Digest,
    item_id: record.item_id as Sha256Digest,
    attempt,
    owner_id: owner,
    lock_generation: lockGeneration,
    claimed_at: claimedAt,
    estimated_cost_microusd: cost,
  };
}

function validateOutcome(value: JsonValue, manifest: BuiltRouterRunManifest): RouterAttemptOutcome {
  const record = closed(value, [
    "schema", "manifest_digest", "item_id", "attempt", "claim_digest", "status",
    "finished_at", "duration_ms", "request_id", "resolved_model_id", "raw_text", "ranking",
    "confidence_millionths", "rationale", "error_code", "error_message", "usage",
  ]);
  literal(record.schema, ROUTER_OUTCOME_SCHEMA);
  binding(record, manifest);
  assertSha256Digest(record.claim_digest, "claim_digest");
  const status = outcomeStatus(record.status);
  const attempt = positiveInteger(record.attempt, "attempt");
  if (attempt > manifest.manifest.plan.max_format_attempts) invalid("attempt exceeds manifest maximum");
  const finishedAt = nonempty(record.finished_at, "finished_at");
  requireTimestamp(finishedAt, "finished_at");
  const duration = nonNegativeInteger(record.duration_ms, "duration_ms");
  const ranking = stringArray(record.ranking, "ranking");
  if (new Set(ranking).size !== ranking.length) invalid("ranking must contain unique values");
  assertKnownSkills(ranking, manifest);
  const confidence = nullableInteger(record.confidence_millionths, "confidence_millionths");
  if (confidence !== null && (confidence < 0 || confidence > 1_000_000)) invalid("confidence is out of range");
  const rationale = boundedNullableString(record.rationale, "rationale", MAX_MESSAGE_BYTES);
  const rawText = boundedNullableString(record.raw_text, "raw_text", MAX_RAW_TEXT_BYTES);
  const errorCode = boundedNullableString(record.error_code, "error_code", MAX_TOKEN_BYTES);
  const errorMessage = boundedNullableString(record.error_message, "error_message", MAX_MESSAGE_BYTES);
  if (status === "finished") {
    if (
      rawText === null || ranking.length === 0 || confidence === null ||
      rationale === null || errorCode !== null || errorMessage !== null
    ) {
      invalid("finished outcome requires raw prediction fields and forbids error fields");
    }
  } else {
    if (ranking.length !== 0 || confidence !== null || rationale !== null) {
      invalid("non-finished outcome cannot contain a parsed prediction");
    }
    if (status === "format_failure") {
      if (errorCode === null || errorMessage === null) {
        invalid("format failure requires an error code and message");
      }
    } else if (status === "provider_error" || status === "model_unavailable") {
      if (rawText !== null || errorCode === null || errorMessage === null) {
        invalid(`${status} requires error fields and forbids raw output`);
      }
    } else if (status === "cancelled" && rawText !== null) {
      invalid("cancelled outcome cannot contain raw output");
    }
  }
  return {
    schema: ROUTER_OUTCOME_SCHEMA,
    manifest_digest: record.manifest_digest as Sha256Digest,
    item_id: record.item_id as Sha256Digest,
    attempt,
    claim_digest: record.claim_digest,
    status,
    finished_at: finishedAt,
    duration_ms: duration,
    request_id: boundedNullableString(record.request_id, "request_id", MAX_TOKEN_BYTES),
    resolved_model_id: boundedNullableString(
      record.resolved_model_id,
      "resolved_model_id",
      MAX_TOKEN_BYTES,
    ),
    raw_text: rawText,
    ranking,
    confidence_millionths: confidence,
    rationale,
    error_code: errorCode,
    error_message: errorMessage,
    usage: validateUsage(record.usage),
  };
}

function validateTerminal(value: JsonValue, manifest: BuiltRouterRunManifest): RouterTerminalRecord {
  const record = closed(value, [
    "schema", "manifest_digest", "item_id", "prompt_id", "model_id", "rep", "shuffle_seed",
    "outcome_digests", "status", "completed_at", "total_duration_ms", "ranking",
    "confidence_millionths", "rationale",
  ]);
  literal(record.schema, ROUTER_TERMINAL_SCHEMA);
  binding(record, manifest);
  const digests = digestArray(record.outcome_digests, "outcome_digests");
  const status = outcomeStatus(record.status);
  const completedAt = nonempty(record.completed_at, "completed_at");
  requireTimestamp(completedAt, "completed_at");
  const ranking = stringArray(record.ranking, "ranking");
  assertKnownSkills(ranking, manifest);
  const confidence = nullableInteger(record.confidence_millionths, "confidence_millionths");
  const rationale = boundedNullableString(record.rationale, "rationale", MAX_MESSAGE_BYTES);
  return {
    schema: ROUTER_TERMINAL_SCHEMA,
    manifest_digest: record.manifest_digest as Sha256Digest,
    item_id: record.item_id as Sha256Digest,
    prompt_id: nonempty(record.prompt_id, "prompt_id"),
    model_id: nonempty(record.model_id, "model_id"),
    rep: nonNegativeInteger(record.rep, "rep"),
    shuffle_seed: nonNegativeInteger(record.shuffle_seed, "shuffle_seed"),
    outcome_digests: digests,
    status,
    completed_at: completedAt,
    total_duration_ms: nonNegativeInteger(record.total_duration_ms, "total_duration_ms"),
    ranking,
    confidence_millionths: confidence,
    rationale,
  };
}

function validateTerminalAgainstState(
  record: RouterTerminalRecord,
  item: RouterPlanItem,
  attempts: readonly ScannedAttempt[],
  manifestDigest: Sha256Digest,
): void {
  const outcomes = attempts.map((attempt) => attempt.outcome as RouterAttemptOutcome);
  const last = outcomes.at(-1) as RouterAttemptOutcome;
  const expectedDigests = attempts.map((attempt) => sha256Bytes(attempt.outcomeBytes as Buffer));
  if (
    record.manifest_digest !== manifestDigest || record.item_id !== item.item_id ||
    record.prompt_id !== item.prompt_id || record.model_id !== item.model_id ||
    record.rep !== item.rep || record.shuffle_seed !== item.shuffle_seed ||
    record.status !== last.status || record.completed_at !== last.finished_at ||
    record.total_duration_ms !== safeSum(outcomes.map((outcome) => outcome.duration_ms), "duration") ||
    record.outcome_digests.length !== expectedDigests.length ||
    record.outcome_digests.some((digest, index) => digest !== expectedDigests[index])
  ) {
    throw new RouterRunStoreError("RESULT_CONFLICT", "terminal record disagrees with attempt evidence");
  }
  const expectedRanking = last.status === "finished" ? last.ranking : [];
  if (
    record.ranking.length !== expectedRanking.length ||
    record.ranking.some((value, index) => value !== expectedRanking[index]) ||
    record.confidence_millionths !== (last.status === "finished" ? last.confidence_millionths : null) ||
    record.rationale !== (last.status === "finished" ? last.rationale : null)
  ) {
    throw new RouterRunStoreError("RESULT_CONFLICT", "terminal prediction disagrees with outcome evidence");
  }
}

function buildOutcome(
  claim: RouterInflightClaim,
  claimDigest: Sha256Digest,
  settlement: RouterAttemptSettlement,
  manifest: BuiltRouterRunManifest,
): RouterAttemptOutcome {
  requireTimestamp(settlement.finished_at, "finished_at");
  const duration = nonNegativeInteger(settlement.duration_ms, "duration_ms");
  const ranking = settlement.ranking ? [...settlement.ranking] : [];
  const outcome: RouterAttemptOutcome = {
    schema: ROUTER_OUTCOME_SCHEMA,
    manifest_digest: claim.manifest_digest,
    item_id: claim.item_id,
    attempt: claim.attempt,
    claim_digest: claimDigest,
    status: settlement.status,
    finished_at: settlement.finished_at,
    duration_ms: duration,
    request_id: settlement.request_id ?? null,
    resolved_model_id: settlement.resolved_model_id ?? null,
    raw_text: settlement.raw_text ?? null,
    ranking,
    confidence_millionths: settlement.confidence_millionths ?? null,
    rationale: settlement.rationale ?? null,
    error_code: settlement.error_code ?? null,
    error_message: settlement.error_message ?? null,
    usage: settlement.usage ?? null,
  };
  return validateOutcome(outcome as unknown as JsonValue, manifest);
}

function binding(record: Record<string, JsonValue>, manifest: BuiltRouterRunManifest): void {
  assertSha256Digest(record.manifest_digest, "manifest_digest");
  assertSha256Digest(record.item_id, "item_id");
  if (record.manifest_digest !== manifest.digest) invalid("record binds another manifest");
  if (!manifest.manifest.plan.items.some((item) => item.item_id === record.item_id)) {
    invalid("record binds a foreign plan item");
  }
}

function isTerminal(outcome: RouterAttemptOutcome, maximumAttempts: number): boolean {
  return outcome.status !== "format_failure" || outcome.attempt === maximumAttempts;
}

function attemptFileName(manifest: Sha256Digest, item: Sha256Digest, attempt: number): string {
  const payload = canonicalJsonBytes({ attempt, item_id: item, manifest_digest: manifest });
  return `${digestHex(domainSeparatedDigest("router-attempt-state-file/v1", payload))}.json`;
}

function terminalFileName(manifest: Sha256Digest, item: Sha256Digest): string {
  const payload = canonicalJsonBytes({ item_id: item, manifest_digest: manifest });
  return `${digestHex(domainSeparatedDigest("router-terminal-state-file/v1", payload))}.json`;
}

function attemptKey(item: Sha256Digest, attempt: number): string {
  return `${item}:${attempt}`;
}

function digestHex(value: Sha256Digest): string {
  assertSha256Digest(value);
  return value.slice("sha256:".length);
}

function closed(value: JsonValue, keys: readonly string[]): Record<string, JsonValue> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) invalid("record must be an object");
  const record = value as Record<string, JsonValue>;
  if (Object.keys(record).length !== keys.length || keys.some((key) => !Object.hasOwn(record, key))) {
    invalid("record fields do not match the closed schema");
  }
  for (const key of Object.keys(record)) if (!keys.includes(key)) invalid(`unknown record field ${key}`);
  return record;
}

function validateUsage(value: JsonValue): RouterUsage | null {
  if (value === null) return null;
  const record = closed(value, [
    "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "total_tokens",
    "reasoning_tokens",
  ]);
  return {
    input_tokens: nonNegativeInteger(record.input_tokens, "input_tokens"),
    output_tokens: nonNegativeInteger(record.output_tokens, "output_tokens"),
    cache_read_tokens: nonNegativeInteger(record.cache_read_tokens, "cache_read_tokens"),
    cache_write_tokens: nonNegativeInteger(record.cache_write_tokens, "cache_write_tokens"),
    total_tokens: nonNegativeInteger(record.total_tokens, "total_tokens"),
    reasoning_tokens: nonNegativeInteger(record.reasoning_tokens, "reasoning_tokens"),
  };
}

function digestArray(value: JsonValue, label: string): Sha256Digest[] {
  if (!Array.isArray(value)) invalid(`${label} must be an array`);
  return value.map((entry) => {
    assertSha256Digest(entry, label);
    return entry;
  });
}

function stringArray(value: JsonValue, label: string): string[] {
  if (!Array.isArray(value)) invalid(`${label} must be an array`);
  return value.map((entry) => nonempty(entry, label));
}

function assertKnownSkills(
  ranking: readonly string[],
  manifest: BuiltRouterRunManifest,
): void {
  const allowed = new Set(manifest.manifest.inputs.skill_catalog.skill_ids);
  if (ranking.some((skillId) => !allowed.has(skillId))) {
    invalid("ranking contains a skill outside the bound catalog");
  }
}

function outcomeStatus(value: JsonValue): RouterAttemptStatus {
  const allowed = new Set<RouterAttemptStatus>([
    "finished", "format_failure", "provider_error", "cancelled", "model_unavailable",
  ]);
  if (typeof value !== "string" || !allowed.has(value as RouterAttemptStatus)) invalid("unknown outcome status");
  return value as RouterAttemptStatus;
}

function literal(value: JsonValue, expected: string): void {
  if (value !== expected) invalid(`schema must equal ${expected}`);
}

function nonempty(value: JsonValue, label: string): string {
  if (typeof value !== "string" || value.length === 0) invalid(`${label} must be a non-empty string`);
  return value;
}

function nullableString(value: JsonValue, label: string): string | null {
  if (value === null) return null;
  return nonempty(value, label);
}

function boundedNullableString(value: JsonValue, label: string, maximumBytes: number): string | null {
  const result = nullableString(value, label);
  if (result !== null && Buffer.byteLength(result, "utf8") > maximumBytes) {
    invalid(`${label} exceeds ${maximumBytes} UTF-8 bytes`);
  }
  return result;
}

function nonNegativeInteger(value: JsonValue, label: string): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0 || Object.is(value, -0)) {
    invalid(`${label} must be a non-negative safe integer`);
  }
  return value;
}

function positiveInteger(value: JsonValue, label: string): number {
  const result = nonNegativeInteger(value, label);
  if (result === 0) invalid(`${label} must be positive`);
  return result;
}

function nullableInteger(value: JsonValue, label: string): number | null {
  return value === null ? null : nonNegativeInteger(value, label);
}

function requireOwner(value: string): void {
  if (!OWNER_ID.test(value)) invalid("owner_id must be a portable token");
}

function requireLockGeneration(value: string): void {
  if (!LOCK_GENERATION.test(value)) invalid("lock_generation must be 256 bits of lowercase hex");
}

function requireTimestamp(value: string, label: string): void {
  const match = UTC_SECOND.exec(value);
  if (!match) invalid(`${label} must be UTC second time`);
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const second = Number(match[6]);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (
    year < 1 ||
    month < 1 || month > 12 ||
    day < 1 || day > (days[month - 1] as number) ||
    hour > 23 || minute > 59 || second > 59
  ) {
    invalid(`${label} must be a real UTC calendar second`);
  }
}

function requireNotBefore(later: string, earlier: string, message: string): void {
  requireTimestamp(later, "later timestamp");
  requireTimestamp(earlier, "earlier timestamp");
  if (later < earlier) invalid(message);
}

function safeSum(values: readonly number[], label: string): number {
  const total = values.reduce((sum, value) => sum + BigInt(value), 0n);
  if (total > BigInt(Number.MAX_SAFE_INTEGER)) invalid(`${label} exceeds safe integer range`);
  return Number(total);
}

function publicState(state: ScannedState): RouterResumeState {
  return {
    pending: state.pending,
    terminal_pending: state.terminal_pending,
    completed_item_ids: state.completed_item_ids,
    claimed_invocations: state.claimed_invocations,
    claimed_cost_microusd: state.claimed_cost_microusd,
  };
}

function invalid(message: string): never {
  throw new RouterRunStoreError("INVALID_RECORD", message);
}

function wrongFilename(name: string): never {
  throw new RouterRunStoreError("FOREIGN_STATE", `record filename does not match its identity: ${name}`);
}

function duplicateState(): never {
  throw new RouterRunStoreError("DUPLICATE_STATE", "duplicate logical state record");
}
