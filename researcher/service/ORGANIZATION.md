# Repository-native organization coordinator

Status: developmental, 29 September 2026. `organization.py` joins the existing
retrieval scheduler and `Workflow` to the [research pipeline](RESEARCH_PIPELINE.md).
It is a foreground Python process, not a Codex heartbeat, a new agent framework,
or an accepted-knowledge authority. Its research executor is the
[Codex SDK `CodexCampaign`](CODEX_SDK.md); it does not create managed Agents sessions.

## Ownership and bounded operation

The operator supplies an **existing** retrieval `Store` and **existing** OpenAI
`CodexCampaign`. The coordinator never creates, resets or tops up that spending
authority. Research, critic, editor and optional evaluation calls all use the
same Campaign ledger and its cumulative reservations. Source requests retain
their separate source Store budgets. Account-side limits and other clients
remain outside these local ledgers.

The source configuration must contain only retrieval schedules, with no models,
model-call budget, MCP tools/reads, GitHub publishing or notifications enabled.
An explicit policy maps every configured schedule to one to three existing
skills. There is no model-selected routing or inferred evaluation gold.

Each cycle:

1. Validates immutable bindings and both pause controls; rejects clock rollback.
2. Prioritizes previously completed/manual source jobs and interrupted pipeline
   dispatches. Otherwise admits at most the configured number of source jobs
   using the existing UTC-day slot IDs and at least 30 seconds of ingestion lag.
   It runs at most that many queued source jobs through `Workflow`.
3. Dispatches at most one fresh completed source job to the pipeline, without
   holding the source worker lock during pipeline capture verification.
4. Retains one terminal receipt per source-job/manifest digest, including
   abstention, source ineligibility, validation failure and `awaiting_dataset`.
   A terminal job is not retried on the next cycle.
5. When explicitly enabled, ticks the metadata-only Raindrop pumps after the
   cycle span closes, including failed cycles. Research results and budget
   receipts are not changed by a delivery failure.

Before dispatch, the coordinator freezes the latest bounded set of prior terminal
pipeline references in `learning-sources.json`. The pipeline replays compatible
research and admits at most five whole entries / 32 KiB into researcher-only
context. Evaluator gold, answers, scores and critic/editor outputs are excluded.
`duplicate_candidate` avoids evaluation only for exact frozen bytes and the same
previously completed, verified evaluation contract. This is distinct from duplicate
source-job admission. See [learning and replay](RESEARCH_PIPELINE.md).

`retrieval_complete` is necessary, not sufficient: the pipeline independently
requires all-observed discovery, replay-verified captures, primary evidence and
freshness before research. A partial source job or uncertain effect never becomes
research authority. Stale/non-complete jobs get an explicit ineligible receipt.
There is no historical-slot backfill, publication, skill acceptance or promotion.

## Explicit policy and CLI

Example policy; `daily-context` must exactly match a configured schedule ID:

```json
{
  "schema": "research-organization-policy/v1",
  "schedules": [
    {"schedule_id": "daily-context", "skills": ["context-fundamentals"]}
  ],
  "poll_seconds": 60,
  "max_source_jobs_per_cycle": 1,
  "maximum_age_seconds": 172800,
  "evaluation": {"seed": 1, "replications": 3, "max_sessions": 144}
}
```

Bounds: polling 5–3600 seconds; source jobs 1–4 per cycle; freshness 60–604800
seconds; evaluation replications 1–10 and sessions 1–480. At most 10 schedules,
10,000 source/index records and 16 MiB of source manifests are scanned. Limits
fail closed, rather than silently evicting earlier failures or history.

All four commands require the same paths and bindings. `--state` must be outside
the checkout, initially absent under an existing private directory. Policy,
dataset and credentials are operator-reviewed input files, not generated labels.

```sh
python -m researcher.service.organization init \
  --repo /absolute/reviewed/repository \
  --sdk-python /opt/context-research/codex-venv/bin/python \
  --source-config /private/operator/retrieval.json \
  --source-state /private/operator/source-state \
  --authority /private/operator/existing-openai-authority \
  --policy /private/operator/organization-policy.json \
  --state /private/operator/new-organization
```

Replace `init` with `status` to inspect digest/count/outcome/budget summaries
without credentials. Both commands reject `--live` and `--env-file`. They do not
start a worker or initialize either supplied Store.

Replace `init` with `cycle` and add
`--live --env-file /private/operator/service.env` for one explicitly authorized
cycle. Use `serve` for a foreground loop; add `--max-cycles 30` for a finite
rehearsal. This is 30 cycles, not 30 elapsed days. The private env loader has no
ambient-variable fallback. Only configured source credentials and
`OPENAI_API_KEY` are used; credential values are not persisted in organization
records. Reported job/path identities are digests, not raw private paths/queries.

An optional `--dataset /private/operator/preregistered-eval.json` is bound at
initialization and every restart. Without it, a structurally valid candidate
stops at `awaiting_dataset`; the coordinator does not invent labels or claim an
effectiveness gain. Fixture datasets establish wiring only, not independent
held-out effectiveness. No CLI fixture mode is exposed.

For model-selected captured-evidence reads and a bounded specialist consultation,
add `"research_profile": "captured-actions-v1"` to the policy before initialization.
See [agent actions](AGENT_ACTIONS.md) for schemas, limits and authority boundaries.
Omission preserves the fixed researcher profile; unknown profiles are rejected.
Changing this field after initialization is an input change, not a live toggle.

To deliver completed metadata after cycles, add `--trace-export` to `cycle` or
`serve`. The explicit env file must contain `RAINDROP_WRITE_KEY` and
`RAINDROP_PROJECT_ID`; use `--trace-allow-default-project` only when approving an
explicit `default` project. Initialization/status reject export activation and
do not read credentials. Credential presence alone never activates the pumps.

There are two pumps: journal `0` is the cumulative research authority, journal `1`
is the source Store. Each exports at most 100 pending completed spans once per due
tick, with a process-local 60-second minimum interval. Event creation and associated
OTLP delivery each have an isolated ten-second deadline. Thus two journals can add
at most four transport attempts and forty transport seconds per cycle, excluding
local bookkeeping. This is not continuous streaming during a long model turn.
`trace_delivery` progress events report the
closed delivery result. A broken telemetry progress sink cannot mask research
results or skip the other journal. Inspect durable receipts when stdout is lost.
Partial/rejected/unknown delivery or local delivery failure latches that pump;
restart never clears durable claims or resends previously uncertain spans.
Backlogs over 100 per journal remain visible for subsequent due ticks. Child-only
continuations require a locally confirmed root Event phase; an unconfirmed root
halts delivery before claiming the children. Retain the same verified Raindrop
account/project across batches; cross-target journal migration is unsupported.

## Recovery and operator control

One advisory process lock covers a complete cycle or foreground serving loop.
The source Store and Campaign retain their own effect locks. Do not run the old
retrieval worker alongside this coordinator against the same Store. Pause either
Store to prevent new source/research admission. A pause during source work is
rechecked before pipeline dispatch; in-flight calls are not retroactively undone.

SIGINT/SIGTERM in `serve` request a cooperative drain, not remote provider
cancellation. The current admitted source effect or SDK turn finishes and commits
its actual result; no subsequent effect starts. Candidate preparation is one
atomic local phase and finishes before draining, because an incomplete frozen
candidate directory cannot be silently recreated. Completed receipts remain
replayable and the interrupted source/pipeline stays nonterminal, not a fabricated
failure or evaluator result. A fresh explicit process resumes those same receipts;
the stop signal itself is in-memory and grants no persistent authority.
The supplied unit allows 600 seconds for one candidate phase (five validators,
each bounded to 90 seconds), or one 150-second SDK turn, plus up to 40 seconds for
two configured telemetry pumps (two 10-second requests each) and receipt
bookkeeping. Its `KillMode=mixed` sends the initial TERM only to the coordinator;
remaining children are forcibly stopped after coordinator exit or grace expiry,
as specified by [systemd's kill contract](https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html).
This is a configured grace allowance, not a measured storage-latency
guarantee; a hung filesystem or uncooperative child can still force termination.
Preserve the private state directory on interruption.
Restart replays immutable Campaign results and resumes the exact pipeline path;
unknown provider effects are not resubmitted. Partial candidate directories
remain fail-closed. A receipt published before its index checkpoint is reconciled
without changing its outcome or repeating research.

The private input record binds repository HEAD/implementation/corpus, source
config/directory, Campaign config/directory/implementation, policy, dataset and
fixture class. Drift, missing artifacts, malformed records or modified digests
stop execution. These checks assume cooperative owner-writable local storage,
not protection from a hostile same-UID writer. There is no automatic state
repair, code migration or authority rollover. Changing code or preregistration
requires an explicit new reviewed coordinator identity, preserving the same
spending authority and inspecting earlier receipts rather than evading failures.

## Verification boundary

`tests/test_organization.py` uses actual Stores, source capture/replay and primary
verification with network access blocked. Injected pipeline outcomes are clearly
fixture-only; a separate test resumes the real pipeline around an interrupted
injected Campaign research call. The compressed 30-day test advances UTC slots,
restarts daily, checks duplicate suppression and keeps one authority. Its mixed
outcomes are injected, not measured research yield or month-long uptime.

```sh
.venv/bin/python -m unittest researcher.service.tests.test_organization -v
```

This coordinator closes local dispatch wiring. It does not establish scientific
improvement, unattended production reliability, account-wide spending guarantees,
multi-host coordination or automatic publication readiness.

`tests/test_sdk_learning.py` separately runs three simulated daily cycles through
actual pinned SDK processes and synthetic source/provider responses. It retains
candidate validation, twelve independent evaluation turns on day one, exact
duplicate suppression on day two, researcher archive isolation, and no-call same-slot repeat.
The day-three abstention is scripted, not evidence that memory improved reasoning.
The retained evidence and live experiments are summarized in the
[closure report](../../docs/product/research-organization-closure-2026-09-29.md).
