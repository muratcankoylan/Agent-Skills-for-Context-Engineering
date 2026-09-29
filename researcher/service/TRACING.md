# Trace architecture and operator runbook

Status: explicit operational Events and linked spans verified in the authenticated
Production dashboard, 2026-09-29. A new real research cycle appears with 37 spans,
including source retrieval, primary reading, action selection and five completed
SDK turns. See the [UI verification and release record](../../docs/product/raindrop-ui-release-verification-2026-09-29.md).

Correction to earlier evidence: 246 spans received transport acknowledgements,
but the configured project still showed zero Events. Keep those historical
receipts as transport evidence, not dashboard visibility or persistence evidence.
No global installer or local collector is required. Inspect delivery receipts.

The retained initial backlog contributed 144 spans. Automatic post-cycle delivery
then acknowledged 37 spans from a completed live study, 30 from a transport-failed
study and 35 from a contract-rejected study, with zero rejections. See the
[dated verification report](../../docs/product/agentic-raindrop-verification-2026-09-29.md)
for totals and experiment boundaries.

## Foreground Organization delivery

The repository coordinator now supports `--trace-export` on explicit live `cycle`
and `serve` commands. It preflights the explicit Raindrop configuration before
opening state or admitting work, then ticks the existing research and source
journals after each cycle span closes. See [Organization](ORGANIZATION.md) for the
complete invocation. `default` requires `--trace-allow-default-project` as well.

Each journal has a process-local 60-second cadence and one batch of at most 100
spans per due tick. A batch uses at most two isolated ten-second requests: create
operational Events for completed roots, persist that phase receipt, then send
linked OTLP. Two journals therefore permit at most four requests and forty seconds
of transport deadlines after a cycle, excluding local bookkeeping. It is not an in-turn
stream, background thread, installed scheduler or raw log uploader. Unknown,
partial, rejected and local delivery failures halt that pump for inspection;
durable claims survive restart and prevent automatic resending. A failed progress
output sink cannot change the research outcome. Export credentials stay in the
trusted coordinator and never enter the SDK worker or model prompts.

## Optional deployment cadence

The reviewed `deploy/context-research-traces.service` and `.timer` templates send
one batch of at most 100 completed pending spans from the existing authority journal
per activation, approximately once per minute. They do not admit model work or
retry previously uncertain export claims. They are **not installed or enabled**
by the repository. Enable only after the exact-host canary and operator approval.

Provision a dedicated, service-owned `0600` literal env file at
`/etc/context-research/trace-literals.env` containing only `RAINDROP_WRITE_KEY` and
an explicit non-default `RAINDROP_PROJECT_ID`. Do not reuse provider secrets.
Keep source and environments read-only. The unit can write only the telemetry
subdirectory, not budget/effect state. Its direct diagnostic entrypoint does not
perform the agent release launcher's attestation checks; provisioning must pin
the reviewed release. If using the default project, explicitly review and add
`--allow-default-project`; there is no implicit fallback.

Run `systemd-analyze verify` on the selected Linux host before installation.
Inspect `trace_cli status` for backlog and `deliveries` for unknown/partial
delivery. This capacity is at most 100 spans per activation, not a throughput
SLO. Separate source-only jobs have a separate journal; export that directory
with a separately reviewed unit if needed. The organization records nested source
and research work in the campaign trace context when it owns the whole cycle.
Use the [private dossier](DOSSIER.md) for source/model contents rather than raw
automatic cloud uploads.

## Boundary

Tracing observes work; it cannot authorize work. The service keeps budget
reservations, execution receipts, source captures and candidate freezes in their
existing authorities. The private trace journal is a separate bounded SQLite
database under an existing state directory's `telemetry/` directory.

```text
Organization / Workflow / Campaign / ManagedResearch
  -> fixed operation spans + parent/child context
     -> local metadata-only SQLite journal
        -> inspect / timeline / bounded OTLP preview
        -> explicit non-retryable batch intent
           -> root operational Events -> durable Event phase receipt
           -> associated OTLP spans -> final composite delivery receipt
           -> authenticated UI / separately configured Query API readback
```

The fixed operation catalog is inspectable with:

```sh
python -m researcher.service.trace_cli tools
```

These are named capabilities at existing effect boundaries, not automatic
registration of every Python function as an agent tool. Deterministic validation,
budget admission and persistence remain deterministic. Remote MCP discoveries,
research content and trace attributes cannot register tools or expand permission.

## What is captured

| Boundary | Recorded evidence | Important limit |
| --- | --- | --- |
| Organization and pipeline | Cycle, phase, candidate-review and research/evaluation nesting | Does not assert a research improvement |
| Native model calls | Provider, opaque model reference, role where known, input/output byte counts, observed tokens, reservation and estimated cost where supplied | Estimated cost is not an invoice; replay is labelled, not charged again |
| Workflow effects | Opaque operation reference, reservations, replay/completion and exceptions | Budget/effect ledger remains authoritative |
| Discovery and primary reading | Adapter-level spans; discovery request/byte/item counts from receipts | Not separate DNS, TCP, TLS or server-side timings |
| MCP | Read, initialize, list and invoke spans when in the traced process | Isolated child-process internals are not automatically propagated; parent effect duration remains available |
| Managed Agents | Submit, watch/polls, observe, cancel and HTTP request spans | Cancellation acknowledgement is not proof of stop; unknown creates are not retried |
| GitHub publication | Publisher span within the effect-owned workflow | No new publication permission, automatic merge or remote setting change |
| Trace delivery | Pre-POST intent and fixed outcome/count/error receipt | Ingestion ACK is not proof of dashboard persistence |

Spans use monotonic elapsed time anchored to their start wall time. Wall-clock
rollback cannot produce a negative elapsed duration. Async tasks preserve nesting;
new threads/processes do not inherit arbitrary trace context automatically.
Exception type is a closed enum; an exception code can become a local keyed
reference, never arbitrary exception text. An interrupted process can leave an
unfinished span. It is not exported as a fabricated completed operation.

SDK turns additionally project `failure.kind` from a fixed gateway-code allowlist:
HTTP authentication/rate-limit/client/server/redirect classes, network/TLS/timeout,
framing/type/size refusal and worker failures. Unknown strings become
`unclassified`, never raw error text. Observation runs on the parent SDK thread
before its span closes, not by assuming trace context crosses the HTTP server
thread. These categories do not resolve unknown spend or authorize retries.
Historical `transport_unknown` failures cannot be retroactively classified.

Operation/session/model references use a private journal-specific HMAC key.
References support correlation inside that journal without exposing literal
identifiers. A single active root tracer owns nested work, including descendants
that have their own default state directory. Independent CLI operations therefore
may use different journals. Random span IDs distinguish individual attempts;
opaque operation references correlate logical work across restarts.

On `workflow.effect`, `model_calls` and `source_requests` describe reservation
ceilings, not observed requests. Do not sum reservation/cost fields across nested
or replay spans. Discovery receipt counts are observations at their own adapter
boundary; the execution ledger remains the budget source of truth.

## Data deliberately not captured

No prompts, model responses, tool arguments/results, raw source content, query
strings, source URLs, HTTP headers, credentials, arbitrary model/tool names,
exception messages, private paths or provider metadata are accepted as trace
attributes. This is a closed typed projection, not a regex promise to redact
arbitrary content after collection.

Full research evidence and model receipts already retained by the harness remain
private and separately access-controlled. They are not uploaded to Raindrop.
The trace system does not expose hidden reasoning, and trace volume or successful
tool invocation is not a scientific-quality metric.

The journal directory is owner-only 0700; files are 0600, regular, owner-held and
not symlink/hardlink aliases. The default span cap is 10,000 and SQLite is bounded
to approximately 32 MiB. Completed exported spans can be pruned explicitly.
Unexported/uncertain evidence is not silently deleted or overwritten to make
space. Operators must monitor capacity; this is not an unbounded logging promise.

An unavailable/full/corrupt trace journal produces a safe first-failure diagnostic
and tracer health counts. It must not mask an application exception, release a
budget reservation, duplicate a model request, or change an already completed
effect. Remote telemetry delivery instead requires a durable intent before POST:
if that intent cannot be written, no export is attempted.

## Local inspection

Use the existing private service, cumulative campaign, or managed-session state
directory that owns the root operation. These commands do not load API keys or
start research:

```sh
python -m researcher.service.trace_cli status --state /absolute/private/state
python -m researcher.service.trace_cli list --state /absolute/private/state --limit 100 --after 0
python -m researcher.service.trace_cli preview --state /absolute/private/state --limit 100
python -m researcher.service.trace_cli deliveries --state /absolute/private/state
```

List/delivery pages use increasing local sequence cursors. The preview shows both
operational Events and OTLP for completed spans eligible for their first delivery.
Inspection opens an existing validated journal read-only. It never creates or
repairs missing directories, locks, correlation keys, databases or schema. An
empty, damaged or WAL/recovery-pending journal is refused without mutation.
Export and prune also require existing valid state before their explicit writes.

## Optional Raindrop Cloud

Rotate any credential pasted into chat. In the ignored, mode-0600 `.env.local`:

```dotenv
RAINDROP_WRITE_KEY=
RAINDROP_PROJECT_ID=
```

Use a newly rotated ingestion write key and the slug of an existing active
Raindrop project. Do not use an MCP query key or a browser token. The documented
existing `default` project requires an explicit `--allow-default-project` flag;
an absent or blank project never selects it implicitly. Credentials are read literally from the explicit file; the
file is never sourced as shell code. Configuration alone does not enable export.

Check syntax and configuration without opening trace state or contacting the
provider. This does not authenticate the key or verify project existence:

```sh
python -m researcher.service.trace_cli preflight --env-file /absolute/private/.env.local
```

After reviewing the local preview, explicit delivery is:

```sh
python -m researcher.service.trace_cli export --state /absolute/private/state --env-file /absolute/private/.env.local --limit 100 --live
```

If intentionally using the configured `default` project, add
`--allow-default-project` to preflight and export. Validate a new exact-host canary
by opening its Event and inspecting its trace tree, not by treating an HTTP status
or an empty pending queue as proof that the dashboard received usable records.

The exporter validates again in an isolated child, sends credentials over stdin,
has a ten-second absolute process deadline for each phase, and uses only the fixed
Raindrop `/v1/events/track` and `/v1/traces` HTTPS paths. It refuses alternate destinations, proxies,
redirects, oversized responses and malformed acknowledgements. No SDK automatic
instrumentation, background exporter, installer, daemon or retry loop is enabled.

A durable per-span delivery claim is recorded before either POST, after the local
root-Event prerequisite described below is verified. New Event creation applies
only to roots in this batch; child-only continuation requires a retained successful
Event phase for its root. New Event acknowledgement is saved before OTLP.
Both phases must acknowledge before the batch is marked
exported. A partial, rejected, interrupted or unknown
delivery is retained for inspection and cannot be silently sent again by another
export command. There is deliberately no automatic retry or claim of exactly-once
ingestion. A partial ACK does not identify individual rejected spans, so no subset
is guessed. A future operator reconciliation feature must explicitly handle this
uncertainty, rather than resetting claims.

Raindrop supports OTLP/HTTP traces, not OTLP/gRPC, metrics or logs on this endpoint.
The local structured operation records are projected to trace spans; this is not
a generic raw-log upload. Standard GenAI token attributes are projected where
known. Model identity remains opaque by default. [Raindrop contract](https://www.raindrop.ai/docs/sdk/opentelemetry/)

## Operational Event contract

Plain Events use the opaque trace ID as `event_id`, the fixed service actor
`context-research-harness` as `user_id`, the registered root operation as `event`,
and the actual root start timestamp. Properties are closed: metadata-only marker,
root status, elapsed milliseconds and fixture flag if observed. They carry no
`ai_data`, conversation identity, invented model result or synthetic finish reason.
Every OTLP span receives the exact Event association and fixed service actor.
Leaf source/MCP/publication/SDK-tool/action operations additionally receive the
SDK's `traceloop.span.kind=tool` and registered `traceloop.entity.name` markers.
Wrapper spans such as `workflow.effect` are not counted again as tools.

The HTTP documentation specifies 204. The live service returned 200 with an
`events` array of acknowledged `event_id` objects on September 29. Accept either
an empty 204 or a strictly validated 200 JSON body whose unique IDs exactly match
the submitted roots. Other 2xx responses, incomplete/foreign IDs and malformed
framing remain unknown. This is a compatibility rule supported by a retained
wire experiment and UI readback, not an assumption that any 200 means success.
[HTTP Events](https://www.raindrop.ai/docs/sdk/http-api/),
[pinned SDK](https://files.pythonhosted.org/packages/d5/cf/a76bb191b8448039ed23ac3a733a76a928e314b29e83dfd92e4e4f484553/raindrop_ai-0.0.69.tar.gz).

Composite `trace-export-result/v2` receipts keep Event and OTLP outcomes separate.
An interrupted attempt can retain `trace-export-progress/v2` while still running.
Historical v1 receipts remain readable without a SQL schema migration and are
never upgraded into Event-delivery evidence. No earlier unknown is resent.

Normal Organization export occurs after the root closes. Before claiming a batch,
every selected trace must have its unique completed root in that batch or a
validated successful Event phase for that root in the same journal. This also
protects restart after a rejected/unknown root Event in a batch over 100 spans.
Unconfirmed child-only batches fail with `TRACE_EVENT_ROOT_UNCONFIRMED` before
claiming or I/O; children remain pending. Historical OTLP-only acknowledgements
cannot satisfy the gate. A durably successful Event phase can satisfy it even
when its subsequent OTLP delivery is uncertain; those older spans stay quarantined.
No root is invented and no uncertain request is resent.

This local receipt invariant assumes the same verified Raindrop account/project
across batches. Receipts do not bind the remote destination; repointing a populated
journal to another account or project is unsupported. Key rotation must preserve
that verified destination. A root Event receipt still is not a visibility or
retention guarantee. Unfinished root traces stay local until completion; journal
capacity and delivery status need operator monitoring. Query API verification requires a separately provisioned read
key, not the ingestion key. Neither raw-content issue detection nor cloud model-cost
attribution is implied by metadata-only telemetry. The private dossier retains the
research outputs; the budget authority retains cost evidence.

## Managed provider snapshot

OpenAI documents a separate session trace export endpoint. Availability can lag a
completed turn, and access requires the organization's trace export setting and
appropriate trace/agent read scope. A result is a snapshot, not a live stream or
complete billing record. [OpenAI trace export](https://developers.openai.com/api/docs/guides/agents-api/tracing)

```sh
python -m researcher.service.trace_cli managed-preview --session-state /absolute/private/session --env-file /absolute/private/.env.local --live-read
```

This reads only an existing known session, at most three pages, and returns a
strict metadata projection. It does not create a session, run a model or upload
provider traces. Input size/node/span limits, page continuity, timestamps,
duplicate identities and parent cycles are checked before projection. Content,
event bodies and arbitrary attributes are discarded, not forwarded.

The currently verified public shape does not establish a stable role
discriminator for every provider span. Exported provider spans are explicitly
unclassified `managed.agent`, not guessed as model calls from name substrings.
Missing parents and truncated pagination are reported. Usage is preserved when
explicitly reported, not summed across nested spans into a fabricated total.
Automatic merging of provider snapshots into local execution history, streaming
tailing and cloud upload of those snapshots are not enabled.

## Retention, recovery and deployment

Execution recovery bundles explicitly exclude the reserved top-level
`telemetry/` directory after validating its private directory boundary. Traces
and their delivery claims cannot become restored budget/execution authority.
This means execution recovery is not a trace backup. Preserve the private journal
and correlation key separately if trace retention is required. Do not place
them in public GitHub artifacts.

Explicit retention deletes only confirmed-exported spans:

```sh
python -m researcher.service.trace_cli prune --state /absolute/private/state --older-than-days 30 --apply
```

Delivery receipts remain bounded audit metadata. No new periodic task is
installed. A deployed private controller must own persistent telemetry storage,
monitor capacity/unfinished delivery intents, and separately authorize any
scheduled exporter. GitHub-hosted runner workspace deletion must not be mistaken
for trace durability. This instrumentation does not implement the outstanding
shared remote budget/CAS authority described in the deployment plan.

## Verification scope

### Codex SDK observation

`codex_traces.run_traced_worker` observes one pinned worker invocation without
creating a journal, admitting spend or enabling export. SDK tools are siblings
of the turn, including overlapping calls; an active parent owns the journal.
Only closed operation kinds, bounded sequence numbers, statuses and durations
are recorded. Thread/turn/model identities use keyed references. Prompts,
reasoning, tool names, arguments, outputs, paths and capability tokens are not
journaled. Turn-level usage is recorded once; missing usage is unknown, not zero.

SDK event coverage is partial. A denied native patch may emit no tool item event.
Arrival-time spans are observer latency, while paired SDK events also carry their
monotonic tool duration. An unfinished tool is marked incomplete/interrupted
observation, not remotely cancelled. A successful terminal response does not
overwrite a failed tool outcome. Telemetry failures preserve the original worker
result or exception and never dispatch a retry.

The optional real-runtime tests require `CODEX_WORKER_TEST_PYTHON` pointing to an
environment with exact `openai-codex` and `openai-codex-cli-bin` 0.159.0. They use
synthetic loopback responses and temporary workspaces, not provider credentials.
The parent environment must permit the loopback fixture and nested SDK sandbox;
do not weaken the worker's own sandbox to accommodate a restricted test runner.

```sh
python -m unittest researcher.service.tests.test_codex_worker researcher.service.tests.test_codex_traces
```

The active research pipeline and Organization use these components through
`CodexCampaign`. Actual-SDK tests, bounded live runs and retained failure receipts
are distinct evidence classes; their integration is not a cloud deployment claim.
The opt-in [captured action profile](AGENT_ACTIONS.md) adds harness-dispatched
functions between SDK turns, not native SDK tool authority.

### Existing service instrumentation

The regression suites exercise closed metadata, corruption and alias rejection,
bounded storage/concurrency, async nesting, latency, process interruption,
trace-write failure, real fixture workflow/MCP paths, uncertain effect accounting,
delivery intent/ACK atomicity, partial/unknown delivery, no retries, retention and
recovery exclusion. They run without provider credentials or external networking.

```sh
python -m unittest researcher.service.tests.test_tracing researcher.service.tests.test_trace_export researcher.service.tests.test_trace_cli researcher.service.tests.test_trace_integration researcher.service.tests.test_managed_traces
```

See the [implementation evidence](../../docs/product/tracing-engineering-verification-2026-09-29.md)
for actual measured results and remaining release checks, and the
[Raindrop research note](../../docs/product/raindrop-integration-research-2026-09-29.md)
for installer/privacy/SDK analysis. The synthetic cloud ACK does not establish
that an earlier exposed key was rotated. Organization retention/access review
and authenticated dashboard readback remain separate acceptance steps.
