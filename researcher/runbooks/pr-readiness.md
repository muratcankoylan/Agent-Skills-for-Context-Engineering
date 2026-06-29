# PR Readiness Runbook

Use this checklist before an autonomous researcher prepares a PR.

## Required Artifacts

- [ ] Source evaluation JSON exists and matches `../templates/source-evaluation.json`.
- [ ] Skill proposal exists and names the target path.
- [ ] Skill proposal records novelty-check command, verdict, max mechanism overlap, and top mechanism overlaps.
- [ ] `validate_run.py --run-dir <run>` passes and `run-state.json` is at `pr_ready` or `closed`.
- [ ] Mechanism proposals are either promoted, rejected, or explicitly deferred with rationale.
- [ ] Research thread records discovery, evaluation, and draft decisions.
- [ ] All cited sources were retrieved successfully.
- [ ] Rejected or partial sources are recorded as gaps, not cited as evidence.
- [ ] Human review notes are included when any rubric routes to `HUMAN_REVIEW`.

## Skill Structure Checks

- [ ] New or changed `SKILL.md` has YAML frontmatter with `name` and `description`.
- [ ] Skill directory name matches `name`.
- [ ] `SKILL.md` is under 500 lines.
- [ ] Description is third person and describes task boundaries rather than keyword triggers.
- [ ] Skill contains practical guidance and gotchas.
- [ ] Volatile evidence is in `references/`, not overloaded into the main skill.
- [ ] Integration section references related skills by plain name.

## Sync Checks

If publishing a new skill, update:

- [ ] `README.md`
- [ ] root `SKILL.md`
- [ ] `.claude-plugin/marketplace.json`
- [ ] `.plugin/plugin.json` when description or version needs to reflect the new scope
- [ ] `CLAUDE.md` and `CONTRIBUTING.md` if authoring or packaging rules changed

## Review Checks

- [ ] The proposal explains why this is not duplicate content.
- [ ] The proposal cites accepted mechanisms that overlap and explains why the delta is still needed.
- [ ] The PR body lists risks and gaps.
- [ ] The test plan includes deterministic structure checks.
- [ ] `python3 -m unittest researcher.scripts.tests.test_skill_frontmatter` passes.
- [ ] `python3 researcher/scripts/validate_platform_compat.py --require-reference-validator` passes.
- [ ] `python3 researcher/scripts/validate_repo.py --strict` passes.
- [ ] `python3 researcher/scripts/skill_health.py --strict --no-history` passes.
- [ ] Activation regression cases and researcher benchmarks pass, or failures are listed as risks.
- [ ] The PR body states that merge requires human approval.
- [ ] No secrets, credentials, or private source material are included.

## Stop Conditions

Stop before PR creation when:

1. Any source was not retrieved but is needed for a claim.
2. A rubric changed during the same run and no independent review occurred.
3. Manifest sync is ambiguous.
4. The draft adds a new skill but activation scenario or mechanism overlaps strongly with an existing one.
5. The user has not approved pushing to GitHub.
