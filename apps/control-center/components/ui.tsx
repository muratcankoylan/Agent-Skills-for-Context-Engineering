import Link from "next/link";
import type { ReactNode } from "react";
import type {
  ControlCenterSnapshot,
  Freshness,
  HealthTone,
  MutationCapability,
} from "../lib/domain.ts";
import { humanizeIdentifier, shortDigest } from "../lib/view-model.ts";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  readonly eyebrow: string;
  readonly title: string;
  readonly description: string;
  readonly actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="page-header__description">{description}</p>
      </div>
      {actions === undefined ? null : <div className="page-header__actions">{actions}</div>}
    </header>
  );
}

export function FixtureStatePicker({ route }: { readonly route: string }) {
  const states = ["ready", "empty", "stale", "error", "permission"] as const;

  return (
    <details className="fixture-picker">
      <summary>Preview states</summary>
      <div className="fixture-picker__menu">
        <p>Deterministic UI scenarios</p>
        <ul>
          {states.map((state) => (
            <li key={state}>
              <Link href={`${route}?state=${state}`} prefetch={false}>
                {state}
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </details>
  );
}

export function FreshnessNotice({ freshness }: { readonly freshness: Freshness }) {
  if (freshness.state === "current") {
    return null;
  }

  return (
    <section
      className={`notice notice--${freshness.state === "stale" ? "warning" : "neutral"}`}
      aria-labelledby="freshness-notice-title"
    >
      <div className="notice__icon" aria-hidden="true">
        {freshness.state === "stale" ? "!" : "?"}
      </div>
      <div>
        <h2 id="freshness-notice-title">
          {freshness.state === "stale" ? "Projection is stale" : "Freshness is unknown"}
        </h2>
        <p>{freshness.detail}</p>
        <code>{freshness.reasonCode}</code>
      </div>
    </section>
  );
}

export function SnapshotStrip({ snapshot }: { readonly snapshot: ControlCenterSnapshot }) {
  const accepted =
    snapshot.repositoryAcceptance.state === "known"
      ? snapshot.repositoryAcceptance.value
      : humanizeIdentifier(snapshot.repositoryAcceptance.state);
  const deployment =
    snapshot.deploymentPointer.state === "known"
      ? snapshot.deploymentPointer.value
      : humanizeIdentifier(snapshot.deploymentPointer.state);

  return (
    <section className="snapshot-strip" aria-label="Projection identity">
      <div>
        <span>Projection</span>
        <strong>Sequence {snapshot.identity.sourceSequence}</strong>
      </div>
      <div>
        <span>As of</span>
        <strong>{formatUtc(snapshot.identity.asOf)}</strong>
      </div>
      <div>
        <span>Accepted repository (fixture)</span>
        <strong>{accepted}</strong>
      </div>
      <div>
        <span>Active deployment</span>
        <strong>{deployment}</strong>
      </div>
      <div className="snapshot-strip__digest">
        <span>Event chain</span>
        <strong title={snapshot.identity.eventChainDigest}>
          {shortDigest(snapshot.identity.eventChainDigest)}
        </strong>
      </div>
    </section>
  );
}

export function StatePill({
  label,
  tone = "neutral",
}: {
  readonly label: string;
  readonly tone?: HealthTone;
}) {
  return (
    <span className={`state-pill state-pill--${tone}`}>
      <span className="state-pill__dot" aria-hidden="true" />
      {humanizeIdentifier(label)}
    </span>
  );
}

export function EmptyState({
  title,
  description,
}: {
  readonly title: string;
  readonly description: string;
}) {
  return (
    <section className="empty-state" aria-labelledby="empty-state-title">
      <div className="empty-state__glyph" aria-hidden="true">
        ∅
      </div>
      <h2 id="empty-state-title">{title}</h2>
      <p>{description}</p>
    </section>
  );
}

export function PermissionState({ detail }: { readonly detail: string }) {
  return (
    <section className="permission-state" aria-labelledby="permission-state-title">
      <p className="eyebrow">View profile denied</p>
      <h1 id="permission-state-title">This projection is outside your fixture profile.</h1>
      <p>{detail}</p>
      <code>fixture_profile_forbidden</code>
      <Link className="text-link" href="/">
        Return to overview
      </Link>
    </section>
  );
}

export function MutationBlock({
  capability,
  buttonLabel,
}: {
  readonly capability: MutationCapability;
  readonly buttonLabel: string;
}) {
  const descriptionId = `capability-${capability.action}`;

  return (
    <div className="mutation-block">
      <button type="button" disabled aria-describedby={descriptionId}>
        {buttonLabel}
      </button>
      <div id={descriptionId}>
        <strong>Mutation unavailable · {capability.reasonCode}</strong>
        <p>{capability.reason}</p>
        <span>Owned by {capability.ownerSpecs.join(" + ")}</span>
      </div>
    </div>
  );
}

export function SectionHeading({
  id,
  eyebrow,
  title,
  detail,
}: {
  readonly id?: string;
  readonly eyebrow?: string;
  readonly title: string;
  readonly detail?: string;
}) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow === undefined ? null : <p className="eyebrow">{eyebrow}</p>}
        <h2 id={id}>{title}</h2>
      </div>
      {detail === undefined ? null : <p>{detail}</p>}
    </div>
  );
}

export function formatUtc(value: string): string {
  return value.replace("T", " ").replace("Z", " UTC");
}
