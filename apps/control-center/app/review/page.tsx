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
import type { ReviewState } from "../../lib/domain.ts";
import {
  getMutationCapability,
  parseFixtureMode,
  readControlCenterFixture,
} from "../../lib/fixture-adapter.ts";

export const metadata: Metadata = {
  title: "Review queue",
};

interface PageProps {
  readonly searchParams: Promise<{
    readonly state?: string | readonly string[];
  }>;
}

function reviewTone(state: ReviewState) {
  if (state === "ready_for_decision") return "good" as const;
  if (state === "blocked_dependency") return "warning" as const;
  return "neutral" as const;
}

export default async function ReviewPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const result = readControlCenterFixture(parseFixtureMode(params.state));

  if (result.kind === "permission_denied") {
    return <PermissionState detail={result.detail} />;
  }

  const snapshot = result.data;
  const decisionCapability = getMutationCapability(
    snapshot,
    "record_review_decision",
  );

  return (
    <>
      <PageHeader
        eyebrow="Human decision boundary"
        title="Reviews do not approve themselves."
        description="Checks, risk, dependency blockers, and decision ownership are visible together. Fixture rows cannot approve, merge, promote, or publish anything."
        actions={<FixtureStatePicker route="/review" />}
      />
      <FreshnessNotice freshness={snapshot.identity.freshness} />
      <SnapshotStrip snapshot={snapshot} />

      {snapshot.reviewQueue.length === 0 ? (
        <EmptyState
          title="No review items"
          description="The selected fixture has an empty review projection. No statement about GitHub or candidate readiness is implied."
        />
      ) : (
        <div className="table-surface surface">
          <table className="data-table">
            <caption>
              Review items derived from a finite fixture, not from live GitHub state.
            </caption>
            <thead>
              <tr>
                <th scope="col">Subject</th>
                <th scope="col">State</th>
                <th scope="col">Risk</th>
                <th scope="col">Checks</th>
                <th scope="col">Decision owner</th>
                <th scope="col">Submitted</th>
              </tr>
            </thead>
            <tbody>
              {snapshot.reviewQueue.map((item) => (
                <tr key={item.id}>
                  <td>
                    <span className="table-primary">{item.title}</span>
                    <span className="table-secondary">
                      {item.kind} · <span className="mono">{item.id}</span>
                    </span>
                    {item.blocker === undefined ? null : (
                      <span className="table-secondary">Blocker: {item.blocker}</span>
                    )}
                  </td>
                  <td>
                    <StatePill label={item.state} tone={reviewTone(item.state)} />
                  </td>
                  <td>
                    <StatePill
                      label={`${item.risk} risk`}
                      tone={item.risk === "high" ? "danger" : item.risk === "medium" ? "warning" : "neutral"}
                    />
                  </td>
                  <td>
                    <strong>
                      {item.checks.passed}/{item.checks.total}
                    </strong>
                  </td>
                  <td>{item.decisionOwner}</td>
                  <td className="mono">{formatUtc(item.submittedAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <MutationBlock capability={decisionCapability} buttonLabel="Record review decision" />
    </>
  );
}
