import type { Metadata } from "next";
import { headers } from "next/headers";
import { EmptyState, PageHeader, StatePill, formatUtc } from "../../components/ui.tsx";
import { readObservationView } from "../../lib/observation-reader.server.ts";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const metadata: Metadata = { title: "Local observations" };

const unavailableTitles = {
  disabled: "Local observations are disabled.",
  missing: "No local observation summary is available.",
  invalid: "The local observation summary could not be validated.",
} as const;

export default async function ObservationsPage() {
  const requestHeaders = await headers();
  const result = await readObservationView({ requestHost: requestHeaders.get("host") });
  const data = result.data;

  return (
    <>
      <PageHeader
        eyebrow="Local observation pilot"
        title="Research observations and unfinished work."
        description="Actual local query summaries, separate from the fixture control pages. Captures and prepared context have not been reviewed by a researcher model or an independent evaluator."
        actions={<a className="text-link" href="/observations">Refresh observations</a>}
      />
      <section className="notice notice--warning" aria-labelledby="observation-boundary">
        <div className="notice__icon" aria-hidden="true">!</div>
        <div>
          <h2 id="observation-boundary">Research and independent review remain unfinished.</h2>
          <p>No model calls, accepted research claims, or production authority are represented here. This page cannot start agents, change runs, or activate deployment.</p>
        </div>
      </section>
      {data === null ? (
        <EmptyState
          title={unavailableTitles[result.state as keyof typeof unavailableTitles]}
          description={`${result.reason}. No fixture values or previous successful reads were substituted.`}
        />
      ) : (
        <>
          <section className={`notice notice--${result.state === "stale" ? "warning" : "neutral"}`} aria-labelledby="observation-freshness">
            <div>
              <h2 id="observation-freshness">{result.state === "stale" ? "Observation summary is stale." : "Local observation summary loaded."}</h2>
              <p>Generated {formatUtc(data.generated_at)}. Read {formatUtc(result.checked_at)}. Freshness window: two hours. Older runs retain their original observation times.</p>
              {result.state === "stale" ? <p>These values remain inspectable but do not describe the current state of the research process.</p> : null}
              <a className="text-link" href="/api/observations">Read the validated summary API</a>
            </div>
          </section>
          {data.runs.length === 0 ? (
            <EmptyState title="No observations recorded." description="The configured local summary contains no runs. This is not evidence that research has completed." />
          ) : (
            <section className="observation-list" aria-label="Local research observations">
              {data.runs.map((run) => (
                <article className="surface observation-card" key={run.run_id}>
                  <div className="observation-card__heading">
                    <h2>{run.query}</h2>
                    <StatePill label={run.status} tone="warning" />
                  </div>
                  <p className="table-secondary mono">Run {run.run_id}</p>
                  <p>Observed <time dateTime={run.observed_at}>{formatUtc(run.observed_at)}</time></p>
                  <dl className="observation-counts">
                    <div><dt>Source leads</dt><dd>{run.source_count}</dd></div>
                    <div><dt>Response captures</dt><dd>{run.capture_count}</dd></div>
                    <div><dt>Prepared context bytes</dt><dd>{run.context_bytes}</dd></div>
                    <div><dt>Model calls</dt><dd>{run.model_calls}</dd></div>
                  </dl>
                  <p className="observation-digest mono">Observation report digest: {run.report_digest}</p>
                  <h3>What remains</h3>
                  {run.blockers.length === 0 ? <p>Researcher execution and independent review have not occurred.</p> : (
                    <ul>{run.blockers.map((blocker, index) => <li key={`${run.run_id}-${index}`}>{blocker}</li>)}</ul>
                  )}
                </article>
              ))}
            </section>
          )}
        </>
      )}
    </>
  );
}
