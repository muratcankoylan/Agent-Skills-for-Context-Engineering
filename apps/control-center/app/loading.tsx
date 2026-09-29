export default function Loading() {
  return (
    <section className="loading-state" aria-busy="true" aria-live="polite">
      <p className="eyebrow">Loading fixture projection</p>
      <div className="loading-state__title" />
      <div className="loading-state__line" />
      <div className="loading-state__grid">
        <div />
        <div />
        <div />
      </div>
      <span className="sr-only">Loading the read-only control center.</span>
    </section>
  );
}
