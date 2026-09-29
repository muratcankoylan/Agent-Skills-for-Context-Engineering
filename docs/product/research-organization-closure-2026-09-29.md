# Research organization: implementation and execution evidence

29 September 2026. Unpublished integration work, not a release or cloud activation.
This report supersedes finding-only status for the changes below. It preserves
failed experiments and distinguishes runtime correctness from research quality.

## What changed

| Finding | Implemented correction | Verification |
| --- | --- | --- |
| A private SDK HOME did not isolate administrator/system configuration | Explicit configuration boundary before SDK startup; deny ambient notification/export channels; no host policy overrides | 79 focused tests; eight hardened Linux contamination/clean-start probes across ARM64 and AMD64 |
| Usage details were lost or unknown was conflated with zero | Versioned cache-read/cache-write/reasoning counters; historical receipt compatibility; strict usage validation through receipt, trace and recovery | Focused runtime/receipt/recovery tests plus the complete suite |
| Later studies did not receive verified prior research | Frozen, replay-verified researcher archive, at most five entries / 32 KiB; explicit omissions and no evaluator-answer leakage | Actual-SDK three-day scenario and adversarial learning tests |
| Repeated candidates could repeat an already-completed evaluation | Exact frozen baseline/corpus/path/bytes plus matching completed evaluation-plan digest | Day two avoided 12 evaluation turns; changed dataset/seed and previously unevaluated candidates still execute |
| Valid OpenAI SSE metadata was rejected by the durable integer-only JSON decoder | Separate bounded external JSON decoder accepts finite metadata floats; usage and durable receipt contracts remain strict | Reproduction, 174 focused tests with actual SDK frames, independent adversarial review, four successful live turns |
| Local arXiv spacing could become a preventable failed discovery effect | One bounded three-second pre-dispatch wait; collector is outside the retry catch | Tests prove no HTTP retry, including collector timeout and collector-raised spacing error; final live discovery completed |
| One-host selection left a configured primary-read slot unused | Explicit diversity-first then same-host-fill profile, maximum two predetermined URLs | 97 focused tests; historical default selections unchanged; final live study retained two cards rather than one |
| Failure receipts returned normally and produced successful root spans | Map pipeline/Organization outcomes into status and metadata; instrument foreground cycles once | Three focused tests, independent seven-outcome review, final live failed receipt emitted error spans |
| Research and trace outputs were difficult to inspect | Private digest-checked JSON/HTML dossier and Linux exporter service/timer templates | 15 dossier tests, trace/deployment tests, generated 12-pipeline dossier; services not activated |
| Linux verifier hid safe child failure codes behind a generic unavailable result | Versioned v3 diagnostic field, closed four-code allowlist; aggregate failure and limits unchanged | 47 focused tests, independent review, complete suite rerun |

The [current architecture](research-organization-architecture.md) describes the
module boundaries. The [implementation plan](research-organization-implementation-plan-2026-09-29.md)
records remaining scientific and deployment gates. Official Codex documentation
informed configuration isolation, SDK lifecycle, and the separation of tool-free
execution from native-tool sandbox support; those contracts are linked in the architecture.

## Executed verification

- Complete final service suite: **1,081 executed, zero failures, errors, skips, expected
  failures or unexpected successes; 238.093 seconds**. No provider credentials.
  Actual SDK subprocess tests were explicitly enabled. The parent socket guard
  allowed numeric loopback only; this guard is not a general OS sandbox.
- Separate retained fault run: **207 tests across four scenario groups**, all
  passing with zero skips. This overlaps the complete suite, not 207 additional
  unique cases. Daily restart group: 25; capture/grounding: 37;
  budget/uncertainty: 23; trace isolation: 122.
- The daily group includes compressed 30-day admission/restart exercises with
  captured fixture responses and injected outcomes. It is not 30 days of uptime.
- Repository validator: zero errors/warnings, 17 skills. Platform compatibility:
  17 skills across four local install layouts, reference validator required.
- Changed Python scope passed Ruff; `git diff --check` passed.
- First-epoch suite also passed 1,056 tests. That earlier pass did not establish
  live interoperability: the live experiment below found additional issues,
  which were fixed and reverified in a 1,077-test run. A subsequent deployment
  diagnostic correction added four tests; the final 1,081-test run also passed.

Final implementation digest:
`sha256:9118e32f19fea540532a9f01fdc1bb648c76e6455ac52ec8a3bcf813c6aa3ea1`.
The implementation remained unchanged during the full suite and final live run.
Repository HEAD was `c6cd52017b247804373339e1c3c103d42554b0a1`; HEAD alone does
not identify the dirty integration worktree. Final documentation edits occurred
after the executable source freeze.

### Hardened Linux gate

The ARM64 image passed **31/31 mandatory actual-SDK tests, zero skips**, covering
campaign (25), pipeline (2), Organization (3), and the three-day learning scenario
(1). Dependency/runtime identity 0.159.0 and source stability passed. Image:
`sha256:cca85eb9853e38a3007394a004e8fdbf95036c5630d3fb2787a46abb5f70e748`.

The emulated AMD64 image passed startup/version checks but did not pass the complete
gate. Its initial receipt reported `TOOL_FREE_TESTS_UNAVAILABLE`, motivating the
diagnostic correction above. One same-limit diagnostic confirmed `TIMEOUT` at
300,011 ms; the result remained unsuccessful. No limit was increased. Image:
`sha256:7ca2e8b944ab8d9fcf18b97df713f7be5dd4497d970acb3738a674bf6bd8e545`.
This is not evidence of native AMD64 success or failure. Both runs used the same
non-root, network-disabled, read-only, no-capabilities/no-new-privileges profile,
2 GiB memory, two CPU quota, 256 PID cap and the unchanged 300-second test deadline.
Neither used provider credentials or relaxed native-tool sandboxing.

These Linux runs used a frozen 933-file snapshot with release-source digest
`sha256:cca593e9bd7882cf08d937ed03cca470d5de824dc260812c67cda4b46c674582`.
Their v2 receipts predate the diagnostic-only v3 wrapper change and subsequent
documentation updates. The final local suite includes that correction. Native
Linux tool execution remains a separate, previously unsuccessful namespace gate.

## Actual SDK, three simulated daily cycles

This uses actual pinned SDK 0.159.0 processes, real Stores, primary-capture replay,
Organization dispatch, candidate freezing, validators and evaluation wiring.
Source and model responses are synthetic. Its separate fixture allowance is not
the real $100 authority. Both the first and final executable versions were run,
and both records were retained.

| Day | Researcher archive entries | SDK turns | Outcome | Same-slot repeat admission |
| --- | ---: | ---: | --- | ---: |
| 1 | 0 | 15: three roles plus twelve evaluations | Evaluated, not accepted | 0 |
| 2 | 1 | 3 | Exact duplicate; twelve repeat evaluations avoided | 0 |
| 3 | 2 | 2 | Scripted abstention | 0 |

Each run made three fixture discovery and three fixture primary reads, twenty
SDK turns, and zero external model requests. The candidate was a deliberately
synthetic evidence-ID instruction, never an accepted skill update. The day-three
response was scripted: it does not show that memory caused better reasoning.
The helper recreates the Organization object daily but repeats the same-slot
cycle on that object; process/Store restart recovery is separate test evidence.
Baseline changes, corrupt memory, changed evaluation contracts, source mutation,
prompt injection, outages and pause are covered separately by named regression
modules, not by pretending this three-day helper exercises all of them.

## Live external research: failed experiment, fixes, repeated experiment

Three retrospective daily windows ending September 27, 28 and 29 were fetched
on September 29. arXiv/feed adapters do not all apply those windows, so these are
three scenarios, not measurements of three elapsed production days.

Each final scenario used arXiv, Hacker News and Hugging Face discovery, at most
two selected primary HTML reads, then fresh tool-free SDK researcher/critic roles
for eligible evidence packets.
Model: `gpt-6-sol`, default service tier, concurrency one. Dataset, publication,
notifications and model-selected tools were disabled. Maximum plan: nine role
attempts and $3.50 additional conservative reservation, against the existing
cumulative authority. No allowance was reset.

| Query / selected skill | Earlier live outcome | Final live outcome |
| --- | --- | --- |
| `agent memory` / memory-systems | One primary card; SDK response rejected; uncertain attempt retained | Two primary cards; researcher and critic completed; critic abstained from a skill proposal |
| `context engineering` / context-fundamentals | No primary card; handoff refused | Two reads attempted: one captured HTTP 404, one wire-size refusal at 1.5 MB; zero model calls; handoff refused |
| `TRACE` / self-improvement-loops | Local arXiv spacing rejection; incomplete handoff | Discovery completed, two primary cards, researcher and critic completed; critic abstained |

The first live provider wire was not retained. The finite-metadata-float defect
was independently reproduced against official-shaped response envelopes, and
the repaired gateway completed the later live turns. That is strong supporting
evidence, not proof of the exact unretained earlier response bytes.

Final execution: 15 source-request reservations, four completed live model turns,
92,166 input tokens and 1,900 output tokens. Individual turn wall times were
17.998, 11.996, 20.110 and 8.174 seconds; four samples do not establish a latency
distribution. Total source workflow time was approximately 26.894 seconds across
three sequential jobs, including spacing waits. Nested trace durations overlap.

### Actual research output

The memory study proposed testing whether promotion of memories should require
recorded use and successful outcomes across distinct tasks. Its paired plan holds
model, retrieval budget, verifier and resident-context cap constant, with separate
ablations for adoption gating, cross-task repetition and resident promotion.
The critic withheld an edit because the paper's domain-specific results and
partial methods do not establish transfer to general cross-session coding agents.

The TRACE study proposed execution-segment token forecasting to schedule or defer
evaluation runs, while leaving the evaluator, acceptance rule and hard spending
limit outside the editable harness. The critic identified missing full methods,
untested transfer from offline replay, and an unquantified latency threshold.
Neither proposed experiment was executed as a scientific effectiveness study.

These are useful hypotheses and explicit next experiments, not successful skill
improvements. Full role outputs, source IDs, exact grounding, phase receipts and
both failed and successful runtime attempts are retained in the private dossier.
The live studies consumed zero prior archive entries: the TRACE study omitted
one incompatible study and one without research. The synthetic SDK scenario
demonstrates archive wiring; this live run does not demonstrate learning benefit.

## Live connectors and MCP

Eleven retained HTTP diagnostics returned successful validated responses:

| Surface | Narrow measured result |
| --- | --- |
| OpenAI | Authenticated model listing, 141 returned IDs; not inference evidence by itself |
| GitHub | Authenticated identity and repository read; no PR creation or push |
| Firecrawl | Credit-availability contract, one research-paper abstract, one 2,372-byte scrape |
| OpenAlex | Authenticated budget contract; ten records, nine abstracts; capture replay |
| Parallel | One search result and one extraction result |
| X | Ten posts with IDs, dates, authors, conversations, entities and metrics; capture replay |

The separately registered Parallel MCP read completed one tool call with 1,935
output bytes. Its twelve-request value is a protocol ceiling, not a measured
request count. Diagnostic cost reservations were $0.063 for HTTP checks and
$0.010 for the MCP check; neither is a provider invoice. Parallel/Firecrawl
diagnostics do not make them active Organization daily source lanes.

## Spending and traces

After both live experiments, the original OpenAI authority records:

- Authorized ceiling: $100.000000.
- Cumulative conservative reservations: **$5.271875**; remaining local allowance:
  **$94.728125**. This is not an account balance.
- Forty cumulative attempts, 38 completed, two unresolved. One unresolved attempt
  predates this exercise; the other is the retained first-experiment failure.
  The final live experiment added no unresolved attempt.
- Observed completed-call upper-cost estimate: $0.933216 cumulative, including
  $0.249416 for the four final live turns. Unknown attempts remain reserved;
  there are no refunds and no invoice verification.

The final fixture journal contains 89 spans. The final live source journal has
51 spans; the original authority journal has 56 spans across both live experiments.
All were finished at inspection. Failed context handoff now emits error-status
pipeline and cycle spans; legitimate abstentions retain successful execution
status with explicit abstention metadata. Historical false-green spans were not
rewritten to manufacture a clean history.

**Current Raindrop upload has not occurred.** The environment selects `default`;
the safety review required explicit approval of that destination and the proposed
operation/latency/usage/status/opaque-ID payload. A question was presented and no
approval was received at report time. Nothing was retried around that decision.
Local journals and the exporter are working; no current ingestion ACK or dashboard
readback is claimed. The previous synthetic ingress canary is historical evidence.

## Release interpretation

Implemented: the listed corrections, compatible historical replay, current
architecture/runbooks, visible private outputs and bounded exporter templates.
Measured: deterministic faults, actual SDK integration, narrow connector access,
and four successful real research turns with truthful abstention.

Not established: accepted scientific improvement, full-paper coverage for every
source, month-long reliability, automatic PR publication, or cloud activation.
The next research gate is full-methods evidence plus independently labeled paired
tasks. The next deployment gate is execution on the selected host with private
operator access, restore/reconciliation and explicitly approved telemetry. No
GitHub push, merge, credential rotation or service activation occurred in this work.
