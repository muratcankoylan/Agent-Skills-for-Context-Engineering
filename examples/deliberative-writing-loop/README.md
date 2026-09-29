# Deliberative Writing Loop

## Draft execution boundary

This is an independent offline research example, not the production research
organization's execution service. **Paid generation, judging, persona extraction,
and Pangram calls are disabled**, including when environment keys are present.
The old direct HTTP implementations have been removed. No CLI flag enables them.
A future live path must use the repository's admitted SDK/broker, cumulative
budget authority, cancellation/recovery, and private publication boundaries.

The `mock` adapter and deterministic persona compiler remain executable. Passing
offline tests establishes local control-flow properties, not writing quality,
provider compatibility, calibrated token costs, or readiness for paid deployment.
The example requires Python 3.10+ on Linux/macOS with POSIX `fcntl` file locking;
Windows execution is not implemented. This repair was tested on macOS.

An inference-time writing harness that produces persona-faithful long-form prose from
any chat model, with no fine-tuning. It decomposes writing the way a working writer
does: extract a persona's tacit knowledge once, plan the piece as paragraph contracts,
draft one paragraph at a time, critique sentence by sentence against deterministic
gates, repair only what failed, and compact everything already written into a ledger
the drafter cannot contradict.

The counterpart example to `examples/book-sft-pipeline` (which reaches author style by
training): this project tests how far pure context engineering gets on the same goal.

## Thesis

Training-time approaches (SFT on author text, distribution fine-tuning) move a model's
output distribution toward a target corpus. This harness enforces the same objective at
inference time: the persona's measured stylometry is the target distribution, the slop
profiler is the divergence detector, and the repair loop is the optimizer. The trade is
tokens for weights. Call count depends on the generated plan and repairs. No live
quality/cost benchmark is published by this example.

## Research grounding

Each design decision is downstream of a specific published result:

| Decision | Grounding |
| --- | --- |
| Iterate, but bound repairs at 2-3 rounds | Self-Refine gains (arXiv:2303.17651); refinement converges to a model-preferred fixed point within a few iterations (arXiv:2607.22653), so unbounded loops drift toward slop |
| Deterministic gates before any LLM judgment | LLM judges fail to detect slop reliably (arXiv:2509.19163); judges favor LLM-typical text (arXiv:2404.13076, PNAS 2025) |
| Slop = overrepresentation vs a reference corpus, not a keyword list | Antislop frequency-ratio profiling; some patterns are 1000x human rate (arXiv:2510.15061) |
| Paragraph contracts planned before drafting | DOC: shifting creative burden to planning improves coherence 22.5% absolute over Re3 (ACL 2023); Re3 itself (EMNLP 2022) |
| Paragraph = generation unit, sentence = repair unit | Whole-document refinement degrades passing sentences; sentence-only generation destroys rhythm (DOC's controller evidence) |
| Explicit tacit-knowledge extraction, not raw few-shot samples | LLMs fail implicit style imitation from samples alone; explicit rules + curated exemplars is the documented mitigation (EMNLP 2025 Findings, arXiv:2509.14543) |
| Summaries + ledger + verbatim tail instead of full history | RecurrentGPT's language-based LSTM (arXiv:2305.13304); compaction-as-action (CompactionRL arXiv:2607.05378, SUPO ACL 2026) |
| Detector scores as diagnostic, never target | Training-free detector evasion is already established (DIPPER arXiv:2303.13408; Adversarial Paraphrasing NeurIPS 2025), so "fools detectors" is not evidence of quality |

## Architecture

```
persona corpus ──> [1. persona compiler] ──> persona.json
                        │  deterministic stylometry (code)
                        │  tacit craft rules (LLM, checkable imperatives)
                        │  tagged exemplar bank (code selects)
brief ──> [2. planner] ──> plan.json (thesis + paragraph contracts)
per paragraph:
  [3. drafter]  writes under contract + compacted memory
  [4. critic]   deterministic gates: slop ratios, opener runs, echo,
                spent-phrase reuse, rhythm deviation from persona profile
                then one rubric pass using the persona's own rules
  [repair]      rewrites only flagged sentences, at most 2 rounds
  [commit]      summary -> memory; claims -> ledger; phrases -> spent;
                repeated findings -> standing lessons for later paragraphs
[5. final]      metrics.json: style distance, slop score, residual flags
```

Every stage writes artifacts to `runs/<run-id>/`. Only a completed run with an exact
matching source/input/configuration receipt can be reused without new calls.
Interrupted runs are not automatically replayed.
If a paragraph still fails after the repair budget, the harness keeps the best version
by deterministic flag count and records the residual flags rather than hiding them.

## Configuration

No keys are needed or used for the supported offline execution path. To inspect
configuration without enabling live execution:

```bash
dwl check-env        # masked presence report, makes no API calls
```

`.env` is gitignored. The CLI loads it automatically from this directory or any parent;
pass `--env-file path/to/other.env` to point elsewhere. Values already present in the
real environment always win over the file, so exported shell variables and
platform-injected secrets are never silently overridden by a stale local file.

| Variable | Required | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | unused | does not enable execution |
| `OPENAI_API_KEY` | unused | does not enable execution |
| `PANGRAM_API_KEY` | unused | does not enable detector execution |
| `DWL_ANTHROPIC_MODEL` / `DWL_OPENAI_MODEL` | optional | constructor-time offline identity; legacy defaults are not current model recommendations |
| `DWL_*_URL` | optional | constructor-time identity only; no outbound transport |

The test suite, `--dry-run` forecasts, and `--provider none` persona compilation all work
with no keys at all.

## Quick start

```bash
pip install -e ".[dev]"
pytest                      # offline tests; no network required

# 1. Compile a persona (see personas/README.md for corpus guidance)
dwl compile-persona --name sample-essayist \
    --corpus personas/sample-essayist/corpus --provider none

# 2. Forecast only (not a billing bound)
dwl write --persona personas/sample-essayist/persona.json \
    --brief eval/briefs/b01-remote-work.json --provider anthropic --max-usd 3 --dry-run

# 3. Inspect a proposed grid; paid execution without --dry-run refuses
dwl benchmark --providers anthropic,openai --max-usd 25 --dry-run   # forecast
# Exercise local receipt mechanics with synthetic mock output only
dwl benchmark --providers mock --conditions oneshot,selfrefine --max-calls 80
dwl judge --judges mock
```

Model IDs default to `DWL_ANTHROPIC_MODEL` / `DWL_OPENAI_MODEL`; pin dated snapshots
before any future authorized live benchmark. These are resolved after the CLI
loads the environment file, not at module import time.

## Offline accounting and recovery contract

- `--max-calls` is a **total campaign limit**, not a per-cell limit. Completed and
  unknown calls consume capacity across restarts. Benchmark, judge, and write
  commands have separate named local ledgers; this is not a shared production
  dollar authority.
- The ledger reserves integer microdollar **estimates** before an injected effect.
  Unsettled reservations remain liabilities; NaN/infinite/negative limits are
  rejected. Static fixture prices and character-based estimates are not verified
  pricing or token bounds. An estimate overrun is recorded and blocks admission.
- `.state/*-budget.json` holds limits/reservations under an OS file lock with
  fsynced atomic writes. Changing limits on resume is rejected. Keep ledgers and
  receipts together. Deleting/copying state to obtain new capacity is not resume.
- Cell receipts bind the exact brief, persona content, target word count,
  provider/model/endpoint, budget limits, and all `src/dwl` Python source bytes.
  Completed result digests are checked. Old unbound JSON cannot be reused.
- Each judge pair persists a started marker before either order. Completed pairs
  are reused exactly; the aggregate `judgments.json` is never a benchmark input.
  An interrupted pair, unknown response, or failed terminal receipt write blocks
  replay and requires explicit operator reconciliation. There is no automatic
  retry or claim of exactly-once delivery. Use a new experiment identity only
  after acknowledging the previous unknown work, not as a budget-reset shortcut.
- `write --run-id ID` can reuse a matching completed run. Partial paragraph
  artifacts are diagnostic only, not resumable authority. Local trusted storage
  and cooperating writers are assumed; this is not a cloud/distributed journal.
- `--detector none` is the default. Explicit `--detector pangram` also refuses
  until a budgeted connector is admitted; key presence never activates it.

Budget ledgers and operation receipts are local research records, not production
approval receipts or authenticated attestations. Do not place them on a hostile
shared filesystem or treat a content digest as proof of who produced a result.

## Benchmark design

Three conditions per (brief, persona, provider) cell: `oneshot` (same model, same
persona information, single call), `selfrefine` (whole-document refinement, two
rounds; not compute-matched to DWL), and `dwl`. Proposed metrics:

- **Deterministic (primary):** stylometric distance to the persona corpus, slop
  findings per 1000 words, opener diversity, lexical variety (MATTR), em-dash rate.
- **Pairwise LLM judgment (secondary):** both providers judge every pair in both
  orders; only order-stable verdicts count; same-provider judgments are marked
  self-judged. Reported per-item, never as one blended accuracy number.
- **Pangram (future diagnostic):** currently disabled. Would never be used inside
  the optimization loop; a key alone must not enable an external request.

## What this does not claim

- Not "better than any AI writing." Reduced slop findings and stylometric distance
  at acceptable cost are hypotheses to test, not results established by this
  example. Live quality, cost, compute-matched baselines, and judge calibration
  remain unmeasured. Mock outputs do not provide evidence for these hypotheses.
- Persona fidelity from in-context methods has a documented ceiling (EMNLP 2025).
  The harness measures where that ceiling is; it does not pretend to break it.
- The stylometric distance is comparative, not an authorship verdict.

## Skills applied

context-fundamentals (attention budget spent on contracts and ledgers, not history),
context-compression (trace compaction, commitments ledger), memory-systems (three-tier
run memory), evaluation and advanced-evaluation (deterministic-first gates, position-
bias-controlled pairwise judging), harness-engineering (budget gates, resume, artifact
trail), long-horizon-prompting (paragraph contracts as task briefs).
