# Qualitative retrieval case: RICE-Alpha

Reviewed: 2026-09-29 UTC. Source: [arXiv 2609.34004v1](https://arxiv.org/html/2609.34004v1).
Disposition: **adjacent-domain candidate; not accepted for a skill update**.
This is one qualitative case from the live `agent memory` canary, not a benchmark.

## Structured assessment

- **Source-reported mechanism:** issuer-specific time-eligible memory, typed event
  graphs, lifecycle-gated updates, and residual correction against existing forecasts.
- **Source-reported method:** financial backtesting with component ablations,
  common portfolio rules and bootstrap comparisons. We did not reproduce it.
- **Source-reported limitation:** pretrained models may know information after a
  forecast date. Time-filtered retrieval does not remove that contamination.
- **Reviewer inference:** lifecycle gating and testing incremental value over an
  existing context baseline could transfer to research memory. Finance-specific
  results do not establish general multi-agent or context-engineering benefits.
- **Missing verification:** independent execution, extraction accuracy, prompt and
  dataset snapshots, and compute-matched comparisons for our target task.

## Evidence anchors

Offsets are half-open UTF-8 byte ranges in the retained normalized extraction,
not the original HTML. Text digest:
`sha256:414ca0189ab082fb925957afe8b6b1834ba8bdb6c76c868ea5e042089e3b29fe`.

| Assertion | Exact retained span | Text |
| --- | --- | --- |
| Lifecycle gating | `[19045, 19114)` | “Only validated New and Updated records create dated graph occurrences” |
| Model contamination caveat | `[39856, 39928)` | “Both models may contain information that postdates individual\nforecasts.” |

The `\n` above denotes the retained newline. The source URLs, captures and parser
identity are bound in the private primary-reading checkpoint. HTML extraction
flattens tables and duplicates some math representations; complete-paper or
equation fidelity has not been established.

## Implication for our retrieval evaluation

Technical vocabulary overlap is insufficient. Label direct methodological
research separately from adjacent applications, retain useful counterevidence,
and evaluate whether a proposed transferable mechanism changes our behavior.
Do not hard-code a finance blacklist or treat company/paper reputation as quality.

Proposed experiment, not yet executed: compare indiscriminate memory appends
against explicit episode lifecycle and outcome-maturity gates on a frozen
research-stream fixture. Measure stale/duplicate memory, unsupported conclusions,
missed revisions and downstream task quality under equal retrieval/context cost.
Require a directly relevant baseline and independent review before a skill change.
