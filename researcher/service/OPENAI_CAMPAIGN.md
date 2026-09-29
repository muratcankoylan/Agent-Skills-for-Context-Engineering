# Bounded OpenAI research and evaluation authority

This repository-owned authority now admits [Codex SDK](CODEX_SDK.md) turns through
a tool-free Responses-compatible gateway. The SDK owns threads and turns; the
gateway owns per-request admission and receipt validation, not an agent loop.
The same persistent authority retains historical native reservations and receipts.
New built-in native calls are retired. This is not a desktop automation, managed
session, permission to publish, or an account-wide invoice guarantee.

## Budget invariants

`openai_campaign.py` owns an explicit private authority directory containing
`authority.json`, SQLite, its journals and worker lock. Research roles and
evaluation arms use the **same** directory. The approved amount is cumulative
across jobs, dates and restarts. Initialization is explicit, rejects an existing
directory, and has no reset or top-up command. A path is not account-wide policy:
the deployment must fence alternative workers, authority copies and direct API
clients. Creating another directory does not create another spending allowance.

Before each network attempt, the Store transaction reserves worst-case cost.
Completed, failed and unknown effects all remain charged against that reservation.
Usage-based estimates never refund reservations. Operator-account usage outside
this authority must be included in `prior_spend_microusd`; an empty local ledger
does not prove an empty provider invoice. A dedicated OpenAI project and its
[hard spend limit](https://developers.openai.com/api/docs/guides/spend-limits)
provide an additional boundary. Provider enforcement can lag, so it is not a
replacement for pre-dispatch reservations.

The current price policy is dated and expires before further execution unless
reviewed. It pins `gpt-6-sol`, Standard/default tier, short text context, and the
most expensive documented input/cache-write rate. It reserves one token per
canonical request byte plus 4,096 framing tokens, and the entire output ceiling
including reasoning. The request-byte ceiling keeps this path below long-context
pricing. No hosted tools, background requests, conversation reuse, regional
endpoints, storage, fast tiers or managed sessions are admitted. The
[model page](https://developers.openai.com/api/docs/models/gpt-6-sol) and
[Responses contract](https://developers.openai.com/api/reference/python/resources/responses/methods/create)
are the pricing and wire references; estimates are not invoices, taxes or a
guarantee against provider pricing changes.

## Execution and recovery

- One worker at a time. `--concurrency 1` is explicit; other values are rejected.
- Each campaign/item binds the exact prompt, role, model, reasoning/output limits,
  caller provenance, pricing policy and relevant implementation digest.
- A completed receipt replays without a key or new effect, including recovery
  after a crash between receipt commit and terminal bookkeeping.
- An ambiguous request never retries. Its reservation and uncertainty survive
  process death. A deliberate new experiment is a distinct, budgeted work item,
  not an overwrite of the old result.
- Calls run in a credential-isolated child with a wall deadline. Progress appears
  every five seconds. The deadline is not proof that remote computation stopped;
  its output-token reservation remains retained.
- Returned model, tier and usage must fit the admitted contract. Known credential
  reflection is checked before persistence. This is not a general DLP classifier.

The research path executes separate researcher, critic and conditional editor
roles. The researcher selects deterministic source-bound span IDs. The harness
resolves those IDs to exact original text, validates the unchanged literal
citation schema, and checks grounding before paying for a critic. It never
repairs a guessed quotation by fuzzy matching. The catalog binds source/evidence
hashes and UTF-8 offsets, preserves source qualifiers, and records omitted bytes.
Its bounded round-robin selection is a transport policy, not a claim of semantic
retrieval quality. Corpus excerpts are baseline material, not external evidence.
The critic may abstain, and that is a valid research outcome. A proposed edit has
no acceptance authority and must pass [candidate review](CANDIDATE_REVIEW.md).

The evaluation executor sends only `agents_evals.task_request()` projections.
Gold labels, group identities and arm labels stay local. Each item uses a fresh
tool-free request; plan order is deterministic and bound to the seed. Missing,
failed and malformed outcomes remain in the denominator. Completed response IDs,
usage, latency and raw answer text are retained privately. Public fixture tasks
prove wiring only; they are not independent held-out effectiveness evidence.

## Operator commands

Create a single authority on the persistent service volume, outside the read-only
release. The following amount is the user's existing allowance, not a new budget:

```sh
python -m researcher.service.openai_campaign init \
  --authority /var/lib/context-research/openai-budget \
  --cap-microusd 100000000 --prior-spend-microusd 0

python -m researcher.service.openai_campaign status \
  --authority /var/lib/context-research/openai-budget

python -m researcher.service.openai_campaign eval \
  --authority /var/lib/context-research/openai-budget \
  --sdk-python /opt/context-research/codex-venv/bin/python \
  --env-file /etc/context-research/provider.env \
  --input /var/lib/context-research/evals/plan.json \
  --output /var/lib/context-research/evals/execution.json \
  --campaign reviewed-evaluation-id --concurrency 1 --live
```

Use the actual reconciled prior spend, not zero by habit. Inputs and outputs are
private regular files. Existing output files are not overwritten. `research`
accepts a prepared packet, but capture authenticity remains the caller's duty;
prefer the capture-verified pipeline over manually constructed evidence.

Back up this authority separately with the explicit budget-authority profile in
the [artifact-complete recovery runbook](../runbooks/service-recovery.md).
Restores remain paused. Fence the original writer and reconcile post-snapshot
effects before admitting anything on a restored copy. Copying an old budget
database and continuing both copies would invalidate cumulative containment.

No command here starts a scheduler, opens a PR, enables GitHub writes or deploys
cloud infrastructure. The separate [organization coordinator](ORGANIZATION.md)
owns recurring dispatch and must receive this existing authority explicitly.
