export type ContractErrorCode =
  | "ARTIFACT_TARGET_INVALID"
  | "CANDIDATE_CYCLE"
  | "CANDIDATE_PARENT_MISMATCH"
  | "CAPABILITY_WINDOW"
  | "CLASSIFICATION_MISMATCH"
  | "DISCRIMINATOR_MISMATCH"
  | "DUPLICATE_KEY"
  | "DUPLICATE_SCHEMA"
  | "ENVELOPE_PAYLOAD_INVALID"
  | "ENVELOPE_TARGET_INVALID"
  | "EVENT_AUTHORITY_MISMATCH"
  | "EVENT_CAUSATION_INVALID"
  | "EVENT_DETAIL_REF_INVALID"
  | "EVENT_PAYLOAD_DIGEST_MISMATCH"
  | "EVENT_PAYLOAD_MISMATCH"
  | "EXPORT_DECISION_MISMATCH"
  | "FIXTURE_INVALID"
  | "FIXTURE_MISMATCH"
  | "GRANT_DIGEST_MISMATCH"
  | "INVALID_ID"
  | "INVALID_DIGEST"
  | "INVALID_JSON"
  | "INVALID_UNICODE"
  | "INTEGRITY_MISMATCH"
  | "MISSING_DISCRIMINATOR"
  | "PATH_ESCAPE"
  | "PREFIX_KIND_MISMATCH"
  | "PROFILE_MISMATCH"
  | "REGISTRY_INVALID"
  | "RUN_EVENT_ORIGIN_MISMATCH"
  | "RUN_EVENT_TRANSITION_INVALID"
  | "SCHEMA_DIGEST_MISMATCH"
  | "SCHEMA_ID_MISMATCH"
  | "SCHEMA_INVALID"
  | "SCHEMA_INACTIVE"
  | "SCHEMA_MISSING"
  | "SCHEMA_VALIDATION"
  | "TREE_DIGEST_MISMATCH"
  | "TREE_MANIFEST_INVALID"
  | "UNKNOWN_KIND"
  | "UNSUPPORTED_MAJOR"
  | "UNSAFE_NUMBER";

/** A stable, non-sensitive failure at the cross-language contract boundary. */
export class ContractError extends Error {
  readonly code: ContractErrorCode;
  readonly safeMessage: string;

  constructor(code: ContractErrorCode, safeMessage: string) {
    super(`[${code}] ${safeMessage}`);
    this.name = "ContractError";
    this.code = code;
    this.safeMessage = safeMessage;
  }
}
