import type { Metadata } from "next";
import {
  EmptyState,
  FixtureStatePicker,
  FreshnessNotice,
  MutationBlock,
  PageHeader,
  PermissionState,
  SectionHeading,
  SnapshotStrip,
  StatePill,
  formatUtc,
} from "../components/ui.tsx";
import {
  parseFixtureMode,
  readControlCenterFixture,
} from "../lib/fixture-adapter.ts";
import { buildOverviewViewModel } from "../lib/view-model.ts";

export const metadata: Metadata = {
  title: "Overview",
};

interface PageProps {
  readonly searchParams: Promise<{
    readonly state?: string | readonly string[];
  }>;
}

export default async function OverviewPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const result = readControlCenterFixture(parseFixtureMode(params.state));

  if (result.kind === "permission_denied") {
    return <PermissionState detail={result.detail} />;
  }

  const snapshot = result.data;
  const view = buildOverviewViewModel(snapshot);

  return (
    <>
      <PageHeader
        eyebrow="Operations snapshot"
        title="Understand the system before changing it."
        description="A discardable design experiment over deterministic, fabricated fixtures. It is interface evidence only, not an implementation of draft owner specifications or organizational truth."
        actions={<FixtureStatePicker route="/" />}
      />
      <FreshnessNotice freshness={snapshot.identity.freshness} />
      <SnapshotStrip snapshot={snapshot} />

      <div className="hero-grid">
        <section className="status-hero surface surface--accent" aria-labelledby="operational-state-title">
          <div className="status-hero__top">
            <p className="status-hero__state">{view.stateLabel}</p>
            <h2 id="operational-state-title">
              Evidence is visible. Authority is not active.
            </h2>
          </div>
          <p className="status-hero__bottom">{view.summary}</p>
        </section>

        <section className="health-stack surface surface--dark" aria-labelledby="health-signals-title">
          <h2 id="health-signals-title" className="sr-only">
            Health signals
          </h2>
          {snapshot.health.map((signal) => (
            <article className="health-signal" key={signal.id}>
              <div>
                <strong>{signal.label}</strong>
                <p>{signal.detail}</p>
              </div>
              <span>{signal.value}</span>
            </article>
          ))}
        </section>
      </div>

      <SectionHeading
        eyebrow="At a glance"
        title="Operational pressure"
        detail="Counts are derived from the selected fixture prefix and never refreshed from a provider."
      />
      <section className="metrics-grid" aria-label="Operational metrics">
        {view.metrics.map((metric) => (
          <article className={`metric-card metric-card--${metric.tone} surface`} key={metric.label}>
            <span>{metric.label}</span>
            <div>
              <strong>{metric.value}</strong>
              <p>{metric.detail}</p>
            </div>
          </article>
        ))}
      </section>

      <div className="two-column">
        <section aria-labelledby="activity-title">
          <SectionHeading id="activity-title" eyebrow="Journal view" title="Recent fixture events" />
          {snapshot.events.length === 0 ? (
            <EmptyState
              title="No events in this fixture"
              description="The empty preview has no durable-prefix events to display."
            />
          ) : (
            <div className="list-panel surface">
              <ol className="activity-list">
                {snapshot.events.slice(-5).reverse().map((event) => (
                  <li className="activity-item" key={event.id}>
                    <time dateTime={event.occurredAt}>{formatUtc(event.occurredAt).slice(11)}</time>
                    <div>
                      <strong>{event.summary}</strong>
                      <p>{event.subject}</p>
                    </div>
                    <StatePill
                      label={event.kind}
                      tone={event.severity === "warning" ? "warning" : "neutral"}
                    />
                  </li>
                ))}
              </ol>
            </div>
          )}
        </section>

        <section aria-labelledby="blockers-title">
          <SectionHeading id="blockers-title" eyebrow="Why not production" title="Active blockers" />
          <div className="blocker-panel surface">
            <p>
              Stable causal explanations from fixture-owned state.
            </p>
            <ul className="blocker-list">
              {view.blockers.map((blocker) => (
                <li className="blocker-item" key={blocker.id}>
                  <strong>{blocker.title}</strong>
                  <span>{blocker.reason}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>

      <MutationBlock capability={view.mutationCapability} buttonLabel="Activate deployment" />
    </>
  );
}
