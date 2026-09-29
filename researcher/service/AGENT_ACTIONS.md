# Bounded captured-evidence agent loop

Implementation contract, 29 September 2026. The opt-in policy
`research_profile: "captured-actions-v1"` lets the researcher select typed
functions across fresh Codex SDK turns. This is **harness-dispatched action
selection**, not SDK-native function calling. The default historical profile
keeps its fixed researcher/critic/editor sequence and record shapes.

## Objective and design decision

Allow the researcher to decide what captured evidence to inspect and whether
specialist analysis is useful, with inspectable decisions and existing cumulative
spend/recovery guarantees. Agent count and tool-call count are not quality metrics.

Three credible designs were considered:

| Design | Benefit | Trade-off / decision |
| --- | --- | --- |
| Fixed roles over the complete bounded packet | Smallest protocol and fewer model round trips | Kept as default and comparison baseline; no model-selected reads |
| Typed decisions between fresh admitted SDK turns | Reuses immutable single-attempt receipts and pure replay | Implemented opt-in; extra decision cost, bounded captured evidence only |
| SDK-native dynamic tools / open exploration | Native tool events and richer interactive execution | Not enabled; requires a multi-request budget/recovery contract and new source-capture phase |

The pinned Python SDK offers a low-level experimental dynamic-tools surface.
Its synchronous request handler runs on the RPC reader thread. Enabling it is not
equivalent to adding a tool schema: our current gateway admits one provider
request per immutable turn. This implementation does not silently weaken that
invariant or reenter the RPC client from a tool callback.
See the [official SDK documentation](https://learn.chatgpt.com/docs/codex-sdk)
and [current runtime boundary](CODEX_SDK.md).

## Roles and functions

```text
reviewed schedule -> deterministic discovery/capture/replay -> immutable packet
  -> researcher decision -> typed function validation -> bounded dispatch
       inspect_context: selected corpus (source index/coverage stay in input header)
       read_span: exact registered captured bytes + offsets/hashes/qualifiers
       ask_specialist: one methods OR transfer advisor, revealed evidence only
       finish: span-bound hypothesis/claims/test plan -> grounding
       stop: explicit abstention
  -> existing separate critic -> optional scoped editor
  -> candidate freeze + structural checks -> supplied separately executed evaluation
  -> operator review, never automatic acceptance or merge
```

The researcher has at most **four decision turns** and **one specialist turn**.
The subsequent critic and optional editor retain their existing gates, giving
at most seven model turns before any separately budgeted evaluation. The model
must reserve a decision for `finish` or `stop`. Exhaustion produces an explicit
limit abstention, not a finding that no improvement exists.

Each decision returns one closed JSON action. Unknown actions, extra fields,
repeated actions, unregistered spans, unrevealed citations and an extra specialist
request fail without a paid format-repair loop. A specialist must have revealed
evidence and may cite only that evidence. It receives no prior research archive,
evaluation gold, general filesystem or credentials. Its advice is not independent
corroboration, a semantic judge score, or permission to accept a skill.
The critic is self-critique from another thread, not independent replication or
consensus. Separately executed evaluation does not establish that the supplied
dataset is truly held out; current comparison receipts retain `held_out_verified: false`.

`finish` requires `abstain: false` and at least one supported claim. Insufficient
evidence uses `stop(reason)`, even if some author-reported observations are useful.
The harness does not silently clear claims or relabel a contradictory final output
as an accepted abstention. This action-specific contract leaves shared historical
research schemas and downstream grounding checks unchanged.

The exact schemas live in `agent_actions.py`: `ACTION_SCHEMA`,
`SPECIALIST_SCHEMA`, and `citation_spans.SPAN_RESEARCH_SCHEMA`. This avoids a
second prose-defined protocol drifting from the executable contract.

Each decision carries the same `RESEARCH_RUBRIC` used by the fixed researcher:
mechanism and transfer assumptions, paired baseline, held-out task family,
ablations, outcome, failure criterion and cost/latency constraints. The original
capture-bound `retrieval_context` header preserves primary links, omission counts
and explicit limits on scientific/coverage claims. It is validated before any
decision is admitted. The source index appears once; inspection history does not
duplicate an index already present in every decision's header. These are prompt
and context contracts, not evidence that a model will satisfy every criterion.

## Ownership and invariants

| Agent may decide | Harness retains |
| --- | --- |
| Which registered span to read | Capture provenance, immutable span IDs/bytes and read bounds |
| Whether to consult methods or transfer advisor | One-consultation ceiling, allowed roles and credential isolation |
| Hypothesis, limitations, test plan, finish or stop | Citation resolution, schema validation and terminal receipts |
| A proposed scoped skill edit after critique | Editable surface, exact freeze, validators and evaluation policy |

Every paid decision and consultation uses the supplied `CodexCampaign`, the
existing cumulative allowance, a fresh SDK turn, an input/history digest and a
durable receipt. No action can initialize an allowance, change the model, schedule
more work, invoke shell/HTTP/MCP, send a notification, publish a PR or merge.
External text and prior research remain untrusted data.

`read_span` exposes only bytes registered in the immutable evidence packet.
It cannot read methods omitted by primary extraction, follow a new URL, process
a PDF, or infer that an entire paper was read. This profile establishes controlled
agent orchestration, not a full-paper research browser. A future pre-packet
exploration phase needs independent capture/effect budgets, provenance closure,
and replay tests before it can broaden that scope.

## Recovery, visibility and evaluation

The private transcript records decisions, exact tool projections, specialist
advice, receipt references, termination and resolved research digest. Campaign
receipts authenticate paid decisions; deterministic replay rederives tool outputs.
A recomputed local checksum alone is not proof that a model ran. Unknown provider
effects retain their reservation and are not resubmitted on restart.

The complete `research-actions.json` checkpoint is written only after the action
loop and final grounding succeed. If a later decision fails, earlier completed
decisions remain in the per-turn Campaign receipts and metadata traces, but there
is no fabricated complete transcript. The dossier shows that failed pipeline
without an action record; inspect the retained Campaign checkpoints for its
partial decision history.

Use the [private dossier](DOSSIER.md) for full source/model content and the
[trace runbook](TRACING.md) for metadata-only latency and delivery evidence.
The Raindrop export does not contain prompts, quotes, specialist text or tool
arguments. Harness actions and SDK-native tools must not be conflated in reports.

The verification ladder is closed-schema/fault tests, actual pinned SDK with a
synthetic local provider, then bounded live queries using the same authority.
Compare this profile with the fixed baseline on identical frozen inputs and
independently labeled tasks before claiming better research. Measure useful
evidence coverage, grounded-claim precision, task effectiveness, latency and cost;
neither an ingestion ACK nor a successful action loop proves improved skills.

## Activation

Add `"research_profile": "captured-actions-v1"` to a reviewed
[Organization policy](ORGANIZATION.md) **before initialization**. It is bound in
the immutable organization and pipeline inputs. Do not edit a running policy or
rewrite prior receipts to migrate them. An explicit new coordinator identity
must retain the existing spending authority and inspect previous work.

To export completed metadata after cycles, add `--trace-export` to the existing
explicit `cycle` or `serve --live --env-file ...` invocation. The configured
`default` Raindrop project additionally requires
`--trace-allow-default-project`. Credentials alone activate nothing.
