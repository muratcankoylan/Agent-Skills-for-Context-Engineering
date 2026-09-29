# Living-organization development iteration

Date: 8 September 2026. Status: local, uncommitted development work. Authority: none. Production readiness: false. No specification lifecycle, GitHub state, accepted repository pointer, credential grant or deployment was changed.

## Outcome and scope

This iteration delivers a [specification-based execution plan](living-organization-plan.md), a [machine-readable coverage plan](spec-execution-plan.json), a read-only plan validator, two reproduced prototype integrity repairs, and corrections to draft evaluation methodology. It does **not** implement or accept the full specification program.

The plan covers all 27 current specifications, 253 visible acceptance checkboxes and 54 ordered implementation slices. Each specification binds current source bytes, revision, lifecycle observation and direct dependencies. Each slice identifies deliverables, verification and rollback. All acceptance criteria remain `unassessed`. Coverage is not proof of all prose requirements, sufficiency of a test design, protected-default acceptance or completed implementation.

The core recommendation is one trusted local control service with isolated workers, not one service per agent role. First prove a model-free work/result/recovery path, then evidence-to-report, constrained improvement, human-reviewed release and separately authorized deployment. Optional archive search, adaptive routing and community intake do not delay the first operational release.

## Implemented repairs

| Finding | Reproduced or observed failure | Change and limit |
| --- | --- | --- |
| Shared evaluator corruption | Same-length source-text corruption in both reference and candidate could still yield success and a candidate-dominates decision. Follow-up probes also exposed shared omissions and envelope forgery. | `research_experiment.py` snapshots original observations before invoking the builder. Both packets must preserve selected content, provenance occurrences, all source/lane envelopes including failures and empty lanes, pending links, requested question, budget, policy labels and non-authority fields. Failed proof cannot earn a valid score. |
| Journal overwrite by projector | Configuring the projection path as the journal path let rebuild replace the journal and report success; subsequent integrity checking found corruption. Reproduced only in disposable test state. | `run_projector.py` rejects journal, sidecar, halt-marker and lock-target collisions before mutation and again before publication. Tests cover aliases, hardlinks, reassigned paths and protected-file preservation. |
| Shadowed concurrency test | Two test methods had the same name, so Python silently replaced the earlier method. | Renamed the earlier method so its subject-state and journal-tail assertions actually execute. |
| Inventory fixture drift | Adding the plan's two support documents left copied inventory test fixtures incomplete. | Added the two declared inputs to the fixture list. Existing omission checks remain strict. |
| Generated schema evidence drift | Generated legacy migration reports counted 26 claims while the existing input contained 27. | Regenerated reports and inventory from existing inputs; no claim was created or changed in this iteration. |

The new source oracle is independent of the packet builder's outputs, not an independent implementation of every trusted primitive. URL/work identity, canonicalization and shared source-mode conventions remain common dependencies. These tests establish finite mechanical integrity, not scientific relevance, ranking quality or hostile-worker isolation. The path guard assumes cooperative local processes; it is not containment against a malicious same-UID process racing filesystem replacement.

## Plan tooling and draft corrections

`researcher/scripts/spec_program.py` exposes two read-only commands:

```sh
python researcher/scripts/spec_program.py plan
python researcher/scripts/spec_program.py check docs/product/spec-execution-plan.json
```

The first prints an intentionally incomplete template. The second validates exact specification/criterion coverage, source bindings, dependency order and bounded closed shapes. It rejects missing, duplicated, extra, stale or unsafe inputs. It cannot mark a criterion passed, change a lifecycle, execute plan prose or grant authority. CI and generated inventory now include the coverage check.

The parser also fails conservatively on ambiguous comment/code-span Markdown rather than silently dropping acceptance text. Checked boxes are retained as source observations and never interpreted as verification receipts.

Draft SPEC-016 now distinguishes proposer-facing reviewers from separately authorized evaluator-owned semantic judges. A role label does not grant hidden-data access; evaluator tasks require scoped evidence, blinded arms, exposure accounting and separation from proposing/search/attestation.

Draft SPEC-020 now requires a direction-neutral, preregistered trace-access ablation. The test may show improvement, no difference or degradation; it must not encode the desired research conclusion as an acceptance predicate. Resource ceilings and non-ablated inputs match, while audit retention and safety controls remain enabled. Both specifications retain their existing draft status and revision.

The deployment plan explicitly preserves the current SPEC-025 local-first launchd contract. The Linux operations design is an alternative requiring contract review. The plan also names cross-store backup closure through `BackupGenerationBarrier`, separate recovery-key custody, no restored live capabilities, and refusal of automatic binary rollback after irreversible schema/artifact migrations.

## Verification and evidence interpretation

The first full run executed 1,130 tests but failed with 13 inventory-fixture failure records. Its schema check also reported stale generated evidence. That run is retained under private `researcher/runtime/living-organization-20260908/validation-01/`; it was not relabeled or overwritten.

After the fixture correction, the focused inventory suite passed 119 tests under Python 3.12.9 in 89.812 seconds. The fresh cross-version regression suite passed 165 tests under Python 3.11.0 in 49.118 seconds. These suites overlap the full suite and must not be added as independent tests or samples.

Fresh `validation-02` completed at 05:31:49 UTC against unchanged recorded source bindings:

| Check | Observed result | Scope |
| --- | --- | --- |
| Full Python suite | 1,130 tests passed; Python 3.12.9; 213.356 seconds command elapsed | Local deterministic/integration tests, not live model research |
| Plan, inventory, repository, platform, schema and event-journal checks | Passed | Current source and generated evidence; reference format validator enabled |
| Product-readiness assessment | Valid blocked assessment | Cannot certify production readiness |
| Activation and skill health | Passed | Structural/token-overlap checks, not semantic effectiveness |
| Stage 0 | Passed; zero benchmark scenarios executed by this command | Repository and activation checks plus catalog validation |
| Separate adversarial runner | Seven catalog scenarios executed and passed | Finite contract mutations; some semantic outcomes are supplied fixtures |
| Ruff | Passed on new planner, evaluator, their tests and projector source | Not a whole-repository lint claim; event-store tests retain pre-existing unused imports |

The repaired evaluator was exercised on three retained campaigns, two fixed policies and three packet budgets, yielding 18 policy-condition records and nine pairs. The original campaign/cache bytes were unchanged; recomputation returned the identical experiment result. Fresh source HTTP calls, product model calls and paid product calls were all zero. Network and fresh-retrieval entry points were explicitly denied during this replay.

The result was **`insufficient_evidence`**, not a proposal. On the retained September 8 campaign, the baseline returned `BUDGET_INSUFFICIENT` at 64 KiB; that pair remains unavailable. The other conditions do not erase the missing comparison. No condition was dropped, budget widened or gate relaxed after seeing this result. The campaigns share information needs and publisher windows; they are not independent research samples. This run makes no semantic-utility or production-promotion claim. Its next evaluation question is whether this resource ceiling is a required availability target, to be specified before a new study rather than retrofitted here.

Private execution records bind the tested source, configuration, command outputs and retained inputs. They are development receipts, not independent production attestations or public release manifests. The Git ancestor does not identify the uncommitted candidate.

## Release blockers and next authorized unit

1. Reconcile protected-default foundations. Local SPEC-000 through SPEC-003 revision 1 are terminal `amended` and lack their named replacement revisions. SPEC-004 through SPEC-026 remain draft. Follow the [conditional merge assessment](status-and-merge-plan-2026-09-08.md), then lawful replacement and isolated acceptance review. No PR has been made merge-ready by these local edits.
2. Implement accepted journal and work/effect ownership before connecting production consumers. The current journal, scheduler, legacy run files and fixture controls are not one accepted state machine.
3. Repair recovery through the accepted owner contract. `restore_verified()` can return a writable older prefix; `clear_operator_halt()` has no authorized recovery-ticket/known-tail continuity protocol. The path-collision repair does not solve this. The [runbook](../../researcher/event_journal/README.md) now forbids live pointer replacement and halt clearing through these prototype paths.
4. Establish isolated live executors and independent semantic evaluation before claiming research or skill improvement. Authenticated X access, paid-provider contracts, held-out utility, exact-tree review and clean-host installation remain unverified here.
5. Prove authenticated operator commands, cross-store recovery, actual elapsed operation and a separately authorized deployment canary. A Codex heartbeat is not the product scheduler; source replay is not uptime.

The next normative implementation unit is D1 from the plan: accepted generic journal plus one model-free validation work order with restart, fencing, exactly-one result application and recovery tests. Current lifecycle prerequisites require maintainer action first. No paid product calls, automatic source campaign, proposal application, commit, push, merge or deployment was authorized by this document.
