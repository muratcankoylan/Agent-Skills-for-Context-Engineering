import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { isDeepStrictEqual } from "node:util";

import { canonicalize, sha256Bytes } from "./canonicalize.js";
import { ContractError } from "./errors.js";
import { parseJsonStrict, type JsonValue } from "./json.js";
import {
  repositoryRootFromModule,
  validateRegistryAndGoldens,
  type RegistryValidationResult,
} from "./registry.js";

interface ValidCanonicalizationCase {
  readonly canonical: string;
  readonly digest: string;
  readonly id: string;
  readonly result: "pass";
}

interface RejectedCanonicalizationCase {
  readonly id: string;
  readonly reason_code: string;
  readonly result: "reject";
}

export type CanonicalizationCaseResult =
  | ValidCanonicalizationCase
  | RejectedCanonicalizationCase;

export interface ConformanceResult extends RegistryValidationResult {
  readonly canonicalizationCases: readonly CanonicalizationCaseResult[];
  readonly suiteDigest: string;
}

/** Run the vectors and prove exact agreement with the generated Python report. */
export function runRepositoryConformance(
  repositoryRoot = repositoryRootFromModule(),
): ConformanceResult {
  const suitePath = resolve(
    repositoryRoot,
    "researcher/schemas/fixtures/canonicalization-v1.json",
  );
  const reportPath = resolve(
    repositoryRoot,
    "researcher/schemas/generated/conformance-report.json",
  );
  const suiteBody = readFileSync(suitePath);
  const suite = expectObject(parseJsonStrict(suiteBody.toString("utf8")), "suite is not an object");
  const caseValues = suite.cases;
  if (!Array.isArray(caseValues) || typeof suite.profile !== "string") {
    throw new ContractError("FIXTURE_INVALID", "canonicalization suite is invalid");
  }

  const canonicalizationCases = caseValues.map((value) => runCase(expectObject(value, "case")));
  const registry = validateRegistryAndGoldens(repositoryRoot);
  const suiteDigest = sha256Bytes(suiteBody);
  const report = expectObject(
    parseJsonStrict(readFileSync(reportPath, "utf8")),
    "conformance report is not an object",
  );

  if (!isDeepStrictEqual(canonicalizationCases, report.cases)) {
    throw new ContractError(
      "FIXTURE_MISMATCH",
      "TypeScript canonicalization cases differ from generated conformance report",
    );
  }
  if (
    report.canonicalization_profile !== suite.profile ||
    report.suite_digest !== suiteDigest ||
    report.registered_schema_count !== registry.registeredSchemaCount ||
    report.golden_record_count !== registry.goldenRecordCount ||
    report.schema_version !== registry.document.schema_version ||
    report.result !== "pass"
  ) {
    throw new ContractError(
      "FIXTURE_MISMATCH",
      "TypeScript conformance counts or metadata differ from generated report",
    );
  }

  return {
    ...registry,
    canonicalizationCases,
    suiteDigest,
  };
}

function runCase(record: Record<string, JsonValue>): CanonicalizationCaseResult {
  if (
    typeof record.id !== "string" ||
    typeof record.input_json !== "string" ||
    typeof record.valid !== "boolean"
  ) {
    throw new ContractError("FIXTURE_INVALID", "canonicalization case is invalid");
  }
  try {
    const canonical = canonicalize(parseJsonStrict(record.input_json));
    const digest = sha256Bytes(Buffer.from(canonical, "utf8"));
    if (!record.valid) {
      throw new ContractError("FIXTURE_MISMATCH", "invalid canonicalization vector passed");
    }
    if (canonical !== record.expected_canonical || digest !== record.expected_digest) {
      throw new ContractError("FIXTURE_MISMATCH", "canonical output differs from golden");
    }
    return { id: record.id, result: "pass", canonical, digest };
  } catch (error) {
    if (!(error instanceof ContractError)) {
      throw error;
    }
    if (record.valid || error.code !== record.expected_code) {
      throw error;
    }
    return { id: record.id, result: "reject", reason_code: error.code };
  }
}

function expectObject(value: JsonValue, context: string): Record<string, JsonValue> {
  if (value === null || Array.isArray(value) || typeof value !== "object") {
    throw new ContractError("FIXTURE_INVALID", `${context} is invalid`);
  }
  return value;
}
