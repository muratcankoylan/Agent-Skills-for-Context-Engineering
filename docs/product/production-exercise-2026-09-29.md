# Production preparation exercise: 29 September 2026

Status: measured local engineering evidence, not a released product, a hosted
availability report, or evidence of scientific self-improvement. The tested
candidate is the integrated, uncommitted worktree. Historical baseline commits
do not identify these new bytes. Private manifests bind implementation hashes,
exact inputs, observations and outputs; their private locators are not exported.

## Objective and release boundary

Build a repository-owned research organization that can run on a Linux host
without Codex, a desktop scheduler or an interactive researcher. The intended
loop is bounded discovery, capture verification, primary-source reading,
research and critique, a frozen skill candidate, independent evaluation tasks,
and a review packet. Acceptance, GitHub publication and deployment activation
are separate decisions, not consequences of a model claiming success.

The immediate engineering question is whether the harness can execute that
path, explain failures, preserve evidence and budget across restarts, and stop
when evidence is insufficient. The scientific question is different: whether
its proposed changes improve downstream outcomes on independently constructed,
held-out tasks. This exercise measures the first question and exposes missing
evidence for the second. It does not substitute public smoke fixtures for a
research-paper evaluation.

## Architecture exercised

```text
daily UTC retrieval windows
  -> bounded source adapters / reviewed MCP operations
  -> captured responses + deterministic replay + explicit omissions
  -> selected primary HTML observations
  -> capture-verified context packet + exact skill baseline
  -> researcher -> deterministic grounding -> critic -> optional editor
  -> immutable candidate + full-checkout structural checks
  -> supplied three-arm evaluation plan + fresh model calls
  -> durable results for operator review

One cumulative OpenAI authority covers every funded role and evaluation call.
Unknown external effects keep their reservations and are not retried.
```

MCP has been exercised through the actual registered bridge, not just a direct
HTTP imitation. Daily retrieval still uses the explicitly supported source
adapters; a successful MCP canary does not make MCP part of every retrieval job.
The native budgeted pipeline and managed Agents sessions share context/proposal
contracts but have different execution and spending boundaries. See the
[architecture](research-system-architecture-2026-09-29.md),
[budget authority](../../researcher/service/OPENAI_CAMPAIGN.md),
[pipeline](../../researcher/service/RESEARCH_PIPELINE.md), and
[candidate review](../../researcher/service/CANDIDATE_REVIEW.md).

The [organization coordinator](../../researcher/service/ORGANIZATION.md) closes
the recurring retrieval-to-pipeline handoff. It owns one process lock and an
immutable manifest binding the source configuration, authority, skill baselines,
implementation, policy and optional dataset. It dispatches at most one research
study per cycle, retains terminal outcomes, and resumes interrupted work only
under the original bindings. Both source and model-authority pause states stop
admission. The coordinator cannot initialize a second allowance or publish a PR.
The separate legacy-compatible native preview is not this funded worker and
must not be activated alongside it under a claim of shared spending containment.

## Live connector and model evidence

The [connector verification record](connector-verification-2026-09-29.md)
contains the scoped checks and receipts. Successful operations included:

- X recent search with post, author, conversation, time and engagement fields.
- OpenAlex authenticated work discovery with reconstructed abstracts.
- Parallel search, extraction and MCP web-fetch.
- Firecrawl account access, Research Index paper search and a bounded scrape.
- GitHub authenticated identity and repository reads, without writes.
- arXiv, Hacker News and company-feed observations in separate retrieval jobs.

The connector agent's initial 11 checks used 14 HTTP requests. Across its
subsequent generic-MCP investigations and canaries, reservations allowed at most
50 HTTP requests and $0.103. The latter are conservative reservation ceilings,
not measured HTTP usage or a provider invoice. They do not include the separate
arXiv retrieval follow-ups below. No successful key check establishes unlimited
quota, write permissions, future uptime or semantic retrieval quality.

The funded model path uses `gpt-6-sol`, low reasoning, Standard service tier,
bounded output, one active call, no hosted tools, no background execution and no
automatic retry. Research roles are separate requests; they are not independent
scientific reviewers. The managed Agents API also returned a successful
read-only session listing. No managed session was created in this exercise.

The harness reserves a conservative input/cache-write price ceiling and maximum
output before every request. Token usage estimates are not invoices, and unused
reservations are not refunded. The local authority does not cover clients that
use the key outside this harness. A dedicated provider project hard spend limit
is the additional account-side boundary; the provider documents possible
enforcement lag. Pricing is pinned to a dated policy with an expiry, not assumed
stable indefinitely. Sources: [model pricing](https://developers.openai.com/api/docs/models/gpt-6-sol),
[Responses configuration](https://developers.openai.com/api/reference/python/resources/responses/methods/create),
[spend limits](https://developers.openai.com/api/docs/guides/spend-limits).

Final funded-authority snapshot for this exercise:

| Quantity | Recorded value |
| --- | ---: |
| User-authorized cumulative OpenAI ceiling | $100.000000 |
| Retained reservations | $3.869170 |
| Remaining reservation capacity | $96.130830 |
| Completed-call usage-price estimate | $0.683800 |
| Submitted attempts / completed receipts / unresolved attempts | 35 / 34 / 1 |
| Recorded completed input / output tokens | 238,811 / 8,677 |

The unresolved attempt is the initial response-framing failure. It was not
retried under the same identity or refunded. Its actual provider billing is
unknown; the estimate covers only completed receipts. Local historical records
were audited before initial admission, but the provider account invoice was not
reconciled. No other authority was created for later jobs or dates.

## Failure-derived engineering changes

| Observed failure | Mechanism-level change | Verification and retained limitation |
| --- | --- | --- |
| A real OpenAI response had repeated case-varied CORS headers; a generic header canonicalizer rejected it | Interpret only relevant response/framing headers; continue rejecting duplicate framing | New live canary succeeded; original uncertain attempt and reservation remain, without retry |
| Researcher cited a skill-corpus excerpt as external evidence | Explicit evidence namespace and deterministic grounding before paying for critique | Grounded follow-up produced claims and a critic abstention; corpus is never external evidence |
| Managed MCP SDK metadata contained fractional priority/timing fields | Hash the bounded SDK envelope separately; validate the narrow evidence projection under the integer-only contract | Real registered Parallel web-fetch and offline replay succeeded; evidence floats remain rejected |
| arXiv received raw query grammar where the adapter expected topical text | Use the adapter's documented plain-text query contract in a distinct follow-up job | Original HTTP 400 remains recorded; corrected query returned ten observations |
| Relevant TRACE HTML exceeded the historical 500 KB reader cap | Explicit `large-paper-html-v1`, bounded to 1.5 MB, binding both old parser and new profile hashes | Real HTML read succeeded; historical reader bytes/replay unchanged; still only bounded excerpts, not complete paper understanding |
| TRACE researcher changed whitespace while copying a real passage | Deterministic source-bound citation selection, followed by the unchanged literal-grounding boundary | The failed original result remains in the experiment denominator; no fuzzy quote repair or silent model retry |
| Known-key guard missed JSON-escaped keys nested inside a request prompt | Bounded recursive inspection of JSON/URL encodings, fail closed on scan exhaustion | Regression tests reject before persistence/dispatch; this is not arbitrary secret classification |
| Database-only backup omitted artifact closure | Closed, content-hashed recovery bundle for database, captures, candidates and explicit session/budget ledgers | Actual isolated restore preserved capture replay, reservations and unresolved effect state; restore remains paused |
| A disk error between result receipt and final index/state publication could overwrite a completed outcome | Separate execution errors from terminal checkpoint errors; reconcile the retained receipt on exact restart | Injected filesystem-error regressions require preserved completion and no second model/pipeline execution |
| The actual MCP-enabled container build rejected conflicting shared `click` pins | Constrain the optional dependency input to the core lock; align exact version/hashes; install both locks in one resolver transaction | Shared-pin regression, successful hash-verified container rebuild and offline `pip check`; no hash checks disabled |
| Production npm audit found vulnerable transitive `sharp` and `fast-uri` versions | Pin narrowly compatible patched dependencies without upgrading Next, React or AJV; require production audits on all three Node surfaces in CI | Reproduced the URI authority-injection case, added URI/native-image regressions and retained disabled install lifecycle scripts; audit results below |

### Primary-source scope

The larger-reader canary discovered
[TRACE: Governing Memory Validity in Evolving Multi-Agent Systems](https://arxiv.org/abs/2609.33517v1)
and retrieved its primary HTML through the service. One credential-free HEAD
observed a 665,363-byte HTML representation; the subsequent two-effect retrieval
completed discovery plus the larger-profile read and produced 12 evidence rows.
The profile permits one request, no redirects, 15 seconds, 1.5 MB response bytes
and 100 KB retained normalized text. The context projection selects at most two
4,096-byte primary excerpts. These caps and omissions are explicit. This is not
a claim that the agent received every method, table or appendix.

An earlier memory-retrieval packet had 16 discovery rows plus two primary
excerpts. Its adjacent-domain primary paper did not justify the proposed memory
skill change; the critic abstained. This is a useful stopping outcome, not a
successful skill improvement. Broader source recall, qualified relevance and
section-selection quality still require independently labeled retrieval tasks.

The final live organization cycle reused the replay-verified TRACE captures,
without a new source request, under the new citation-span contract. The researcher
produced three grounded claims; the critic supported all three as author
descriptions/reported results but abstained from an edit. It identified missing
primary methods/appendices, untested transfer, incomplete decision thresholds and
mixed downstream results. Both role calls completed. The coordinator retained
the terminal abstention and reopened with identical status without credentials.
No dataset was supplied and no editor, candidate acceptance or publication was
triggered. Organization identity:
`sha256:f7472a585cf2cd05368bbe0d870ebcf608cc82c5e6022f9fc340b60b3731bcb4`.
Pipeline result digest:
`sha256:d8a05a1e38af14ea95455e06d60ab5b72ced2b5f9f20d4443205afa49fd46356`.

This is an operational grounding/dispatch result, not evidence that the proposed
memory intervention works. The automatic evidence-follow-up policy remains a
distinct design/evaluation task; the coordinator does not hide missing methods
by rewriting an abstract as implementation advice.

## Live evaluation methodology

The execution canary used the existing four-task public fixture, three arms
(`no_skill`, baseline, candidate), two replications and seed 29: 24 separately
executed model calls. Baseline and candidate were the **same** evaluation skill.
This is an A/A integration control, not an intervention-effect study. Gold labels,
condition names and group identifiers were removed from model task inputs.

Plan digest:
`sha256:70fa218d2ba9c878d92d0fe53d0d2812adb5fc64151b536d12d2be7f2c29ce86`.
Comparison digest:
`sha256:572d5c9901d554aea4c68d1af54083efc2f3f884962b183a95807ee6657436f6`.

All 24 calls completed with valid output format. Each arm had eight planned
items, eight usable outputs and four strict-gold passes. The observed usage was
67,820 input tokens and 1,775 output tokens, a $0.187300 conservative usage-price
estimate; summed call latency was 58.556 seconds. There were eight paired task
blocks across three group families, not 24 independent research problems.

The strict failures exposed grader representation limits:

- In insufficient-evidence cases, the model abstained but cited the explicit
  no-outcomes statement; the fixture expected an empty citation set.
- In capture-transfer cases, grounded answers used a scoped paraphrase where
  the fixture required one exact rewrite string.
- Conflict and prompt-injection fixtures passed.

Do not interpret 4/8 as semantic research quality, tune against these examples,
or alter the gold after observing outputs and report an improvement. A new
evaluation epoch needs prespecified semantic acceptance rules, independent
annotation, representative source/task families, leakage controls, paired
analysis at the family level and uncertainty intervals. Completed-plan replay
was checked before later source changes and made no new calls or reservations.
Source drift intentionally invalidates reuse under a different implementation.

## Recovery, operator interface and month simulation

The actual retrieval store and cumulative OpenAI authority were separately
snapshotted and restored into fresh private locations. The retrieval closure
contained 15 files and 1,188,626 bytes; the budget closure contained two files
and 840,335 bytes. Both restored paused. Replayed evidence matched; budget status
and the unresolved effect were preserved. No provider call was needed. These
snapshots predate later funded calls and must not be activated as a fresh
allowance. Encrypt backup storage and transport, fence the original writer and
reconcile post-snapshot effects before activation. See the
[recovery runbook](../../researcher/runbooks/service-recovery.md).

The Control Center passed 54 tests, TypeScript checking, a production build and
a standalone smoke test that fetched nine static assets. A separate real-store
check connected the production UI to the loopback Python API and the funded
authority: completed calls and uncertain-effect status rendered, the operator
credential was absent from HTML, an unauthenticated API request returned 401,
and the authenticated status matched the store. This is private operator access,
not tested public ingress or an authoritative approval interface.

The compressed month simulation ran actual scheduler/store/workflow boundaries
over 30 synthetic completed UTC windows with restarts. It exercised empty X
results, a captured 429, ambiguous provider failure, interruption after a
completed effect, repeated and changed observations, backward-clock rejection,
history bounds and budget exhaustion. It recorded 30 retrieval completions,
one reconciliation probe and one budget-denial probe; 62 effect reservations,
61 completed effects, one unknown, 61 fixture HTTP operations and 62 capture
replays. A separate lifetime-budget drill admitted 15 ten-unit reservations and
denied 15 more across 30 days. Actual provider spend was zero. This verifies
state-machine behavior, not a month of wall-clock availability or research yield.

A separate organization-level rehearsal exercised 30 actual fixture retrieval
jobs with capture replay, daily coordinator reconstruction and duplicate cycles.
Its pipeline outcomes were explicitly injected: ten abstentions, ten
`awaiting_dataset` and ten failures. All terminal outcomes were retained without
duplicate dispatch; the same budget authority remained unchanged and no model
was called. This tests dispatch and recovery, not those outcomes' scientific merit.

## Deployment and next evidence

### Dependency security

AJV remains 8.20.0 with a scoped `fast-uri` 3.1.7 override. The pre-patch
regression reproduced a crafted port changing the parsed hostname; the patched
suite rejects eight malformed port vectors through serialization and
normalization, with three valid-port controls. The installed transitive instance
is checked, not a separately imported substitute. The current
[maintainer advisory](https://github.com/fastify/fast-uri/security/advisories/GHSA-qw65-cvwx-89v3)
identifies 3.1.7 as a fixed version.

The UI keeps Next 16.3.3 and React 19.2.8, pinning `sharp` to compatible 0.35.4
and its matching native package family. This includes libheif 1.23.2, as
specified by the
[maintainer advisory](https://github.com/lovell/sharp/security/advisories/GHSA-rgj7-g3m4-5g8c).
Regression coverage checks the actual instance resolved by Next, native
PNG-to-WebP resizing, and preservation of Next's AVIF decode guard. Neither
audit suppression nor a broad forced dependency upgrade was used. CI now runs
`npm audit --omit=dev` for the UI, schema package and SDK planner, with a
deployment-contract test retaining these gates. A clean audit is a dated
registry result, not proof that dependencies have no undiscovered defects.

### Verification ledger

| Surface | Executed result |
| --- | --- |
| Python service, source/MCP contracts, pipeline and fault suite | 723 tests passed, 79.467 seconds |
| Deployment contracts, launcher, shared-lock and dependency-audit regressions | 14 tests passed |
| Researcher scripts | Final frozen-source rerun: 1,157 tests passed, 194.824 seconds |
| Control Center | 54 tests passed; typecheck, production build, nine-asset standalone smoke and real API/ledger check passed |
| TypeScript schema contract | Typecheck and 25 tests passed, including the URI security regressions |
| Legacy SDK planner contract | Typecheck and 82 tests passed; both deny-SDK dry runs made zero SDK calls |
| Source/citation/profile targeted suites | Included in service/script totals; no additional independent sample claim |
| Strict repository and reference platform compatibility | Passed; 17 skills and four local installation layouts |
| Activation, inventory and schema consistency | 23 activation cases; 344 inventory records; 22 schemas/23 goldens/55 legacy records passed |
| Deterministic benchmark catalog | Three checks passed, zero scenarios executed; not a model effectiveness run |
| Executable adversarial fixtures | Seven contract-mutation scenarios passed; semantic classification was not measured |
| Governance and documentation | 2,142 exhaustive policy decisions passed; public export check passed; 120 local links in nine current documents resolved |
| Python static checks | Service/new reader Ruff check passed with Python 3.11 language target; diff whitespace check passed |
| Dependency resolution | Local installed-package check and combined-lock container `pip check` passed |
| Production Node dependency audits | UI, schema package and SDK planner each reported zero known vulnerabilities |

Intermediate failures were not waived. A renamed CI step violated the existing
lifecycle-order test and was restored without removing the combined dependency
install. A later full-suite run detected concurrent schema dependency changes
through the evaluator's identity boundary. The isolated case, evolution and
experiment suites passed once dependencies were frozen; the final full rerun
above then passed. No identity check was relaxed. The rebuilt UI's real API/store
canary was also rerun after the security upgrade and passed without provider calls.

The public-tree scan of present Git-listed/nonignored candidate files reported
zero findings across 869 files. This is not the committed-release scan: a pre-existing unstaged
deletion of `researcher/reports/benchmark-history.jsonl` remains in the Git index,
where the index-based public validator still identifies it as private/missing.
No files were staged or Git history changed to hide that discrepancy. The exact
approved release must include the intended deletion and all reviewed additions,
then rerun the committed/index-based gate. The readiness declaration remains
non-authoritative and does not mark draft owner specifications accepted.

### Deployment scope

The first deployment topology is one dedicated Linux VM, encrypted local
persistent storage, a read-only approved release, one organization coordinator,
a loopback API and an optional loopback Control Center through SSH. Avoid
multiple schedulers, network-mounted SQLite and parallel budget authorities.
The [deployment contract](../../researcher/service/DEPLOYMENT.md) specifies
identity, dependencies, resource bounds, credentials, recovery and activation.
No cloud resource, recurring research process, GitHub write or deployment was
activated by this exercise. Docker Desktop was started for local packaging tests.
The MCP-enabled runtime image built successfully after the shared-lock fix:

- Official base: `python:3.12.14-slim-bookworm` on Linux ARM64/v8, pinned to
  `sha256:eb5be8e5b4d0a159c237946bbdd06356dda5d19c30fc4f7843e8046d3a590333`.
- Local image: `context-research-runtime:canary-20260929`,
  `sha256:590ddd6343d000c6f1a1611d8ddf4f5239bab1fc2ef2d9a787fb9fd496917f4c`.
- Image size 314,136,527 bytes; successful rebuild 8.116 seconds; offline smoke
  0.759 seconds. Timings describe this cached local machine, not cold-cloud capacity.
- Both locks installed together with hashes. Offline imports and `pip check`
  passed under UID/GID 10001, Python 3.12.14, MCP 1.30.0 and HTTPX 0.28.1.
- Smoke used no network, read-only filesystem, dropped capabilities, no new
  privileges, 256 MiB memory, one CPU and 64 PIDs. No source, configuration,
  budget or credential mounts; no published ports. Test containers auto-removed;
  the image was retained. Existing containers and volumes were unchanged.

The restrictive build context was approximately 62 KB of dependency/build inputs,
not the private checkout. This is a runtime/dependency-image test, not execution
of an approved source release, systemd activation, AMD64 validation, vulnerability
assessment or a hosted soak. Record both source-release and image identities for
the selected deployment; the image does not contain or attest the repository.

The next controlled study should preregister source relevance labels and
downstream memory/retrieval tasks before candidate generation, then compare
unchanged skill versus proposed skill with independent task families. Measure
unsupported-claim rate, abstention utility, qualified-source recall, useful
candidate yield, downstream correctness, latency and total cost. Keep source
discovery, entailment, structural validity and effectiveness as separate outcomes.
Only a reviewed candidate with this evidence should proceed to an authorized
draft PR and human release decision.
