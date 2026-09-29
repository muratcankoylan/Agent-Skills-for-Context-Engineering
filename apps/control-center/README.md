# Agent Research Control Center

Status: read-only local observation pilot alongside a non-authoritative fixture interface

This application explores a possible private operator interface for the Agent Research organization. It is not an implementation of draft owner specifications and is not production-readiness evidence. If the governing lifecycle treats even interface experiments as prohibited prototype work, this directory must remain unshipped or be discarded until that work is explicitly authorized.

The application is read-only. Its existing control pages use fabricated fixtures. The separate `/observations` page can read one explicitly configured local summary file when the loopback pilot is enabled. Neither surface reads runtime queues, GitHub, credentials, or provider APIs, and neither can create a command, work order, review decision, capability grant, canary, or deployment epoch.

The global orange boundary banner is part of the product contract. Removing it or enabling a mutation before the owning specifications are accepted would be a correctness failure, not a cosmetic change.

## What is implemented

- Next.js 16.3.3 App Router and React 19.2.8, with exact direct dependency pins and a committed npm lock.
- Server Components for data views. Client code provides the reset boundary, active navigation, and route-specific authority banner; observation file access stays in a Node-only server module.
- Overview health, research runs, review queue, artifacts, and deployment views.
- Current, empty, stale, deliberate error, and permission-denied fixture scenarios.
- Separate accepted-repository and active-deployment slots on every data view.
- Projection sequence, fixed `as_of` observation, freshness, and event-chain identity.
- Disabled mutation controls with `dependency_inactive` reason codes and owning specifications.
- Bounded JSON `GET /api/status` and cursor-paged `GET /api/events` handlers.
- Opt-in, dynamically read `/observations` and `GET /api/observations`, with strict summary validation and distinct disabled, missing, invalid, current, and stale states.
- Responsive semantic navigation with current-page state, tables, status text, visible focus, and reduced-motion behavior.
- A production nonce-based Content Security Policy for rendered pages and a deny-all document policy for JSON APIs.
- A standalone-output, non-root Docker image with an HTTP fixture health check.
- Dependency-free unit tests plus a bounded standalone-runtime asset and header smoke test.

No external fonts, images, analytics, scripts, or browser-side data clients are used.

## Proposed product and deployment boundary

This experiment proposes the following split. It is amendment-gated design input, not an accepted deployment decision:

```text
human operator
  -> private Control Center / orgctl
  -> one launchd-supervised orgd control process on the maintainer's macOS host
       -> trusted, deterministic, bounded local child work only
       -> remote accepted GKE sandbox for every untrusted code/tool attempt
  -> append-only journal + immutable content-addressed artifacts
  -> deterministic projections consumed by this UI
```

The Control Center is a view and command client, never a state authority. The first real deployment should bind the web UI to a loopback or private-network read adapter owned by SPEC-008. Commands should travel through the authenticated SPEC-006 command boundary. The UI must not write a queue, database row, Git repository, credential store, or provider API directly.

Local child execution is limited to work that is trusted, deterministic, and bounded. Untrusted code or tool execution must never run on the maintainer host; it routes to a remote accepted GKE sandbox with attempt-bound, fenced capabilities. Results return as typed result envelopes and immutable `ArtifactRef` records. The event journal remains canonical, projections remain rebuildable, and large artifact bodies are resolved only through an authorized storage binding.

The Dockerfile provides build and runtime parity for review and a future private deployment. It does not make this slice deployable. Continuous operation remains blocked until the accepted owner contracts, canary, backup/restore, upgrade/rollback, reconciliation, budget, and emergency-stop drills exist.

Do not introduce a public ingress, hosted control plane, or multiple control daemons into the supervised local pilot. Remote GKE is an execution isolation boundary only in this proposal. It remains gated on an accepted deployment amendment, threat model, identity and network policy, artifact-return contract, and measured sandbox isolation. Until those contracts exist, untrusted execution is disabled rather than silently falling back to a local child.

## Interaction model

Current interaction is inspection only:

- Navigate between server-rendered fixture projections.
- Select deterministic states with the **Preview states** menu.
- Read exact dependency blockers on disabled controls.
- Fetch bounded fixture JSON from the two GET endpoints.

The future interface may request pause, review, recovery, and activation intents only after authenticated identity, exact target/version guards, policy decisions, runtime grants, idempotency, durable receipts, and stale-state handling are implemented. GitHub remains the merge surface; the Control Center should never expose a merge button.

## Fixture scenarios

Append a `state` query parameter to a fixture UI route or either fixture API route. This parameter does not select observation data on `/observations`:

| Query | Behavior |
| --- | --- |
| no query or `?state=ready` | Complete finite fixture with current freshness |
| `?state=empty` | Empty collections and explicit unknown freshness |
| `?state=stale` | Last-known values with a visible stale warning |
| `?state=error` | Deliberate adapter failure; UI error boundary or API 503 |
| `?state=permission` | Classification-profile denial; UI denial state or API 403 |

An unknown UI `state` value, or repeated UI `state` keys, fails into the deliberate error scenario instead of being silently repaired. API query keys are stricter: repeated `state`, `after`, or `limit` keys return a typed HTTP 400 response even when their values match.

The typed fixture in `lib/fixtures.ts` mirrors a non-authoritative authority envelope and selected blocker concepts from `docs/product/production-readiness.json`. Its assessment baseline is `c6cd52017b247804373339e1c3c103d42554b0a1`; the candidate state is `uncommitted_worktree`, so `candidateCommit` is `null`. The separately displayed accepted-repository value is fabricated fixture data and must not be interpreted as candidate or deployment identity. Fixture routes do not read the assessment document or local observation file. The observation route uses its separate contract below; it never re-labels fixture projections as live.

## Local observation pilot

After building, start the application with `HOSTNAME=127.0.0.1`, `RESEARCH_OBSERVATIONS_ENABLED=1`, and `RESEARCH_OBSERVATION_FILE` set to the absolute path of the operator-produced summary file. Open `/observations` through `http://127.0.0.1:<port>`. These are server-only settings. No request parameter selects a path, and no configured path appears in a response.

This opt-in is a supervised local read surface, not authentication, a hosted service, or runtime activation. The request Host must also be `127.0.0.1` with an optional valid port. Do not put this pilot behind public ingress or a reverse proxy.

The input is `local-research-observation-view/v1`: authority `none`, production readiness `false`, a whole-second UTC `generated_at`, and at most 50 unique UUID run summaries. Each run contains only its query, observation time, `awaiting_researcher`/`partial`/`failed` status, lead/capture/context counts, zero model calls, report digest, and short blockers. The producing operator owns sanitization of query and blocker text; raw source bodies, private paths, and credentials must never enter this summary. Lead and capture counts are independently bounded at 1,000 because a failed request can produce a capture without producing a lead.

Reads use a 256 KiB cap, direct single-link regular files, no-follow checks including ancestors, bounded strict UTF-8/JSON parsing, duplicate/unknown-key rejection, and timestamp validation. Timestamps more than 60 seconds in the future fail; summaries more than two hours old remain visible as stale. Atomic replacement by the producer is supported. No successful data is cached as fallback after a missing or corrupt input.

`GET /api/observations` returns a `local-research-observation-read/v1` envelope and the validated summary, with `Cache-Control: no-store` and authority `none`. Disabled reads return 403, missing/invalid reads return 503, and current/stale readable summaries return 200 with their explicit state. The page performs the same dynamic server read and displays observation dates, counts, and incomplete research/review work. It has no refresh timer, provider integration, raw evidence viewer, agent dispatch, or mutation path. The manual refresh link performs a new read.

## Read API

### Status

```http
GET /api/status
```

Returns `control-center-status.v1`, including fixture identity, freshness, typed dependency slots, view records, and mechanically disabled capabilities. Responses use `Cache-Control: no-store` and `X-Control-Center-Authority: fixture-non-authoritative`. Repeated `state` keys return `duplicate_query_parameter` with HTTP 400.

### Events

```http
GET /api/events?after=cc-fixture-v1.1143&limit=3
```

`after` is exclusive. `limit` must be an integer from 1 through 50. A returned `nextCursor` can be supplied to the next request; `hasMore: false` and `endOfFixture: true` terminate iteration. Every page carries the snapshot `asOf`, observation identity, and freshness state. Unknown, malformed, cross-fixture, and beyond-tail cursors return HTTP 400. Repeated `state`, `after`, or `limit` keys return `duplicate_query_parameter` with HTTP 400.

This endpoint returns finite JSON pages. It is not SSE, long polling, WebSocket transport, a canonical watch, or evidence of a running event journal. The response and `X-Control-Center-Stream: finite-json-page-not-live` header state that boundary explicitly.

Only `GET` is exported. Next.js returns method-not-allowed for mutation verbs.

## Development and verification

Prerequisite: Node.js 22.12 or newer.

```bash
npm ci --ignore-scripts --no-audit --no-fund
npm test
npm run typecheck
npm run build
npm run test:runtime
```

`npm test` uses Node's `--experimental-strip-types` mode so the pure TypeScript domain, adapter, view-model, and route-handler contracts can be tested without a test framework dependency. Node may print an experimental-feature warning on Node 22 and 23.

`npm run build` stages `.next/static` and `public` into the standalone output. `npm start` repeats that idempotent staging step before starting the standalone server, preventing a local standalone launch from serving HTML whose CSS and JavaScript return 404. `npm run test:runtime` starts the production server on an ephemeral loopback port, fetches every rendered static asset and the public marker, checks CSP nonce propagation, validates finite APIs, mutation-method rejection, current-page navigation, and landmark label references, and terminates the process. `npm run verify` runs the complete deterministic sequence.

The tests cover:

- isolated fixture reads and all five display states;
- fail-closed mutation capabilities and owning-spec evidence;
- cursor round trips, exclusive pagination, page bounds, end-of-fixture behavior, and forged cursors;
- stale and empty overview derivation;
- status and event snapshot identity, freshness, response headers, duplicate-key rejection, and typed HTTP failures;
- production CSP construction, navigation matching, and small-text color contrast contracts;
- standalone server asset delivery, CSP nonce propagation, current navigation, and landmark-reference smoke checks; and
- absence of POST, PUT, PATCH, and DELETE exports.

These checks do not constitute an automated browser accessibility gate. Browser-level accessibility and responsive-layout automation remain blocked/planned for any production candidate, alongside clean-container build verification, Software Bill of Materials generation, image vulnerability scanning, ingress preservation of the application CSP/security headers, and rendered parity against immutable SPEC-008 fixtures.

## Container preview

```bash
docker build -t agent-research-control-center:fixture .
docker run --read-only --tmpfs /tmp --cap-drop ALL \
  --security-opt no-new-privileges --publish 127.0.0.1:3000:3000 \
  agent-research-control-center:fixture
```

Open `http://127.0.0.1:3000`. Binding to loopback is deliberate. Do not expose the fixture shell as a production control plane.

## Production activation gate

Before replacing the fixture adapter, all of the following must be true:

1. Required owner specs are accepted and implemented in dependency order.
2. The read adapter consumes a pinned SPEC-008 projection and preserves freshness, sequence, classification, and unknown/stale distinctions.
3. Authenticated command ingress is separated from reads and passes authority, stale-version, replay, and collision tests.
4. The supervisor, remote untrusted-executor isolation, trusted-local-work restrictions, journal, artifact store, credentials, budgets, and reconciliation paths pass crash and adversarial tests.
5. Backup restore succeeds into a clean directory and reproduces projection digests.
6. A bounded canary is independently attested against a closed evidence window.
7. A human with current production-activation authority advances the deployment pointer exactly once.
8. Rollback and emergency stop are rehearsed without journal rewind or fabricated completion.

Until then, `dependency_inactive` is the correct product state.
