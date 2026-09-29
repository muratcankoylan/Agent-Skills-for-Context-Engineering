"use client";

export default function ErrorBoundary({ reset }: { readonly reset: () => void }) {
  return (
    <section className="error-state" role="alert" aria-labelledby="error-title">
      <p className="eyebrow">Fixture adapter error</p>
      <h1 id="error-title">The projection could not be rendered.</h1>
      <p>
        No fallback data was substituted. Retry the deterministic fixture read or
        return to the normal preview.
      </p>
      <div className="error-state__actions">
        <button type="button" onClick={reset}>
          Retry
        </button>
        <a className="text-link" href="/?state=ready">
          Open normal fixture
        </a>
      </div>
    </section>
  );
}
