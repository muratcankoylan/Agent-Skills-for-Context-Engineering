# Tracing and engineering verification

Date: 2026-09-29. Scope: local implementation candidate, not a deployed release.

## Implemented changes

1. **Private operation journal.** Correlated spans cover organization, pipeline
   phases, research/evaluation roles, model calls, effects, source reads/replay,
   MCP boundaries, managed lifecycle/HTTP and publication. Closed attribute
   validation excludes payloads and secrets.
2. **Durable telemetry delivery.** Fixed-origin Raindrop OTLP/HTTP, explicit
   project/key, isolated deadline, bounded acknowledgement parsing, per-span
   delivery intent and atomic full acknowledgement. Partial/unknown outcomes
   never automatically retransmit. No installer, daemon or automatic upload.
3. **Managed snapshot projection.** Existing-session trace GET, bounded pages,
   graph/identity/time/usage checks and content-free unclassified projection.
   No invented inference classification, streaming or billing claim.
4. **Failure noninterference.** Trace initialization, capacity, write, clock and
   exception-inspection failures cannot mask the original result or grant another
   effect. Recovery excludes exactly the validated top-level telemetry directory.
5. **Installer safety.** No overwrite/deletion of existing targets; symlink,
   traversal, source-overlap and broad-target rejection; literal portable paths
   and concurrent installs tested.
6. **Evaluation-example safety.** Durable local attempt slots, explicit shared
   runtime, no ambient live keys or SDK retries, per-pass pairwise admission,
   sequential rubric calls, stricter output validation and offline default tests.

The [trace runbook](../../researcher/service/TRACING.md) defines coverage,
retention and commands. The [research note](raindrop-integration-research-2026-09-29.md)
explains direct OTLP/HTTP versus a machine-level control-plane installation.

## Verification actually executed

Counts overlap. Do not add them into a count of independent scenarios.

| Check | Observed result | Scope |
| --- | --- | --- |
| Full Python service suite, frozen source | 850 passed in 90.158 s | Includes 105 dedicated tracing/export/projection/integration tests |
| Full repository-script suite | 1,175 passed in 203.870 s | Includes 18 new installer cases |
| Release scenario catalog | 427 tests across 11 groups passed | Credential-free fault/restart/recovery, injected providers |
| Deployment/launcher/workflow tests | 29 passed | Local, not hosted GitHub execution |
| Independent integration selection | 173 passed in 40.707 s | Current-code insertion review, not pristine Git diff |
| Evaluation example | 40 passed; clean offline install, build, source/test/example typecheck and ESLint passed | 12 cooperating processes admitted exactly 3 effects under a 3-attempt cap |
| Linux installer fixtures | 18 passed in 0.307 s | No network, two source files streamed into ephemeral tmpfs |
| Linux AMD64 trace/export/projection/CLI | 101 passed in 0.729 s | Existing AMD64 image under local ARM64 emulation; no network/credentials, explicit public file list streamed into tmpfs |
| Platform packaging | 17 skills, four local layouts passed | Required upstream reference validator via existing venv PATH |
| Strict repo / skill health / activation | Passed; 23 activation cases | Deterministic, not a new model effectiveness study |
| Ruff / whitespace | Passed | Service, installer test and changed source |

An initial full-service pass overlapped source/inventory edits and failed one
source-sensitive pipeline case before its expected evaluation interrupt.
The isolated case then passed; the entire frozen-source suite was rerun and
passed 850/850. Final evidence uses the stable rerun. The platform check first
lacked the existing venv executable on PATH; correcting PATH passed without
installation.

Host-bind Docker attempts stalled before creating a container; their client
processes were stopped. A no-download image-start check passed. The successful
Linux installer run streamed only two non-secret source files into an ephemeral,
network-disabled container. No user installation or existing directory changed.

The Stage-0 benchmark command also passed its executable checks and catalog
validation, but executed zero scientific scenarios. That command is not model
quality evidence. The separate release catalog executed the 427 tests above.

## Local overhead experiment

The retained [aggregate measurement](evidence/tracing-overhead-2026-09-29.json)
binds its [reproduction script](evidence/tracing-overhead-repro-2026-09-29.py) and
measured source by SHA-256.

Method: one fresh private journal; five batches of 100 completed empty spans;
alternating baseline/traced order; no warmup; initialization excluded;
`perf_counter_ns`; nearest-rank p95; SQLite DELETE journal with
`synchronous=FULL`. CPython 3.11.0, SQLite 3.38.4, macOS 26.6.1 arm64.

The retained run observed median **0.860 ms**, p95 **1.074 ms** and maximum
**5.498 ms** per complete span. Five hundred spans occupied **126,976 database
bytes**, with zero unfinished spans/write failures. Baseline median/p95 were
42/84 ns, near timer resolution; slowdown ratios would be misleading. Only
aggregate and batch statistics, not individual samples, were retained.

A preceding exploratory run observed median 1.184 ms and p95 3.324 ms on the
same unchanged code. This is uncontrolled host/filesystem variability, not an
optimization claim or statistical effect. Neither run measures contention, real
provider latency, production throughput or power-loss durability.

A real child process completed one span then called `os._exit(73)` inside
another. Reopening preserved `[ok, running]`; unfinished end/duration stayed
null; actual CLI preview included only the completed span. No fabricated
completion or automatic upload occurred.

Reproduce from the checkout:

```sh
.venv/bin/python -B docs/product/evidence/tracing-overhead-repro-2026-09-29.py
```

## Authority, privacy and release status

- No paid model calls or new OpenAI spend occurred in this iteration.
- No Raindrop upload, global installer, cloud daemon or MCP registration ran.
- The chat-pasted key was not used and must be rotated. Blank
  `RAINDROP_WRITE_KEY` and `RAINDROP_PROJECT_ID` fields were added to the
  ignored private environment file and public empty template.
- No PR push/update/approval/merge, repository protection change or cloud
  activation occurred. Existing local changes were preserved.
- The evaluation example's inherited dependency audit still reports seven
  affected packages, including one high severity finding. Its SDK v4 line is
  unsupported. Attempt/retry bugs are fixed; dependency migration/security
  clearance is not claimed. This example is excluded from the production runtime.
- Shared remote admission/CAS authority, hosted deployment rehearsal,
  independently frozen evaluation data, repository protection changes and
  rotated-key cloud acceptance remain explicit launch work in the
  [deployment plan](github-release-plan-2026-09-29.md).

Reservation metadata on nested/replayed spans must not be summed as actual calls
or billed cost. Traces explain execution; they do not replace budget authority,
source evidence, evaluation receipts or human publication decisions.
