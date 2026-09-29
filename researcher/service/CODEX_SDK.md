# Codex SDK research runtime

Status: local pre-release integration, 2026-09-29. The supported initial profile
is **tool-free SDK roles plus deterministic retrieval**, not autonomous shell/MCP
agents. The Codex desktop app and its account session are not dependencies.
Executed tests and release limits are recorded in the
[dated verification report](../../docs/product/codex-sdk-migration-verification-2026-09-29.md).

## Ownership and invariants

```text
source Store -> capture replay -> immutable context packet
  -> Organization / research_pipeline
     -> CodexCampaign -> fresh SDK thread + one turn
        -> private loopback gateway -> existing cumulative authority -> OpenAI
        <- validated, durably committed response <- bounded buffered SSE
     -> deterministic grounding -> critic -> optional editor
     -> exact candidate freeze -> structural checks
     -> independent SDK evaluation threads -> deterministic grading
  -> abstained / awaiting_dataset / evaluated_not_accepted / explicit failure
```

`codex_worker.py` launches the official Python `openai-codex==0.159.0` SDK and
matching CLI runtime in a clean subprocess with a private home, explicit denial
callbacks, read-only sandbox and no inherited provider credentials. The SDK owns
the actual app-server/thread/turn lifecycle. No desktop authentication is used.

`codex_gateway.py` is a narrow provider boundary, not an agent loop. It accepts
only the measured first-turn envelope, removes generated tools/host metadata,
forwards only the immutable task, fixes the output ceiling and rejects tools,
non-default tiers, usage drift, incomplete streams and repeat requests. It reserves
the existing budget before dispatch and commits the validated provider receipt
before sending output to the SDK. Nothing streams speculatively to the worker.

`codex_campaign.py` binds task, runtime/configuration, source and pricing identity.
It records SDK start intent before creating a thread, then records observed thread
and turn IDs. A result is accepted only when SDK text/usage agree with the gateway
receipt. A completed receipt can replay without a credential; an interrupted
started turn cannot be silently replaced. Recovery distinguishes a provider receipt
from a completed SDK turn. There is no implicit native/managed fallback.

The researcher, critic, editor and each evaluation item use fresh SDK threads.
Deterministic source selection, literal grounding, scheduling, freezing, accounting
and objective scoring stay ordinary code. Gold labels and arm bookkeeping are not
passed to the task-solving threads. Synthetic labels test wiring only.

## Configuration and credentials

Use the locked [Linux image/runtime instructions](deploy/CODEX_RUNTIME.md).
The supervisor environment needs repository validation dependencies; `--sdk-python`
selects the separate SDK interpreter. Both versions and effective configuration
are checked. A dependency upgrade is a new tested runtime, not a rolling alias.

The approved pricing policy in `openai_campaign.py` currently fixes `gpt-6-sol`,
default service tier and concurrency one. Roles use explicit reasoning and output
limits; SDK calls cannot override the model or cumulative allowance. Pricing
expires and must be reviewed before more execution. Conservative reservations are
not provider invoices or guarantees about other account clients.

Add `OPENAI_API_KEY` only to the private, ignored operator env file. No new
`CODEX_API_KEY`, desktop token or SDK-worker provider key is needed. The worker
receives only an ephemeral loopback capability. `RESEARCH_OPERATOR_TOKEN` belongs
only to the server-side operator client. See [credential setup](../../docs/product/provider-credentials.md).
Known-key reflection checks are not general data-loss prevention. Same-UID process
isolation does not hide host files; deployed mounts, UID and egress remain separate
security boundaries.

## Local verification without paid calls

Run from the reviewed checkout, with a supervisor interpreter that has the
reference `agentskills` validator installed. The test interpreter path must be
absolute and contain the pinned SDK. Do not load provider env files for tests.

```sh
CODEX_WORKER_TEST_PYTHON=/absolute/codex-venv/bin/python \
  .venv/bin/python -B -m unittest \
  researcher.service.tests.test_codex_worker \
  researcher.service.tests.test_codex_traces \
  researcher.service.tests.test_codex_campaign \
  researcher.service.tests.test_codex_gateway_adversarial \
  researcher.service.tests.test_codex_recovery \
  researcher.service.tests.test_codex_pipeline \
  researcher.service.tests.test_codex_organization -v
```

These tests run real SDK processes against synthetic loopback responses. Missing
SDK opt-in produces skips in the generic unittest command, which is **not** release
evidence. The dedicated Linux verifier requires complete execution with zero skips.
Startup-only `codex_preflight --profile tool_free` does not by itself prove model
execution. Native-tool preflight is a separate, stricter gate. Do not enable tools
or grant extra container privileges to turn its failure into a green SDK check.

Do not edit bound source files while running replay/freeze scenarios. Binding drift
must fail, even if an unrelated document or implementation change appears harmless.

## Explicit operator entrypoints

Use the existing authority, never initialize a replacement to escape prior spend.

```sh
python -m researcher.service.openai_campaign status \
  --authority /private/operator/existing-openai-authority

python -m researcher.service.openai_campaign pause \
  --authority /private/operator/existing-openai-authority

python -m researcher.service.openai_campaign api \
  --authority /private/operator/existing-openai-authority \
  --env-file /private/operator/service.env --port 8788
```

Authenticated `GET /v1/runtime` returns SDK version, profile, observed thread/turn
IDs, receipt availability and unresolved counts without prompts or credentials.
`GET /v1/status` preserves the existing UI contract; `POST /v1/pause` controls new
admission. This authority API cannot enqueue source jobs. Use the separate source
Store API for that purpose. The existing Control Center is read-only and does not
yet render SDK-specific reconciliation controls.

`pause` blocks new admission; it does not prove an already dispatched request was
cancelled. `remote_stop_confirmed` remains false. Inspect unresolved receipts and
reconcile provider usage before a separately authorized new item. Do not delete
tombstones, lower prior spend, reuse stale authority copies, or reset job identity
to bypass an uncertain effect. Use [artifact-complete recovery](../runbooks/service-recovery.md)
and fence the original writer before restoring a paused copy.

For explicit scheduled/manual execution follow [Organization](ORGANIZATION.md)
with `--sdk-python`, the original source/budget Stores and reviewed policy. `init`
and `status` do not activate the service; `cycle`/`serve` require `--live` and an
env file. Candidate publication/acceptance is not enabled by the SDK migration.

## What is not established

No paid SDK quality benchmark, SDK production soak, cloud launch, accepted skill
improvement, autonomous tool/MCP grant, or automatic PR publication is established
by local fixtures. Historical native and managed benchmarks retain their own
backend and epoch. The next paid canary needs reconciled remaining allowance,
reviewed pricing, explicit activation and a preregistered comparison plan.

The worker boundary follows the [official SDK documentation](https://learn.chatgpt.com/docs/codex-sdk)
and [sandboxing guidance](https://learn.chatgpt.com/docs/sandboxing). Exact observed
wire behavior is encoded in tests rather than inferred from feature flags.
