# Managed Agents API integration

Runtime migration: new built-in managed submissions are retired in favor of
[Codex SDK execution](CODEX_SDK.md). Retained identities can still be inspected,
watched and cancelled. The submission commands below describe the earlier canary;
they are not a fallback around SDK admission or an active production path.

This package is repository-owned application code for the new OpenAI Agents API,
not a Codex desktop automation. The API is a public beta. This integration is a
developmental canary, not full SPEC-014/025 conformance or a production release.

## Modules and ownership

- `openai_agents.py`: stdlib-only fixed-origin HTTP adapter; create, retrieve,
  list turns/items, request cancellation. No automatic retries.
- `agents_context.py`: pure compiler for selected skill baselines and evidence;
  validates the returned research/critique/scoped-proposal packet.
- `agents_runtime.py`: private single-session submission intent, manifest binding,
  recovery, observation and cancellation. At most one create attempt per directory.
- `retrieval_handoff.py`: replay-verified completed retrieval job to a prepared
  managed packet. No retrieval, model submission or publication effects.
- `research_brief.py`: bounded retrieval provenance and falsifiable transfer rubric;
  no source-quality score or authority promotion.
- `agents_evals.py`: immutable three-condition task plan and deterministic scorer.
  It does not execute models or certify scientific effectiveness.

The transport is publishable independently. The other modules depend on the
integrated service/research primitives and must be published with that reviewed
dependency closure. Do not assume a transport PR contains the entire service.

## Before a real run

Use an application project API key exposed explicitly as `OPENAI_API_KEY`. The
documented permissions are `api.agents.read`, `api.agents.write`, and
`api.responses.write`. Do not paste keys into chat or place them in a prompt,
sandbox, state packet, source file, Git remote or PR.

Confirm that provider storage is appropriate for the selected public research
inputs. The managed API is currently US-resident and not ZDR-eligible. Verify the
applicable project/organization spend controls and billing state independently.
An alert is not a hard limit; provider enforcement can overshoot. Local source or
native-model reservations do not enforce a managed-session dollar cap.

There is no documented per-session hard dollar/token cap in the reviewed create
contract. The CLI's deadline means “attempt cancellation when observed,” not “the
provider cannot spend after this instant.” One create can contain multiple model
calls. A crashed supervisor cannot enforce its local deadline. Do not connect
this canary to recurring admission until the production containment gate passes.

## Prepare and inspect

The preferred path reuses a completed daily retrieval job whose reviewed schedule
enabled primary HTML reading. It requires every discovery lane to be `observed`,
no failed/unknown effects or source-failure entries, and at least one primary card.
A known captured rate limit is not sufficient. Bounded-page coverage and incomplete
primary extraction remain explicit limitations, not reasons to claim a full search.

```sh
python -m researcher.service.retrieval_handoff \
  --repo /path/to/reviewed/repository \
  --config /private/state/retrieval-service.json \
  --source-state /private/state/retrieval-service \
  --job completed-retrieval-job-id \
  --state /private/state/research-canary-001 \
  --model gpt-6-astra \
  --skill context-fundamentals \
  --max-subagents 0

python -m researcher.service.agents_runtime status \
  --state /private/state/research-canary-001
```

Use the source state's unchanged bound configuration and an actual completed job
ID. Preparation reconstructs the exact report and replays retained discovery and
primary captures; it makes no provider call and needs no credential. The source
window can be at most two days old by default. `--maximum-age-seconds` accepts
60–604800 seconds; freshness is checked again before submission. `--fixture` is
only for an explicitly fixture-bound source run and creates a non-submittable packet.

The packet binds source job/manifest/report identities, evidence digests,
discovery-to-primary excerpt links, source windows and omission/coverage counts.
The rubric requires a mechanism, assumptions, counterevidence and a falsifiable
paired held-out test plan. These are requested outputs, not executed experiments
or evidence of scientific relevance. The handoff has no service-wide owner link:
a second destination directory is not globally prevented from preparing the same
job. Operators must not use new directories to bypass admission or cost limits.

### Advanced manual evidence preparation

Alternatively, choose explicit public evidence records produced and replay-verified by the
source-capture pipeline. Each record needs `id`, `source`, `text`, `sha256`, and
`evidence_scope`. Use a private, regular mode-0600 JSON file containing a list.
The compiler verifies bytes, not source authenticity; capture verification is
the caller's responsibility on this manual path. It does not acquire the verified
retrieval-job binding above. Synthetic fixture success is not research evidence.

```sh
python -m researcher.service.agents_runtime prepare \
  --repo /path/to/reviewed/repository \
  --state /private/state/manual-research-canary-001 \
  --evidence /private/state/verified-evidence.json \
  --model gpt-6-astra \
  --query 'Which evidence-transfer failure should this skill address?' \
  --skill context-fundamentals \
  --max-subagents 0

python -m researcher.service.agents_runtime status \
  --state /private/state/manual-research-canary-001
```

The state parent must already exist. Preparation creates a fresh mode-0700
directory and never overwrites an existing one. `packet.json` binds the model,
compiled request, exact context, evidence, baseline and implementation digest.
Review those inputs locally. They are what the model provider will receive.

## Run one supervised canary

Only after explicit cost-risk approval and credential availability:

```sh
python -m researcher.service.agents_runtime run \
  --repo /path/to/reviewed/repository \
  --state /private/state/research-canary-001 \
  --env-file /private/state/service.env \
  --live --acknowledge-no-hard-session-cost-cap \
  --max-seconds 120 --max-polls 24 --poll-seconds 5
```

The acknowledgement records an invocation choice, not verified billing policy.
`--env-file` is an explicit private literal file, with no shell evaluation,
automatic dotenv discovery or ambient fallback. Only the credential selected by
`--credential-env` (default `OPENAI_API_KEY`) is exposed to the provider adapter.
Without the flag, that selected variable is read from the process environment.
Use `submit` only when another reviewed supervisor immediately takes over
observation. A session ID is persisted before other effective configuration is
interpreted. CLI progress omits source text, prompts and secrets.

After a disconnect or process restart, do not issue another create:

```sh
python -m researcher.service.agents_runtime watch \
  --state /private/state/research-canary-001 \
  --env-file /private/state/service.env --max-polls 24

python -m researcher.service.agents_runtime cancel \
  --state /private/state/research-canary-001 \
  --env-file /private/state/service.env
```

`watch` uses saved-turn/item pagination. It requests cancellation on observation
exhaustion, interruption or polling failure. Cancel acknowledgement is explicitly
unconfirmed until terminal remote work is observed. Clock rollback prevents new
admission/observation but does not prevent emergency cancellation.

If create outcome is unknown and no safe session ID was retained, use the OpenAI
Agents dashboard and the local packet to investigate. The adapter intentionally
has no “retry create” or unaudited session-adoption shortcut. Preserve that state.
An unresolved case blocks further work under the same identity.

## Results and evaluation

Only an observed completed root turn with terminal subordinate work and one
validated final answer produces `result.json`. This is still
`awaiting_independent_evaluation`. It confers no registry, GitHub or deployment
authority. Source-level literal grounding is not semantic entailment.

The comparison planner uses no-skill/current/candidate arms, fresh session IDs,
fixed randomized order and exact manifest/result bindings. Include all missing,
failed, invalid and cancelled attempts. Public fixture tasks validate the scorer,
not a held-out benchmark. No model-effectiveness claim follows from their success.

## Verification

```sh
python -m unittest discover -s researcher/service/tests -p 'test_*agents*.py' -v
python -m unittest researcher.service.tests.test_retrieval_handoff -v
```

The tests inject fake transport and known answers; they make zero paid calls.
The transport subprocess test exercises the actual Python worker boundary, not
the live provider. Real protocol, cancellation, tool, quality and deployment
canaries must be reported separately.

The September 29 [integration verification record](../../docs/product/research-integration-verification-2026-09-29.md)
owns dated focused/full-suite results and retained-source preparation evidence.
Passing transport or handoff tests is not a measured skill-effectiveness result.

## Provider contract boundaries

Session creation can return HTTP 201. The adapter accepts that create response
without broadening success statuses on other endpoints; shape and effective
configuration still require validation. See the [create-session reference](https://developers.openai.com/api/reference/python/resources/beta/subresources/agents/subresources/sessions/methods/create).

An empty `tools` list does not disable the provider's default programmatic tool
calling. The data-only compiler explicitly sends
`{"type":"programmatic_tool_calling","enabled":false}` and verifies the
effective response. The path supplies no environment or vault and grants no
external tool authority. See [programmatic tool calling for Agents API](https://developers.openai.com/api/docs/guides/tools-programmatic-tool-calling#agents-api).

Provider [spend controls](https://developers.openai.com/api/docs/guides/spend-limits)
are separate from this ledger. Neither `max_subagents`, a local deadline nor a
single create intent bounds total model calls or guarantees a hard session cost.
Spend containment, independent usage reconciliation and crash-safe supervision
remain requirements before recurring managed admission.

## Deployment boundaries

The current managed path has no external tools, environment, vault, GitHub write
or notification capability. It is not installed as a cron job. The existing
control-center `/service` page does not yet read this ledger. Production needs
owner-store integration, authenticated UI/actions, global admission and billing
containment, scheduled verified handoff, independent frozen evaluation, complete backup/restore,
scoped GitHub App delivery, a reviewed deployment and human launch approval.

References: [quickstart](https://developers.openai.com/api/docs/guides/agents-api/quickstart),
[session API](https://developers.openai.com/api/reference/resources/beta/subresources/agents/subresources/sessions/methods/create),
[events and recovery](https://developers.openai.com/api/docs/guides/agents-api/sessions/events),
[usage](https://developers.openai.com/api/docs/guides/agents-api/observability),
[spend controls](https://developers.openai.com/api/docs/guides/spend-limits).
