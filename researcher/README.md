# Researcher Operating System

Current corpus counts, source digests, compatibility status, and unresolved-reference status are generated in the [live corpus inventory](generated/corpus-summary.md). Historical reports retain the values measured at their dated snapshot.

The [specification program](../docs/specs/README.md) defines the dependency-ordered contracts for evolving this file-based loop into a durable autonomous organization. Published drafts are not accepted automatically; lifecycle changes require human-merged pull requests.

The public/private boundary is defined by `governance/export-policy.yaml` and `scripts/validate_export.py`. Real private plans and receipts stay under ignored local paths; only validated projection trees are proposed for public review.

Cross-runtime records, typed IDs, private artifact references, and candidate freeze receipts use the SPEC-003 contracts in [`schemas/README.md`](schemas/README.md). Existing claims, mechanisms, run state, and queues remain in place behind validated legacy adapters.

The standalone `governance/authority-vocabulary.schema.json` describes the future SPEC-000 revision-2 authority registry and its synthetic offline fixture manifest. It is deliberately outside the SPEC-003 durable-record registry: SPEC-000 must bind the schema and registry independently by exact path, version, and digest before either can become constitutional input. The dependency-light loader accepts only the code-pinned canonical schema bytes, while CI independently meta-validates those bytes as Draft 2020-12. While revision 1 remains current, inventory reports the schema as unbound machinery and no registry, fixture manifest, or conformance receipt exists.

The version-2 registry uses actor-specific typed predicate sets, exact `{spec_id, revision, minimum_runtime_stage}` requirements, an operation-specific grant, and a componentwise maximum-effect ceiling. Effect codes are incomparable unless equal; target and state-transition counts must each narrow independently. The schema admits `implemented`, `verified`, or `operational` minima, and every current profile requires `operational`; fixtures also supply preimplementation, terminal, missing, and mismatched synthetic evidence to prove denial. All fixture evidence is explicitly `synthetic_offline`, and identity fixtures use only canonical `synthetic:<token>` labels: these class-policy test inputs are not claims about a current promoted runtime record or authenticated provider identity.

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
- `../governance/authority-vocabulary.schema.json` - dormant SPEC-000 authority-catalog and synthetic-fixture contract; not a runtime evidence schema.
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
- `scripts/validate_public_repo.py` - tracked-tree guard against workstation paths and credential material; CI also runs Gitleaks over Git history.
- `scripts/validate_spec_lifecycle.py` - compares proposed specification changes with an exact transition base and requires replacement predecessors to be byte-identical on a separately pinned protected-default tree.
- `scripts/validate_authority_contract.py` - owns the closed authority registry, typed predicates, effect-ceiling and exact-dependency algebra, synthetic fixtures, policy closure, evaluator bundle, and offline conformance-receipt semantics consumed by lifecycle and governance validation.
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

Authority conformance is not runtime authorization. Its receipt is scoped to offline class-policy conformance and declares that it grants no runtime authority; individual decisions carry the same explicit offline/no-runtime boundary. Conformance also closes the policy lifecycle marker, actor descriptors, protected surfaces, emergency controls, amendment procedure, allow reason semantics, and the exact default-deny form rather than attesting only finite cases. Explicit deny rules are forbidden in this oracle because a selectively targeted denial could preserve every sampled decision while disabling a reviewed action. Runtime actor class, dependency state, assignment and fence, and capability grant must eventually come from trusted authenticated resolvers; caller-supplied fixture fields, synthetic identities, or evidence tuples never satisfy that boundary.

## Local Commands

```bash
python researcher/scripts/validate_repo.py
python researcher/scripts/validate_spec_lifecycle.py \
  --base-ref origin/main \
  --promoted-ref origin/main
python researcher/scripts/validate_run.py --run-dir researcher/runs/<run-id>
python researcher/scripts/research_loop.py init --title "Source title" --url "https://example.com/source"
python researcher/scripts/novelty_check.py --file researcher/fixtures/skill-proposals/harness-engineering-proposal.md
python researcher/scripts/compare_skill_revisions.py skills/evaluation/SKILL.md skills/advanced-evaluation/SKILL.md
python researcher/scripts/check_activation_cases.py
python researcher/scripts/run_benchmarks.py
```

## Current Published Research Skills

The first published skill from this operating system is `harness-engineering`. Skill evolution remains internal to this directory until the process has enough examples and validation data to justify a standalone published skill.
