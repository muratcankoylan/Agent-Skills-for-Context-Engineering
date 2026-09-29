# Portable harness: local verification results

Date: September 7, 2026 (America/Toronto); experiment receipt timestamp September 8 at 00:40:24 UTC. Status: local development result, not production acceptance. The [paper protocol](portable-harness-paper-protocol.md) is proposed methodology, not a completed confirmatory study.

## Implemented and exercised

The new provider-neutral runner imports verified source campaigns, freezes the input and two predeclared data policies, materializes candidates, evaluates the complete paired population, and persists all outcomes plus an inert proposal or rejection. It has no candidate-code execution, model provider, live-policy update or repository-write action. It works from an ordinary terminal outside the checkout through its absolute script path.

Three specialized reviews covered architecture/owner contracts, evaluation methodology and adversarial integrity. The resulting fixes include strict campaign-to-child binding; canonical JSON comparisons that distinguish booleans from integers; bounded non-aliasing CAS reads; cooperative whole-invocation time checks; refusal to repeat unknown outcomes; and verification that does not initialize, chmod or repair missing state. Read-only source replay requires a completed checkpointed scheduler and rejects nonempty WAL/journal files, following SQLite's [immutable-mode caveats](https://www.sqlite.org/uri.html). This is not hostile same-UID isolation; normal filesystem access timestamps can still change.

## Frozen real-data experiments

Input: two historical campaigns containing seven source lanes. The first has 56 unique work records; the follow-up has three. Their group labels do not establish independent research needs. The original arXiv timeout remains represented. Both campaigns were replayed from their original local captures, not re-fetched.

The policies and compact representation were already known from the previous sourcing work. This is a retrospective integration/negative-control experiment, not discovery by an autonomous agent or preregistered confirmation of a new optimization. Every condition is development-visible.

| Campaign | Byte budget | Original selected / bytes | Compact selected / bytes |
| --- | ---: | ---: | ---: |
| Main, 56 works | 65,536 | 2 / 65,182 | 15 / 65,288 |
| Main, 56 works | 131,072 | 29 / 130,807 | 42 / 130,801 |
| Main, 56 works | 262,144 | 56 / 214,203 | 56 / 189,526 |
| Follow-up, 3 works | 65,536 | 3 / 11,103 | 3 / 9,606 |
| Follow-up, 3 works | 131,072 | 3 / 11,104 | 3 / 9,607 |
| Follow-up, 3 works | 262,144 | 3 / 11,104 | 3 / 9,607 |

The fixed decision rule prefers greater selected-work coverage, then fewer bytes at equal coverage, and rejects any paired regression. Thus slightly greater bytes at the smallest main-campaign budget are acceptable only because coverage improves and the ceiling is respected. This is not semantic ranking. All successful rows passed exact selected-text, expanded-provenance, source/failure visibility and selection-accounting invariants.

| Direction | Outcome | Logical evaluation rows | Initial invocation elapsed |
| --- | --- | ---: | ---: |
| Original incumbent, compact candidate | `proposal_ready`, apply disabled | 12 | 3,076 ms |
| Compact incumbent, original candidate | `rejected`, no proposal | 12 | 3,068 ms |

Each direction covers the same six case/budget conditions with two policies. Reversing them and replaying them does not create independent samples. Verification and exact resume reproduced each result and every runtime file's bytes. Total measurement-driver duration, including repeated replay, was 16,091 ms. These single local timings were collected while other tests ran; they are not throughput estimates, latency SLOs or performance comparisons.

Actual new calls during this measurement: zero HTTP/DNS retrievals (network entry points patched to reject), zero model calls, zero paid calls. Earlier capture acquisition and this turn's literature research are separate work, not included in this zero-call statement. No skill, mechanism, repository commit, PR, deployed policy or production release was promoted.

## Verification

The frozen-code full Python suite passed **1,078 tests in 225.740 seconds** using Python 3.12.9. The dedicated lifecycle suite separately passed all 37 tests on Python 3.11.0 (29.287 seconds) and Python 3.12.9 (29.466 seconds), run concurrently. Both versions exercised the absolute-path CLI from outside the checkout. This verifies two interpreter versions on this machine, not clean Linux installation or cross-version replay of one manifest.

The 78 added tests comprise 22 pure evaluator cases, 37 lifecycle cases, nine campaign-replay cases and ten read-only storage cases. They include missing artifacts, malformed fields, false/zero substitution, forged scores, CAS tampering, symlinks/hardlinks/FIFOs, missing locks/directories, unchanged metadata, explicit and resumed deadlines, partial intents, source identity drift and a genuine insufficient-evidence packet failure. No-op and regression comparisons are explicit. Existing tests remain in the full suite.

Strict repository validation, platform compatibility, generated inventory consistency and affected-file Ruff checks passed. After the documentation and claim-index update, 143 publication/inventory/product-readiness tests also passed in 88.824 seconds. The 23 activation fixtures passed; these are deterministic routing smoke checks, not live model routing. Stage 0 passed three checks, of which two execute validators; it executed zero benchmark scenarios. None of these results establishes semantic research effectiveness, accepted production authority or a long-duration canary.

Gitleaks found zero leaks in a 708-file prospective publication snapshot. This covers present tracked plus non-ignored untracked files, not the Git index or repository history. Private runtime evidence stays excluded. The scan receipt records its exact input population and the previously missing tracked file; this task does not repair unrelated changes.

## Evidence and reproducibility

Ignored private artifacts under `researcher/runtime/portable-harness-20260907/`:

- `measurement-receipt.json`: input/result digests, full per-condition metrics, private original-source bindings and measured timings.
- `forward/` and `reverse-negative-control/`: manifests, content-addressed input/candidate bytes, freeze receipts, both outcomes, comparison and report.
- `run_replay_experiments.py` and `experiments.log`: bounded measurement driver and actual progress/output.
- `python-tests.log`, `platform-check.log`, `repo-check.log`, `inventory-check.log`, `activation-check.log`, `stage0.json`, `ruff-check.log`: verification output.
- `prospective-inputs.json`, `gitleaks-final.json` and `verification-receipt.json`: final publication-input bindings, scan findings and collected verification evidence.

The [runbook](portable-harness.md#run-locally-without-codex) gives the public CLI and fixture-test commands. Private captured source bodies and locators are intentionally not part of the public release. Redistributable input data, license/retention review and a validated redacted export remain necessary for independent real-data reproduction. Synthetic regression fixtures are public-safe but are not interchangeable with the captured research pool.

## Remaining production and paper gates

This result establishes a bounded data-only research-to-proposal lifecycle on one local environment. It does not establish semantic retrieval quality, novel research synthesis, stronger downstream skills, useful adaptive search, hidden-holdout integrity, authenticated provider execution or unattended production reliability.

Next: accept the missing work/experiment/evaluation/promotion owner contracts, validate a constrained provider/executor boundary, then run the blinded need-level and downstream-task protocol. Clean Linux/macOS installation, backup/restore, actual scheduled canaries, operator task testing, source licensing and reversible authorized promotion remain release gates. The local observation heartbeat is not a portable scheduler or a completed long-duration soak test.

The previously configured bounded observation heartbeat was paused during source edits and restored afterward with its original prompt, schedule and authority limits. It was not expanded to generate candidates, spend on models or promote repository changes.
