import type { Metadata } from "next";
import {
  EmptyState,
  FixtureStatePicker,
  FreshnessNotice,
  MutationBlock,
  PageHeader,
  PermissionState,
  SnapshotStrip,
  StatePill,
  formatUtc,
} from "../../components/ui.tsx";
import {
  getMutationCapability,
  parseFixtureMode,
  readControlCenterFixture,
} from "../../lib/fixture-adapter.ts";
import type { RunState } from "../../lib/domain.ts";

export const metadata: Metadata = {
  title: "Runs",
};

interface PageProps {
  readonly searchParams: Promise<{
    readonly state?: string | readonly string[];
  }>;
}

function runTone(state: RunState) {
  if (state === "blocked_dependency") return "warning" as const;
  if (state === "closed") return "good" as const;
  return "neutral" as const;
}

export default async function RunsPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const result = readControlCenterFixture(parseFixtureMode(params.state));

  if (result.kind === "permission_denied") {
    return <PermissionState detail={result.detail} />;
  }

  const snapshot = result.data;
  const pauseCapability = getMutationCapability(snapshot, "pause_run");

  return (
    <>
      <PageHeader
        eyebrow="Research execution"
        title="Runs and their stopping reasons."
        description="Every nonterminal fixture run exposes its stage, evidence count, and blocker. There is no implied worker, lease, or live process behind these records."
        actions={<FixtureStatePicker route="/runs" />}
      />
      <FreshnessNotice freshness={snapshot.identity.freshness} />
      <SnapshotStrip snapshot={snapshot} />

      {snapshot.runs.length === 0 ? (
        <EmptyState
          title="No research runs"
          description="No run summaries are present in this deterministic preview. Empty does not mean the live organization has no work."
        />
      ) : (
        <div className="table-surface surface">
          <table className="data-table">
            <caption>
              Fixture-backed research runs. Updated values are fixed UTC observations.
            </caption>
            <thead>
              <tr>
                <th scope="col">Run</th>
                <th scope="col">State</th>
                <th scope="col">Stage</th>
                <th scope="col">Progress</th>
                <th scope="col">Evidence</th>
                <th scope="col">Updated</th>
              </tr>
            </thead>
            <tbody>
              {snapshot.runs.map((run) => (
                <tr key={run.id}>
                  <td>
                    <span className="table-primary">{run.objective}</span>
                    <span className="table-secondary mono">{run.id}</span>
                    <span className="table-secondary">Owner: {run.owner}</span>
                    {run.blocker === undefined ? null : (
                      <span className="table-secondary">
                        {run.blocker.reasonCode}: {run.blocker.detail}
                      </span>
                    )}
                  </td>
                  <td>
                    <StatePill label={run.state} tone={runTone(run.state)} />
                  </td>
                  <td>{run.currentStage}</td>
                  <td>
                    <div className="progress" aria-label={`${run.completionPercent}% complete`}>
                      <progress max={100} value={run.completionPercent}>
                        {run.completionPercent}%
                      </progress>
                      <span>{run.completionPercent}% fixture estimate</span>
                    </div>
                  </td>
                  <td>{run.evidenceCount}</td>
                  <td className="mono">{formatUtc(run.updatedAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <MutationBlock capability={pauseCapability} buttonLabel="Pause selected run" />
    </>
  );
}
