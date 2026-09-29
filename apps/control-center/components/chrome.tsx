"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { PrimaryNavigation } from "./primary-navigation.tsx";

export function AppChrome({ children }: { readonly children: ReactNode }) {
  const pathname = usePathname();
  const observations = pathname === "/observations";
  const service = pathname === "/service";
  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <div className="authority-banner" role="status">
        <span className="authority-banner__mark" aria-hidden="true" />
        <strong>{service ? "Standalone research service." : observations ? "Local observation pilot." : "Discardable design experiment."}</strong>
        <span>
          {service
            ? "Read-only status from the explicitly configured local service. This page issues no commands and does not attest production readiness. Model and source counts are reservations, not verified paid requests."
            : observations
            ? "Local summaries are unreviewed observations, not accepted research or production status. Agent dispatch, mutations, and deployment activation remain disabled. Other control pages use fabricated fixtures."
            : "Fabricated fixture data is non-authoritative and does not implement draft owner specifications. All mutations, dispatch, and deployment activation are mechanically disabled. Local observations have a separate read-only page."}
        </span>
      </div>
      <header className="app-header">
        <Link className="brand" href="/" aria-label="Agent Research Control Center home">
          <span className="brand__glyph" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span>
            <strong>ARCC</strong>
            <small>Agent Research Control Center</small>
          </span>
        </Link>
        <div className="header-context" aria-label="Environment">
          <span className="header-context__dot" aria-hidden="true" />
          <span>{service ? "Research service" : observations ? "Local observations" : "Fixture"}</span>
          <span className="header-context__divider" aria-hidden="true" />
          <span>Read only</span>
        </div>
      </header>
      <div className="app-frame">
        <aside className="sidebar">
          <PrimaryNavigation />
          <div className="sidebar-note">
            <p className="eyebrow">Authority boundary</p>
            <p>
              {service
                ? "The repository-owned service governs its own jobs and effects. This loopback-only page reads status; it provides no cloud authentication, merge authority, or deployment activation."
                : observations
                ? "This view reads an explicitly configured local summary. It grants no authority, invokes no agents, and does not provide authentication or hosted access."
                : "This experiment observes fabricated deterministic fixtures. It neither implements draft specifications nor mints commands, grants, reviews, or deployment epochs."}
            </p>
          </div>
        </aside>
        <main id="main-content" className="main-content" tabIndex={-1}>
          {children}
        </main>
      </div>
      <footer className="app-footer">
        <span>{service ? "Research service status · read only" : observations ? "Local observation summary · read only" : "Discardable Control Center experiment · fixture adapter v1"}</span>
        <span>Canonical authority remains in accepted contracts and durable receipts.</span>
      </footer>
    </>
  );
}
