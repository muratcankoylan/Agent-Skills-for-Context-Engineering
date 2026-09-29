import Link from "next/link";

export default function NotFound() {
  return (
    <section className="error-state" aria-labelledby="not-found-title">
      <p className="eyebrow">404 · Unknown view</p>
      <h1 id="not-found-title">This control-center route does not exist.</h1>
      <p>No runtime object was queried and no state was changed.</p>
      <Link className="text-link" href="/">
        Return to overview
      </Link>
    </section>
  );
}
