import type { Metadata } from "next";
import {
  EmptyState,
  FixtureStatePicker,
  FreshnessNotice,
  PageHeader,
  PermissionState,
  SnapshotStrip,
  StatePill,
  formatUtc,
} from "../../components/ui.tsx";
import {
  parseFixtureMode,
  readControlCenterFixture,
} from "../../lib/fixture-adapter.ts";
import { formatBytes, shortDigest } from "../../lib/view-model.ts";

export const metadata: Metadata = {
  title: "Artifacts",
};

interface PageProps {
  readonly searchParams: Promise<{
    readonly state?: string | readonly string[];
  }>;
}

export default async function ArtifactsPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const result = readControlCenterFixture(parseFixtureMode(params.state));

  if (result.kind === "permission_denied") {
    return <PermissionState detail={result.detail} />;
  }

  const snapshot = result.data;

  return (
    <>
      <PageHeader
        eyebrow="Evidence and lineage"
        title="Artifacts are references, not authority."
        description="Integrity, classification, and provenance remain distinct. The interface exposes bounded fixture metadata and never resolves a private storage locator."
        actions={<FixtureStatePicker route="/artifacts" />}
      />
      <FreshnessNotice freshness={snapshot.identity.freshness} />
      <SnapshotStrip snapshot={snapshot} />

      {snapshot.artifacts.length === 0 ? (
        <EmptyState
          title="No artifacts in scope"
          description="The fixture profile returned no artifact summaries. Missing records are not treated as deleted or invalid."
        />
      ) : (
        <section className="artifact-grid" aria-label="Artifact summaries">
          {snapshot.artifacts.map((artifact) => (
            <article className="artifact-card surface" key={artifact.id}>
              <div className="artifact-card__top">
                <StatePill
                  label={artifact.integrity}
                  tone={
                    artifact.integrity === "verified"
                      ? "good"
                      : artifact.integrity === "quarantined"
                        ? "danger"
                        : "warning"
                  }
                />
                <code>{artifact.classification}</code>
              </div>
              <h2>{artifact.name}</h2>
              <p>{artifact.lineage}</p>
              <dl>
                <dt>Kind</dt>
                <dd>{artifact.kind}</dd>
                <dt>Digest</dt>
                <dd title={artifact.digest}>{shortDigest(artifact.digest)}</dd>
                <dt>Size</dt>
                <dd>{formatBytes(artifact.bytes)}</dd>
                <dt>Observed</dt>
                <dd>{formatUtc(artifact.createdAt)}</dd>
              </dl>
            </article>
          ))}
        </section>
      )}
    </>
  );
}
