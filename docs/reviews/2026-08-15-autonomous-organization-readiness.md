# Autonomous Organization Readiness Review

Date: 2026-08-15
Status: historical audit snapshot
Authoritative public base: `6dbe1a1d868eab51a3bc9011b0f55e2891513e40`

## Decision

The repository has a reproducible constitutional and data-contract foundation. It does not yet have authority or runtime support for a continuously self-improving production organization.

Use the prompt bundle in `researcher/orchestration/prompts/` as a supervised engineering bootstrap only. The production design is not one persistent model session. It is an event-driven sequence of bounded attempts, each compiled from authoritative state and ending in a durable checkpoint, independently reviewed candidate, or typed blocker.

The current activation boundary is:

- agents may research, inspect, plan, implement locally, test, and prepare review artifacts within an explicitly authorized work order;
- agents must not infer authority from chat, a local branch, or a status string outside protected `main`;
- agents must not merge, enable auto-merge, change repository rules, or describe merged code as deployed;
- skill, prompt, evaluator, or harness optimization remains proposal-only until the evaluation and promotion specifications are accepted and implemented;
- the stricter workspace rule still requires explicit human approval before each push or pull-request creation.

## Audit method

Three independent read-only reviews examined:

1. all 53 merged GitHub pull requests, with deeper inspection of the constitutional stack and the research/skill infrastructure that preceded it;
2. the local specification-program roadmap and the uncommitted SPEC-004A prototype;
3. the specification dependency graph, context architecture, agent contracts, improvement loop, and the repository's `long-horizon-prompting` skill.

The merged baseline was also cloned into an isolated Git repository and tested. A first archive-only reproduction was discarded because migration tests depend on a real tracked-file boundary.

## Authority ledger

| Layer | Identity at audit time | Meaning |
| --- | --- | --- |
| Protected public base | `main` and `origin/main` at `6dbe1a1` | Authoritative merged state |
| SPEC-000 PR | [#116](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/116), merge `48bc565` | Machine-testable constitution |
| SPEC-001 PR | [#117](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/117), merge `4deb96c` | Deterministic repository reconciliation |
| SPEC-002 PR | [#119](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/119), merge `69bc429` | Public/private artifact boundary |
| SPEC-003 PR | [#120](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/120), merge `6dbe1a1` | Runtime-neutral schemas and immutable identity |
| Roadmap candidate | local commit `b2576ba` | Reviewed proposal; no remote branch or PR |
| SPEC-004A candidate | uncommitted work above `b2576ba` | Incomplete, non-authoritative prototype |

Default-branch reachability plus constitutional policy determines authority. A local document saying `accepted`, `implementing`, or `implemented` is not sufficient.

## What the merged stack establishes

### SPEC-000: constitutional authority

The first layer turns governance into executable decisions rather than prompt convention. It supplies deny-by-default authorization, exhaustive rule evaluation, explicit human-only merge and amendment authority, and deterministic governance tests.

### SPEC-001: deterministic organizational inventory

The second layer reconciles the repository into a source-byte-bound inventory. It excludes timestamps and self-referential commit identities, records unresolved references, and makes generated summaries derivable rather than manually maintained.

### SPEC-002: public/private projection boundary

The third layer makes public export an allowlisted transformation. Public manifests bind public projections and outputs without publishing private source paths, locators, or input digests. Correction and removal are testable operations.

### SPEC-003: portable contracts and immutable identity

The fourth layer provides the runtime-neutral schema registry, integer-only canonical JSON profile, typed UUID identities, artifact/reference separation, local content-addressed storage, candidate freezing, migration evidence, and Python/TypeScript conformance.

Together these layers answer four prerequisite questions: who may act, what the canonical repository contains, what may cross the public boundary, and how durable records retain portable identity.

## Reproduced merged-baseline evidence

The isolated clone of `origin/main` produced:

- 148 of 148 Python tests passing;
- 26 governance rules and 2,142 exhaustive authority decisions;
- 258 artifacts and 127 canonical inventory sources;
- 20 schema contracts, 21 goldens, and 50 migrated legacy records with zero quarantine;
- TypeScript typecheck and 20 of 20 tests passing;
- strict repository validation with 17 skills, zero errors, and zero warnings;
- skill health `0.9221` with no flagged skill;
- 23 of 23 activation cases and seven adversarial scenarios passing;
- four platform installation layouts passing;
- router and effectiveness dry-runs completing with zero paid API calls;
- a clean final worktree and no generated drift.

GitHub's latest `main` workflow at audit time also passed. This proves the current tree against its current gates. It does not retroactively make sparse historical PR evidence complete.

## Historical lessons that shape the organization

The repository history contains useful reversals:

- an internal database surface was introduced and later removed;
- individual marketplace plugins were later consolidated;
- a broad skill rewrite required a follow-up that removed fabricated benchmark content and repaired scripts;
- the long-horizon site deployment failed before later repair;
- most older PRs had neither recorded checks nor formal reviews.

These are evidence for append-only supersession, independent verification, failure memory, exact candidate identity, and human merge authority. A merge commit alone cannot tell a future agent which mechanism remains valid or why another was rejected.

## Residual risks on the merged base

1. Stage-3 effectiveness coverage contains one task. Router accuracy measures activation, not whether a loaded skill improves execution. Autonomous skill promotion is therefore unjustified.
2. Stage-4 composition evaluation is not implemented.
3. One pipeline example has an unvalidated batch identifier on a destructive cleanup path. Open PR #109 proposes a fix but is not authoritative.
4. Hosted-agent examples demonstrate unsafe token and shell patterns. Open PR #110 is partial and needs independent review.
5. Python dependency resolution on `main` is not fully hash-locked. The exact Cursor SDK installation reports advisories whose remediation is deliberately deferred pending compatibility evidence.
6. The research loop imports `fcntl` and is not a Windows-durable cross-process implementation.
7. Durable organization-wide request, token, and cost accounting does not yet exist outside bounded benchmark runners.
8. Historical PR evidence is sparse: current gates protect today's tree, not the claims in old PR descriptions.

Open external PRs are evidence or candidate patches only. The orchestrator must not absorb them without a scoped work order, rebase, independent audit, and current gates.

## Local roadmap review

Commit `b2576ba` adds the 27-spec program, lifecycle and dependency graph, ADR-0005 and ADR-0006, stronger public-release validation, exact workflow pins, hash-locked Python tooling, and deterministic spec/ADR parsing. In isolated validation it passed 188 Python tests, 20 TypeScript schema tests, repository and public-boundary gates, platform checks, skill health, activation cases, benchmark dry-runs, and site validation.

It remains a local proposal. The human must explicitly authorize a push and PR. Merging the roadmap publishes draft contracts; it does not accept SPEC-004 through SPEC-026.

The program has six delivery waves:

1. durable control: event journal, work orders, commands, GitHub lifecycle, status;
2. evidence to context: source registry, retrieval, evidence graph, context compiler, role contracts, Hermes adapter, notifications;
3. evaluated promotion: evaluation registry and runner, candidate archive, promotion/release;
4. bounded recursive improvement: meta-harness, routing, collaborative evolution;
5. sustainable operation: open-source governance, private control plane, durable deployment;
6. optional training and reinforcement-learning research, under separate human authority.

## SPEC-004A candidate review

The local prototype contains event and research-run-transition contracts, Python/TypeScript semantic parity, deterministic import identities, a SQLite event store, optimistic concurrency, exact duplicate handling, hash-chain verification, backup/restore, a deterministic projector, an operator halt, ADR-0007, and a recovery runbook.

It is not ready for an implementation PR:

- SPEC-004 is still `draft` and ADR-0007 is `proposed`;
- the full Python suite has two failures caused by generated inventory and journal-report drift;
- the event-journal inventory omits the projector SQL and manifest;
- two concurrency tests share one method name, so Python silently drops the first;
- the public validator sees only tracked files until an explicit candidate staging pass;
- the initial projector lock is POSIX-only and that runtime limit is not documented;
- 004B's file-first bridge, repairable outbox, shadow parity, and public projection do not exist.

The safe sequence is roadmap review and merge, explicit SPEC-004 architecture review and acceptance, repair and verification of 004A, then 004B. Implementation evidence must not be used to bypass lifecycle authority.

## Operating architecture

One indefinite prompt is the wrong unit. Work lifetime exceeds session lifetime, and compaction cannot be organizational state. The bootstrap bundle has four components:

1. `organization-root-brief.md`: stable outcome, invariants, non-counting outcomes, delegation policy, and return contract;
2. `spec-work-brief.template.md`: one exact accepted spec or vertical slice compiled for one wake;
3. `fresh-verifier-brief.md`: an independent audit with no builder transcript or prior verdict;
4. `resume-brief.template.md`: restart from a validated checkpoint rather than conversational memory.

The future harness compiles those components with an authority snapshot, ContextPackage, WorkOrder, capability grant, budget, repository state, and external events. Until SPEC-005, SPEC-012, and SPEC-013 exist, those records are provisional bootstrap inputs and must not be presented as registered durable contracts.

## Context contract

The context system has eight separate memory authorities: constitutional, evidence, semantic, procedural, episodic, working, preference, and compatibility. Models may propose semantic, procedural, and preference changes; they do not directly rewrite those memories.

Every wake receives an exact ordered context chain with provenance, freshness, inclusion and exclusion reasons, contradiction completion, and a token allocation. Private bodies stay behind references. Abstractive summaries orient the model but do not prove claims. Prompt versions freeze for an attempt; an improvement becomes a child candidate and never hot-swaps the running attempt.

The checkpoint preserves objective, success predicate, authority, decisions, rejected routes, contradictions, branch and commit identities, changed paths, verification evidence, budgets, exact next action, and stop condition. Agent-to-agent communication that affects decisions becomes a durable artifact or event.

## Activation ladder

| Level | Prerequisite | Permitted behavior |
| --- | --- | --- |
| 0: supervised bootstrap | current merged base | inspect, research, plan, local implementation, tests, review packet; explicit approval before external writes |
| 1: durable supervised builder | roadmap plus SPEC-004 through SPEC-008 | resumable work, authenticated commands, deterministic status, agent-authored PRs; human merge |
| 2: context-compiled research organization | SPEC-009 through SPEC-015 | evidence ingestion, reproducible contexts, versioned roles, replaceable Hermes execution, draft notifications |
| 3: evaluated promotion organization | SPEC-016 through SPEC-019 | immutable epochs, independent evaluations, candidate archive, exact-SHA promotion packets |
| 4: recursive shadow laboratory | SPEC-020 through SPEC-022 | optimizer proposes bounded child candidates against pinned production; no direct production edit |
| 5: continuous credentialed operation | SPEC-023 through SPEC-025 | private broker, local-first durable operations, measured workflow escalation, public contribution governance |

SPEC-026 remains optional and independently authorized. No activation level may be inferred from a prompt alone.

## Exact next program actions

1. Preserve the current SPEC-004 worktree without mixing in unrelated edits.
2. With explicit human approval, push and open the roadmap PR from `b2576ba`.
3. Run GitHub CI and history-level leak scanning, then obtain a human merge.
4. Resolve lifecycle migration and whether `implementing` is a merged transition or derived PR projection.
5. Move SPEC-004 through human-merged architecture review and acceptance.
6. Fix 004A inventory closure and the shadowed concurrency test.
7. Regenerate schema, journal, inventory, and summary evidence only after source fixes settle.
8. Run complete CI-equivalent, public-boundary, leak, concurrency, crash, recovery, and staged-tree gates.
9. Submit 004A as one exact-SHA review packet; retain human-only merge.
10. Implement 004B before calling the event journal operational.
11. Continue one accepted spec or explicitly named vertical slice per PR.

## Production launch rule

The manual engineering-orchestrator brief may be used now. Continuous autonomous promotion may not.

Production launch requires executable authority, event persistence, work orders, context compilation, role and capability contracts, independent evaluation, exact-SHA promotion, private credential brokering, deterministic status, recovery, and a tested kill path. If a hard boundary exists only as prompt prose, it is not a production control.

## Prompt-bundle verification snapshot

The settled bootstrap-v1 proposal produced the following local evidence:

- fresh-context adversarial prompt audit: `20/20`, with all ten `long-horizon-prompting` rubric dimensions at `2/2`;
- Python unit discovery: 191 of 191 tests passing;
- deterministic inventory: 298 artifact records, 173 canonical sources, zero unresolved references;
- governance: 26 rules and 2,142 exhaustive decisions;
- schema contract: 20 contracts, 21 goldens, and 50 legacy migrations with zero quarantine;
- TypeScript schema package: typecheck and 20 of 20 tests passing, zero reported package vulnerabilities;
- public candidate scan: 543 tracked-plus-candidate files, six untracked candidate files, zero findings;
- Gitleaks 8.30.1: 152 committed-history revisions and every changed candidate surface scanned with no leak;
- platform reference validation: 17 skills across four local installation layouts from a fresh hash-locked Python environment;
- strict repository validation: 17 skills, zero errors, zero warnings;
- skill health `0.9221`, 23 activation cases, and seven adversarial scenarios passing;
- router and effectiveness runner typechecks and bounded dry-runs passing with zero paid calls;
- prompt-lab build and site validation passing with no generated drift;
- Ruff and targeted mypy checks passing for the modified inventory code and tests;
- Git whitespace check passing.

The benchmark SDK installation still reports the 12 advisories already recorded in the roadmap audit. Its calls remained disabled. Gitleaks must run again in GitHub CI after an explicitly authorized push because local evidence cannot attest the future remote candidate.

The generated inventory owns the exact source-tree digest. It is intentionally not copied into this source document, which would create a self-referential digest.
