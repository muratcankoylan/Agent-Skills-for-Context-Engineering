import type {
  ControlCenterSnapshot,
  HealthTone,
  MutationCapability,
} from "./domain.ts";

export interface MetricViewModel {
  readonly label: string;
  readonly value: string;
  readonly detail: string;
  readonly tone: HealthTone;
}

export interface OverviewViewModel {
  readonly operationalState: "preproduction_blocked" | "degraded";
  readonly stateLabel: string;
  readonly summary: string;
  readonly metrics: readonly MetricViewModel[];
  readonly blockers: readonly {
    readonly id: string;
    readonly title: string;
    readonly reason: string;
  }[];
  readonly mutationCapability: MutationCapability;
}

function deploymentCapability(snapshot: ControlCenterSnapshot): MutationCapability {
  const capability = snapshot.capabilities.find(
    (candidate) => candidate.action === "activate_deployment",
  );

  if (capability === undefined) {
    throw new Error("Missing activate_deployment capability declaration");
  }

  return capability;
}

export function buildOverviewViewModel(
  snapshot: ControlCenterSnapshot,
): OverviewViewModel {
  const stale = snapshot.identity.freshness.state !== "current";
  const activeRuns = snapshot.runs.filter((run) => run.state !== "closed").length;
  const blockedRuns = snapshot.runs.filter(
    (run) => run.state === "blocked_dependency",
  ).length;
  const waitingReviews = snapshot.reviewQueue.filter(
    (item) => item.state !== "ready_for_decision",
  ).length;
  const verifiedArtifacts = snapshot.artifacts.filter(
    (artifact) => artifact.integrity === "verified",
  ).length;

  const blockers = [
    ...(snapshot.deploymentPointer.state === "dependency_inactive"
      ? [
          {
            id: "deployment-contract",
            title: "Deployment owner contract inactive",
            reason: `${snapshot.deploymentPointer.owner} revision ${snapshot.deploymentPointer.requiredRevision} is not accepted.`,
          },
        ]
      : []),
    ...snapshot.runs.flatMap((run) =>
      run.blocker === undefined
        ? []
        : [
            {
              id: `${run.id}-${run.blocker.reasonCode}`,
              title: run.objective,
              reason: run.blocker.detail,
            },
          ],
    ),
  ];

  return {
    operationalState: stale ? "degraded" : "preproduction_blocked",
    stateLabel: stale ? "Degraded fixture" : "Pre-production · blocked",
    summary: stale
      ? "The fixture projection is stale. It remains inspectable but cannot support an operational decision."
      : "Repository evidence is inspectable, but runtime and deployment authority remain intentionally inactive.",
    metrics: [
      {
        label: "Open runs",
        value: String(activeRuns),
        detail: `${blockedRuns} dependency-blocked`,
        tone: blockedRuns > 0 ? "warning" : "good",
      },
      {
        label: "Review queue",
        value: String(snapshot.reviewQueue.length),
        detail: `${waitingReviews} awaiting checks or human review`,
        tone: waitingReviews > 0 ? "warning" : "good",
      },
      {
        label: "Verified artifacts",
        value: String(verifiedArtifacts),
        detail: `${snapshot.artifacts.length} total fixture records`,
        tone: verifiedArtifacts === snapshot.artifacts.length ? "good" : "neutral",
      },
      {
        label: "Deployment",
        value: "Inactive",
        detail: "No active deployment pointer",
        tone: "neutral",
      },
    ],
    blockers,
    mutationCapability: deploymentCapability(snapshot),
  };
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) {
    return "Unknown";
  }

  if (bytes < 1_024) {
    return `${bytes} B`;
  }

  if (bytes < 1_048_576) {
    return `${(bytes / 1_024).toFixed(1)} KiB`;
  }

  return `${(bytes / 1_048_576).toFixed(1)} MiB`;
}

export function shortDigest(digest: string): string {
  const [algorithm, value] = digest.split(":", 2);
  if (algorithm === undefined || value === undefined || value.length < 12) {
    return digest;
  }

  return `${algorithm}:${value.slice(0, 12)}…`;
}

export function humanizeIdentifier(value: string): string {
  return value.replaceAll("_", " ");
}
