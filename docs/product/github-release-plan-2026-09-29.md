# GitHub production architecture and merge preparation

Date: 29 September 2026. Status: reviewed implementation candidate and deployment design, not an activated deployment or accepted specification.

Later SDK update: the [runtime migration](codex-sdk-runtime-migration.md) supersedes
the managed-executor decision below. The [SDK runbook](../../researcher/service/CODEX_SDK.md)
describes the integrated caller/gateway and persistent Linux reference profile.
This PR inventory remains a dated snapshot; the [author-scoped stack receipt](pr-stack-2026-09-29.md)
records the narrower authorized release chain. No SDK integration was published
or merged by changing these plans.

## Executive decision

The product belongs in the open-source repository. Its proposed production control plane runs through GitHub, and its managed model runtime is the OpenAI Agents API. Neither the Codex desktop application nor a personal scheduled task is a production dependency.

All **36 open PRs** received head-pinned, risk-focused review. They are not one mergeable product backlog. Twelve form the existing governance/transport stack; eleven security/maintenance proposals need replacement, splitting or correction; thirteen community/content proposals are independent of the production runtime. Inspection limits, especially the 599-file #40 import, are explicit in the linked audits. This is not a claim that every line of every PR was certified.

The concrete release work in this iteration is a local exact-stack rehearsal, executable merge-queue authority tests, a secret-free release workflow, runner-loss/recovery scenarios, a closed aggregate-evidence contract and updated merge/deployment documentation. No remote PR was changed, no branch pushed, no merge performed, no repository protection changed and no paid model session started.

The principal next implementation is **remote durable admission**, not another agent or cron wrapper. Local SQLite, local locks and post-run artifact uploads cannot preserve pre-call budget/session intent across destruction of an ephemeral runner. The managed-runtime cost contract must also be resolved explicitly before paid unattended execution under an absolute cumulative allowance.

## Review inventory and merge order

### Latest PR refresh and isolated update package

The [PR update package](pr-updates-2026-09-29/README.md) is the current handoff:
36 exact-head dispositions, the existing dependency graph, three independently
scoped patch files, their SHA-256 bindings, and fresh combined-tree evidence.
It supersedes earlier recommendations only where explicitly stated. The remote
heads are unchanged. Nothing has been pushed, retargeted, closed or merged.

The narrow #134 transport correction and replacements for #83/#80 were isolated
from the unpublished service. The combined candidate passes 389 repository tests
and 69 focused tests; the same 69 focused tests pass on native Linux ARM64.
These counts overlap and do not establish research quality or hosted deployment.
The package records the AMD64-emulation filesystem side effect and remaining
hosted-CI check rather than hiding the initial failing experiment.

The subsequent [tracing and engineering pass](tracing-engineering-verification-2026-09-29.md)
adds private telemetry, explicit Raindrop export, managed trace projection,
installer safety and evaluation-example attempt/retry controls. Its release
catalog runs 427 tests across 11 groups. These are local follow-on changes, not
updates to the remote PR heads reviewed below.

The [refreshed machine-readable observation](evidence/github-pr-refresh-2026-09-29.json) preserves public PR metadata. Fresh exact-head audits are [core](pr-refresh-core-2026-09-29.md), [maintenance](pr-refresh-maintenance-2026-09-29.md), and [community](pr-refresh-community-2026-09-29.md). Earlier source reviews, whose unchanged heads remain relevant, are:

| Review | PRs | Disposition |
| --- | --- | --- |
| [Governance/runtime stack](pr-stack-review-2026-09-29.md) | 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 134 | Sequential human review and merge; carry the transport/dependency corrections before managed-runtime release |
| [Security/maintenance audit](pr-security-review-2026-09-29.md) | 113, 112, 111, 110, 109, 100, 92, 83, 82, 81, 80 | None of these exact heads should merge unchanged |
| [Community/content audit](pr-community-review-2026-09-29.md) | 133, 132, 95, 89, 88, 72, 55, 52, 40, 38, 36, 24, 17 | No core launch dependency; revise useful content separately, do not import unrelated execution systems |

```text
main@6dbe1a1
  -> #121 -> #122 -> #123 -> #124 -> #125 -> #126
  -> #127 -> #128 -> #129 -> #130 -> #131 -> #134
  -> reviewed production follow-on slices
  -> exact-build hosted rehearsal
  -> separately approved canaries and activation
```

The isolated local branch `codex/pr-stack-rehearsal-20260929` reaches #134 at `9639dda3c5b2b6fb3ddfd88a3478c3dc90aa7c54`. Its tree is `d1503a3e550eda804f5583e3ce6f0278a94e23ac`. Git integration against observed main is conflict-free. However, one aggregate main-to-tip lifecycle check rejects four legacy-adoption transitions. Each exact-parent transition passed. Merge #121's normalization before the later amendments; do not disable the gate or include #121 and all amendments in one lifecycle interval. The refresh also tested a hypothetical already-promoted #121 base: a cumulative #122–#134 candidate then passes the lifecycle gate. That is a possible separately approved consolidation, not evidence of current promotion or permission to retarget the existing PRs. Preserve the current chain by default.

#121 is the first review candidate. #122 through #131 and #134 are still drafts. None has an approving review. Historical green checks are not current approval of the unpublished service.

### Findings that change the merge plan

- **#134:** its published transport rejects HTTP 201 on session creation. A successfully created session could be classified as uncertain before retaining its identity. The integration candidate accepts 201 specifically for create and hardens duplicate/framing-header handling, with three additional transport tests. Preserve those local fixes when incorporating #134.
- **#113/#112/#109/#81:** process-lock exclusion, per-effect budgets, item-path containment and credential isolation respectively remain incomplete in the proposed fixes. Stronger local replacements have targeted tests; the superseded PRs must not overwrite them.
- **#100/#52:** zero-work or regression-failing evaluations can produce favorable publication claims. Their live runners also lack the current source/budget/reconciliation boundary. Separate historical evidence from executable authority.
- **#72:** the proposed persistence layer can erase its registry with `--force`, does not enforce promised lifecycle evidence, and races concurrent updates. It must not become production state.
- **#55:** a SHA-pinned action still downloads a mutable shell installer while holding a GitHub token. Default successful execution is not a gating content-quality result.
- **#132:** failed CI and experimental accounting/resume issues remain. It is a separate draft example, not part of deployment.
- **#80:** invalid frontmatter is a small independent correction, not a launch dependency. #133 and #88 are relevant content after integration/provenance corrections. #36 is a separate documentation decision.

### Repository protection is part of deployment

Observed active ruleset `11425130` requires PRs and conversation resolution but **zero approving reviews and no successful status checks**. Stale approvals are not dismissed, last-push approval is not required and administrator bypass is always available. Code-level checks cannot enforce a boundary that repository settings permit bypassing.

Before activation, separately authorize: stable required validation/release checks, an independent approving review, stale-review dismissal, last-push approval, applicable code ownership and narrowly documented emergency bypass. Verify the actual check names after their first hosted run. A candidate-controlled workflow is not its own trusted verifier; protect the required workflow or execute the authoritative verifier from a protected approved source. No API or publication secret belongs in public PR CI. GitHub specifically cautions against executing untrusted PR code in privileged event contexts. [GitHub workflow security](https://docs.github.com/en/actions/reference/security/secure-use), [pull_request_target guidance](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target).

## Runtime architecture

```text
PUBLIC REPOSITORY
  untrusted proposals -> secret-free CI -> human merge -> approved source SHA
                                                 |
PRIVATE CONTROL PLANE                            v
  manual/daily trigger -> stable schedule slot -> durable admission transaction
                                                 |
                           bounded retrieval + capture verification
                                                 |
                              OpenAI managed Agents API session
                                                 |
                           frozen proposal -> independent evaluation
                                                 |
                            validated sanitized export receipt
                                                 |
SEPARATE PUBLISHER                                v
  short-lived repository-scoped credential -> draft PR + operator notification
                                                 |
                                      human review and merge
```

The OpenAI Agents API is a managed Codex harness. The Agents SDK, Responses API and a local Codex SDK/action are different deployment surfaces. The existing bounded Responses pipeline must not be relabeled as managed Codex execution. The current managed adapter is a separately supervised canary, not a deployed shared scheduler. [OpenAI agents guide](https://developers.openai.com/api/docs/guides/agents), [Codex GitHub Action](https://learn.chatgpt.com/docs/github-action).

### Deployment alternatives

| Option | Advantage | Cost or limitation | Decision |
| --- | --- | --- | --- |
| Private GitHub controller plus conditional private Git ledger | GitHub-native operator experience; small low-throughput ledger without another database | New backend required; Git retention/deletion and large captures are awkward; token can mutate state unless protections are enforced | Recommended pilot control topology, subject to owner approval and fault tests |
| Private GitHub controller plus transactional database and private object storage | Explicit transactions, retention, queryability and large-artifact handling | Additional account, credentials, migration and operations | Better growth path if capture volume or retention requirements justify it |
| Persistent Linux coordinator | Existing local transactional/locking model maps directly | Requires an always-on host; not the requested GitHub-hosted control plane | Retained as optional deployment profile, not the default target |
| Public Actions plus caches/artifacts as authority | Superficially simple | Private-data exposure, stale restore and lost pre-effect reservations | Reject |

The proposed private repository is not yet created or selected. A private Git ledger should use immutable commits and a single authoritative ref with expected-current-OID conditional updates. GitHub documents atomic `updateRefs` operations with `beforeOid`; this is a candidate primitive, not proof of an implemented backend. Do not use unconditional branch replacement, force-push or last-writer-wins JSON uploads. Large raw captures should not be put into an ever-growing Git history by default. [GitHub conditional reference updates](https://docs.github.com/en/graphql/reference/git).

### Component responsibilities and state ownership

| Component | May do | Must not do |
| --- | --- | --- |
| Public CI | Parse, lint, test fixtures, build isolated dependency images | Receive provider/write secrets, run paid experiments, promote itself |
| Private coordinator | Admit stable slots, reserve allowance, supervise known sessions, reconcile outcomes | Infer a new allowance from a new runner or directory; execute unapproved source |
| Retrieval adapters | Use reviewed API/MCP contracts, capture bounded responses, retain provenance | Treat retrieved text as instructions or let model-supplied URLs choose credential destinations |
| Managed research roles | Analyze verified context, cite capture spans, propose bounded edits | Access publication credentials, modify controller policy, invent evaluation gold |
| Independent evaluator | Execute frozen candidate/control under exact fixture/model/source identities | Let candidates change graders or see held-out answers |
| Publisher | Consume validated path-limited export; reconcile deterministic draft PR identity | Run generated programs, merge PRs, amend approval or spending policy |
| Operator | Approve releases, pause admission, review uncertainty and proposals | Treat telemetry or a generated report as independent acceptance evidence |

The role pipeline remains researcher, critic and optional editor. Role outputs are typed, source-grounded and separately recorded. More agents are not a quality target. Add parallel branches only when paired experiments show a useful improvement per cost and latency.

## Remote admission and recovery contract

This section specifies the next implementation, not existing remote behavior. The current local Campaign and managed SessionLedger provide reusable invariants and tests, but their file locks do not coordinate ephemeral hosts.

One atomic admission must bind:

1. Stable schedule slot and operation ID, independent of GitHub run/retry IDs.
2. Approved source, runtime/dependency, prompt/configuration and policy digests.
3. Existing cumulative budget authority and conservative reservation.
4. Current writer epoch or compare-and-swap predecessor.
5. Exact effect request identity and durable `prepared` intent.

Only after that write is confirmed can a provider effect begin. If the write response is lost, read/reconcile the authoritative ref before dispatch. If provider submission is uncertain, preserve the reservation and prevent automatic recreation. Once a session ID is known, persist it immediately and observe that session after restart. A completed remote result still needs independent review; it cannot create a publication outbox entry by itself.

Restoring an older snapshot cannot prove that later effects did not happen. Fence the prior writer, reconcile remote sessions and post-snapshot reservations, and restore paused. A final upload step is recovery material, not write-ahead authority. Managed event streams do not replay all missed events; recover using persisted session identities and session/item APIs. Cancellation requires terminal observation rather than assuming a cancel request stopped all work. [Agents sessions](https://developers.openai.com/api/docs/guides/agents-api/sessions).

Required remote-backend tests before connecting paid effects: simultaneous admission by two runners, CAS conflict, accepted write with lost response, stale read, runner loss before/after POST, unknown create, cancellation disconnect, corrupt/partial state, stale restore, prior writer alive, month rollover, controller upgrade and publication accepted with lost response. The new local runner-recovery tests cover several corresponding invariants, not a live remote CAS implementation.

## Scheduling, context and evaluation

- Start with manually dispatched private fixture runs. Then one bounded daily retrieval slot, deliberately away from the top of the hour, with stable UTC slot identity and bounded missed-slot handling. Scheduled GitHub jobs can be delayed or dropped; public scheduled workflows can be disabled after inactivity. A schedule is a wakeup hint, not a durable queue or service-level guarantee. [GitHub workflow events](https://docs.github.com/actions/using-workflows/events-that-trigger-workflows).
- Do not use `cancel-in-progress` as a safety mechanism for production effects. It is appropriate for the new secret-free CI rehearsal, but a killed production coordinator leaves remote work to reconcile. Provider-session supervision must survive the coordinator.
- Daily discovery currently supports arXiv, selected company feeds, Hacker News, X and OpenAlex. Retain provenance, deduplicate canonical works, distinguish research evidence from social popularity, and require primary-source support before skill changes. Parallel and Firecrawl connectivity observations do not mean every daily lane already invokes them.
- Context handoff must replay stored discovery and primary captures, bound excerpts and citation spans, and retain unsupported/contradictory evidence. Model output must not manufacture a source or promote an unverified title/abstract into a demonstrated result.
- Use deterministic structural and grounding gates first. Research quality requires a separately frozen representative dataset, candidate/control pairing, task-level uncertainty estimates, ablations and negative results. The earlier same-skill A/A pilot and the current fixture scenarios do not demonstrate improved research or skill effectiveness.
- Preserve rejected proposals and failure-derived evals without treating repetition or model confidence as novelty. No dataset means an explicit waiting state, not invented gold or automatic acceptance.

## Credentials, permissions and operator interaction

Do not upload `.env.local` or place it in a build context, Actions artifact, commit or generated PR. Transfer individual secrets only into the approved private controller environment. Its approved source SHA and configuration must be controlled independently of proposed skill changes.

| Secret/identity | Placement | Scope |
| --- | --- | --- |
| OpenAI project credential | Private research executor only | Dedicated project; reviewed model/tool configuration; no public CI exposure |
| X, OpenAlex, Parallel, Firecrawl credentials | Only enabled reviewed retrieval adapters | Provider endpoint allowlist, request/response bounds, least available permission |
| Private state writer | Coordinator only | Selected private state authority; not passed to model-controlled tools |
| GitHub publisher App installation token | Separate trusted publisher job | Selected public repository, required contents/PR operations only; no administration/workflows/deletion |
| Operator authentication | Separate operator surface | Never browser-public variables, generated code or public artifacts |

No universal MCP credential is needed. Each registered MCP connection must have an explicit server identity, tool/schema allowlist, output bounds and credential owner. Provider key presence never enables a schedule by itself.

GitHub is the initial operator surface: run summaries, reviewed reports, draft PRs and actionable notifications. The current Control Center is a real authenticated **loopback-only, read-only** local service UI. GitHub Actions cannot keep that web server running indefinitely. Public/private hosted UI deployment needs a separate authenticated hosting decision; a static Pages site must contain only approved public projections, never private live state.

Public Actions artifacts are downloadable by repository readers and expire according to retention policy. They contain only approved aggregate evidence here. Private captures, prompts, session records and allowance authority belong elsewhere. Review managed Agents data controls before transferring private material; current session retention/data-residency limitations are separate from where the GitHub controller runs. [GitHub artifact access](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts), [artifact retention](https://docs.github.com/en/organizations/managing-organization-settings/configuring-the-retention-period-for-github-actions-artifacts-and-logs-in-your-organization), [Agents data controls](https://developers.openai.com/api/docs/guides/agents-api/overview).

## Spending invariant

The existing OpenAI allowance is **$100 cumulative**, not $100 per runner, workflow, model, directory or month. This review spent **$0 on OpenAI**. Preserve prior completed and uncertain reservations when migrating authority. Do not initialize a fresh $100 cloud ledger alongside the local one.

Current OpenAI documentation supports project/organization **hard monthly spend limits**, but explicitly allows some overrun during enforcement propagation. Monthly limits also reset. They are useful defense in depth, not proof of a strict cumulative $100 maximum. Managed session usage is best-effort and may arrive late; the reviewed create contract does not establish a per-session hard dollar bound. A timeout, zero subagents, polling limit or cancellation request cannot provide that missing bound. [Spend limits](https://developers.openai.com/api/docs/guides/spend-limits), [Agents usage](https://developers.openai.com/api/docs/guides/agents-api/observability).

Keep managed paid scheduling disabled until a verifiable spending contract exists or the owner explicitly authorizes the documented residual risk and allowance policy. The existing bounded Responses path can still provide supervised research/evaluation within its admitted call contract, but it is not a silent substitute for the requested managed Codex runtime.

## Executable release scenarios

The new [release scenario runner](../../researcher/service/release_scenarios.py) executes ten named groups, 318 constituent test cases. It creates fresh credential-free subprocesses, permits only numeric loopback in its network tripwire, applies per-group deadlines, rejects empty constituent modules/skips/contradictory results, and emits only closed-schema aggregate counts/test IDs. It binds executable tests/workflows and the bounded public release-source snapshot. It is reviewed-test isolation, not an OS sandbox for arbitrary candidate code.

| Group | Important scenarios |
| --- | --- |
| managed-lifecycle | HTTP 201, malformed framing, persisted create intent, known-session recovery, cancellation, malformed provider results |
| runner-recovery | Lost runner, known ID without recreation, unknown POST, pre-POST crash, stale snapshot, missing result/capture closure, preserved uncertain budget |
| budget-and-uncertainty | Reservation before call, shared allowance, replay, denied/unknown effects |
| capture-grounding | Tampered capture, unsupported citation/span, primary-reader limits, exact handoff |
| pipeline-checkpoints | Abstention, interrupted research/candidate/evaluation, zero-call replay, no automatic publication |
| daily-restarts | Compressed daily slots, restarts, duplicate work, pause, independently supplied datasets |
| artifact-recovery | Complete closure, tampering, paused restore, retained unknown authority |
| frozen-candidates | Exact source/skill freeze, isolated overlay, structural verification, incomplete candidate refusal |
| publication-boundary | Scoped repository/path inputs, deterministic identity and failure handling with injected GitHub |
| operator-isolation | Actual loopback HTTP behavior, authentication and environment isolation |

Run after installing the combined hash-locked dependencies:

```sh
python -m unittest researcher.service.tests.test_release_scenarios
python -m unittest discover -s researcher/service/deploy -p 'test_*.py'
python -m researcher.service.release_scenarios --output release-rehearsal.json
```

The new [GitHub workflow](../../.github/workflows/release-rehearsal.yml) runs these checks on PRs, main pushes, merge-group requests and manual dispatch, without provider secrets. It separately builds the MCP-enabled dependency image and performs nonroot, read-only, network-disabled imports and dependency checks. Its only uploaded file is the aggregate report, retained for 14 days. This workflow is not the scheduled production coordinator and has not been executed on GitHub in this review.

### Evidence and limits from this iteration

- Exact stack: all parent lifecycle/inventory checks passed; 362 foundation tests, 39 exact-PR transport tests and 82 runner tests passed. Two instrumented dry plans made zero SDK calls. Whole-stack aggregate lifecycle rejection is preserved as a negative test.
- Final local integration: **741 service tests passed in 90.531 seconds** on Python 3.11.0, credential-free with injected providers. An earlier sandbox-restricted attempt had 16 loopback-bind setup errors; loopback-permitted runs passed. The ten runner-contract tests and 29 deployment tests also passed separately, including ten actual-shell merge-group scenarios.
- The full script suite passed 1,157 tests in 206.176 seconds. Strict repository validation reported zero errors/warnings; reference platform validation passed 17 skills across four layouts; generated inventory passed 344 records and 319 declared inputs. These are implementation/packaging checks, not independent research-quality trials.
- Initial ten-group rehearsal executed 318 tests and correctly reported one pipeline structural-check failure while generated inventory was being refreshed. The 25-test pipeline group subsequently passed without a code change. A later attempt refused to emit an aggregate when its release-source snapshot changed. The final stable run passed **all ten groups and 318 tests, with no skips or errors**; its [closed aggregate receipt](evidence/github-release-rehearsal-2026-09-29.json) binds 850 source inputs. These earlier failures are retained as engineering observations, not discarded scientific trials. The receipt identifies the tested working-tree snapshot, not a clean release commit; adding this evidence/documentation afterward does not retroactively change its input identity.
- The MCP-enabled image built locally on Linux ARM64, image `sha256:38f3946ce5f963777b8f7f65ed65f1e1b78e226a198298dfca731e6e9d1c639b`. Nonroot UID/GID 10001, MCP 1.30.0/httpx 0.28.1 imports and `pip check` passed with networking disabled. This is not hosted AMD64 execution or a complete application launch. The OS package layer still resolves distribution packages at build time; record/audit the resulting image, not merely the Python base digest.
- A second build explicitly targeted **Linux AMD64**, image `sha256:47e1b9df2e2c41441fb7721d6eb5ce459f92e4b1dacde0e0184f536597b935ca`. Under local Docker emulation, Python 3.12.14 reported `x86_64`; the same nonroot/offline import and dependency checks passed. No application source, credentials or host sockets were mounted. This verifies the target-architecture dependency image, not execution on GitHub's hosted runner.
- The present nonignored source candidate passed the public-boundary scanner with 850 files and zero findings before adding the final evidence file. This is not an index/tree attestation: the approved release must still stage the intended deletion of the formerly tracked runtime history and exclude private/ignored material. A final read-only GitHub head check found the same 36 PRs with no head changes.
- Prior live source/model evidence remains in the [production exercise](production-exercise-2026-09-29.md). Those calls were not repeated here. Test counts across overlapping suites must not be added and described as independent scientific trials.

## Production follow-on review units

The integrated checkout contains extensive unpublished implementation beyond #134. The full dependency closure must include tracked changes outside `researcher/service/`, generated inventory, schema fixtures, public-export policy, documentation and removal of the formerly tracked runtime history. Do not publish a dirty directory wholesale or select only the obvious new folders.

1. **Safety foundation:** additive #134 protocol repairs, patched/audited dependency locks, public-runtime exclusions, merge-group handling and secret-free release scenarios.
2. **Storage/provenance:** portable artifact/schema/event-journal semantics, exact fixtures, Python/TypeScript conformance and migration/restore tests.
3. **Retrieval/context:** bounded connectors, capture replay, primary content profiles, citation spans, configuration and relevance evaluation fixtures.
4. **Research/evaluation:** existing cumulative allowance, grounded roles, frozen candidates, independent datasets, deterministic/paired evaluation and restart-safe organization outcomes.
5. **GitHub control plane:** approved source pin, remote conditional admission and reconciliation, private-state permissions, manual/slot triggers and operator pause.
6. **Delivery/operations:** separately credentialed draft-PR publisher, sanitized export, ambiguity reconciliation, actionable notification and hosted restore/rollback evidence.

These are proposed review units, not created PR numbers or independently tested cherry-pick sets. Each needs a clean import/config/test/documentation closure and current-base checks. Existing draft specifications remain draft; this document does not accept them or grant implementation authority through prose.

## Launch and rollback procedure

1. Approve exact release files, protection settings and private-state topology. Apply and read-back verify the separately authorized protections before merges. Freeze public source and dependency identities.
2. Merge the reviewed existing stack in order, rerunning exact-base/protected-default lifecycle checks after each transition. Prefer ancestry-preserving merges; squash/rebase requires explicit descendant restacking and fresh receipts.
3. Review and integrate the production slices. Recreate a clean release tree and run public-file/secret checks against the **actual index/tree**, not an untracked working directory. Confirm private state and credentials are absent.
4. Run the secret-free workflow on GitHub's real Python 3.12/Ubuntu target. Require its recorded source SHA, dependency/image identities and aggregate report. A local run cannot satisfy this hosted gate.
5. Exercise the private controller manually with fixtures, then retrieval-only. Demonstrate remote write-ahead admission and all crash/ambiguity scenarios before any paid managed call.
6. Resolve the managed-budget contract and migrate the existing allowance without resetting unknown reservations. Conduct narrowly authorized model and draft-PR canaries against the same approved release.
7. Enable one daily schedule only after reviewing run outcomes, source quality, notifications, pause and restore. Keep human merge. New harness versions remain proposals until separately approved.
8. On rollback, pause new admissions, fence the writer, reconcile in-flight sessions/publication, preserve all reservations and receipts, then pin the prior approved source. Never restore an older budget balance or drop unknown outcomes to make a release appear healthy.

The desired outcome is a self-improving research organization with externally enforced constraints. Automatic proposal generation is compatible with that objective; automatic alteration of its own budget, evaluator, credential scope or release policy is not part of this launch.

## Sources

Primary OpenAI runtime, session, usage and spend-limit documentation and GitHub workflow-security, scheduling, retention and conditional-reference documentation are linked inline. Official-document research informed the separation between managed sessions and bounded native calls; Parallel search informed the GitHub scheduling/artifact/security review. Repository measurements and exact-head audits take precedence over general recommendations for claims about this implementation.
