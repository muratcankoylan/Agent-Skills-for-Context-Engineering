import type { Metadata } from "next";
import { headers } from "next/headers";
import { EmptyState, PageHeader, StatePill, formatUtc } from "../../components/ui.tsx";
import { readServiceStatus } from "../../lib/service-reader.server.ts";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const metadata: Metadata = { title: "Research service" };

const unavailableTitles = {
  disabled: "Research service access is disabled.",
  missing: "The research service connection is not configured.",
  unavailable: "The research service did not return a current status.",
  invalid: "The research service response could not be validated.",
} as const;

export default async function ServicePage() {
  const requestHeaders = await headers();
  const result = await readServiceStatus({ requestHost: requestHeaders.get("host") });
  const data = result.data;
  const reconcile = data?.jobs.filter((job) => job.status === "reconciliation_required").length ?? 0;

  return (
    <>
      <PageHeader
        eyebrow="Standalone research service"
        title="Queue, reservations and intervention state."
        description="Live reads from the repository-owned Python service, independent of Codex scheduling. This local operator view has no fixture fallback and does not issue commands."
        actions={<a className="text-link" href="/service">Refresh service status</a>}
      />
      <section className="notice notice--warning" aria-labelledby="service-boundary">
        <div>
          <h2 id="service-boundary">Development service, not a production attestation.</h2>
          <p>This connection is available only on loopback. Cloud ingress still requires reviewed authentication and TLS. A published job means a draft PR was created, not merged or proven effective.</p>
          <a className="text-link" href="#operator-cli">Operator CLI instructions</a>
        </div>
      </section>
      {data === null ? (
        <EmptyState
          title={unavailableTitles[result.state as keyof typeof unavailableTitles]}
          description={`${result.reason}. No previous successful read or fixture values were substituted.`}
        />
      ) : (
        <>
          <section className="snapshot-strip" aria-label="Research service status">
            <div><span>Admission state</span><strong>{data.paused ? "Paused" : "Not paused"}</strong></div>
            <div><span>Returned jobs</span><strong>{data.jobs.length} of at most 100</strong></div>
            <div><span>Require reconciliation</span><strong>{reconcile}</strong></div>
            <div><span>Last event sequence</span><strong>{data.last_event}</strong></div>
            <div><span>Status read</span><strong>{formatUtc(result.checked_at)}</strong></div>
          </section>
          {data.paused || reconcile > 0 ? (
            <section className="notice notice--warning" aria-labelledby="service-intervention">
              <div>
                <h2 id="service-intervention">Operator attention required.</h2>
                {data.paused ? <p>Admission is paused. This page cannot resume the service.</p> : null}
                {reconcile > 0 ? <p>{reconcile} returned job(s) have uncertain external outcomes. Inspect their effect records before any retry; an unacknowledged request is not permission to repeat it.</p> : null}
              </div>
            </section>
          ) : null}
          <section className="surface observation-card" aria-labelledby="service-reservations">
            <h2 id="service-reservations">Daily reservations</h2>
            <p>Up to seven recorded UTC days. Model-call reservations include offline fixtures; these are not counts of paid requests. Reserved amounts are budget commitments, not provider invoices.</p>
            {data.usage.length === 0 ? <p>No reservations recorded.</p> : data.usage.map((day) => (
              <div key={day.day}>
                <h3>{day.day} UTC</h3>
                <dl className="observation-counts">
                  <div><dt>Model-call reservations</dt><dd>{day.model_calls}</dd></div>
                  <div><dt>Source-request reservations</dt><dd>{day.source_request_reservations}</dd></div>
                  <div><dt>Reserved micro-USD</dt><dd>{day.reserved_microusd}</dd></div>
                </dl>
              </div>
            ))}
          </section>
          {data.jobs.length === 0 ? (
            <EmptyState title="No research jobs recorded." description="The service returned an empty queue history. This is not evidence that research has completed." />
          ) : (
            <section className="observation-list" aria-label="Research service jobs">
              {data.jobs.map((job) => (
                <article className="surface observation-card" key={job.id}>
                  <div className="observation-card__heading">
                    <h2 className="mono">{job.id}</h2>
                    <StatePill label={job.status === "published" ? "draft_pr_created" : job.status}
                      tone={job.status === "reconciliation_required" || job.status === "failed" ? "warning" : "neutral"} />
                  </div>
                  <p>Created {formatUtc(new Date(job.created * 1000).toISOString())}. Updated {formatUtc(new Date(job.updated * 1000).toISOString())}.</p>
                  {job.reason !== null ? <p>Reason: <code>{job.reason}</code></p> : null}
                  {job.status === "proposal_ready" ? <p>A candidate is ready for review. This state is not an accepted research finding.</p> : null}
                  {job.status === "retrieval_complete" ? <p>A bounded discovery digest is available. This is not qualified research evidence. Inspect the report for coverage gaps and source qualifiers.</p> : null}
                </article>
              ))}
            </section>
          )}
        </>
      )}
      <section className="surface observation-card" id="operator-cli" aria-labelledby="operator-cli-title">
        <h2 id="operator-cli-title">Operator CLI</h2>
        <p>Run <code>python -m researcher.service --help</code> from the repository for the supported commands. Use <code>status</code> and <code>inspect</code> with your private configuration/state paths; the CLI also provides explicit <code>pause</code> and <code>resume</code>.</p>
        <p>The versioned operating instructions are in <code>docs/product/cloud-research-service.md</code>. Keep <code>RESEARCH_OPERATOR_TOKEN</code> in the server environment, never a browser field or <code>NEXT_PUBLIC_*</code> variable.</p>
      </section>
    </>
  );
}
