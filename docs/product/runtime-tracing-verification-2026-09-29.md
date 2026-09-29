# SDK worker and tracing verification, 29 September 2026

## Outcome and evidence boundary

This pass improves the unpublished integration checkout. It is not a production
launch, a claim that production callers already use the SDK, or a replacement
for the exact-head PR stack receipts. No OpenAI model calls were made and no new
spending authority was initialized. The only live telemetry effect was one
metadata-only Raindrop upload. No recurring service or deployment was activated.

The source tree contains broader pre-existing work and is not a clean release
commit. Do not publish it wholesale. The clean PR stack and integrated harness
have different source identities and different test counts.

## Failure-derived changes

| Observed failure or ambiguity | Implemented boundary | Verification |
| --- | --- | --- |
| A synthetic upstream could reflect the worker's broker capability in output | Exact capability reflection fails closed in child and outer worker result handling | Real pinned SDK fixture; no reflected capability returned |
| Malformed usage or interrupted streams could be mistaken for successful accounting | Negative/inconsistent usage rejected; missing usage remains unknown; stream error/truncation terminal without transport retry | Real SDK error, missing/invalid usage and timeout fixtures |
| SDK tools needed inspectable lifecycle metadata without exporting content | Closed, paired tool start/completion events with bounded indices, monotonic timestamps and turn identity checks | Worker contract and real patch/tool fixtures |
| Overlapping SDK tools and returned failures need truthful traces | Sibling tool spans; active parent owns journal; failed returned outcomes set span status without inventing exceptions | Projection tests including independent review regressions |
| Telemetry metadata projection could replace worker validation | Guard optional request/result observation; preserve result and exception identity | Malformed request/result and trace-write fault tests |
| A configured Raindrop default project was rejected without actionable diagnostics | Value-free zero-network preflight; explicit default-project opt-in, no blank fallback | Unit tests and one live two-span ACK |
| `export` without `--live` could open state; inspection could create missing state | Approval before state access; existing-only validated journal; read-only inspection; no file/key/schema repair | Nine new no-repair regressions, byte/mode/mtime preservation |
| A timeout test assumed a macOS-specific Python location | Use the executing interpreter, not a hardcoded executable path | Linux rerun removed this error |

SDK telemetry includes only closed kinds, statuses, counts, durations and keyed
references. It does not contain prompts, reasoning, tool arguments/results,
paths, raw thread/turn identities or credentials. Usage is emitted once per
fresh-thread turn, not summed again on every tool. An incomplete observation does
not mean a remote operation was cancelled. A completed model response does not
erase a failed tool outcome. SDK-emitted events do not cover all denied attempts.

These semantics follow the [official app-server event model](https://learn.chatgpt.com/docs/app-server).
The [service tracing runbook](../../researcher/service/TRACING.md) documents the
implemented API and operating commands.

## Executed local verification

Counts below describe overlapping suites and must not be summed as unique tests
or independent scientific observations.

| Scope | Result | Interpretation |
| --- | --- | --- |
| Final integrated service suite with real SDK fixtures enabled | 905 passed, 0 errors/failures/skips; 122.169 seconds | Local service correctness and fault handling, not live-model quality |
| Final release-scenario catalog | 443 passed across all 11 groups, no skips | Managed lifecycle, recovery, budget uncertainty, grounding, checkpoints, daily restarts, frozen candidates, publication/operator boundaries and traces |
| Integrated repository-script suite | 1,223 passed; 194.270 seconds | Broader unpublished script source; this ran before the final no-repair service change |
| Focused SDK worker and projection pass | 39 passed; 20.093 seconds | Real pinned SDK processes against loopback synthetic responses plus unit contracts |
| Expanded tracing review pass | 135 passed; 3.487 seconds, no skips | Includes the nine no-repair regressions and real SDK projection |
| Structural checks | Strict validation: 0 errors/warnings; reference compatibility: 17 skills, 4 layouts; inventory check passed | Packaging/inventory, not operational launch acceptance |

The final catalog's [machine-readable receipt](verification-2026-09-29/release-scenarios.json)
binds the tested implementation and source closure. Its source identity is not
just Git HEAD: the integration checkout is dirty and the report was added after
execution. Compressed daily/month fixtures are not elapsed production uptime.

The raw-index public-repository check on the dirty integration checkout still
reports four pre-existing findings: a tracked-but-deleted private benchmark
history entry and three tracked missing paths, including that same entry. The
clean stacked PR checkouts are assessed separately. No index rewrite was used to
hide this distinction.

## Raindrop live ingress proof

The explicit private environment file contained the write credential and a
configured existing default project. Preflight first refused without the new
opt-in and made no request. The approved opt-in then sent **one 1,193-byte batch
containing two synthetic parent/child spans**. The exporter obtained HTTP 200 and
a valid full OTLP acknowledgement: two spans accepted, zero rejected, no warning.
Whole CLI elapsed time was approximately 0.473 seconds, not a provider latency
benchmark. A guarded second export returned empty without invoking transport.

The [safe canary receipt](verification-2026-09-29/raindrop-canary.json) contains no
credential values, prompts or private locators. The canary preceded the final
no-repair change; the latter was verified offline without another live upload.
This proves scoped ingress acceptance, not dashboard readback, query/MCP access,
retention, project visibility or rotation of a previously exposed credential.

Provider configuration was checked against [Raindrop OTLP documentation](https://www.raindrop.ai/docs/sdk/opentelemetry/)
and [project semantics](https://www.raindrop.ai/docs/platform/projects/) using
Parallel URL extraction. No global installer, daemon or ambient MCP registration
was introduced.

## Linux runtime experiment: not a passing release gate

The eight-package SDK closure was downloaded as Linux aarch64/CPython 3.12 wheels
and installed with exact versions, wheel hashes, `--no-index`, `--require-hashes`
and `--only-binary=:all:`. The SDK and bundled CLI were both 0.159.0.

The disposable test container used Python 3.12.14, UID/GID 10001, a read-only
root filesystem, no external network, all capabilities dropped,
`no-new-privileges`, bounded CPU/memory/processes and private tmpfs workspaces.
No host directories, Docker socket, provider keys or production state were mounted.
The immutable base image was
`sha256:38f3946ce5f963777b8f7f65ed65f1e1b78e226a198298dfca731e6e9d1c639b`.
The existing production dependency image was not modified.
The [reproduction recipe, wheel lock and non-skipping launcher](verification-2026-09-29/linux-sdk-proof.md)
preserve the diagnostic without distributing runtime binaries or credentials.

The first run exposed two failures. The interpreter-path test was fixed. The
second run executed all 25 worker tests with no skips: **24 passed and the
workspace-write patch test failed**. Read-only patch denial, protocol faults,
usage handling and other tests passed. Moving the fixture from `/tmp` to a
dedicated `/workspace` tmpfs did not remove the write failure. Direct Python
writes in that workspace succeeded, while SDK file-change events reported failure.

The image has no external Bubblewrap and `unshare --user --map-root-user` is denied.
The SDK reports fallback to its bundled Bubblewrap. A separate fixed local
`codex sandbox linux --help` probe exits 1 because Bubblewrap cannot create a new
namespace, before any guarded child executes. This establishes an unavailable
Linux sandbox prerequisite. The exact source of the denial, such as the container
seccomp profile versus host namespace restrictions, was not independently isolated.
Follow the [official Linux sandbox prerequisites](https://learn.chatgpt.com/docs/sandboxing)
and [Docker namespace constraints](https://learn.chatgpt.com/docs/agent-approvals-security).
No capabilities, seccomp rules or host namespace settings were relaxed to make
the experiment green. This image is not accepted for SDK workspace-write use.
The next deployment experiment needs a supported isolated Linux runner/VM with
namespace capability verified before accepting any paid work. The test remains
a failure; it was not weakened to accept a denied write as a successful write.

## What is not shipped by this pass

The clean published stack currently has only the small managed transport module,
not the integrated tracing and native research service dependency closure. The
worker can be reviewed independently; copying the entire native service merely
to satisfy tracing imports would be an unjustified release expansion.

Before cloud launch, the [SDK migration contracts](codex-sdk-runtime-migration.md)
still require a per-request gateway using the existing cumulative authority,
production caller migration, SDK-bound candidate/evaluation receipts, complete
restart/recovery, operator controls and a Linux deployment profile with tested
tool isolation. Held-out effectiveness experiments and a sustained production
canary remain separate from these deterministic proofs. There is no new
scientific quality, speedup or cost-reduction claim in this report.
