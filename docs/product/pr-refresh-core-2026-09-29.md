# Core PR refresh, 2026-09-29

## Latest read-only recheck: 13:07–13:10 UTC

The second GitHub refresh found **no head, base, base-branch, draft-state, review,
or check drift** for #121–131/#134. Every exact SHA and dependency edge below
still matches [the prepared update manifest](pr-updates-2026-09-29/manifest.json).
Main remains `6dbe1a1d868eab51a3bc9011b0f55e2891513e40`; all twelve PRs remain
open/clean/mergeable against their existing bases, only #121 is non-draft, and
none has an approving review. The displayed checks are still August 15 through
September 11 runs, not fresh hosted validation of the proposed updates.

This recheck compared each current GitHub changed-file inventory with the local
exact base/head Git diff and repeated all twelve ancestry checks. All paths and
text line deltas agree. #121's binary `cdc_proof.txt` has Git `-/-` line counts
and GitHub `0/0`, a representation difference, not a changed diff. Unchanged
source retains the earlier risk-focused review; no second exhaustive review is
claimed. The full #134 transport/workflow/guide delta and the complete proposed
two-file correction were re-read.

Personally executed again, using the existing Python 3.11 interpreter with an
empty environment and no provider credentials:

- Exact remote #134: **39 transport tests passed**, 0.093 s.
- Existing detached #134 plus the two-file repair: **42 passed**, 0.090 s.
- The repair still applies to untouched #134, and its complete binary Git diff
  exactly matches the packaged SHA-256
  `d1f30929266b5d7bbedcf440a64b981edd7f218bf9fbfda16894d06194505813`.
- Exact-tip lifecycle against actual #131 base/current main: passed. The whole
  current-main-to-tip interval still rejects the same four legacy-adoption
  findings. The hypothetical post-#121 interval passed; #121 has not actually
  been promoted.
- Exact remote tip: reference compatibility passed for 17 skills/four layouts;
  strict repository validation reported zero errors/warnings; inventory passed
  with 328 records/205 sources, digest prefix `59df505ba5bb`.

Fresh effective-main-rules inspection returned only deletion, non-fast-forward,
and pull-request rules from ruleset `11425130`: zero required approvals and no
required-check rule. The separate classic branch-protection endpoint returned
404 `Branch not protected`; main's `protected: true` reflects its ruleset, not
an additional classic status-check policy. The ruleset's administrator-role
always-bypass remains present. No protection settings were changed.

**Disposition is unchanged:** retain the exact foundation chain; publish the
prepared #134 correction only through the separately authorized update action;
obtain new head-bound CI and independent review before merge. For a merge queue,
the remote root validation workflow still needs its narrowly reviewed
`merge_group` authority selection and tests. Do not infer that a path-filtered
transport check is an always-present required release gate.

The core tip's entire `researcher/service` addition is still only its initializer,
managed transport, transport tests, and guide. It contains no full organization
runner, retrieval/evaluation service, operator UI, deployment closure, or Codex
SDK execution integration. The local service and release-rehearsal workflow
remain unpublished work, not covered by these PR checks. Keep them in separately
reviewed production slices with their own dependency, recovery, budget and
scenario evidence. This recheck made no remote mutations, branch/commit changes,
package installations, paid provider calls, or SDK migration edits; only this report
was updated. The full-suite and Linux results later in this document remain
earlier, explicitly attributed evidence and were not rerun in this recheck.

## Result and scope

Fresh read-only GitHub observation at **2026-09-29 07:38 UTC** found **no changed heads or bases** in PRs #121–131 and #134 relative to the [earlier core audit](pr-stack-review-2026-09-29.md). All twelve remain open and GitHub reports `CLEAN`/`MERGEABLE` against their current proposal bases. Eleven remain drafts. None has an approving review. Historical green checks are not new CI evidence for the unpublished production harness.

This refresh re-read each PR's exact base/head, branch names, changed-file inventory, draft/review state and check summary; verified every base-to-head ancestry edge locally; re-read the full remote-versus-local transport/test delta; and reran the bounded scenarios below. Prior risk-focused reviews of unchanged source are carried forward by exact SHA, not claimed as a second complete line-by-line review. No remote write, push, merge, commit, PR edit, workflow dispatch, credential-bearing PR execution or paid API call occurred.

The only repository edit from this refresh is this report. A proposed two-file transport repair was exercised in a separate temporary archive, without editing the integrated checkout or the prior isolated Git clone.

## Exact current dependency graph

```text
main@6dbe1a1d868eab51a3bc9011b0f55e2891513e40
 -> #121 -> #122 -> #123 -> #124 -> #125 -> #126
 -> #127 -> #128 -> #129 -> #130 -> #131 -> #134
 -> separately reviewed production closure
```

Every table base is exactly the previous table head. `git merge-base --is-ancestor` passed for all twelve edges.

| PR | Exact head | Exact current base | State | Changed files | Latest observed check completion (UTC) |
| --- | --- | --- | --- | --- | --- |
| [#121](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/121) | `aed122474c31c7afd2b7e90d8f2efc4ef6305278` | `6dbe1a1d868eab51a3bc9011b0f55e2891513e40` | Non-draft | 61 | 2026-08-15T18:40:53Z |
| [#122](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/122) | `0030fdbf8da082f8029972cbe04140c12ce508e7` | `aed122474c31c7afd2b7e90d8f2efc4ef6305278` | Draft | 11 | 2026-08-15T19:03:08Z |
| [#123](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/123) | `48e17e8b7de61925a644ad5e62f5609525bcadc0` | `0030fdbf8da082f8029972cbe04140c12ce508e7` | Draft | 6 | 2026-08-15T19:12:56Z |
| [#124](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/124) | `c91780589ed79e1fcfc034894d02e52981983ab0` | `48e17e8b7de61925a644ad5e62f5609525bcadc0` | Draft | 6 | 2026-08-15T19:19:10Z |
| [#125](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/125) | `c50cc4cdbc0c5a07714ea6ef105affa12e6c4215` | `c91780589ed79e1fcfc034894d02e52981983ab0` | Draft | 21 | 2026-08-15T21:59:12Z |
| [#126](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/126) | `7c0c92d20244ab7fa03edcbe1fd5851b24e5445c` | `c50cc4cdbc0c5a07714ea6ef105affa12e6c4215` | Draft | 21 | 2026-08-15T21:59:27Z |
| [#127](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/127) | `ec6f25c609029474b7bfcbebba20d7792f3d01dd` | `7c0c92d20244ab7fa03edcbe1fd5851b24e5445c` | Draft | 6 | 2026-08-15T22:07:41Z |
| [#128](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/128) | `d1fc8c2e3d7cbacd2c99f2d730ae6b92f91a06af` | `ec6f25c609029474b7bfcbebba20d7792f3d01dd` | Draft | 6 | 2026-08-15T22:22:19Z |
| [#129](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/129) | `f5f1dda3e0f42d8e680f01917786f67fd60e3fa1` | `d1fc8c2e3d7cbacd2c99f2d730ae6b92f91a06af` | Draft | 9 | 2026-08-15T22:57:32Z |
| [#130](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/130) | `54580840f75556290f32ffcbaa8342bb00ea9343` | `f5f1dda3e0f42d8e680f01917786f67fd60e3fa1` | Draft | 12 | 2026-09-11T00:12:02Z |
| [#131](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/131) | `c6cd52017b247804373339e1c3c103d42554b0a1` | `54580840f75556290f32ffcbaa8342bb00ea9343` | Draft | 14 | 2026-09-11T00:13:54Z |
| [#134](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/134) | `9639dda3c5b2b6fb3ddfd88a3478c3dc90aa7c54` | `c6cd52017b247804373339e1c3c103d42554b0a1` | Draft | 5 | 2026-09-11T00:08:45Z |

All check results above remain historical August/September runs; this refresh did not rerun hosted CI. More detailed dispositions:

- **#121: feat(governance): publish and enforce the specification program.** Specification program, adoption, lifecycle/public-boundary gates; retain as separate first adoption interval. Current checks: `build` SUCCESS, `validate` SUCCESS, `deploy` SKIPPED, `Cursor Bugbot` SUCCESS. Two COMMENTED reviews only; no approval (the bot review references an earlier commit).
- **#122: feat(orchestration): add supervised long-horizon bootstrap briefs.** Supervised long-horizon briefs; after #121, no autonomous runtime authority. Current checks: `validate` SUCCESS. No submitted reviews.
- **#123: docs(spec-003): authorize classification invariant amendment.** SPEC-003 terminal amendment; preserve ADR-0007 and exact revision binding. Current checks: `validate` SUCCESS. No submitted reviews.
- **#124: docs(spec-000): authorize authority vocabulary amendment.** SPEC-000 terminal amendment; preserve ADR-0008 and exact revision binding. Current checks: `validate` SUCCESS. No submitted reviews.
- **#125: fix(benchmarks): contain Cursor SDK and harden evidence.** Cursor SDK containment; carry reviewed lock/security follow-up before release. Current checks: `validate` SUCCESS. No submitted reviews.
- **#126: test(benchmarks): add private manifest resume substrate.** Private manifest/resume substrate; zero-call tooling, not paid provider activation. Current checks: `validate` SUCCESS. No submitted reviews.
- **#127: docs(spec-001): authorize snapshot identity amendment.** SPEC-001 terminal amendment; preserve ADR-0009 and exact revision binding. Current checks: `validate` SUCCESS. No submitted reviews.
- **#128: docs(spec-002): authorize projection-boundary amendment.** SPEC-002 terminal amendment; preserve ADR-0010 and exact revision binding. Current checks: `validate` SUCCESS. No submitted reviews.
- **#129: fix(governance): require promoted revision predecessors.** Protected-default predecessor gate; preserve gate, add isolated merge-group CI coverage separately. Current checks: `validate` SUCCESS. No submitted reviews.
- **#130: Extract authority contract and bind evaluator provenance.** Evaluator contract/provenance boundary; conditional foundation layer. Current checks: `validate` SUCCESS, `validate` SUCCESS, `validate` SUCCESS. No submitted reviews.
- **#131: Harden offline authority vocabulary semantics.** Offline authority vocabulary hardening; dormant authority, not identity/production activation. Current checks: `validate` SUCCESS, `validate` SUCCESS, `validate` SUCCESS, `validate` SUCCESS. No submitted reviews.
- **#134: feat(runtime): add bounded OpenAI Agents API transport.** Bounded managed-Agents transport; apply standalone 201/header repair before release. Current checks: `offline-contracts (3.11)` SUCCESS, `validate` SUCCESS, `offline-contracts (3.12)` SUCCESS. No submitted reviews.

These are conditional merge dispositions, not GitHub approvals. In particular #134 is a five-file transport addition, not the currently tested standalone service, retrieval system, organization loop, UI, tracing or deployment package.

## Smallest safe stack: distinguish Git ancestry, lifecycle, and human review

The original twelve-PR order remains the default operational plan. The following fresh experiment refines the earlier report's conservative statement that every later layer must be a separate lifecycle interval:

| Exact #134 candidate checked against | Promoted authority supplied | Result |
| --- | --- | --- |
| Current main `6dbe1a1…` | Current main `6dbe1a1…` | Rejects four `INVALID_LEGACY_LIFECYCLE_ADOPTION` findings, SPEC-000 through SPEC-003 |
| Hypothetical main after #121, `aed1224…` | Same hypothetical promoted #121 `aed1224…` | Passes |
| Current #134 base #131, `c6cd520…` | Actual current main `6dbe1a1…` | Passes |
| Hypothetical main after #131, `c6cd520…` | Same hypothetical promoted #131 `c6cd520…` | Passes |

All rows used the exact #134 lifecycle validator and candidate files. The hypothetical rows are **what-if tests, not evidence that any draft or unmerged predecessor has been promoted**.

Consequences:

1. The whole current main-to-tip interval cannot be shipped as one lifecycle transition. Git does permit a conflict-free fast-forward: `merge-tree --write-tree` returned tip tree `d1503a3e550eda804f5583e3ce6f0278a94e23ac`. Git compatibility does not override lifecycle policy.
2. For this existing core stack, the validator's minimum mechanical partition is **#121 adoption, then a cumulative #122–#134 interval**. It does not itself require eleven separate intervals after adoption.
3. Prefer the current chain and exact-parent review units unless the maintainer specifically approves consolidation. A consolidated second interval needs a newly reviewed cumulative diff, exact base/protected-default refresh and fresh hosted checks after #121 actually lands. It is not permission to merge the current #134 PR directly against its still-draft #131 base and claim the rest landed.
4. Preserve ancestry by the approved merge method. Squash/rebase or early branch deletion requires deliberate descendant restacking and fresh evidence. Do not silently close or retarget intermediate PRs based on this offline experiment.
5. Keep the production closure separately reviewed. New revision-2 successors still require their exact terminal revision-1 predecessor and decision bytes to be present on the actual protected default. This refresh did not validate the entire dirty product closure as a release candidate.

## Concrete update units

### A. Standalone #134 protocol correction: two files, no tracing dependency

Target `researcher/service/openai_agents.py` and `researcher/service/tests/test_openai_agents.py` on exact remote #134.

- In `AgentsClient._request`, accept HTTP 201 only for session creation: POST, empty path, no cancellation operation key. Reads and cancellation retain their prior status contracts.
- In `_native`, validate duplicate content-type/content-length/content-encoding/transfer-encoding as before, but forward only those framing headers. Repeated uninterpreted headers must not fail the later case-insensitive mapping check.
- Add three regression methods: `test_create_accepts_http_201_once`, `test_http_201_is_not_success_for_retrieval_or_cancellation`, and `test_native_repeated_cors_headers_do_not_reject_created_or_read_session`.
- Change the create-error status fixture from 201 to 202, and extend malformed-usage recovery identity checks to both 200 and 201.
- Retain the existing pinned, credential-free Python 3.11/3.12 transport workflow.

The minimal proposed repair was exercised in a private temporary archive of exact #134 with only those two files modified. Its **42 transport tests passed**. The durable patch is in the [update package](pr-updates-2026-09-29/README.md), not a new remote head or a commit.

The root agent independently prepared the same narrow repair in a separate
private temporary checkout, based on detached exact #134,
without the broad production overlay. Root-reported counterfactual evidence:
the new 42-test suite on the unpatched baseline produced one failure and three
errors; the patched suite passed all 42. A separate retrieval reviewer reported
42 passing tests plus 15 mock-native adversarial cases covering duplicate framing,
content-length/transfer-encoding conflicts, malformed framing, 201 rejection for
read/cancel, header/body credential handling and unread 500 bodies. Those are
collaborator-reported runs, distinct from this refresh's personally executed
42-test archive run. The root's later completed full core run passed 362 tests
in 101.085 seconds; the combined three-patch candidate passed 389 repository
tests. See the [final update package](pr-updates-2026-09-29/README.md) for exact
composition and environment limits. These are not inferred from transport tests.

### B. Keep the newer local tracing integration in the production closure

The current integrated transport now additionally imports `.tracing`, instruments `managed.http`, records typed metadata and adds the bounded `traces()` GET method with two tests. Those are useful changes but have a different import/test/privacy closure.

Copying the complete current module over standalone #134 would introduce an import of a module that #134 does not contain. Carry tracing, projection, export, CLI and their tests together in the production slice; do not include them in the two-file protocol repair by accident. Current integrated transport has **44 tests**, versus remote #134's **39** and the proposed minimal repair's **42**.

| Snapshot | Module SHA-256 | Test-file SHA-256 |
| --- | --- | --- |
| Remote #134 | `38add7a3ca642a947fea2bab2d82bf9fb5f8e103ad18755d7d297a1e9fbb8f20` | `71b529e7b0e7d6621d7ebdbd4133e6a5e6f94fb6e633b2ccbc9a242e7abf44fd` |
| Minimal proposed repair | `3a74c86a82ebdfd67a4873afb1a64bbe85694131506c6e7bf38352977b9af9a4` | `f6c526f3b1f26e6d1b0bb036c0c944130a90476fe93291e5d5c2eb08c70c8f96` |
| Current integrated transport | `073938767d3442f183047bbf4f93973f9e8b48a2ece31180ca9b7fd2203a03de` | `b56f6e3a70e78c1d880feb3010136731f64d23d343a3b3aafffaddadc0ad14f9` |

The integrated checkout's tracked HEAD remains #131, and it has neither `.github/workflows/agents-api.yml` nor `researcher/service/AGENTS_API_TRANSPORT.md`. Its object database also did not contain #134 during this refresh. Start a release export from the verified #134 lineage and overlay the approved explicit closure; do not mirror/delete files from the older dirty checkout and silently discard #134's workflow/documentation.

### C. Small CI and dependency follow-ups, not a blind copy of local workflow

The local `validate.yml` includes important fixes, but also refers to unpublished service, retrieval, UI and evaluation files. For a small core follow-up, isolate:

- `persist-credentials: false` on checkout;
- `merge_group: checks_requested` with exact nonzero event base SHA and matching default-branch base ref;
- the executable lifecycle-selector regression tests, relocated with their true dependencies or shipped with the larger service/deploy test closure;
- current dependency lock corrections and explicit audit gates.

The local SDK package pins transitive Undici `6.28.1` under `@connectrpc/connect-node`; the schema package pins `fast-uri 3.1.7` under `ajv@8.20.0`. Ship each package manifest and lock together and run that exact package's tests/audit. The schema slice also has unrelated semantic changes: do not accidentally bundle all of them into a narrowly named dependency fix. This refresh inspected the manifest differences but did **not** rerun registry audits or all JavaScript suites; the earlier audit findings remain dated evidence, not a fresh vulnerability verdict.

### D. Repository protection is still a required administrator action

Fresh REST inspection of ruleset `11425130`, “Main Branch Protection,” returned active enforcement, a pull-request rule with **zero required approvals**, no required-check rule, no stale-review dismissal, no CODEOWNERS review requirement, no last-push approval, and administrator-role bypass `always`. These settings are unchanged from the earlier audit.

Apply an explicitly authorized protection policy before release merges, then read it back and validate enforcement. Protect independent review and stable required checks. Candidate-controlled validator code alone does not make the checks tamper-resistant. No settings were changed here.

## Freshly executed evidence

All runs used the existing Python 3.11 integration virtualenv with `env -i` and `-B`; transport tests use fixtures/mocks. No package installation, API credential, or paid endpoint was used.

- Exact remote #134 transport: **39 passed**, 0.099 s.
- Proposed two-file #134 repair: **42 passed**, 0.099 s.
- Current integrated transport: **44 passed**, 0.140 s.
- All twelve base/head ancestry checks passed.
- Main-to-tip merge-tree returned the unchanged exact tip tree without conflicts.
- Lifecycle scenarios: actual main-to-tip intentionally rejected; hypothetical post-adoption and #134 actual-parent scenarios passed as described above.
- Exact remote tip `validate_repo.py --strict`: 0 errors, 0 warnings, 17 skills.
- Exact remote tip platform compatibility with required reference validator: 17 skills, 4 layouts.
- Exact remote tip inventory: 328 records, 205 canonical sources, digest prefix `59df505ba5bb`.

The prior private isolated Git clone remains clean,
branch `codex/pr-stack-rehearsal-20260929`,
HEAD `9639dda3c5b2b6fb3ddfd88a3478c3dc90aa7c54`.

Hosted Linux/Python 3.12, refreshed dependency audits, final source export, human review, actual protected-default promotion and cloud activation remain distinct release actions. The exact core stack is reviewed and locally rehearsed, not production-deployed.
