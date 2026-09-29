export type IsoTimestamp = string;

export type FixtureMode =
  | "ready"
  | "empty"
  | "stale"
  | "error"
  | "permission";

export type Freshness =
  | {
      readonly state: "current";
      readonly observedAt: IsoTimestamp;
    }
  | {
      readonly state: "stale";
      readonly observedAt: IsoTimestamp;
      readonly reasonCode: "fixture_observation_expired";
      readonly detail: string;
    }
  | {
      readonly state: "unknown";
      readonly reasonCode: "fixture_has_no_observation";
      readonly detail: string;
    };

export type DependencySlot =
  | {
      readonly state: "dependency_inactive";
      readonly owner: string;
      readonly requiredRevision: number;
      readonly reasonCode: "owner_spec_not_accepted";
    }
  | {
      readonly state: "known";
      readonly value: string;
      readonly sourceEvent: string;
    }
  | {
      readonly state: "stale" | "unknown";
      readonly reasonCode: string;
    };

export type HealthTone = "good" | "warning" | "danger" | "neutral";

export interface SnapshotIdentity {
  readonly fixtureId: "control-center-fixture-v1";
  readonly authority: "fixture_non_authoritative";
  readonly sourceSequence: number;
  readonly eventChainDigest: string;
  readonly asOfObservationId: string;
  readonly asOf: IsoTimestamp;
  readonly freshness: Freshness;
}

export interface HealthSignal {
  readonly id: string;
  readonly label: string;
  readonly value: string;
  readonly tone: HealthTone;
  readonly detail: string;
}

export type RunState =
  | "evaluating"
  | "novelty_check"
  | "awaiting_review"
  | "blocked_dependency"
  | "closed";

export interface ResearchRun {
  readonly id: string;
  readonly objective: string;
  readonly state: RunState;
  readonly currentStage: string;
  readonly owner: string;
  readonly updatedAt: IsoTimestamp;
  readonly evidenceCount: number;
  readonly completionPercent: number;
  readonly blocker?: {
    readonly reasonCode: string;
    readonly detail: string;
  };
}

export type ReviewState =
  | "needs_human_review"
  | "checks_running"
  | "blocked_dependency"
  | "ready_for_decision";

export interface ReviewItem {
  readonly id: string;
  readonly kind: "pull_request" | "candidate" | "specification";
  readonly title: string;
  readonly state: ReviewState;
  readonly risk: "low" | "medium" | "high";
  readonly checks: {
    readonly passed: number;
    readonly total: number;
  };
  readonly submittedAt: IsoTimestamp;
  readonly decisionOwner: string;
  readonly blocker?: string;
}

export type ArtifactClassification =
  | "public"
  | "public_derived"
  | "private";

export interface ArtifactSummary {
  readonly id: string;
  readonly kind: string;
  readonly name: string;
  readonly classification: ArtifactClassification;
  readonly digest: string;
  readonly bytes: number;
  readonly createdAt: IsoTimestamp;
  readonly integrity: "verified" | "unverified" | "quarantined";
  readonly lineage: string;
}

export interface DeploymentTopologyNode {
  readonly id: string;
  readonly label: string;
  readonly detail: string;
  readonly boundary: "operator" | "supervisor" | "worker" | "storage";
}

export interface DeploymentStatus {
  readonly lifecycle: "dependency_inactive" | "canary" | "healthy" | "paused";
  readonly target: "supervised_local_control_remote_untrusted";
  readonly ownerSpec: "SPEC-025";
  readonly requiredRevision: 1;
  readonly activeCommit: DependencySlot;
  readonly processManager: "launchd";
  readonly supervisor: "orgd";
  readonly interactionMode: "read_only_fixture";
  readonly resultPath: string;
  readonly topology: readonly DeploymentTopologyNode[];
  readonly readiness: readonly DeploymentReadinessItem[];
}

export interface DeploymentReadinessItem {
  readonly id: string;
  readonly label: string;
  readonly state: "passed" | "blocked" | "not_run";
  readonly evidence: string;
}

export interface ProductReadinessMirror {
  readonly sourceDocument: "docs/product/production-readiness.json";
  readonly authoritative: false;
  readonly productionReady: false;
  readonly baselineCommit: string;
  readonly candidateState: "uncommitted_worktree";
  readonly candidateCommit: null;
  readonly notice: string;
}

export interface ControlCenterEvent {
  readonly sequence: number;
  readonly id: string;
  readonly occurredAt: IsoTimestamp;
  readonly kind: string;
  readonly subject: string;
  readonly summary: string;
  readonly severity: "info" | "warning" | "error";
}

export interface MutationCapability {
  readonly action:
    | "pause_run"
    | "resume_run"
    | "record_review_decision"
    | "activate_deployment";
  readonly enabled: false;
  readonly reasonCode: "dependency_inactive";
  readonly reason: string;
  readonly ownerSpecs: readonly string[];
}

export interface ControlCenterSnapshot {
  readonly identity: SnapshotIdentity;
  readonly health: readonly HealthSignal[];
  readonly repositoryAcceptance: DependencySlot;
  readonly organizationVersion: DependencySlot;
  readonly deploymentPointer: DependencySlot;
  readonly runs: readonly ResearchRun[];
  readonly reviewQueue: readonly ReviewItem[];
  readonly artifacts: readonly ArtifactSummary[];
  readonly deployment: DeploymentStatus;
  readonly readinessAssessment: ProductReadinessMirror;
  readonly events: readonly ControlCenterEvent[];
  readonly capabilities: readonly MutationCapability[];
}

export type AdapterResult<T> =
  | {
      readonly kind: "data";
      readonly data: T;
    }
  | {
      readonly kind: "permission_denied";
      readonly reasonCode: "fixture_profile_forbidden";
      readonly detail: string;
    };

export interface EventPage {
  readonly fixtureId: SnapshotIdentity["fixtureId"];
  readonly authority: SnapshotIdentity["authority"];
  readonly sourceSequence: number;
  readonly asOfObservationId: string;
  readonly asOf: IsoTimestamp;
  readonly freshness: Freshness;
  readonly events: readonly ControlCenterEvent[];
  readonly afterCursor: string;
  readonly nextCursor: string;
  readonly hasMore: boolean;
  readonly endOfFixture: boolean;
  readonly streamMode: "finite_fixture_page";
}

export interface ApiError {
  readonly error: {
    readonly code: string;
    readonly message: string;
  };
}
