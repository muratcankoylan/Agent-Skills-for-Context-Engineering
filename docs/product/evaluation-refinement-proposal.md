# Evaluation refinement proposal: derived-record conformance

Status: candidate guidance, not promoted or effectiveness-validated

## Evidence and novelty disposition

The local observation implementation exposed a reproducible gap: a resumed source checkpoint could refer to intact captured bytes while containing edited lead fields. Hash-only validation did not establish that the title, URL or summary came from the response. The implementation now replays captured responses through a bounded offline transport and compares ordered extracted fields. The independent regression/ablation is in `researcher/scripts/tests/test_research_pipeline_adversarial.py`; ordinary known-answer parsing tests remain in `test_source_connectors.py`.

This strengthens `deterministic-first-validation`, not a new mechanism. Existing evaluation guidance already requires deterministic checks before model judgment; self-improvement guidance already requires raw-artifact binding and locked evaluators. Do not add a duplicate registry entry or claim novel scientific insight from this engineering repair.

## Candidate wording

Add a short section under the evaluation skill's practical guidance:

> When a deterministic parser derives records from captured responses, hashes establish byte integrity, not that a displayed title, URL, result or score came from those bytes. Re-extract the fields under the recorded query, parser version and limits, then compare the ordered output before accepting a resumed checkpoint. Keep original captures immutable and use a replay transport with no network fallback. Missing redirect or timing metadata is an explicit unsupported case, not permission to invent it.

> Test valid known-answer extraction separately from tampered derived fields, missing or duplicated captures, and partial outcomes. Reusing the same parser can reproduce its own bug, so replay consistency is not semantic truth. A hash-only versus replay ablation measures this mechanism; it does not show that this skill's wording improves an agent without a separate baseline/candidate/control effectiveness experiment.

The private full candidate is retained with this implementation's runtime artifacts. Its description, activation rules and integration boundaries are unchanged. A frontmatter/placeholder check validates its packaging, not its usefulness. No accepted skill, mechanism ledger, claim index or corpus index was changed by this proposal.

## Experiments and acceptance

The mechanical experiment pairs a hash-only baseline with the replay implementation on valid outputs and derived-record/capture mutations. Report false acceptance and false rejection by case, including partial/error outcomes, and preserve all observations. It is a finite regression/ablation, not an estimate of real-world adversarial failure probability. Parser known-answer tests are separate because both replay and extraction can share a defect.

The later Stage 3 study must compare frozen current skill, candidate skill and oracle-control guidance on identical vulnerable starter code and hidden grader inputs. Give the implementation agent only its assigned skill and task; keep evaluator source and held-out mutation families outside its context. Use the approved runner, paired independent task families, preregistered stopping/budget rules, failed-result accounting and the methodology in `researcher/benchmarks/PLAN.md`. No score-bearing model calls have occurred for this candidate.

Only after that study and separate review should a revision update the skill body and metadata, existing mechanism description/evidence, corpus activation scenarios, fixture coverage and generated inventory. Add claim provenance for any new quantitative or volatile claim. Recheck body activation/integration consistency even if frontmatter is unchanged. A human-approved repository change and deployment activation remain distinct decisions.
