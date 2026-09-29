# Codex SDK migration: implementation and verification

Date: 2026-09-29. Scope: unpublished local integration, not production activation,
specification acceptance or a scientific effectiveness result. Machine-readable
counts, source identities and both Linux receipts are in the
[verification record](codex-sdk-migration-verification-2026-09-29.json).

## Outcome

The supported initial research/evaluation path now executes through the official
Python Codex SDK and matching CLI runtime, both pinned to `0.159.0`. It is not a
Codex desktop automation. Scheduled and manual Organization callers reach actual
SDK threads through `CodexCampaign`, a narrow budget gateway and the existing
cumulative authority. The supported profile is tool-free roles with deterministic
external retrieval. No provider key is passed to SDK workers.

This iteration made **zero live provider/model calls**. Its measured outcomes are
execution, security-boundary and recovery tests against synthetic upstreams, not
model quality, retrieval relevance or a month of production operation. Historical
native/managed results retain their original runtime attribution.

## Implemented boundaries

| Component | Change and invariant |
| --- | --- |
| SDK worker | Fresh private home/workspace and thread per role/task; pinned runtime identity; denial callbacks; strict output/schema and lifecycle validation; parent-side known-key reflection checks |
| Gateway | Exactly one admitted request per turn; validates the observed SDK envelope; removes ambient tools/paths; bounds context/output; reserves before dispatch; buffers and validates complete SSE; commits before delivery |
| Campaign and pipeline | Researcher, critic, editor and independent evaluation tasks use SDK calls; original budget retained; immutable task/runtime/source identity; output origins reconstructed from committed SDK/gateway receipts |
| Evaluation | Gold-free task projection; separate SDK thread IDs; all planned failures remain in denominators; failed evaluation disposition stable under repeated inspection and verification |
| Recovery | Strict SDK job/receipt closure in the existing backup authority; crash-cut coverage; completed receipt replay without a key; started turns without final receipts quarantined, never automatically resubmitted |
| Operator API | Authenticated `/v1/runtime` reports thread/turn identities, receipt availability and unresolved counts without content; pause controls new admission, not asserted remote cancellation |
| Runtime cutover | New built-in native and managed model submission paths refuse execution; old receipt inspection/replay with matching identities and managed watch/cancel remain compatibility paths |
| Deployment | Separate locked SDK venv; ARM64/AMD64 wheel hashes; runtime lock binding; SDK startup before Organization cycle/serve; inspection/API remain usable for diagnosis |
| GitHub rehearsal | Secret-free CI step runs the real SDK integration gate in a non-root, network-disabled, read-only container and requires zero skips |
| Plans/documentation | README, migration/status documents and runbooks updated; SPEC-014/025 and source-bound machine plan aligned while preserving draft revision 1 and unchecked acceptance criteria |

The shared deterministic research, grounding, freezing and scoring logic is reused.
The gateway does not implement an agent loop. The existing SDK owns app-server,
thread and turn execution. New SDK receipt schemas coexist with, rather than
reinterpret, historical native/managed records.

## Failure-derived fixes

1. The pinned SDK still advertised tools for the measured models despite feature
   flags. The gateway strips both ordinary tools and the observed `gpt-6-sol`
   embedded tool declarations, then rejects any tool-bearing response before SDK
   delivery. Feature configuration alone is not treated as a tool-free guarantee.
2. A reused gateway could encounter a completed reservation. It now refuses
   dispatch before transport, preserving the original receipt and preventing a
   duplicate paid effect.
3. Credentials could be present in task bookkeeping before the old scan point.
   The complete manifest is now checked before admission or durable progress.
4. Truncated/ambiguous SSE and HTTP framing are rejected. A completed provider
   receipt survives local acknowledgement failure; unknown usage retains its
   reservation instead of becoming zero.
5. Repeated inspection of a failed SDK evaluation changed its failure code and
   broke origin verification. The recorded disposition is now preserved across
   repeated evaluation and credential-free verification.
6. A reviewed read-only checkout owned by another UID failed candidate inventory
   reads. The failure was reproduced in Linux. Git now trusts only the exact
   supplied checkout, disables hooks/fsmonitor and ignores ambient configuration.
   A second run with runtime UID 10001 and Git ownership UID 10002 passed.

## Executed verification

Counts overlap and must not be summed as independent tests or experiments.

| Check | Observed result | Evidence scope |
| --- | --- | --- |
| Full service suite, real SDK opt-in | 997 passed; zero skips; 181.015 seconds | Offline contracts, real SDK fixture processes, recovery and adversarial paths |
| Complete release-scenario catalog | 11 groups, 450 tests; zero failures/errors/skips | Credential-free lifecycle, budget, grounding, restart, freeze, API, publication and tracing regressions |
| Focused SDK worker/gateway/tracing/preflight/recovery | 119 passed; zero skips; 31.875 seconds | Real runtime where explicitly selected; synthetic upstreams |
| Deployment test discovery | 36 passed; zero skips | Launcher, locks, arguments and workflow contracts |
| Final Linux ARM64, MCP dependency profile off | 22 passed; zero skips | Real SDK campaign, pipeline and Organization under hardened constraints |
| Final Linux AMD64, MCP dependency profile on | 22 passed; zero skips | Same gate under CPU emulation on the ARM64 host; not native AMD64 performance evidence |
| Repository/platform validation | Zero errors/warnings; 17 skills; four install layouts | Structural/packaging compatibility, not skill effectiveness |
| Inventory/spec plan | Current inventory; no plan findings | Source-bound planning, not acceptance |
| Skill health/activation | No flagged skills; 23 activation cases passed | Deterministic existing corpus checks, not a new quality gain |
| Benchmark catalog check | Three checks passed; zero scenarios executed | Catalog validation only, not a benchmark run |

The Linux integration gate executes research/critic/editor, exact candidate
freeze and structural validation, twelve separate SDK evaluation threads,
scheduled/manual dispatch, pause and credential-free restart. Its fixtures do not
substitute a fake SDK or bypass the candidate validators. Both final runs used
network `none`, read-only root and repository, all capabilities dropped,
no-new-privileges, two CPUs, 2 GiB memory, 256 PID ceiling and private tmpfs.
Installed MCP dependencies do not grant model access to MCP tools.

Source before this report/documentation links: integration HEAD
`c6cd52017b247804373339e1c3c103d42554b0a1`, with unpublished changes. The exact
916-file content digest was
`sha256:bf14dd06b83e757f51319f0add3e34ac60d07c4ddaa2d8fa9a72846bf2dd5e91`.
Release tests and both final Linux gates verified that their source was unchanged.
The JSON record also binds the implementation and 214-file scenario closure.
HEAD alone does not identify these dirty integration bytes.

Earlier unsuccessful checks are not relabeled as passes: one Linux source copy
contained macOS copyfile metadata and failed path validation; one pipeline replay
ran during source edits and correctly rejected changed inputs; an earlier test
interpreter lacked the reference validator. Final tests used a frozen, checked
source snapshot and the actual application validation environment.

## Explicit release limits

- **Native Linux tools are not supported by this evidence.** The separate native
  preflight reports namespace denial under the hardened container profile. No
  privileges, isolation checks or assertions were weakened. Tool-free execution
  passed independently; it does not imply shell/file-change support.
- There was no hosted GitHub Actions run, image push, PR publication, merge,
  scheduler activation or billable cloud deployment in this iteration.
- The full draft work-order/grant/lease architecture, operator UI reconciliation,
  autonomous tool/MCP permissions and automatic skill acceptance/publication are
  not completed merely by adding an SDK executor.
- No live SDK quality/effectiveness benchmark, invoice reconciliation or production
  soak was run. A future paid experiment needs an explicit scope, reviewed pricing,
  remaining allowance and a preregistered evaluation plan. Budgets are not reset.
- The private integration's public-index validator still reports four pre-existing
  findings: a tracked private `researcher/reports/benchmark-history.jsonl` entry,
  and missing tracked entries for that file plus the old judge-example
  `tests/setup.ts` and `tests/skills.test.ts`. Their working-tree deletions predate
  this SDK change. Unrelated changes were neither staged nor reverted to conceal
  this packaging condition. A selected clean release must pass that validator.
- Same-UID process separation is not host-file containment, conservative cost
  reservations are not invoices, and pause/process exit is not remote cancellation.

## Reproduction and next release step

Use the [SDK runbook](../../researcher/service/CODEX_SDK.md) for exact commands,
credentials and operator behavior, and the
[Linux runtime guide](../../researcher/service/deploy/CODEX_RUNTIME.md) for locked
installation and the mandatory zero-skip integration gate. Run the full service
suite with `CODEX_WORKER_TEST_PYTHON` explicitly set to the pinned SDK interpreter;
the main interpreter must include the reference `agentskills` validator. Do not
load production credentials for fixture tests or edit source during replay tests.

The next release step is a selected, clean SDK implementation stack with exact-head
CI and the existing review controls, followed by a separately authorized bounded
live canary. The previously published author-owned PR stack is not automatically
updated by this local integration. Nothing in this report changes merge authority.
