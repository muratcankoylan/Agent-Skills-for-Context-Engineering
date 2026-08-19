# Deliberative Writing Loop

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
tokens for weights: roughly 25 to 35 LLM calls per 900-word piece instead of a training
run per author.

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

Every stage writes artifacts to `runs/<run-id>/`; a run is resumable and auditable.
If a paragraph still fails after the repair budget, the harness keeps the best version
by deterministic flag count and records the residual flags rather than hiding them.

## Quick start

```bash
pip install -e ".[dev]"
pytest                      # 37 tests, no network required

export ANTHROPIC_API_KEY=... OPENAI_API_KEY=...   # PANGRAM_API_KEY optional

# 1. Compile a persona (see personas/README.md for corpus guidance)
dwl compile-persona --name sample-essayist \
    --corpus personas/sample-essayist/corpus --provider anthropic

# 2. Write one piece (budget-gated; --dry-run forecasts first)
dwl write --persona personas/sample-essayist/persona.json \
    --brief eval/briefs/b01-remote-work.json --provider anthropic --max-usd 3

# 3. Benchmark: DWL vs one-shot vs self-refine, both providers
dwl benchmark --providers anthropic,openai --max-usd 25 --dry-run   # forecast
dwl benchmark --providers anthropic,openai --max-usd 25             # run
dwl judge --judges anthropic,openai                                 # cross-judge
```

Model IDs default to `DWL_ANTHROPIC_MODEL` / `DWL_OPENAI_MODEL`; pin dated snapshots
for benchmark runs so results are reproducible.

## Benchmark design

Three conditions per (brief, persona, provider) cell: `oneshot` (same model, same
persona information, single call: the honest baseline), `selfrefine` (whole-document
refinement, call count matched to DWL's repair budget), and `dwl`. Metrics:

- **Deterministic (primary):** stylometric distance to the persona corpus, slop
  findings per 1000 words, opener diversity, lexical variety (MATTR), em-dash rate.
- **Pairwise LLM judgment (secondary):** both providers judge every pair in both
  orders; only order-stable verdicts count; same-provider judgments are marked
  self-judged. Reported per-item, never as one blended accuracy number.
- **Pangram (diagnostic):** reported as a column when `PANGRAM_API_KEY` is set.
  Never used inside the loop. Optimizing against detectors is out of scope by policy.

## What this does not claim

- Not "better than any AI writing." The measurable claim is: against the same model
  given identical persona information, the loop reduces deterministic slop findings
  and stylometric distance, at 10-20x the token cost. Judge preference is reported
  with its known biases labeled.
- Persona fidelity from in-context methods has a documented ceiling (EMNLP 2025).
  The harness measures where that ceiling is; it does not pretend to break it.
- The stylometric distance is comparative, not an authorship verdict.

## Skills applied

context-fundamentals (attention budget spent on contracts and ledgers, not history),
context-compression (trace compaction, commitments ledger), memory-systems (three-tier
run memory), evaluation and advanced-evaluation (deterministic-first gates, position-
bias-controlled pairwise judging), harness-engineering (budget gates, resume, artifact
trail), long-horizon-prompting (paragraph contracts as task briefs).
