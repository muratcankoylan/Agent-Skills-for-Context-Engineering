# Production preparation: implemented local observation slice

Status: verified supervised local pilot; production and autonomous scientific execution remain blocked.

## Delivered

The integration working tree now has an executable path from a question and explicit skill selection to bounded public retrieval, immutable response bodies, provenance-bound context, replay-verified derived leads, durable observation completion, a deterministic report/research handoff, and actual local UI summaries. [Operation and deployment boundaries](research-observation-pipeline.md) document the commands, source semantics, budgets, recovery and stopping procedures.

The implementation adds no model provider, public ingress, organization acceptance authority or cloud service. The control pages remain visibly separate fixtures; `/observations` is the actual read-only pilot. Repository changes are uncommitted. No PR was merged, pushed or changed by this implementation pass.

## Execution evidence

Private receipts are retained under `researcher/runtime/production-implementation-20260907/`. Each live run binds its own implementation, query/configuration, context and exact response bodies. Earlier runs retain their pre-refinement implementation identity; `final-integrated` exercised all three sources with the final Python implementation. These local bindings are not accepted candidate freezes or deployment attestations.

| Check | Observed result | Scope |
| --- | --- | --- |
| Python suite | 907 passed in 164.944 seconds | Final frozen Python sources; initial run had one generated-inventory drift failure, then regenerated and rerun |
| SDK contract suite | 82 passed; typecheck passed | Actual Node 22.20.0; zero provider calls |
| TypeScript schemas | 22 passed; build/typecheck passed | Actual Node 22.20.0 |
| Control Center | 38 passed; production build and standalone nine-asset smoke passed | Actual Node 22.20.0; real browser/API seven-row, partial-result and desktop/mobile checks passed |
| Context scenarios | Six passed | Deterministic selection, budgets and provenance, not semantic retrieval |
| Extraction ablation | Five valid controls accepted; 13 invalid mutations rejected | Finite offline fixtures; hash/membership-only comparator accepted those mutations; no generalization claim |
| Live observation runs | Seven runs, 25 responses, 24 leads, 93,177 response bytes | arXiv, repository commits and bounded HN windows; discovery observations, not accepted research |
| Model/paid calls by pipeline | Zero | Codex-assisted engineering and triage are separate from product-agent execution |

Live observations span 21:25:55 through 21:36:44 UTC on September 7. This is a sparse 10-minute-49-second observation window, not continuous uptime or a completed multi-day soak. An unmatched query correctly produced `partial` with zero leads. A constrained context pack used 32,700 of 32,768 bytes and explicitly listed six omitted sections; it does not represent full activation of both selected skills.

The standalone browser journey verified a six-to-seven-run refresh without rebuilding, HTTP 200 for the actual summary API, HTTP 403 for a hostile Host with a forged forwarded-host value, no-store/CSP response headers, and no browser errors or horizontal overflow at desktop and mobile widths. The inspection-only server remains bound to loopback; process identity and stop instructions are in the private browser receipt.

Strict repository/platform, generated inventory, schema, governance, lifecycle and export checks passed. Dependency audits found no current production dependency advisories in the UI or SDK runner. Gitleaks and the repository-specific boundary checker found no issues across 685 existing tracked plus nonignored untracked prospective public files. This is not a Git-index/history or release attestation: the preexisting deletion of the tracked benchmark-history runtime file remains uncommitted, and no staging was performed to conceal that distinction.

The broad all-field `context engineering` query returned visibly off-topic results. A separate title/abstract phrase query returned a more relevant-looking small set. The new explicit scope/match options follow [arXiv's query contract](https://info.arxiv.org/help/api/user-manual.html#51-details-of-query-construction). This is a configuration probe, not a blinded relevance benchmark or an estimated precision improvement. Do not make a general quality claim from three results.

## Failures turned into checks

- Access-time changes during file reads were mistaken for content mutation. Stable identity/content metadata now exclude access time.
- Completed context artifacts could be overwritten during resume. Changed or missing checkpoints now fail.
- A late capture callback could mutate a returned source record after timeout. Publication now freezes its reference list and leaves late captures unreferenced.
- Digest-valid captures did not prove that checkpoint lead fields came from those bytes. Offline extraction replay now verifies ordered outputs and capture coverage.
- A successful captured response could be relabeled as a parser failure. Replay now validates fully captured failed outcomes as well as successful ones, while retaining genuinely incomplete transport observations.
- Summary publication could resume work. It now requires a completed work order and does not retrieve or claim work.
- The real standalone API rejected legitimate loopback requests because Next.js normalizes its request URL. The API now checks the incoming Host header with existing loopback environment guards, rejects missing/hostile Host values, and ignores forwarded-host claims. A real `NextRequest` regression covers the behavior.

## Research and skill work

The private `research-triage.md` records Codex-assisted screening of nine captured abstracts, exact evidence spans, corpus overlap and two proposed experiments: directional writer/reader memory migration and sham-controlled agent replacement. Neither full papers nor their experiments were reproduced. These are candidate research directions, not accepted mechanisms.

[The evaluation refinement proposal](evaluation-refinement-proposal.md) strengthens an existing deterministic-validation mechanism instead of inventing a duplicate skill. A full private candidate passes the skill packaging validator. Its effectiveness remains unmeasured; the accepted skill, registry, claim index and activation surfaces are intentionally unchanged pending the specified Stage 3 study and review.

## Remaining production gates

1. Locate an authorized credential file or Keychain-backed launcher. The inspected process/launchd environment and project env-file locations did not contain the expected credentials. Do not paste secrets into chat.
2. Complete the existing provider-neutral, authorization, containment and bounded-canary gates before enabling paid Cursor execution. A credential is not a replacement for the missing execution contract.
3. Connect an independently executed researcher and critic, full-paper evidence, candidate freeze and representative paired skill-effectiveness evaluation. The present handoff stops before those steps.
4. Unify canonical work acceptance, journal/outbox and reservations; implement operator commands, authentication, recovery, backup/restore and deployment identity under accepted contracts.
5. Complete real elapsed observation and recovery drills. Resume the existing hourly Codex task for supervised observations; do not describe it as OS cron or an always-running research daemon.
6. Validate the container and hosted isolation path. The local Docker CLI exists, but its daemon was unavailable. Standalone Node success is not a Docker or cloud deployment test.

The immediate location is the maintainer's machine: deterministic Python execution and a read-only Next server bound to loopback. Untrusted code and live model/tool execution remain disabled. [The hosted deployment proposal](deployment.md) remains a separate decision and activation boundary.
