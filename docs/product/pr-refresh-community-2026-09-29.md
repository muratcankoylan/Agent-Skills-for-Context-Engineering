# Community and example PR refresh, 29 September 2026

## Decision

**No PR in this 13-PR batch is a required production-runtime dependency, and none is recommended for an unconditional merge at its current head.** Prioritize narrowly revised #133 and #88 as independent content, replace #89 with a current navigation guide, and handle #36 as a qualified documentation decision. Keep #132 draft. Do not turn the other examples, vendor integrations, or old packaging changes into one production stack.

This is a read-only refresh of [the earlier community audit](pr-community-review-2026-09-29.md), not a remote review, merge approval, implementation of its requested fixes, or proof of accepted skill improvement. No GitHub mutation, commit, push, merge, workflow dispatch, contributor-code execution, installation, provider call, or paid evaluation occurred.

## Latest refresh: 13:10 UTC

The all-open inventory and assigned community reviews were rechecked on **2026-09-29 13:10 UTC**. GitHub still returns **36 open PRs**, exactly the PR-number set in [the local preparation manifest](pr-updates-2026-09-29/manifest.json); no newly open PR is omitted by that inventory. This is an inventory check for all 36, not an additional code review of the other 23.

All 13 community head SHAs, API-reported comparison-base OIDs, draft states, mergeability and check rollups remain as listed below. The remote `main` tip and integrated local HEAD also remain unchanged. All 13 manifest actions and observed heads agree with this report; the manifest was not edited. No community patch is present in its prepared-patch list. “Revise independently” describes work still required, not a completed revision or remote update.

Latest-pass coverage: re-enumerated changed paths and checks for every assigned PR; fully re-read #132's budget base, OpenAI/Anthropic/Pangram adapters, adapter import module, env loader, benchmark controller, CLI, writing controller, benchmark tests and README at its exact SHA. Fully re-read #133's 168-line skill and #89's 167-line guide; refreshed the #133/#88 registration diffs and #88 receipt guidance. No new changes were available to review. The unchanged remaining nine retain the bounded inspection recorded in the earlier sections, not a newly exhaustive source review. The #40 `gh pr view` file field exposes only its first 100 paths despite reporting 599 changed files; do not treat that projection as a complete file inventory. The prior 599-path enumeration and explicit 12-file review limit remain the coverage record.

No PR code, package installer, model, provider connector, benchmark or whole-repository validator was executed in this latest pass. The four structural checks and historical CI-log inspection reported below belong to the earlier 07:40 refresh, not a rerun at 13:10. The old #132 failure remains the sole returned check; the other twelve still have no returned checks.

### Additional confirmed #132 boundaries

These static findings are at `83b5ad0b6afd4eae094493877c58cddf95dcdc00` and strengthen, rather than replace, the existing keep-draft disposition:

| Finding | Exact source/control-flow witness | Required regression and repair |
| --- | --- | --- |
| Advertised env-file model and endpoint pins are ignored | [Adapter imports](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/adapters/__init__.py#L1) eagerly load all adapters before [CLI `load_env`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/cli.py#L253). `DEFAULT_MODEL` and `_API_URL` are captured at import in [OpenAI](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/adapters/openai.py#L15) and [Anthropic](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/adapters/anthropic.py#L17); Pangram's URL is also import-time. A pin supplied only in the advertised `--env-file` does not configure those values, while API keys are read later. | Construct explicit validated configuration after loading the requested file and inject it into adapters. A credential-free subprocess test must place the model and endpoint solely in a fixture env file and assert the mock request uses them. Record effective model/endpoint identity, not just the requested env values. |
| Optional detector calls bypass the declared budget entirely | [`PangramClient.score`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/adapters/pangram.py#L32) posts directly without a `Budget`; benchmark execution enables it based only on key presence. Its provider response is written into results, but its calls/cost are absent from the shared summary. | Require explicit detector enablement and a separate admitted durable reservation before dispatch. Test that a configured key alone cannot cause a request, that exhausted authority denies it, and that failed/unknown requests remain charged conservatively. No current Pangram price or account entitlement was checked here. |
| Non-finite CLI dollar values disable the comparison | All CLI `--max-usd` arguments use `type=float`; [`Budget.charge`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/adapters/base.py#L43) uses `spent + estimate > max_usd` without finite/positive validation. `--max-usd nan` makes that comparison false; `inf` removes a finite dollar ceiling. The call counter is a different bound and does not repair the dollar contract. | Reject NaN, infinity, nonpositive/invalid limits and invalid token/price/usage inputs before creating any client. Add zero-dispatch tests for CLI and direct configuration paths. Prefer validated integer microunits with durable reservations. |

Repeated judging needs two separate regression cases: a second invocation after success currently reads the list-valued `judgments.json` and raises on `data.get`; a crash after one or more paid comparisons but before the final file write leaves no per-comparison receipt and can repeat all those calls on restart. Merely excluding `judgments.json` fixes the first symptom, not the duplicate-effect boundary. Likewise, skipping existing generation filenames does not restore prior cumulative spend or establish result identity.

### Concrete community update plan

- #133: separate content patch for portable references, owner-approved coverage waivers, negative activation fixture and regenerated registration closure. Keep its mechanism `candidate`.
- #88: separate content patch for qualified receipt claims, private/scoped correlation, `candidate` status and current registration closure. This is not a migration of the trace exporter or an acceptance decision.
- #89: replace the copied operating manual with a thin current source-of-truth map; no copied live counts, provider restrictions or push/retry recipe.
- #132: an independently owned repair sequence is configuration correctness, durable shared accounting including detector calls, exact manifest-bound generation resume, per-comparison judgment receipts, then isolated tests and regenerated inventory. Do not connect it to the production scheduler or inherit the research campaign's paid authority.
- #17/#52: prepare attributed supersession decisions, not runtime dependencies. #55/#72 need extraction or rework, not a mechanical stack. #95/#40/#24 need explicit separate product scope. #38/#36 are optional qualified documentation only.

If maintainers later choose a convenience stack for #133/#88/#89, record explicit base/head edges and refresh the combined corpus outputs once against the approved base. None depends on #132 or should inherit its paid execution. Every resulting head still needs its own current deterministic gates; no merge or remote update was performed by this refresh.

## Earlier refresh evidence and comparison boundary (07:40 UTC)

- All 13 PR heads, API-reported comparison-base OIDs, open/draft states and checks were fetched again with authenticated read-only GitHub CLI calls. The final recheck at **2026-09-29 07:40:19 UTC** found every head and reported base unchanged during this refresh, and every head unchanged from the earlier audit.
- Every PR remains open and targets `main`. The independently resolved current remote `refs/heads/main` is `6dbe1a1d868eab51a3bc9011b0f55e2891513e40`. The table preserves the API's per-PR `baseRefOid` values verbatim; several differ from that branch tip. They are not interchangeable with the current release base.
- Integrated local Git HEAD remains `c6cd52017b247804373339e1c3c103d42554b0a1`, with existing uncommitted implementation. A clean GitHub merge bit says nothing about applying the change to this working-tree implementation or passing its current gates.
- The local [service README](../../researcher/service/README.md), [candidate-review boundary](../../researcher/service/candidate_review.py), [trace contract](../../researcher/service/tracing.py), [platform validator](../../researcher/scripts/validate_platform_compat.py), and [generated corpus inventory](../../researcher/generated/corpus-summary.md) were compared directly. The generated inventory is not an exhaustive runtime/security digest.
- #132 still has the same failed `validate` check. All other heads returned an empty check rollup. **Empty checks are absent evidence, not green CI.**

## Exact head/base dispositions

| PR | Exact head SHA | API-reported comparison-base OID | Observed GitHub state | Disposition |
| --- | --- | --- | --- | --- |
| [#133](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/133) | `65f501cdf2148a01b19db6cc6ad569c723b7a7d2` | `6dbe1a1d868eab51a3bc9011b0f55e2891513e40` | mergeable; no checks returned | Revise as independent content; not a service prerequisite. |
| [#132](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/132) | `83b5ad0b6afd4eae094493877c58cddf95dcdc00` | `6dbe1a1d868eab51a3bc9011b0f55e2891513e40` | Draft; mergeable; validate failed | Keep draft; do not fund/run before durable accounting and resume fixes. |
| [#95](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/95) | `f7eedc9104a929a937ebb5fb7aae88e1d4d2ee70` | `25e1fa79a33f0985793bcab3c64dde8d020c5132` | mergeable; no checks returned | Exclude from core; separate vendor scope/permission review. |
| [#89](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/89) | `b84d8fabe14d5f5c71a57207e3ae56d49a8c0775` | `25e1fa79a33f0985793bcab3c64dde8d020c5132` | mergeable; no checks returned | Replace stale instruction copy with a thin current navigation guide. |
| [#88](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/88) | `ef6bb240008631ff5820b347c717bfa32a15ce83` | `61f38ffc0ff3ae83adcf2fe011f3b751105add6d` | conflicting; no checks returned | Rebase and revise content; candidate mechanism, not accepted authority. |
| [#72](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/72) | `c5f5bdb2c2bfd72385a0ec9ab9e5c698562d3153` | `3ab8c948898908e4acc083c32f0390f0caafe3e4` | conflicting; no checks returned | Request major changes or extract prose; do not adopt its state system. |
| [#55](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/55) | `25481be1fa99472f44f1938d32ef6d2a62b838a7` | `87529d9be4488d1d0ad4d02caf9695451e0d3732` | conflicting; no checks returned | Split content from external CI; no blanket cherry-pick. |
| [#52](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/52) | `84439d0a3d6dbe2a622cbcf8bea8713efdf88925` | `3ab8c948898908e4acc083c32f0390f0caafe3e4` | conflicting; no checks returned | Supersede as launch infrastructure; optionally salvage bounded methodology. |
| [#40](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/40) | `a9548805a44ae86fa1b229ce4587d18a1ce2be17` | `da63847a41d49dcfe12ac1d9cc6f7c9596782fa9` | conflicting; no checks returned | Reject wholesale scope; separate plugin suite or tiny independent proposal. |
| [#38](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/38) | `ee0de997f47ad83b812c317bc74c3e8a0d13e2c3` | `7942df36cfcac4f224d310b6be552e99715df5de` | mergeable; no checks returned | Optional external-resource curation only; no delivered integrations. |
| [#36](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/36) | `ecec05aec7acc1fc97944d2e43f1ba95af022720` | `1bda9bd46e28d344dc260f476258423e7c06ccf3` | mergeable; no checks returned | Independent qualified docs change after compatibility evidence. |
| [#24](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/24) | `41eaad316b80307a51922f5fb7046ff581191807` | `9b350229f3da93e7db57d5f023dcfe7f0eb05007` | conflicting; no checks returned | Scope decision before rewrite; not a core architecture implementation. |
| [#17](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/17) | `aaef0164e62b03aa29916cb9899a19a63c428eb2` | `9850a0f5c221f8f0f4faf1cc7e4e202ac1aaf4af` | conflicting; no checks returned | Superseded by current one-bundle packaging; do not merge as-is. |

## #132: the CI fix is necessary but not sufficient

[Draft #132](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/132) is a separate persona-writing experiment: 43 changed files, +3,333/-5. It does not implement the research organization's source retrieval, shared cumulative authority, candidate acceptance, cloud scheduling, or publication controls.

Fresh inspection enumerated all 43 paths and read the pinned README, budget/adapter base, benchmark controller, writing controller, judge/benchmark CLI sections, and benchmark tests. The other adapters, persona/planner/critic/memory/stylometry internals, corpus licensing and paper claims were not exhaustively re-reviewed this turn. Their unchanged-head prior findings remain in the earlier report. No example code was executed.

### Current failure evidence

The [existing job log](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/actions/runs/32206656273/job/95931121150), fetched again, records **148 repository tests, one failure**, `test_committed_generated_outputs_match_builder`, caused by generated inventory digest disagreement. This is the 19 August run at this head, not a fresh test execution and not a failure count for the author's claimed 47 example tests.

Regenerating the inventory can address that observed CI failure. It cannot establish the safety of funded execution:

| Confirmed source defect | Concrete witness | Required fix/test before live use |
| --- | --- | --- |
| Filename-only resume silently accepts a different experiment | [benchmark.py L192-L221](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/benchmark.py#L192) returns any existing result keyed only by brief ID, persona name, condition and provider. | Bind exact brief/corpus/model/config/code/seed identity, schema-validate the result, reject changed identities, serialize writers and retain ambiguous in-flight effects. Tests must change each bound input separately and attempt concurrent resume. |
| Dollar reservation is not retained before dispatch | [base.py L37-L63](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/adapters/base.py#L37) checks an estimate then increments only calls; dollars change only in settlement. State is in-memory, with provider-wide prices and a heuristic input estimate. | Durable cumulative reservation before every paid provider; retain failed/unknown cost; finite, validated caps and pinned price/model identity; explicit restart and failed-response tests. Do not equate characters/4 with a token upper bound. |
| Advertised stage resume restarts paid work | [harness.py L71-L106](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/harness.py#L71) directly rewrites artifacts, plans anew and traverses every paragraph. | Exact bound checkpoints, atomic exclusive receipts, restart reconciliation and no re-dispatch of unknown work. Test crashes before/after each receipt commit. |
| Judge rerun consumes its own output as an input record | [cli.py L150-L197](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/cli.py#L150) reads all top-level JSON via `data.get`, then writes a list to `judgments.json` in that directory. | Separate typed result/judgment namespaces; per-comparison receipts; repeated invocation and interruption tests; avoid repeating funded judgments. |
| Per-cell cap and compute-matching claims exceed implementation | [cli.py L123-L139](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/cli.py#L123) turns a stated per-cell limit into one multiplied global counter. [Self-refine](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/benchmark.py#L105) makes three generation calls, unlike the per-paragraph loop. | Enforce both limits or correct the interface; distinguish quality-vs-cost from matched-compute experiments; include independent held-out measures and immutable experiment records. |

The fresh [benchmark test](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/tests/test_benchmark.py#L36) checks same-input filename reuse but not identity mismatch. That test does not refute the resume finding.

**Disposition:** keep draft and independently owned. Fix these boundaries, then run a credential-free isolated offline suite and regenerate its derived inventory on the selected base. Treat the README's reduction and 10-20x token-cost statements as unverified hypotheses until retained experiments support them. Do not attach current production keys, the $100 authority, or the organization scheduler merely to make the example run.

## Small, relevant content proposals

### #133: rendered UI finish gate

Freshly read the complete seven-file patch and all 168 lines of the skill. The mechanism remains a `candidate`, which is appropriate; no executable runtime or paid integration is added.

Retain the design-contract/state-matrix/rendered-evidence idea, with these exact revision requirements:

1. Replace the [repository-template relative link](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/65f501cdf2148a01b19db6cc6ad569c723b7a7d2/skills/rendered-ui-finish-gate/SKILL.md) with a portable reference or contributor-only documentation. Single-skill installation does not include `../../template/SKILL.md`.
2. Make an unsupported required state a failed/waived criterion, not a pass created by documenting it. Any change to required coverage needs the appropriate product owner, not self-approval by the implementer.
3. Add an adversarial activation fixture for a general evaluation request that merely mentions UI, and a worked failed-state result. Prose saying to render is not rendered evidence.
4. Rebase all registration surfaces and regenerate inventory on the final approved base. The seven-file patch changes inventory inputs but does not refresh the derived inventory/summary.

**Disposition:** optional content revision. Not the implementation of the current control-center UI, its tests, or a service release gate.

### #88: context receipts

Freshly read the complete nine-file patch and all 269 lines of the skill. The loaded-versus-returned distinction, suppression events and transformation-versus-commit separation remain relevant.

Revision requirements are now particularly important because the local service has concrete tracing and candidate boundaries:

1. Change [`redacted-context-receipt`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/ef6bb240008631ff5820b347c717bfa32a15ce83/researcher/mechanisms/registry.jsonl) from `accepted` to `candidate` unless an actual approved acceptance record and supporting evidence are supplied. Self-citing skill prose is not acceptance evidence.
2. Replace unconditional “prove”/“negative guarantee” wording with the exact trusted emission boundary and residual gaps. A JSON boolean saying content was not logged cannot prove absence of leakage. Operational traces are not budget, execution, or acceptance authority.
3. Prefer private bindings or scoped keyed correlation for sensitive low-entropy inputs. Public hashes, including publicly salted hashes, do not automatically prevent guessing.
4. Remove cross-directory skill links, resolve conflicts, drop stale count/version edits, regenerate derived inventory, and add tests/examples distinguishing missing receipt, rejected export, partial/unknown delivery, and unobserved provider internals.
5. Do not claim that merging this prose implements the service's exact capture/replay, ArtifactRef/StorageBinding, trace export, or loading-boundary verification.

**Disposition:** revise and retain as independent content; do not silently promote its mechanism or use it to certify production telemetry.

### #89: internal contributor guide

Freshly re-read the complete 167-line addition. It still embeds version 2.3.0, 15 skills, active legacy retrieval/promotion, Cursor-only live paid execution, filename-resume guidance, and a push/retry recipe. These contradict the integrated operating instructions and model-agnostic service boundaries.

Replace it with a short navigation guide pointing to current `AGENTS.md`, generated inventory, service runbooks, current validator commands and explicit human authority. Do not copy changing counts, prices, runtime status or irreversible-action instructions into a Claude-only second source of truth.

**Disposition:** a replacement guide can be independent documentation. It should not be the base of a production code stack, and no stale instruction should gain authority by surviving a clean merge.

### Can #133, #88 and #89 be stacked?

They share a repository, not a runtime dependency. Prefer three separately reviewable content/documentation changes against the same approved core base. If a maintainer chooses a linear convenience stack, explicitly record its base/head edges and rerun the combined deterministic gates after each derived-inventory refresh. The stack does not establish semantic improvement, mechanism acceptance, UI coverage, or publication authority.

Do not combine their old manifests, copied inventory counts, or `accepted` declarations mechanically. Keep mechanism status `candidate`; preserve contributor attribution when revising or preparing a superseding change.

## Remaining nine dispositions and fresh inspection limits

| PR | Fresh bounded inspection | Current reason and disposition |
| --- | --- | --- |
| #95 | Re-fetched all 515 lines; re-read onboarding, broad activation, messaging/workflow/account-reset portions; reran trusted frontmatter/shape checks. | Unpinned global vendor CLI, credentials in onboarding command arguments, broad externally mutating operations, 515-line/missing-section package failures. Not a research source adapter. Exclude from core; consider a separate scoped example only after dependency/permission/privacy review. |
| #72 | Re-read all 196 lines of `tc_init.py`; other unchanged scripts retain earlier audit findings. | `--force` still promises preserved registry while lines 162-163 overwrite it with an empty registry. Earlier lifecycle/concurrency/path-boundary defects remain unremediated at the identical head. Request changes or extract narrow handoff prose; never replace the service ledger with it. |
| #55 | Re-fetched the complete two-file diff and re-read its workflow and rewrite. Did not re-audit the unchanged third-party action distribution. | Removed corpus headings/boundaries and unconditional retry advice remain. Separate the content proposal from a PR-write external review action; the prior pinned-action/mutable-installer finding is not resolved by this unchanged head. No blanket cherry-pick. |
| #52 | Re-read all 234 lines of the benchmark runner. Other unchanged workflow/fixture findings remain in the prior audit. | It calls a fixed model directly rather than the changed candidate; writes absolute-pass results before relative-regression failure; can overwrite a lower baseline; lacks the service's durable budget/resume boundary and strict judge coverage. Supersede as launch infrastructure, not as proof every methodological idea was implemented elsewhere. |
| #40 | Re-read the complete 54-line copywriter MCP config only. No fresh exhaustive 599-file audit. | Still unpinned `npx -y`, secret placeholders in argv, filesystem writes and unrelated publication/outreach integrations. Prior audit inspected 12 files and all filenames, not all 75,001 lines. Do not import wholesale or label connectors verified. |
| #38 | Re-read the complete sole README patch. | It adds an external-resource recommendation, not 78 delivered skill directories or tested MCP integrations. Optional curation only; remove unsupported “production-ready” wording and blanket `--all` install recommendation. |
| #36 | Re-read the complete one-line README patch. | No new versioned AdaL install/discovery/activation evidence was supplied or executed. Optional qualified compatibility documentation; not a service launch blocker or certification. |
| #24 | Re-fetched the 604-line skill, re-read its opening requirements and supporting-material map, reran trusted frontmatter/shape checks. Did not re-review the 13 references/diagrams. | Missing frontmatter, line cap and required-section failures persist; mandated enterprise tooling is not this product's architecture. Decide scope first, then consider a narrower reference/example. |
| #17 | Re-read the complete two-file patch and current manifest validator. | Still replaces the single bundle with old individual plugin entries. The current validator requires exactly one bundle and source `./`. Superseded packaging proposal; do not regress current discovery parity. |

The unchanged exact heads allow the prior detailed findings to remain applicable. This does **not** enlarge the prior review's coverage: omitted adapters, plugin files, external dependencies, paper claims and diagrams remain unverified.

## Verification performed versus still required

Freshly executed checks were **data-only** using the trusted integrated `skill_frontmatter.parse_frontmatter`, line counts and required-section comparison on pinned public text:

| PR | Fresh result |
| --- | --- |
| #133 | Frontmatter parses, 168 lines, all eight required headings present. |
| #88 | Frontmatter parses, 269 lines, all eight required headings present. |
| #95 | Frontmatter parses, 515 lines, all eight required headings absent. |
| #24 | Frontmatter missing, 604 lines. Seven required sections fail the current validator's substring rule; an exact-heading check misses eight because “References for Deeper Understanding” only satisfies the current substring match. |

These checks do not test a merged checkout, runtime behavior, package installation, live model quality, source-platform access, or whole-PR CI. #132's 148-test failure was **observed remotely**, not executed locally in this refresh. No remote check was triggered.

Before proposing any revised content for merge:

1. Select an exact approved base and preserve the current source/authority boundaries.
2. Prepare the narrow revision or a clearly attributed superseding proposal; do not apply unrelated executables as incidental dependencies.
3. Regenerate declared inventory after the final source changes.
4. Run current trusted `validate_platform_compat.py --require-reference-validator`, `validate_repo.py --strict`, activation/inventory/skill-health gates and relevant unit/security checks in a credential-free isolated snapshot.
5. Review the exact resulting diff and resulting head-bound checks. Keep structural success separate from semantic effectiveness, human acceptance and deployment readiness.
6. Obtain the required explicit authority for any remote update, funded experiment, or merge. This report performs none of those actions.

## Supersession recommendations

- **Clear current-contract supersession:** #17's packaging shape; no need to merge it to unblock release.
- **Supersede as production infrastructure, not research evidence:** #52. The current harness is the appropriate implementation boundary, but separate tasks still need their own effectiveness evidence.
- **Replace stale navigation prose:** #89, preserving useful contributor guidance and attribution.
- **Potential extraction rather than wholesale adoption:** #55 and #72. Only carry forward mechanisms whose independent value and safe boundaries are explicit.
- **Not superseded merely by existing service code:** #133 and #88 still contain independently useful content proposals; revise them rather than claiming the current service already proves their broader guidance.
- **Separate product/scope decisions:** #132, #95, #40, #38 and #24. #36 remains an optional compatibility-documentation decision.

No PR was remotely closed or marked superseded by this work.
