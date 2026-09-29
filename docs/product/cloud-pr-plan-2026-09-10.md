# Cloud-service PR reorientation plan

Date: 10 September 2026. Planning only. The user requested a standalone cloud multi-agent service and updates to the plans/PRs; this document makes no GitHub mutation, merge decision or production activation. The [cloud-service contract](cloud-research-service.md) is the target, not a Codex-scheduled local research tool.

## Evidence and freshness

### Later update: managed Agents API is the primary runtime

The sections below preserve the earlier native-service planning snapshot. They
are superseded on runtime selection by the [managed Agents architecture](openai-agents-research-architecture.md)
and [verification report](openai-agents-verification-2026-09-10.md), not erased.
A fresh GitHub read verified the same six relevant PR heads; their descriptions
were updated in place: #121, #122, #125, #126, #130 and #131. No branch head changed.
[Draft PR #134](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/134)
adds the standalone Agents transport on top of #131. Its Python 3.11/3.12
transport checks and repository validation passed on head
`9639dda3c5b2b6fb3ddfd88a3478c3dc90aa7c54`.

The next review units are managed context/session integration with its complete
research-primitives dependency closure, paired evaluation, scoped source tools,
and operator/deployment integration. N3 below is retained as the explicit native
control/fallback, not the preferred product loop. No existing PR is approved for
merge by this metadata update. Broader local implementation is not present in #134.

### Earlier native-service planning snapshot

This review's attempted `gh pr list` could not connect to `api.github.com`. The exact titles and heads below therefore come from the [September 8 metadata receipt](evidence/github-pr-status-2026-09-08.json), completed at 04:37:49 UTC, and the [historical merge audit](status-and-merge-plan-2026-09-08.md). They are not new September 10 GitHub observations. Re-query head, base, check, review, ownership and effective rules before editing or merging. The main release review may supply a newer receipt separately.

The recorded #121 through #131 stack is linear. Most new sourcing, evidence replay, context, experiments, observation UI and safety repairs are local changes beyond its tip; merging that stack alone does not deliver the service. No existing PR is established as a ready cloud-service implementation.

## Existing PRs: retain purpose, correct scope

| Exact existing PR title | Recorded head prefix | Proposed update or disposition |
| --- | --- | --- |
| [#121: feat(governance): publish and enforce the specification program](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/121) | `aed122474c31` | Update roadmap/PR description to the standalone cloud target and distinguish draft contracts from implementation. Provider/host assumptions in draft bodies need explicit review, not a claim that all specs are accepted. |
| [#122: feat(orchestration): add supervised long-horizon bootstrap briefs](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/122) | `0030fdbf8da0` | Reframe briefs as development/operator task inputs. Remove any implication that Codex tasks, chat memory or bootstrap prompts constitute production scheduling. Runtime implementation belongs in the new service series. |
| [#125: fix(benchmarks): contain Cursor SDK and harden evidence](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/125) | `c50cc4cdbc0c` | Keep containment and exact dependency/evidence tests. Scope Cursor and zero-call restrictions to this legacy benchmark adapter, not all future native-provider integrations. Do not turn a security-maintenance PR into live-provider activation. |
| [#126: test(benchmarks): add private manifest resume substrate](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/126) | `7c0c92d20244` | Retain resume/unknown-outcome regression evidence and clarify that runner-private files are not the service's canonical workflow state. Extract reusable invariants through the new owner integration. |
| [#130: Extract authority contract and bind evaluator provenance](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/130) | `54580840f755` | Preserve provider-neutral authority and evaluator provenance. Add cross-references to service role/effect boundaries without claiming model execution or evaluator independence is implemented here. |
| [#131: Harden offline authority vocabulary semantics](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/131) | `c6cd52017b24` | Keep semantic denial checks; describe them as offline foundation evidence. Native providers/MCP and automatic scoped PR delivery are later registered operations, never blanket grants. |

#123, #124, #127 and #128 remain exact foundation-amendment decisions; #129 preserves the protected-default predecessor predicate. The new target does not justify removing history, changing their accepted authority meaning or treating an unmerged predecessor as accepted. SPEC-000–003 replacements must follow their existing lifecycle; SPEC-014/024/025 are still drafts and this iteration changes no status.

Prefer metadata clarification on the existing train plus a separate draft-contract/product-direction change after a deliberately reconciled base. Editing #121's source rewrites the ancestry assumptions for ten descendants; if chosen, regenerate every affected descendant diff and receipt rather than silently relying on the old green train. Do not bundle all cloud code into #121 or retarget every child at once. Preserve attribution and historical negative results.

## Reassess old provider/MCP exclusions correctly

- [#100: Publish xhigh evidence and harden validation paths](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/100): using a non-Cursor provider is no longer a product-level rejection reason. The historical large conflicting rewrite, outdated base and evidence/authority issues still require exact-diff review. Harvest suitable fixtures or provider-contract lessons in narrow changes; do not merge the old rewrite wholesale.
- [#112: Add cost, request, token, and rate-limit safeguards to API loops and judge examples](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/112): useful motivation for durable service reservations, but process-local/optional preflight checks are not restart-safe billing or retry accounting. Keep the consolidated local repair and implement the service owner separately.
- [#110: Fix shell injection and unsafe secret handling in hosted agents image build example](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/110) and [#81: fix: remove GitHub token from git clone URL in sandbox_manager.py](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/81): consolidate credential/argv fixes; neither is a cloud isolation or GitHub proposer implementation.
- [#38: Add 78 Composio SaaS app automation skills via Rube MCP](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/38) and [#40: Apply context engineering refactor to sales, copywriter, sentinel, solo-maker, and solo plugins](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/40): arbitrary provider/MCP extensibility does not require broad unvalidated tool packs or unrelated business automation. A small registered read-only MCP contract is the relevant new slice.
- [#55: Improve multi-agent-patterns skill and add skill review workflow](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/55): automatic proposals do not justify unpinned downloaded code with PR-write authority. Retain the denial and redesign through scoped service outboxes.
- Historical #94, “Preserve source provenance and add Xquik adapter,” was missing/inaccessible in the last receipt. Do not infer closure or merger. New X work must bind the chosen provider's actual access, rate, cost and provenance contract.

Other optional skills and unrelated PRs are not made launch prerequisites by this reorientation. Existing traversal, calculator, locking and credential defects remain security work regardless of provider choice.

## New implementation series

These are proposed review units, not created PRs. Each includes code, tests, operator behavior, migration/rollback and exact source/config evidence. Implement the smallest useful path within the applicable owner contracts; the developmental pre-release is not an accepted second control plane.

| Unit | Deliverable | Required check before claiming the unit works |
| --- | --- | --- |
| N0: cloud target and draft alignment | SPEC-014 native adapters, SPEC-024 hosted bindings, SPEC-025 standalone cloud deployment; SPEC-013 role alignment and regenerated plan/index | Existing lifecycle unchanged; exact dependency/criterion coverage; historical results preserved; local-only/Cursor-only assumptions scoped |
| N1: publish reusable research primitives | Captures, source replay, primary extraction, context/packet construction, frozen data-policy experiment and known safety repairs | Offline identity/tamper/missingness tests; original positive and insufficient-evidence outcomes retained; no unsupported semantic claim |
| N2: standalone coordinator and roles | Independent Python entry point, durable admission/reservations, data-only researcher/critic/skill-editor contracts, CLI status/pause | Outside-Codex fixture run, restart/duplicate/clock/disk faults, bounded no-answer/failure cases and complete receipts |
| N3: native APIs and read-only MCP | Configurable provider adapter, explicit credential references, registered tool gateway and output schemas | Offline provider contracts, then bounded real canaries; another provider before live interchangeability claims; unauthorized tools/egress/secrets/unknown-charge retries denied |
| N4: supported skill candidate and evaluation | Dossier-to-frozen skill patch, trusted structural checks, independent baseline/held-out task evaluation | Fabricated support, common-mode oracle corruption, invalid surfaces and regressions fail; all rows/costs retained; critic is not final judge |
| N5: automatic GitHub and notifications | Owner outboxes, scoped GitHub App, private delivery adapter, exact-head PR review packet | Sandbox PR/delivery receipts, remote merge denial, changed-human-content preservation, duplicate/lost-response reconciliation and destination restrictions |
| N6: operator surface and cloud packaging | Real authenticated projections/commands, pinned image, local Docker and single-VM service, private persistent storage | Clean host without developer config; restart, pause, encrypted off-host restore, rollback and operator-task tests; no production activation inferred |
| N7: accepted production canary | Integrated owner contracts, exact reviewed release, scoped deployment and fixed research/operational study | Real elapsed observations, measured complete costs/utility/failures, independent health evidence and explicit human activation |

N2/N3 can develop against N1 interfaces in parallel, but fake-provider success cannot substitute for N3 live evidence. N4 semantic effectiveness cannot be inferred from N1's packing benchmark. N5 uses configured automatic proposal/delivery authorization, not manual approval for every allowed routine event; it still has no merge or release permission. N6 must not activate a cloud service by merely building its image.

## Required coordinated edits outside this document

Update AGENTS, benchmark methodology and product entry points to distinguish historical adapter limits from the configurable service. Align SPEC-013 data-only roles, SPEC-015 approved cloud destinations and SPEC-008 real service projections. Regenerate the spec execution plan, spec index and inventory after draft source changes. Review incidental dependency edges through the existing lifecycle rather than adding a shortcut executor with competing authority.

Before any GitHub write, use the fresh exact-head review and approved update scope. Before any real API/tool/effect canary, record provider/repository/destination configuration, credentials by reference, resource ceilings, network permissions and rollback. Do not expose private captures, hidden fixtures or source locators in PR text. Automatic draft PRs, accepted skill changes, service releases and production activation remain different events.
