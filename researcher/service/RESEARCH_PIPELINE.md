# Explicit research-to-evaluation pipeline

Status: developmental, 29 September 2026. `research_pipeline.py` connects a
completed capture-verified source job, research/critic/editor roles, frozen
candidate validation and a supplied evaluation dataset. It creates no managed
Agents session: new non-fixture execution requires the [Codex SDK `CodexCampaign`](CODEX_SDK.md).
It does not publish, accept a skill change, enable a schedule or manufacture gold.

## Ownership and invocation

The caller must open the existing source `Store` and shared OpenAI budget
`CodexCampaign`. All research and evaluation calls use that one authority, including
failures and resumed work. The pipeline cannot initialize/reset/top up the budget.
Secrets remain on the caller's Campaign object; this module does not read the
environment or a credential file and rejects the supplied credential if reflected
into an artifact. This is known-key checking, not general semantic secret detection.

```python
from pathlib import Path
from researcher.service.research_pipeline import run_pipeline

result = run_pipeline(
    Path("/absolute/reviewed/repository"), source_store, "completed-source-job",
    Path("/absolute/private/new-pipeline-directory"),
    campaign=shared_openai_campaign,
    skills=["context-fundamentals"],
    dataset=independently_supplied_dataset,
    seed=1, replications=3, max_sessions=144,
    live=True,
)
```

`live=True` is explicit call authorization, not a spending-cap guarantee. The
Campaign's pinned pricing, conservative cumulative reservations, provider scope
and existing account controls still govern spend. The model is the Campaign's
fixed approved model, not an implicit alias. Its local deadline cannot establish
an account-wide bound on calls outside that authority.

No dataset is invented when `dataset=None`. A valid proposed candidate then stops
at `awaiting_dataset`. Public fixture labels are useful only for wiring tests.
`fixture=True` requires an injected Campaign test adapter and cannot use its
default real-provider worker. The capture/job fixture class must also match.

## Bound phases and restart behavior

### Cross-run learning and repeat-evaluation suppression

`Organization` freezes the latest 32 prior terminal study references before dispatch.
Standalone callers opt in with `learning_sources=[Path(...)]`; an empty list starts
a memory-enabled study with no history. `None` preserves the earlier no-memory input
shape. Only compatible baseline, corpus, schedule, runtime, source and authority
bindings contribute. Consumed captures and SDK role receipts replay before use;
incompatible histories are explicitly omitted rather than rewritten.

The researcher receives at most five whole hypothesis/test-plan entries within
32 KiB. The archive excludes critic text, evaluation scores, gold labels and answers.
It is not injected into critic/editor/evaluator prompts. Prior abstention can be
revisited when new primary evidence resolves a stated gap; the researcher must name
what changed. Archive references do not become fresh supporting evidence.

After structural validation, exact frozen baseline/corpus/path/byte identity may
yield `duplicate_candidate` **only** if a prior completed, replay-verified evaluation
has the same evaluation-plan digest. A newly supplied dataset or changed evaluation
contract is not suppressed. The guard saves repeat evaluation, not the three
research/edit calls already performed. Semantic similarity is not exact identity.
Learning checkpoints and all omission counts appear in the [private dossier](DOSSIER.md).

### Phase receipts

The fresh private directory must be outside the checkout with an existing private
parent. It contains a digest-bound input record, phase receipts, terminal outcome
and candidate-review artifacts. These are non-authoritative recovery records,
not a second knowledge/acceptance registry.

1. Bind root path/HEAD/implementation, source store/job/config, Campaign authority
   and implementation, selected skills, dataset and evaluation settings.
2. Replay discovery and primary captures and reconstruct the source report through
   `verified_bundle`. Prepare a frozen context packet; no fresh source retrieval.
   The existing all-observed/primary/freshness requirements still apply.
3. Use `CodexCampaign.research` for separate SDK researcher, critic and editor threads.
   Deterministic literal grounding precedes later roles. Abstention/no defensible
   proposal is a legitimate terminal research outcome, not a failed optimization.
4. Use [candidate review](CANDIDATE_REVIEW.md) to freeze the inert exact edit,
   derive only declared inventory outputs in an isolated overlay and run the
   four structural checks. No generated code is executed.
5. Execute the caller-supplied three-arm plan through `CodexCampaign.evaluate`, with
   gold-free worker requests and all failures retained. Recompute the deterministic
   comparison before recording `evaluated_not_accepted`.

Every invocation rechecks exact input bindings, retained phase receipt digests,
source capture replay, packet identity and any completed candidate's frozen bytes
and evaluation-plan identity. Verification time is frozen for packet
identity; source freshness and current bindings are rechecked before paid phases.
Changing dataset, config, implementation, selected corpus bytes or source report
does not silently resume old work. Completed terminal replay makes no model calls.
SDK research and evaluation origins are reconstructed from committed gateway/turn
receipts before candidate use and on final replay. A backend label supplied in an
output object is not evidence of SDK execution.

A research/evaluation crash can resume only through Campaign's immutable item
identities: completed calls replay; unknown calls never get resubmitted. The gap
between phase-receipt publication and state checkpoint is reconciled by digest.
An existing partial candidate-review directory is not rerun or overwritten after
interruption. It requires inspection; the pipeline records a terminal failure.

Hard validation/execution errors during active phases produce a private failure
receipt containing only a stable code/stage, not arbitrary exception text. They
stop the pipeline with `automatic_retry: false`. Invalid/unsafe initial paths or
input bindings fail before starting work; partial initialization is not repaired.
Do not delete these directories or change identifiers to evade a failed outcome.

## What the result proves

Possible outcomes are `abstained`, `no_proposal`, `structural_validation_failed`,
`awaiting_dataset`, `evaluated_not_accepted` and `failed`. The final record binds
phase receipts and declares no production, publication or scientific-improvement
authority. Structural correctness, literal quote matching and synthetic known
answers do not establish semantic transfer, independent labels or held-out gains.

The checked-in test suite uses real source capture/replay, shared Store budgeting,
candidate freeze/materialization, trusted overlay validators and deterministic
injected model responses. It makes no provider calls. It separately tests terminal
abstention, invalid grounding, exact resume, receipt/source drift, interruption,
candidate partial-state refusal and private credential handling.

```sh
.venv/bin/python -m unittest researcher.service.tests.test_research_pipeline -v
```
