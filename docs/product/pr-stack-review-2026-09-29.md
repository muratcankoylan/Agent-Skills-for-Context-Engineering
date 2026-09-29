# Governance and runtime PR stack review, 2026-09-29

## Decision summary

The twelve PRs below already form one exact linear ancestry chain. They are a governance foundation plus an isolated managed-Agents transport, not the complete research service currently tested in the local integration checkout. Preserve their ordering and retain the separately reviewed production closure. Do not describe merging the existing stack as deploying the research organization.

The review found three concrete release issues: current repository protection does not require successful checks or an approving review; the published dependency locks retain current advisories; and PR #134 omits two transport fixes already present locally. In addition, a real aggregate lifecycle rehearsal rejects merging the entire stack directly into current `main`, even though Git reports a conflict-free fast-forward. Sequential lifecycle transitions are required.

This report records read-only GitHub inspection and credential-free local tests, not a GitHub approval, settings change, deployment, or paid provider run. No remote branch, PR, comment, merge setting, or ruleset was changed. A candidate branch was prepared only in an isolated local clone.

## Immutable review inputs

Repository: [muratcankoylan/Agent-Skills-for-Context-Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering).

- Observed protected-default commit: `6dbe1a1d868eab51a3bc9011b0f55e2891513e40`.
- Local integration checkout HEAD: `c6cd52017b247804373339e1c3c103d42554b0a1`, exactly PR #131.
- Existing PR stack tip: `9639dda3c5b2b6fb3ddfd88a3478c3dc90aa7c54`, PR #134.
- Stack-tip tree: `d1503a3e550eda804f5583e3ce6f0278a94e23ac`.
- Local rehearsal branch: `codex/pr-stack-rehearsal-20260929`, in an isolated clone only.

Every PR was inspected through fresh GitHub metadata: exact base/head identities, changed-file inventory, commits, body, reviews, draft state and check rollup. Source review was risk-focused, not a line-by-line certification of all generated files or every specification. The per-PR scope below states what was actually examined. Historical counts in PR descriptions are not substituted for the tests personally rerun here.

## Existing dependency stack

```text
main@6dbe1a1
  -> #121 -> #122 -> #123 -> #124 -> #125 -> #126
  -> #127 -> #128 -> #129 -> #130 -> #131 -> #134
  -> separately reviewed unpublished production closure
```

| PR | Exact reviewed head | Current base | Review state | Current disposition |
| --- | --- | --- | --- | --- |
| [#121](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/121) | `aed122474c31c7afd2b7e90d8f2efc4ef6305278` | `main@6dbe1a1` | Open, not draft | First human-review/merge candidate; foundation only |
| [#122](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/122) | `0030fdbf8da082f8029972cbe04140c12ce508e7` | #121 | Draft | After #121; supervised prompt source, no runtime authority |
| [#123](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/123) | `48e17e8b7de61925a644ad5e62f5609525bcadc0` | #122 | Draft | After #122; SPEC-003 terminal amendment only |
| [#124](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/124) | `c91780589ed79e1fcfc034894d02e52981983ab0` | #123 | Draft | After #123; SPEC-000 terminal amendment only |
| [#125](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/125) | `c50cc4cdbc0c5a07714ea6ef105affa12e6c4215` | #124 | Draft | Containment improvement; carry patched dependency follow-up before release |
| [#126](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/126) | `7c0c92d20244ab7fa03edcbe1fd5851b24e5445c` | #125 | Draft | After #125; zero-call resume substrate, not provider activation |
| [#127](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/127) | `ec6f25c609029474b7bfcbebba20d7792f3d01dd` | #126 | Draft | After #126; SPEC-001 terminal amendment only |
| [#128](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/128) | `d1fc8c2e3d7cbacd2c99f2d730ae6b92f91a06af` | #127 | Draft | After #127; SPEC-002 terminal amendment only |
| [#129](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/129) | `f5f1dda3e0f42d8e680f01917786f67fd60e3fa1` | #128 | Draft | After #128; protected-default predecessor gate, not protected CI by itself |
| [#130](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/130) | `54580840f75556290f32ffcbaa8342bb00ea9343` | #129 | Draft | After #129; evaluator provenance machinery |
| [#131](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/131) | `c6cd52017b247804373339e1c3c103d42554b0a1` | #130 | Draft | After #130; dormant offline authority semantics |
| [#134](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/134) | `9639dda3c5b2b6fb3ddfd88a3478c3dc90aa7c54` | #131 | Draft | Transport-only; include local transport correction before managed-session release |

All twelve were reported `MERGEABLE`/`CLEAN` against their current branch bases. This is neither approval nor production readiness. #121 has one bot `COMMENTED` review and one maintainer `COMMENTED` review, neither approval; the other eleven have no submitted reviews. The existing bot finding on #121 concerned a `HEAD^` lifecycle fallback and is corrected in the reviewed `aed1224` head: unsupported/unanchored events fail, PRs use the exact base, and manual validation derives the default-branch merge base.

## Per-PR scope and observed checks

`L+I` below means the exact PR head was checked out in an isolated clone and its own lifecycle validator was run against the exact GitHub base, followed by its own generated-inventory check. For #129 onward, protected-default authority was separately pinned to observed `main@6dbe1a1`. Every `L+I` passed. Inventory digests are output prefixes, not substitute commit identities.

| PR | Diff/source scope actually reviewed | Hosted checks observed | Personally rerun |
| --- | --- | --- | --- |
| #121 | 61-file manifest; workflow/action/dependency changes, lifecycle adoption/authority model, public-file boundary implementation, inventory/ADR closure and tests sampled | `validate`, site `build`, Bugbot success on Aug 15; site `deploy` skipped | L+I; inventory `1f84987dc1d4` |
| #122 | 11-file manifest; prompt-bundle contract and verifier independence/authority clauses, inventory registration and regression diff | `validate` success Aug 15 | L+I; `e18fe120351e` |
| #123 | Complete normative ADR-0007 and SPEC-003 lifecycle diff; generated/test manifest changes | `validate` success Aug 15 | L+I; `2cfc43c9223d` |
| #124 | Complete normative ADR-0008 and SPEC-000 lifecycle diff; generated/test manifest changes | `validate` success Aug 15 | L+I; `1f922e2f5367` |
| #125 | 21-file manifest; zero-call CLI removal of paid execution, bounded planner input/cost validation, current lock risk; report/test changes sampled | `validate` success Aug 15 | L+I; `a68f4881f572`; unchanged runner code exercised at tip |
| #126 | 21-file manifest; engine claim-before-effect/unknown reconciliation, source freeze, filesystem confinement, store bounds and crash/budget tests sampled | `validate` success Aug 15 | L+I; `86862cd0d756`; unchanged runner code exercised at tip |
| #127 | Complete normative ADR-0009 and SPEC-001 lifecycle diff; inventory fixture adjustment | `validate` success Aug 15 | L+I; `00bcaa9f84dd` |
| #128 | Complete normative ADR-0010 and SPEC-002 lifecycle diff; inventory fixture adjustment | `validate` success Aug 15 | L+I; `dac808856b5e` |
| #129 | Complete workflow and lifecycle implementation diff, including promoted predecessor bytes/ADR binding and Git environment isolation; new tests sampled | `validate` success Aug 15 | L+I; `8aa141722074` |
| #130 | 12-file manifest; evaluator extraction, canonical non-symlink reads, executable-component/receipt binding and governance orchestration diff; tests sampled | `validate` success Aug 15 and Sep 10/11 | L+I; `2ace858d7155` |
| #131 | 14-file manifest; exact typed predicates, closed allow paths, synthetic offline identity/SoD boundary, intrinsic datetime schemas, receipt checks and adversarial tests sampled | `validate` success Aug 16 and Sep 10/11 | L+I; `59df505ba5bb`; 362 Python tests; governance closure 2,142 decisions |
| #134 | All five changed files; complete transport, stdlib CI contract and request/response tests, plus byte comparison to local fixes | Python 3.11/3.12 `offline-contracts` and `validate` success Sep 11 | 39 transport tests; lifecycle; strict repository/platform/public/inventory checks |

The transport run [34544934850](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/actions/runs/34544934850) reports exact head `9639dda3c5b2b6fb3ddfd88a3478c3dc90aa7c54`. Hosted checks have not been rerun here, and do not include unpublished integrated service code.

## Executed stack scenarios

1. **Exact-parent lifecycle progression:** all eleven #121–131 heads passed lifecycle plus inventory. #134 passed lifecycle against #131. No revision-2 successor was fabricated or accepted.
2. **Whole-stack Git integration:** `merge-base --is-ancestor(main, tip)` passed. `merge-tree --write-tree(main, tip)` returned `d1503a3e550eda804f5583e3ce6f0278a94e23ac`, exactly the tip tree, with no conflicts.
3. **Whole-stack lifecycle integration:** tip validator against `--base-ref main --promoted-ref main` rejected four `INVALID_LEGACY_LIFECYCLE_ADOPTION` findings for SPEC-000 through SPEC-003. #121 introduces normalized lifecycle metadata; later PRs terminally amend those revisions. One cumulative transition skips that adoption boundary. This is an expected safety rejection, not a reason to disable the gate.
4. **Cumulative foundation regression:** exact #131 source, Python 3.11, 362 tests passed in 100.415 seconds. Existing integration-venv dependencies were used; this was not a new hash-locked Python installation.
5. **Managed transport contract:** exact #134 source, 39 tests passed with injected transport/worker fixtures, no API or model calls. This does not validate a paid remote session.
6. **Tip packaging and public boundary:** its own strict repository validator passed with 0 errors/0 warnings, 17 skills; compatibility passed 4 layouts; public-file scan passed 574 tracked files; inventory passed 328 records/205 sources.
7. **Runner crash/cost/source isolation:** exact tip package installed from its lock with install scripts disabled, Node 24.19.0; typecheck plus 82 tests passed. Both deny-instrumented router/effectiveness dry plans passed with zero SDK calls. Tests include two-coordinator exclusion, unknown claims preventing restart effects, source mutation, immutable manifests, bounded retries, and budget denial. This is not the hosted Node 22 environment or a paid benchmark.
8. **Current dependency vulnerability inventory:** `npm audit --omit=dev` on exact tip locks failed: SDK package has 3 affected package records (1 high, 2 moderate) through Undici; TypeScript schema package has 1 high `fast-uri` record with 5 advisories. Advisories are evidence of affected dependencies, not proof this application has an exploitable network path.

No provider credential was passed to PR code, no authenticated workflow was launched, and no paid model call occurred during this review. The isolated repository and its ignored test dependencies remain available for audit; the integration checkout was not reset or rebased.

## Implemented CI follow-up in the local integration candidate

The review added `merge_group: checks_requested` to the validation workflow and bound both lifecycle authority inputs to that event's exact nonzero `merge_group.base_sha`. It requires `merge_group.base_ref` to equal `refs/heads/<default branch>` and rejects malformed, zero, multiline or mismatched inputs before Git access. A synthetic queue head or newly fetched branch tip cannot become the promoted authority. The existing first five step names and PR/push/manual behavior are preserved.

Ten new executable tests run the workflow's actual extracted Bash script in a sanitized environment against a bounded fake Git, not a second reimplementation of the selector. They cover SHA-1/SHA-256, a non-`main` default branch, unrelated event fields, absent Git objects, malformed event inputs, stacked PR separation, legacy events and unsupported `pull_request_target`. These tests passed locally; they do not claim a hosted merge-queue run or alter GitHub settings. The original combined-stack lifecycle rejection remains intentional: event coverage does not authorize collapsing adoption and amendment transitions.

## Findings and corrections required for the release candidate

### R1: Repository settings do not enforce the stated human/check boundary

Read-only REST inspection of ruleset `11425130`, `Main Branch Protection`, found an active PR requirement and conversation resolution, but `required_approving_review_count: 0`, no required status-check rule, no stale-review dismissal, no last-push approval, and repository administrator-role bypass with `bypass_mode: always`. The classic branch response also lists no required contexts.

Correction: obtain explicit administrator approval to require the stable validation/release checks and an independent approving review, dismiss stale approvals, require last-push approval and applicable CODEOWNERS, and restrict bypass to a documented emergency procedure. Keep repository-write/delivery credentials outside untrusted PR jobs. The candidate's validator/workflow cannot protect itself from a hostile candidate that changes or removes that validator. A protected required workflow or protected-default validation copy is a separate control. Do not put API secrets on `pull_request_target` followed by candidate checkout/execution.

### R2: One conflict-free aggregate merge is not a valid lifecycle transition

The experiment above proves the mismatch. Preserve #121 as the adoption transition, then merge later layers in exact dependency order, refreshing base/protected-default references and hosted checks after each human merge. Prefer merge commits for ancestry preservation. If squash/rebase is selected, explicitly restack descendants and regenerate receipts; do not rely on old check runs or duplicate a prior PR's changes. Do not batch multiple governed lifecycle transitions into one merge-queue group without testing its actual base-to-candidate lifecycle interval.

### R3: Published transport omits already-tested local protocol corrections

PR #134's create path treats HTTP 201 as `HTTP_ERROR`, and its test explicitly expects that rejection. A created session can therefore be classified as an ambiguous failure before preserving its identity. Its native transport also returns uninterpreted repeated headers to a case-folding boundary that rejects repeated non-framing header names. Local changes correctly scope accepted HTTP 201 to create, preserve malformed-session recovery identity, and retain only relevant framing headers after duplicate-framing validation.

The files are **not byte-identical**:

| File | PR #134 SHA-256 | Local reviewed SHA-256 |
| --- | --- | --- |
| `researcher/service/openai_agents.py` | `38add7a3ca642a947fea2bab2d82bf9fb5f8e103ad18755d7d297a1e9fbb8f20` | `284a9c802eb72696ab972d5f14ee290c6f9a9d006b2d7ee050361161a4305b91` |
| `researcher/service/tests/test_openai_agents.py` | `71b529e7b0e7d6621d7ebdbd4133e6a5e6f94fb6e633b2ccbc9a242e7abf44fd` | `a94c360a5e24cfd51742be6c40fcfd5e587c01ad87b253c88132f4105c5cd302` |

Carry the additive local correction after #134, including the three new tests and expanded recovery cases. Do not copy old PR bytes over the locally hardened version. Managed-session lifetime, cost, reconciliation, and remote code execution remain different contracts from this HTTP transport.

### R4: Historical dependency green checks do not cover current advisories

The reviewed stack has no current production dependency-audit gate and retains affected locks. The local SDK override pins Undici `6.28.1`; the schema override pins `fast-uri` `3.1.7`. They, their regression tests and current audit gates need to travel in the production closure, not remain workstation-only. The schema port-injection advisory is [GHSA-qw65-cvwx-89v3](https://github.com/advisories/GHSA-qw65-cvwx-89v3). The current SDK audit includes [GHSA-vxpw-j846-p89q](https://github.com/advisories/GHSA-vxpw-j846-p89q) and [GHSA-m8rv-5g2x-5cg5](https://github.com/advisories/GHSA-m8rv-5g2x-5cg5), among others. Re-audit exact release locks rather than permanently accepting a dated zero-vulnerability result.

### R5: Existing runtime PR does not contain the tested product

In the reviewed local HEAD, `researcher/service/`, `apps/`, `docs/product/`, the event-journal package and the new research/retrieval scripts are untracked. PR #134 adds only transport documentation/module/test, package initializer and dedicated CI. No merge of these twelve PRs publishes the full service, cumulative OpenAI authority, connector suite, candidate pipeline, organization coordinator, private UI, recovery bundle, deployment package or their scenario tests.

The local integration also includes tracked changes outside those directories: inert legacy-loop boundaries; revised spec proposals; schema/artifact semantics; dependency locks; public export checks; corpus/claim inventory; README; and removal of a formerly tracked benchmark-history runtime artifact. Export one explicit reviewed file closure, keep private state and `.env.local` excluded, regenerate inventory on each slice, and validate the actual Git index/release tree. Copying an entire dirty directory or only `researcher/service/` is not a valid dependency closure.

## Proposed production follow-on slices

These are review units, not new remote PRs or accepted specifications:

1. **Release safety and transport repair:** 201/header correction, dependency pins/audits, secret-free workflow permissions, public-runtime exclusions and merge-queue event coverage.
2. **Portable storage and provenance:** schema/artifact correctness, journal identities and deterministic fixtures, with Python/TypeScript parity and exact version/digest evidence.
3. **Bounded retrieval and context:** connector contracts, capture/replay, primary-reader profiles, citation spans, source-quality scenarios and configuration; no agent-driven arbitrary credential destinations.
4. **Research organization and evaluation:** persistent reservation authority, role pipeline, exact frozen candidate reviews, gold-isolated paired evaluations, restart/failure scenarios and claim-limited reporting.
5. **GitHub runtime/delivery and operations:** approved-ref builds, separately scoped execution/delivery credentials, durable state outside ephemeral hosted-runner disks, exact-head PR preparation, notifications, private UI and restore/release procedures.

The root release plan may combine tightly coupled files differently, but every slice needs its own complete import/config/test/documentation closure. The managed Codex/Agents API adapter must remain distinguishable from native synchronous OpenAI calls and from the development client's own tools. A GitHub Actions trigger is not itself durable storage, an agent supervisor, or hard spending enforcement.

## Operator merge procedure

1. Freeze the exact candidate SHAs and the approved patch closure. Re-read remote PR metadata immediately before action.
2. Review and apply separately authorized repository/environment protections. Keep paid API and repository-write secrets unavailable to untrusted CI.
3. Human-review #121; run current exact-base lifecycle/public/dependency checks; merge through the approved method.
4. Retarget/restack the next child only after parent integration, recompute main/base identities, rerun required hosted checks, and review the resulting diff. Repeat through #134.
5. Integrate reviewed follow-on slices, never credential/state files. Rebuild the release from that clean commit, not a developer checkout.
6. Run the offline GitHub release rehearsal, fault/restart/restore tests and narrowly authorized live canaries against the same build. Preserve the existing cumulative OpenAI allowance and uncertain reservations across migration.
7. Approve activation separately. Initial operation should prepare draft proposals under limited credentials and human merge, with observable stop/recovery paths. A green transport test or a critic abstention is not evidence of scientific effectiveness.

See the [production exercise](production-exercise-2026-09-29.md) for prior local integration measurements. Those results do not become exact-PR or hosted-release evidence until the reviewed source closure is published and rerun.
