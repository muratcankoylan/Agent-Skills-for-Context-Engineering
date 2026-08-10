# Researcher Operating System

Current corpus counts, source digests, compatibility status, and unresolved-reference status are generated in the [live corpus inventory](generated/corpus-summary.md). Historical reports retain the values measured at their dated snapshot.

The public/private boundary is defined by `governance/export-policy.yaml` and `scripts/validate_export.py`. Real private plans and receipts stay under ignored local paths; only validated projection trees are proposed for public review.

Cross-runtime records, typed IDs, private artifact references, and candidate freeze receipts use the SPEC-003 contracts in [`schemas/README.md`](schemas/README.md). Existing claims, mechanisms, run state, and queues remain in place behind validated legacy adapters.

This directory defines the repo-native workflow for turning external research into skill changes. It is intentionally file-based so agents can inspect, resume, and audit work without requiring a hosted scheduler.

## Mission

Maintain this repository as the source of truth for context engineering and harness engineering by continuously:

1. Discovering credible papers, engineering posts, benchmark reports, and lab notes.
2. Evaluating sources against explicit rubrics.
3. Extracting implementable mechanisms, not generic takeaways.
4. Mapping mechanisms to new skills, existing skill updates, or reference-only notes.
5. Preparing reviewable PRs after gates pass.

Agents may prepare branches and PR content after passing gates, but humans decide what merges. No workflow in this directory authorizes auto-merge.

## Lifecycle

```text
discover -> triage -> evaluate -> extract -> map -> draft -> validate -> prepare-pr -> human-merge
```

| Stage | Output |
| --- | --- |
| Discover | Candidate source with URL, author, date, and why it matters |
| Triage | Source class and exclusion check from `source-registry.md` |
| Evaluate | JSON matching `templates/source-evaluation.json` |
| Extract | Mechanisms, artifacts, evidence, and failure modes |
| Map | Skill proposal using `templates/skill-proposal.md` |
| Draft | Skill or reference changes in normal repo structure |
| Validate | Rubric scores plus deterministic structure checks |
| Prepare PR | PR-ready summary, test plan, and unresolved review notes |

## Directory Map

- `source-registry.md` - source classes, priorities, and rejection rules.
- `mechanisms/registry.jsonl` - accepted mechanisms used for novelty and skill-delta checks.
- `mechanisms/ledgers/` - append-only accepted and rejected mechanism promotion events.
- `claims/index.jsonl` - provenance for volatile, numeric, or benchmark claims.
- `corpus/index.json` - machine-readable map of skills, mechanisms, claims, and activation scenarios.
- `benchmarks/` - adversarial scenarios and goldens for the researcher harness.
- `schemas/` - digest-pinned durable-record schemas and cross-language conformance evidence.
- `artifacts/` - private CAS contract and ignored runtime root.
- `rubrics/content-curation.md` - gates for accepting external content.
- `rubrics/skill-change.md` - gates for changing skills.
- `rubrics/harness-change.md` - gates for changing research or evaluation harnesses.
- `rubrics/pairwise-skill-revision.md` - comparison rubric for competing skill drafts.
- `templates/source-evaluation.json` - machine-readable evaluation shape.
- `templates/skill-proposal.md` - source-to-skill delta proposal format.
- `templates/mechanism-proposal.jsonl` - run-local mechanism promotion proposal format.
- `templates/research-thread.md` - durable thread log for long-running agents.
- `runbooks/autonomous-research-loop.md` - operating loop for autonomous researchers.
- `runbooks/pr-readiness.md` - pre-PR checklist.
- `scripts/validate_repo.py` - deterministic repository and harness validator.
- `scripts/validate_run.py` - publish-readiness validator for a single research run.
- `scripts/research_loop.py` - creates durable run directories and validation reports.
- `scripts/novelty_check.py` - checks proposal overlap against existing skills and prior runs.
- `scripts/compare_skill_revisions.py` - deterministic pre-check for pairwise skill revisions.
- `scripts/check_activation_cases.py` - deterministic activation-boundary regression checks.
- `scripts/run_benchmarks.py` - deterministic benchmark harness with optional history recording.

## Governance Rules

1. Keep rubrics harder to change than outputs. A source cannot relax the rubric used to admit it.
2. Cite only retrieved sources. If a source failed to load, record the failure and do not cite it as evidence.
3. Separate source quality from skill quality. A strong paper may still produce no actionable skill delta.
4. Prefer updating existing skills over adding new ones unless the activation scenario, mechanism, and operating procedure are distinct.
5. Require human review when evidence is anecdotal, source claims are volatile, or a skill change affects repo-wide guidance.
6. Keep all generated skill changes aligned with `template/SKILL.md`, the 500-line cap, and manifest sync rules.

## Local Commands

```bash
python researcher/scripts/validate_repo.py
python researcher/scripts/validate_run.py --run-dir researcher/runs/<run-id>
python researcher/scripts/research_loop.py init --title "Source title" --url "https://example.com/source"
python researcher/scripts/novelty_check.py --file researcher/fixtures/skill-proposals/harness-engineering-proposal.md
python researcher/scripts/compare_skill_revisions.py skills/evaluation/SKILL.md skills/advanced-evaluation/SKILL.md
python researcher/scripts/check_activation_cases.py
python researcher/scripts/run_benchmarks.py
```

## Current Published Research Skills

The first published skill from this operating system is `harness-engineering`. Skill evolution remains internal to this directory until the process has enough examples and validation data to justify a standalone published skill.
