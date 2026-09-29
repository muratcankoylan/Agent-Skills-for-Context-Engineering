# Community and content PR audit, 29 September 2026

## Decision

Do not merge this batch as a production dependency stack. None of these 13 PRs is required to run the current repo-native retrieval, shared-budget research, candidate-review, organization, or publication boundaries. They are independent content proposals, examples, historical packaging changes, or out-of-scope integrations.

The most promising independent content is #133 (rendered UI evidence) and #88 (context receipts), after the corrections below. #36 is a small documentation-only decision. #89 needs a current, non-duplicative operating guide. #132 should remain a separate draft example until its CI, accounting, resume, and experimental-method issues are fixed. Do not import #52 or #72 as production infrastructure. #17 is superseded by the current packaging contract. #40, #95, and #38 should not expand the core product by default.

This is a read-only review and a local report, not merge approval. No GitHub comment, review, push, merge, workflow dispatch, provider purchase, or paid model request was made.

## Evidence boundary

- Repository: [Agent-Skills-for-Context-Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering).
- Metadata and head SHAs were fetched through read-only GitHub CLI calls and rechecked at **2026-09-29 06:45 UTC**. All 13 heads were unchanged between inspection and recheck. All were open and targeted `main`.
- Remote mergeability refers to GitHub's current `main`, not the integrated local production checkout.
- Local comparison: integrated checkout at Git HEAD `c6cd52017b247804373339e1c3c103d42554b0a1`, including its existing working-tree implementation. The [generated inventory](../../researcher/generated/corpus-summary.md) reports the current corpus. That inventory is not an exhaustive runtime or security digest.
- The [service README](../../researcher/service/README.md), current [platform validator](../../researcher/scripts/validate_platform_compat.py), [corpus validator](../../researcher/scripts/validate_repo.py), and repository operating instructions define the comparison contract.
- The current organization coordinator and cumulative Campaign are repo-native. Daily retrieval-only mode, native compatibility research, and managed Agents sessions have different authority/evaluation boundaries. A contributor's unrelated CLI, MCP configuration, or cron-shaped JSON does not connect to those paths.
- Empty `statusCheckRollup` means **no checks were returned**, not a green test result. PR-body statements about tests or percentages are author-reported evidence, not independently executed verification.
- Full patches were fetched for every listed PR except #40. Inspection depth and omissions are explicit below. No contributor program, install command, workflow, or live model test was executed.
- Executed locally: data-only frontmatter parsing using the trusted current `skill_frontmatter.parse_frontmatter`, plus line-count and current required-section checks for #133, #95, #88, #72, #24, and #55. These are narrow static checks, not full PR test suites, installation tests, effectiveness benchmarks, or a merged-checkout validation.

## Head-pinned inventory

| PR | Exact head SHA | Changed files; lines | Observed remote state | Disposition |
| --- | --- | --- | --- | --- |
| [133](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/133) | `65f501cdf2148a01b19db6cc6ad569c723b7a7d2` | 7; +185/-1 | Mergeable; no checks returned | Independent content. Correct portability/inventory, then run current gates. |
| [132](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/132) | `83b5ad0b6afd4eae094493877c58cddf95dcdc00` | 43; +3333/-5 | Draft; mergeable; validate failed | Keep draft, request accounting/resume/evaluation fixes. |
| [95](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/95) | `f7eedc9104a929a937ebb5fb7aae88e1d4d2ee70` | 1; +515 | Mergeable; no checks returned | Vendor automation scope mismatch; do not add to core. |
| [89](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/89) | `b84d8fabe14d5f5c71a57207e3ae56d49a8c0775` | 1; +167 | Mergeable; no checks returned | Rewrite as a thin current internal map, not duplicated authority. |
| [88](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/88) | `ef6bb240008631ff5820b347c717bfa32a15ce83` | 9; +293/-7 | Conflicting; no checks returned | Useful independent content; rebase and correct acceptance/proof claims. |
| [72](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/72) | `c5f5bdb2c2bfd72385a0ec9ab9e5c698562d3153` | 11; +2113 | Conflicting; no checks returned | Request changes; data-loss/state-integrity defects. Not a runtime dependency. |
| [55](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/55) | `25481be1fa99472f44f1938d32ef6d2a62b838a7` | 2; +86/-194 | Conflicting; no checks returned | Split content from external automation; reject as-is. |
| [52](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/52) | `84439d0a3d6dbe2a622cbcf8bea8713efdf88925` | 6; +608 | Conflicting; no checks returned | Request major changes or supersede with existing native evaluation work. |
| [40](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/40) | `a9548805a44ae86fa1b229ce4587d18a1ce2be17` | 599; +75001 | Conflicting; no checks returned | Scope mismatch. Do not merge wholesale. Limited security-surface review only. |
| [38](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/38) | `ee0de997f47ad83b812c317bc74c3e8a0d13e2c3` | 1; +23 | Mergeable; no checks returned | Optional external-resource curation, not 78 delivered integrations. |
| [36](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/36) | `ecec05aec7acc1fc97944d2e43f1ba95af022720` | 1; +1/-1 | Mergeable; no checks returned | Independent docs; qualify or verify platform compatibility. |
| [24](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/24) | `41eaad316b80307a51922f5fb7046ff581191807` | 15; +3123 | Conflicting; no checks returned | Scope decision plus substantial skill-format rework. |
| [17](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/17) | `aaef0164e62b03aa29916cb9899a19a63c428eb2` | 2; +149/-16 | Conflicting; no checks returned | Superseded; do not replace current bundled discovery. |

## Detailed findings

### #133: Add rendered UI finish gate skill

**Classification:** independent content with a plausible context-engineering boundary; not a control-center implementation or UI test suite.

**Inspected:** complete seven-file patch, including the entire 168-line skill, marketplace registration, corpus entry, activation fixture, mechanism row, and root documentation.

The skill distinguishes product context, required states, rendered evidence, deterministic interaction/accessibility checks, and human judgment. The mechanism is correctly introduced as `candidate`, not silently accepted. No execution hook, paid call, or service change is added.

Corrections before a content merge:

1. [The skill's References section](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/65f501cdf2148a01b19db6cc6ad569c723b7a7d2/skills/rendered-ui-finish-gate/SKILL.md) links `../../template/SKILL.md`. Copying this skill alone to a platform skill root, as the repository documents, does not copy that repository-level template. Use a portable reference or remove the runtime dependency on a contributor template.
2. The patch changes inventory inputs and introduces a skill but does not regenerate `researcher/corpus/inventory.json` or `researcher/generated/corpus-summary.md`. Rebuild and check the generated outputs on the final integration. Do not preserve stale counts/digests.
3. Add an adversarial activation case where a generic agent-evaluation request happens to mention a UI, and a worked finish-gate result containing a real failed state. The one positive activation fixture is useful but does not establish boundary discrimination or downstream effectiveness.
4. Keep unsupported states distinct from required-state passes. The content already mostly makes this distinction; reporting must not turn an acknowledged coverage gap into a completion claim.

**Verification:** trusted data-only check passed frontmatter and all required headings; 168 lines. The author reports several local validators, but GitHub returned no checks. No rendered UI experiment or complete PR checkout validation was performed in this audit.

**Disposition:** prioritize for a small independent content revision after portability and inventory fixes. It is not a prerequisite for launching the service.

### #132: Add deliberative-writing-loop example: inference-time persona writing harness

**Classification:** independent research example, not a replacement for the shared-budget production Campaign.

**Inspected deeply:** example README, adapter base/OpenAI/Anthropic/Pangram implementations, environment loader, CLI, benchmark runner, writing-loop controller, and benchmark tests. The complete 43-file patch and file inventory were fetched. Persona/planner/critic/memory/stylometry internals, synthetic corpus contents, every individual test, and cited literature were not exhaustively reviewed or independently validated. This is a bounded accounting/resume/methodology review, not a 43-file security sign-off.

High-confidence defects:

1. **Resume does not bind experimental identity.** [`benchmark.run_item`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/benchmark.py) accepts any existing filename derived from brief ID, persona name, condition, and provider. Changing brief text, persona corpus, model, target length, or harness code can return an old result without a call or identity rejection. The saved item has no model/config/source closure sufficient for reproducible resume.
2. **Advertised resumable writing is not implemented at the stage boundary.** [`WritingRun.run`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/harness.py) always rewrites inputs, replans, and redrafts. A provided existing run ID does not load a checkpoint or skip paid completed stages. Writes are direct rather than atomic, and there is no durable intent/unknown-effect boundary.
3. **Dollar accounting is not a cumulative hard bound.** [`Budget.charge`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/adapters/base.py) increments calls but does not retain an estimated dollar reservation; only a parsed successful response settles dollars. State resets on process restart. A four-characters-per-token heuristic is not an input-token upper bound, prices are provider-wide rather than model-bound, and non-finite caps are not rejected. The [Pangram call](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/adapters/pangram.py) is outside this budget entirely. The CLI also advertises a per-cell call cap but implements only `max_calls * number_of_items` on one shared counter.
4. **Judging cannot safely resume.** [`_cmd_judge`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/83b5ad0b6afd4eae094493877c58cddf95dcdc00/examples/deliberative-writing-loop/src/dwl/cli.py) scans every top-level JSON result, then writes a list to `judgments.json` in that same directory. The next invocation attempts `data.get("item")` on that list and fails. Judgments are only persisted after the entire loop, so interruption can duplicate previous paid comparisons.
5. **Compute matching and improvement claims are not demonstrated.** Whole-document self-refine makes three generation calls total; the paragraph-level loop can make many more. “Call count matched to DWL's repair budget” is not a matched overall compute baseline. Optimizing and evaluating on the same deterministic stylistic criteria is not independent evidence of improved writing. The README's reduction/token-cost claims need to be hypotheses until supported by retained, version-bound experiments.

**Observed CI:** the [validate job](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/actions/runs/32206656273/job/95931121150) ran on 19 August and failed `test_committed_generated_outputs_match_builder`: **148 repository tests, one failure**, generated inventory digest mismatch. This is the failure observed in the job log; it is not evidence that all 47 example tests failed or ran in that job. The author separately claims 47 offline tests; they were not rerun here.

**Disposition:** keep draft. Fix durable accounting, exact resume identity, repeated judging, generated inventory, and honest experiment claims before a separately reviewed example merge. Do not run this with the production keys or incorporate it into the autonomous loop as-is.

### #95: Add Linked API linkedin skill

**Classification:** vendor-specific LinkedIn automation, outside the core context-engineering/research-harness scope.

**Inspected:** the entire sole 515-line [skill file](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/f7eedc9104a929a937ebb5fb7aae88e1d4d2ee70/skills/linkedin/SKILL.md).

The file documents an external global npm CLI, account credentials, profile/company search, messages, posts, connection removal, account reset, and arbitrary vendor workflows. It is not a repo-native source adapter or MCP registration.

Blocking issues for inclusion as a core published skill:

- It exceeds the enforced 500-line cap and lacks all eight required body headings. It updates no marketplace, corpus, activation, mechanism, or generated-inventory surface.
- Credential onboarding instructs the user to provide tokens and put them in CLI arguments. That exposes secrets to process arguments/tool-call transcripts and contradicts the explicit secret-file/environment boundary used by this harness.
- Read and externally mutating operations share one broadly activated instruction surface without explicit per-action confirmation, least-privilege, idempotency, or uncertain-outcome guidance. Merely asking to interact with LinkedIn is not authorization to send messages, publish, remove connections, or reset accounts.
- A mutable global `npm install -g` is recommended without a reviewed/pinned dependency or a clear manual installation boundary.

**Verification:** data-only frontmatter parsed, but line/heading checks failed as described. No CLI installation, login, API request, platform-terms review, or account action was performed.

**Disposition:** do not merge into the core skill collection. If the maintainer wants this resource, consider a separately scoped example or external link with explicit ownership, privacy, permission, and dependency review.

### #89: Add internal repo-contributor skill as project knowledge base

**Classification:** internal contributor documentation, not a published skill or production feature.

**Inspected:** the complete 167-line [.claude-only guide](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/b84d8fabe14d5f5c71a57207e3ae56d49a8c0775/.claude/skills/repo-contributor/SKILL.md).

Its multi-surface authoring and deterministic-first guidance is useful, and it explicitly says authoritative files override it. However, copying current authority into a second long document has already produced drift:

- It calls version 2.3.0 and 15 skills current, while the integrated corpus is 2.5.0 with a generated current inventory.
- It describes legacy network retrieval and mechanism promotion as active, although current historical docs mark that loop dormant/inert and promotion fail-closed.
- It presents the Cursor SDK as the only live paid surface, while the legacy runner is zero-call and the separately authorized service Campaign owns current funded execution.
- Its gate list omits the current required reference platform validator and the service/candidate/inventory contracts.
- It includes a push-and-retry recipe alongside the explicit no-push-without-approval constraint. Remove executable workflow advice from a memory guide unless it is clearly downstream of current user authority.

**Verification:** source comparison only; no runtime test is applicable to the added instruction document. No CI checks were returned.

**Disposition:** request an updated, short navigation skill that links to current runbooks and generated facts instead of duplicating them. Do not make this Claude-only guide the authority for a cloud, model-agnostic system.

### #88: Add context receipts skill

**Classification:** relevant independent content, overlapping the current artifact/provenance/export architecture but not implementing it.

**Inspected:** complete nine-file patch and entire 269-line [skill](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/ef6bb240008631ff5820b347c717bfa32a15ce83/skills/context-receipts/SKILL.md).

Useful mechanisms include separating returned from loaded context, first-class suppression events, transformation versus committed swap, privacy-aware correlation, and explicit audit gaps.

Required corrections:

1. The new [mechanism row](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/ef6bb240008631ff5820b347c717bfa32a15ce83/researcher/mechanisms/registry.jsonl) labels `redacted-context-receipt` **accepted**, backed only by the new skill itself, with no acceptance-ledger change. Introduce it as a candidate unless the existing acceptance/provenance process has actually been satisfied.
2. A JSON event and `raw_content_logged: false` are assertions, not independent proof that content was loaded or never leaked. Specify the trusted emission boundary, exact source/config binding, retention/export checks, and residual gaps. Align with current schema/ArtifactRef/StorageBinding and export contracts without implying that public hashes confer authority.
3. The text correctly acknowledges hash correlation risk, but exported raw content/query hashes can also reveal low-entropy values by guessing. Prefer opaque/private binding or keyed scoped identifiers where disclosure risk matters; a visible salt alone does not prevent guessing.
4. Cross-skill relative links under `../other-skill/SKILL.md` fail in single-skill installations. Use the repository's plain-name cross-skill convention. Rebase old version/count edits onto the generated inventory and regenerate derived artifacts.

**Verification:** data-only shape check passed frontmatter/all required headings; 269 lines. GitHub reports conflicts and no checks. No receipt implementation, redaction/leak test suite, or effectiveness experiment is included or executed here.

**Disposition:** retain and revise as content. It is a strong candidate for distilling actual production-boundary lessons, but should not be described as adding verifiable runtime receipts merely by merging prose.

### #72: Add session-handoff skill for cross-session task continuity

**Classification:** independent task-tracking system; overlaps existing memory/project/long-horizon guidance and must not replace production run state.

**Inspected deeply:** complete skill, lifecycle reference, and all five Python scripts. All 11 changed paths were inventoried and the patch was fetched. Other reference/template prose was not exhaustively checked.

High-confidence correctness problems:

1. **Registry loss on a documented safe option.** [`tc_init.py`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/c5f5bdb2c2bfd72385a0ec9ab9e5c698562d3153/skills/session-handoff/scripts/tc_init.py) describes `--force` as preserving the registry, but `if not registry_path.exists() or args.force` writes a new empty registry with sequence 1. Reinitializing a populated project loses the index/statistics and may reuse IDs. Existing record files remain, which is not equivalent to preserved registry state.
2. **Claimed validation and lifecycle evidence are absent.** [`tc_update.py`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/c5f5bdb2c2bfd72385a0ec9ab9e5c698562d3153/skills/session-handoff/scripts/tc_update.py) checks the transition pair but never calls the schema validator. An empty-test, unapproved record can walk through implemented, tested, and deployed. The standalone validator also does not verify those state-dependent requirements or replay history transitions. “Always enforced” is therefore false.
3. **Concurrent agents can lose updates.** Create/update read and replace the shared registry without a lock. They use the same deterministic `.tmp` filename. Two creates with different names can allocate the same sequence and overwrite each other's registry entries; concurrent updates can overwrite revisions. This conflicts directly with the skill's recommendation to use background subagents.
4. **Target selection is not exact or confined.** `find_record_path` combines unchecked `--tc-id` with a path, follows existing paths, and otherwise picks the first prefix match. A path-like ID can escape the records directory; an ambiguous prefix can select the wrong record. Validate exact IDs, reject traversal/symlinks as appropriate, and reject multiple prefix matches.
5. The skill claims a shipped `commands/tc.md` dispatcher with resume/close/export/dashboard capabilities, but no such file is added in this PR. These commands are not delivered by the five scripts.
6. No corpus/marketplace/mechanism/activation integration is added. The 218-line skill parses, but six current required headings are missing.

**Verification:** static source/data-only checks only. No contributor script was executed. Required follow-up tests are force-preservation, process-crash between record/index commits, concurrent create/update, malformed state, missing test/approval evidence, ambiguous ID, traversal/symlink refusal, and genuine resume.

**Disposition:** request changes or extract a smaller handoff pattern into existing skills. Do not merge this as the persistence or approval system for the research organization.

### #55: Improve multi-agent-patterns skill and add skill review workflow

**Classification:** existing content change mixed with a new external CI execution surface.

**Inspected:** complete two-file diff and full resulting skill; additionally the pinned external action's `action.yml`, `src/main.ts`, `src/install-tessl.ts`, and `src/skill-review.ts`. Its entire transitive dependency/runtime distribution was not audited.

Problems:

- The rewrite removes seven current required headings, ownership boundaries, and much of the integration guidance. The full resulting skill is 133 lines, but brevity does not substitute for the corpus contract.
- Fixed “3 failures then reroute” and a universal exponential-backoff recipe do not distinguish safe reads from paid or mutating unknown outcomes. Retry/idempotency/budget boundaries must be explicit.
- The retained 15x token and 50% performance statements and new evaluation percentages do not come with this repository's provenance records or a reproducible same-fixture routing/body-effectiveness comparison.
- [The workflow](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/25481be1fa99472f44f1938d32ef6d2a62b838a7/.github/workflows/skill-review.yml) grants PR-write permission to a third-party action. Although that action is SHA-pinned, its [installer](https://github.com/tesslio/skill-review/blob/14b47c8420ff9ac9a12c30ed4b89ce0e9d0355ae/src/install-tessl.ts) executes `curl -fsSL https://get.tessl.io | sh`, so the executed CLI is not frozen by the action SHA. The composite action also supplies the GitHub token to its process. This is an additional supply-chain/data-processing trust boundary, not a deterministic local gate.
- The action's default `fail-threshold` is zero; its code does not fail on review errors or low review scores in this mode. Therefore a successful job is not evidence of content quality. Actual remote processing/privacy behavior was not independently established here.

**Verification:** data-only frontmatter parsed; seven required headings missing. No new CI check is observed. No external installer/action or evaluation was executed.

**Disposition:** split the proposals. Preserve useful workflow explanations only after rebasing and validating the current skill. Do not add the remote review action without a separately approved dependency/data-policy review and an explicit non-gating versus gating contract.

### #52: feat: adding a context benchmarking-skill

**Classification:** a standalone paid demonstration labeled as production regression infrastructure; superseded in scope by current native evaluation boundaries.

**Inspected:** all six changed files, including the complete workflow, runner, skill, and three-case fixture.

Blocking defects:

1. **It does not test the changed system.** [`call_agent`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/84439d0a3d6dbe2a622cbcf8bea8713efdf88925/skills/context-benchmarking/scripts/run-benchmark.py) sends the original context and question directly to a fixed model. No skill body, compression implementation, retrieval adapter, candidate snapshot, or changed configuration is loaded. A passing run cannot establish that a repository skill change did not regress context engineering.
2. **Regression failure can publish a passing result.** `results["passed"]` reflects only the absolute 0.80 threshold and is written before `check_regression`. For a baseline of 1.0 and current 0.90, the process exits 1 on the relative gate, but the stored result and the workflow PR comment say PASSED.
3. **A failed or lower baseline can overwrite the reference.** With `--update-baseline`, the runner writes the current score before its final absolute-threshold failure, and skips relative comparison. This contradicts the skill's promise never to lower the baseline.
4. **Budget control is only a trigger.** Input size and case count are unbounded; there is no cumulative dollar/call reservation, per-item durable receipt, safe resume, or bounded unknown-effect policy. The installed SDK is unpinned. The workflow's label/manual trigger does not make provider execution cost-safe, and the advertised small dollar estimate is not a validated bound.
5. **Judge output is not validated against expected facts.** Arbitrary score counts, duplicate facts, or values outside 0/1 are averaged. A judge can return one favorable fact and produce recall 1.0 while omitting the rest.
6. **Baseline cache and PR integration are not reliable authority.** A constant immutable Actions cache key cannot implement successive baseline updates, and a global score-only baseline does not bind fixtures/model/harness. PR-comment permissions are not explicitly declared, and fork PRs do not receive ordinary repository secrets. These operational limits are omitted from the “CI-ready” description.
7. Seven required skill headings, marketplace/corpus/activation/mechanism registrations, and generated inventory updates are absent. An unrelated empty root package lock is also added.

**Verification:** full static review; no paid runner or workflow execution. The author explicitly says no live run was performed. No CI checks were returned. The numeric witnesses above are source-derived examples, not provider measurements.

**Disposition:** do not merge as a launch gate. Preserve only independently useful methodological prose after reconciling it with current evaluation/harness skills. Any runnable example needs strict schemas, immutable baseline identity, validated score coverage, budget reservation, durable resume, and actual candidate-vs-control execution.

### #40: Apply context engineering refactor to sales, copywriter, sentinel, solo-maker, and solo plugins

**Classification:** scope mismatch, not a refactor of the current research service.

**Inspection limit:** **all 599 changed filenames** were retrieved through paginated REST calls, overcoming the initial CLI metadata's 100-file limit. Twelve files were read in full: root `CLAUDE.md`; copywriter plugin manifest, MCP configuration, hooks, and Reddit server; sales MCP and hooks; sentinel hooks; solo-maker MCP and hooks; solo MCP and hooks. The remaining **587 file contents, including most skills, agents, references, and business data templates, were not audited**. No blanket correctness, licensing, privacy, or security clearance is implied.

The import adds 75,001 lines across five unrelated plugin products. It is not needed for research discovery, exact capture/replay, candidate evaluation, or cloud deployment.

Concrete findings in the inspected subset:

- [Root CLAUDE.md](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/a9548805a44ae86fa1b229ce4587d18a1ce2be17/CLAUDE.md) describes an old documentation-only repository and five marketplace bundles, contradicting the current service and single-bundle packaging.
- [Copywriter MCP configuration](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/a9548805a44ae86fa1b229ce4587d18a1ce2be17/copywriter/.mcp.json) invokes unpinned `npx -y` servers and places password/client-secret placeholders in command arguments. It grants filesystem writes and exposes publication/outreach integrations outside the service's registered, read-only tool contract.
- [The Reddit server](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/a9548805a44ae86fa1b229ce4587d18a1ce2be17/copywriter/scripts/reddit_mcp.py) has no schema maximum for result limits or subreddit count, calls synchronous PRAW operations inside async handlers, suppresses per-subreddit errors while reporting the requested set as searched, and lacks the service's response/capture/budget boundary.
- Hook files point to `../sentinel-v8/agents/reality-checker.md`, but the import creates `sentinel/`, not `sentinel-v8/`. Their `Schedule`, `condition`, and skill/agent dispatch declarations are not registered with the repo-native scheduler; no contract tests or delivered loader establish that these declarations run as claimed.
- None of the newly listed MCP endpoints was initialized or contract-tested in this review. Configuration text is not evidence of a working or authorized connector.

**Verification:** no checks returned; PR test-plan items are unchecked. No code or plugin was installed or executed.

**Disposition:** do not merge wholesale. If useful, ask for one small, mechanism-focused contribution or maintain the plugin suite in its own repository with its own dependency, permissions, test, and licensing review.

### #38: Add 78 Composio SaaS app automation skills via Rube MCP

**Classification:** external vendor-resource recommendation.

**Inspected:** complete sole [README patch](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/ee0de997f47ad83b812c317bc74c3e8a0d13e2c3/README.md).

The change adds 23 documentation lines and a broad `npx skills add ... --all` recommendation. It does **not** add 78 skill directories, register a service MCP tool, provision credentials, validate schemas, enforce read-only scope, or exercise an integration. “Production-ready” is an unverified vendor-quality claim in this patch.

**Verification:** source inspection only; no checks returned. The external 78-skill collection, installer, live endpoint, permissions, pricing, and data policy were not audited.

**Disposition:** optional, clearly labeled external-resource link after a curation decision. Remove the blanket production-readiness claim and avoid recommending automatic installation of every unrelated integration. Do not list this PR as completing research MCP coverage.

### #36: docs: add AdaL to compatible platforms list

**Classification:** independent, one-line documentation change.

**Inspected:** complete [README patch](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/ecec05aec7acc1fc97944d2e43f1ba95af022720/README.md). It adds “AdaL” to the platform list and nothing else.

No executable/package change is present. However, the PR provides no versioned discovery/install/activation evidence for AdaL, and this audit did not perform a platform smoke test. The current repository's deterministic platform checker does not test AdaL runtime discovery.

**Verification:** no CI checks returned, no platform execution performed.

**Disposition:** merge separately only if the maintainer accepts a qualified compatibility statement or obtains a documented install/discovery/activation smoke result. It should not block or certify service launch.

### #24: feat: Add Solution Architecture skill with comprehensive reference ma…

**Classification:** broad enterprise-architecture content, not the architecture implementation of this research harness.

**Inspected:** entire 604-line main skill, ADR template, file inventory, and opening project-structure/requirements sections. The 13 supporting reference files were fetched in the patch but were **not all read exhaustively**; diagrams were not rendered or checked against ArchiMate/UML specifications.

Concrete package and scope problems:

- [`skills/architecture/SKILL.md`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/41eaad316b80307a51922f5fb7046ff581191807/skills/architecture/SKILL.md) has no YAML frontmatter and exceeds the 500-line cap. Seven required section headings are missing. This is a current deterministic publication failure, not a stylistic preference.
- Only README and the new skill/reference tree are changed; marketplace, corpus, mechanisms, activation fixtures, and generated inventory are not integrated.
- It mandates Enterprise Architect/ArchiMate/LinkML deliverables and a large project scaffold for generic architecture tasks. Those are choices for a particular practice, not established requirements of a lightweight, platform-agnostic research harness.
- “Irreversible commitment” as the sole ADR criterion and prescriptive diagram-level restrictions need qualification; important reversible choices and trade-offs also deserve durable decision records. The contribution does not demonstrate a task boundary distinct from project-development/harness-engineering.

**Verification:** trusted parsing returned “missing or invalid frontmatter delimiters”; 604 lines and seven missing headings. No contributor code was run; no checks returned.

**Disposition:** request a narrower scope decision before formatting work. A separately labeled architecture example/reference may fit better than a universally activated core skill. No launch dependency.

### #17: fix: expand marketplace to list individual skills for proper discovery

**Classification:** historical packaging proposal, superseded by the current one-bundle contract.

**Inspected:** complete two-file patch and current local manifest validators.

The [proposed manifest](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/aaef0164e62b03aa29916cb9899a19a63c428eb2/.claude-plugin/marketplace.json) changes the suite into individual plugin entries at old skill-relative sources. The current implementation intentionally requires exactly one `context-engineering` bundle, `source: "./"`, explicit skill paths, and discovery parity with Open Plugins. The historical ten core entries plus book example do not represent the current 17-skill corpus.

Applying this as the current manifest would fail `validate_platform_compat.py` and `validate_repo.py` by construction, break the documented suite installation name, and omit later skills. This is a source-contract comparison; a merged-checkout validator execution was not performed.

**Verification:** no checks returned, no runtime installation performed. GitHub reports conflicts.

**Disposition:** treat as superseded, not an unresolved production blocker. Any future individual-install feature should be a new explicit design with backward compatibility, complete discovery parity, and installation tests.

## Verification summary and limits

| Narrow executed check | Result |
| --- | --- |
| #133 skill data | Frontmatter and all eight required headings present; 168 lines |
| #88 skill data | Frontmatter and all eight required headings present; 269 lines |
| #95 skill data | Frontmatter parses; 515 lines; eight missing required headings |
| #72 skill data | Frontmatter parses; 218 lines; six missing required headings |
| #55 resulting skill data | Frontmatter parses; 133 lines; seven missing required headings |
| #24 skill data | Frontmatter invalid/missing; 604 lines; seven missing required headings |
| Current-head recheck | All 13 exact SHAs unchanged during review |

Separately observed, not executed by this audit: #132's GitHub repository suite ran 148 tests and failed one inventory-consistency test. All other reviewed heads returned no check records.

Not executed: full isolated PR checkout tests, external action installers, API calls, source-platform logins, paid benchmarks, platform runtime installs, diagrams, or deployment. The report deliberately does not convert code inspection into a production-test claim.

## Recommended handling order

1. Keep the production-runtime release dependency graph separate. Finish and verify its own authorization, retrieval, evidence, evaluation, publication, deployment, and recovery gates. None of this batch substitutes for them.
2. Prepare small content-only revisions for #133 and #88. Rebase individually; do not stack them merely because both are new skills. Add portable references, provenance/acceptance correctness, generated inventory, and activation-boundary checks.
3. Resolve #36 and rewrite #89 independently as documentation decisions.
4. Keep #132 a separately budgeted draft research example. Fix its failure modes before any live experiment.
5. Request substantial changes or supersede #52, #72, and #55. Do not deploy their new control paths as part of the research harness.
6. Treat #40, #95, #38, and #24 as separate scope/curation decisions; prefer a focused example or external resource when appropriate. Treat #17 as superseded.

Before any subsequent merge recommendation, re-fetch the head SHA, resolve conflicts against the intended release base, regenerate derived inventory, run the current trusted deterministic gates and relevant unit/security tests in a credential-free isolated checkout, and review the resulting diff. Paid effectiveness evaluation requires its own explicit authority, immutable experiment identity, cumulative reservation, and retained evidence. A clean merge bit or an author-reported score is not that evidence.

