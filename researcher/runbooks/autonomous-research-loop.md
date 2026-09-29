# Supervised Research Workflow

This runbook defines how an agent can turn external research into reviewable
repository changes under operator supervision. Despite this file's historical
name, it does not authorize unattended operation, network retrieval, acceptance,
mechanism promotion, push, merge, or production activation. The launchd entry
points are inert.

## Setup

1. Create and validate the ignored runtime ledgers with `python3 researcher/scripts/loop_status.py --initialize-runtime`.
2. Create a run ID with `python3 researcher/scripts/research_loop.py init --title "..." --url "..."`.
3. Read `../source-registry.md` and select source classes for the mission.
4. Read `../mechanisms/registry.jsonl` as historical corpus memory before claiming novelty.
5. Read the relevant rubrics before evaluating anything.
6. Declare locked surfaces: rubrics, manifests, mechanism registry, and merge policy are not editable during scoring.
7. Declare editable surfaces: evaluations, proposals, drafts, run-local mechanism proposals, and local logs.

## Workflow

Repeat for the operator-selected sources until the operator stops the run:

1. Select candidates from the source registry or the reviewed manual-seed catalog. The inbox is not consumed as an executable work queue.
2. Acquire primary sources through an explicit, reviewed process outside the legacy commands. Record a bounded local evidence file with `research_loop.py retrieve`; no legacy command performs network access.
3. Record retrieval status before evaluating.
4. Apply `../rubrics/content-curation.md`.
5. Reject failed gates immediately and log why.
6. For rubric-approved or reviewed sources, extract mechanisms and artifacts into the proposal. This decision is not a legacy acceptance event.
7. Apply `../rubrics/skill-change.md` or `../rubrics/harness-change.md`.
8. Draft a proposal with `../templates/skill-proposal.md` and any mechanism proposals with `../templates/mechanism-proposal.jsonl`.
9. Run `python researcher/scripts/research_loop.py novelty --run-dir <run>` before changing published skills; registry overlap is the primary duplicate signal.
10. If multiple drafts compete, apply `../rubrics/pairwise-skill-revision.md` and run `compare_skill_revisions.py`.
11. If the proposal passes, prepare repo changes in normal repo structure.
12. Run deterministic repo and run-readiness validation and record results.
13. Prepare PR summary and test plan, but do not merge.
14. Close the run with `rejected`, `reference-only`, or `abandoned` rationale. The legacy workflow cannot write `accepted`.

## Novelty And Refresh Rules

- Before drafting a new skill, compare against the existing mechanism registry and skill boundaries.
- Use `novelty_check.py` as a fast mechanism-overlap gate, then apply human or LLM judgment for semantic novelty.
- For long-running runs, refresh upstream sources before finalizing a proposal.
- Preserve rejected ideas so future agents do not rediscover the same failed path.
- Require a pruning pass when a proposal adds multiple rules or concepts. Remove any piece that does not change behavior.
- Store raw source exports under the run's `sources/evidence/raw/` directory, never at the repository root.
- Treat run-local mechanism proposals as advisory. `research_loop.py promote-mechanisms` always fails closed, and readiness does not grant registry authority.

## Failure Handling

| Failure | Action |
| --- | --- |
| Source is unavailable | Record the missing or partial evidence and stop the dependent claim; no automatic retry or quarantine path exists |
| JSON evaluation invalid | Save raw output and route to human review |
| Evidence weak but relevant | Route to human review, do not publish automatically |
| Skill draft exceeds 500 lines | Move detail to references or reject the draft |
| Manifest sync uncertain | Stop and request human review before PR |
| Conflicting sources | Record both claims and prefer no published change until resolved |

## PR Preparation Policy

Agents may prepare PRs only after:

1. Content and skill or harness rubrics pass.
2. Deterministic checks pass.
3. Every source cited in the change was retrieved.
4. The PR body includes unresolved risks.
5. The PR states that merge requires human approval.

The user rule remains binding: do not push anything to GitHub without explicit approval.

## Handover

Before context compaction, interruption, or model handoff, update the run thread with:

- Current best candidate.
- Evaluations completed and their file paths.
- Rejected candidates and reasons.
- Open risks.
- Next action.
