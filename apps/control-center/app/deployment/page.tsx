import type { Metadata } from "next";
import {
  FixtureStatePicker,
  FreshnessNotice,
  MutationBlock,
  PageHeader,
  PermissionState,
  SectionHeading,
  SnapshotStrip,
  StatePill,
} from "../../components/ui.tsx";
import {
  getMutationCapability,
  parseFixtureMode,
  readControlCenterFixture,
} from "../../lib/fixture-adapter.ts";
import { humanizeIdentifier } from "../../lib/view-model.ts";

export const metadata: Metadata = {
  title: "Deployment",
};

interface PageProps {
  readonly searchParams: Promise<{
    readonly state?: string | readonly string[];
  }>;
}

export default async function DeploymentPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const result = readControlCenterFixture(parseFixtureMode(params.state));

  if (result.kind === "permission_denied") {
    return <PermissionState detail={result.detail} />;
  }

  const snapshot = result.data;
  const deployment = snapshot.deployment;
  const activationCapability = getMutationCapability(
    snapshot,
    "activate_deployment",
  );

  return (
    <>
      <PageHeader
        eyebrow="Runtime and recovery"
        title="Supervised control. Remote isolation for untrusted work."
        description="This discardable fixture explores an amendment-gated boundary: local coordination and trusted bounded work, with untrusted code and tools routed only to a remote accepted GKE sandbox. It does not implement a draft owner specification."
        actions={<FixtureStatePicker route="/deployment" />}
      />
      <FreshnessNotice freshness={snapshot.identity.freshness} />
      <SnapshotStrip snapshot={snapshot} />

      <div className="deployment-hero">
        <section className="deployment-summary surface surface--dark" aria-labelledby="deployment-state-title">
          <StatePill label={deployment.lifecycle} tone="warning" />
          <h2 id="deployment-state-title">No production epoch is active.</h2>
          <p>
            The fabricated accepted-repository fixture and active deployment are
            separate slots. The latter remains dependency-inactive until a
            human-authorized, promotion-bound canary closes successfully. If
            lifecycle policy treats this fixture experiment as prototype work, it
            must remain unshipped until that work is explicitly authorized.
          </p>
          <dl className="deployment-facts">
            <div>
              <dt>Initial control host</dt>
              <dd>Maintainer&apos;s macOS machine</dd>
            </div>
            <div>
              <dt>Process supervision</dt>
              <dd>{deployment.processManager} → {deployment.supervisor}</dd>
            </div>
            <div>
              <dt>Trusted local work</dt>
              <dd>Deterministic and bounded child processes only</dd>
            </div>
            <div>
              <dt>Untrusted code and tools</dt>
              <dd>Remote accepted GKE sandbox only</dd>
            </div>
            <div>
              <dt>Result flow</dt>
              <dd>{deployment.resultPath}</dd>
            </div>
            <div>
              <dt>Assessment baseline</dt>
              <dd>{snapshot.readinessAssessment.baselineCommit.slice(0, 12)} (fixture)</dd>
            </div>
            <div>
              <dt>Candidate state</dt>
              <dd>{humanizeIdentifier(snapshot.readinessAssessment.candidateState)}</dd>
            </div>
            <div>
              <dt>Candidate commit</dt>
              <dd>{snapshot.readinessAssessment.candidateCommit ?? "None"}</dd>
            </div>
            <div>
              <dt>Production ready</dt>
              <dd>{snapshot.readinessAssessment.productionReady ? "Yes" : "No"}</dd>
            </div>
          </dl>
        </section>

        <aside className="deployment-boundary surface" aria-labelledby="interaction-title">
          <p className="eyebrow">Current interaction model</p>
          <h2 id="interaction-title">Observe through server-rendered fixtures.</h2>
          <p>
            Future commands must cross authenticated ingress, deterministic parsing,
            authorization, scheduling, and journal application. None of those write
            boundaries are present in this application. This view is interface
            evidence only, not proof that prototype implementation is lifecycle-valid.
          </p>
          <code>interaction_mode={deployment.interactionMode}</code>
        </aside>
      </div>

      <SectionHeading
        eyebrow="Execution topology"
        title="Where trusted work, untrusted work, and results would belong"
        detail="Local children are restricted to trusted deterministic and bounded work. Untrusted code or tools route to a remote accepted GKE sandbox. Arrows describe a proposed boundary, not active connections or accepted implementation authority."
      />
      <ol className="topology-list">
        {deployment.topology.map((node) => (
          <li className="topology-node surface" key={node.id}>
            <span>{node.boundary} boundary</span>
            <strong>{node.label}</strong>
            <p>{node.detail}</p>
          </li>
        ))}
      </ol>

      <SectionHeading
        eyebrow="Release gates"
        title="Production readiness"
        detail="A pass requires immutable evidence from the frozen candidate. Fixture labels are illustrative only."
      />
      <ol className="readiness-list surface">
        {deployment.readiness.map((item, index) => (
          <li className="readiness-item" key={item.id}>
            <span className="readiness-item__index" aria-hidden="true">
              {String(index + 1).padStart(2, "0")}
            </span>
            <div>
              <strong>{item.label}</strong>
              <p>{item.evidence}</p>
            </div>
            <StatePill
              label={humanizeIdentifier(item.state)}
              tone={item.state === "passed" ? "good" : item.state === "blocked" ? "warning" : "neutral"}
            />
          </li>
        ))}
      </ol>

      <MutationBlock capability={activationCapability} buttonLabel="Start production canary" />
    </>
  );
}
