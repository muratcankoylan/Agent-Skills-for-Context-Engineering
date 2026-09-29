# Offline candidate review preparation

Status: developmental, 29 September 2026. `candidate_review.py` connects an inert
native or completed managed proposal to a frozen skill candidate, isolated
structural validation and an optional independent evaluation plan. It does not
execute models, publish a PR, promote a mechanism or accept a skill change.

## Inputs and ownership

The managed entry point is:

```python
from pathlib import Path
from researcher.service.candidate_review import review_managed

report = review_managed(
    Path("/absolute/reviewed/repository"),
    Path("/absolute/private/completed-managed-session"),
    Path("/absolute/private/new-candidate-review"),
    dataset=independently_supplied_dataset,
    model="explicit-pinned-evaluation-model",
    seed=1,
    replications=3,
    max_sessions=144,
)
```

The source ledger must have a completed result with matching packet, session and
result-envelope bindings. `review_managed` revalidates the output schema, literal
citations and exact edit before proceeding. This is local-record verification,
not a new provider observation or an independent scientific judgment.

For an already retrieved native packet use
`review_candidate(root, destination, corpus=..., evidence=..., output=...,
source_binding=..., dataset=..., model=...)`. `output` has the existing
`managed-research-proposal/v1` shape containing `authority: none`, `research`,
`critic` and `proposal`. Native role outputs can be wrapped into that shape.
`source_binding` contains exactly:

```json
{
  "baseline_commit": "40-character lowercase Git HEAD",
  "manifest_digest": "sha256:<canonical source manifest digest>",
  "result_digest": "sha256:<canonical output object digest>"
}
```

The generic entry point verifies hashes and baseline bytes but cannot authenticate
a supplied native manifest or prove that a model produced it. The caller owns
that provenance. A managed origin receipt additionally binds the verified result
envelope to the review. No secret belongs in these inputs.

## Freeze and validation

1. Reject missing/abstained proposals, stale baseline bytes and edits outside the
   existing exact-body policy. Frontmatter, section structure, activation and
   integration boundaries remain locked.
2. Copy the current Git-listed nonignored checkout into a private overlay, with
   per-file, file-count and total-byte bounds. Ignored runtime state is excluded;
   dotenv credential paths, runtime directories, links and unexpected private run
   paths are rejected. The public `.env.example` is permitted. Dirty reviewed
   source bytes are recorded explicitly; HEAD alone is not their identity.
3. Freeze the single permitted skill file through the existing CandidateArtifact,
   editable-surface policy and CAS receipt. Materialize the frozen bytes before
   using them for either overlay validation or evaluation planning.
4. Run the fixed trusted `build_inventory.py --write` inside the overlay. It may
   change only `researcher/corpus/inventory.json` and
   `researcher/generated/corpus-summary.md`. The derivation receipt binds both
   before/after identities and verifies that every other file is unchanged. The
   SPEC-003 candidate remains the one frozen skill file; generated projections
   neither approve its claims nor modify a mechanism or claim registry.
5. Run fixed trusted repository, required-reference platform, activation and
   inventory checks on that overlay. Commands are not model-generated. Each has
   a 90-second wall limit, CPU/file/output limits, an isolated temporary directory
   and a minimal environment without credentials or Python/proxy hooks. The
   validator tree must be operator-reviewed; this is not an OS network sandbox or
   an executor for untrusted code. Candidate Markdown is only parsed as data.
6. Verify the baseline and post-derivation overlay identities again. Validator
   failures remain failed checks. Other metadata needing coordinated changes
   remains a reported limitation; no semantic metadata is inferred or accepted.

The destination must be fresh, outside the checkout, below an existing private
mode-0700 parent. No in-place source changes or Git writes occur. Partial failed
directories are not valid resume receipts; retain them for diagnosis, rather than
overwriting them. A review cannot authorize another managed session.

## Independent evaluation, not invented evidence

An evaluation dataset must be supplied by the evaluator/operator, not synthesized
from the author's hypothesis or proposed answer. It uses the existing
`context-transfer-dataset/v1` contract. The plan contains no-skill, current-skill
and frozen-candidate arms with fixed randomized order and explicit session limits.
Only `agents_evals.task_request()` may be sent to a worker; the full private plan
contains gold labels. This module does not execute those workers.

Without both dataset and model, omit both arguments: the report records
`unplanned_missing_dataset`. No fixture or judge label is inserted automatically.
An explicitly supplied public fixture dataset is useful for wiring tests only.
Declared held-out status, independence and semantic effectiveness remain unverified.

`review.json` binds the source/result/proposal, baseline/overlay file manifests,
freeze receipt, explicit inventory-derivation receipt, validator outcomes and
optional plan digest. Logs and source
packets remain private. `structural_checks_passed` describes only the four named
checks. It does not assert synchronized mechanism/claim metadata, semantic
consistency, held-out effectiveness, approval or readiness to publish. A successful
review stops at `awaiting_independent_evaluation`; failures stop at
`structural_validation_failed`.

```sh
python -m unittest researcher.service.tests.test_candidate_review -v
```

These tests use synthetic evidence and no model/provider calls. They cover
bindings, inert edit boundaries, frozen materialization, explicit evaluation
inputs, source/overlay drift, private path handling and validator failures.
