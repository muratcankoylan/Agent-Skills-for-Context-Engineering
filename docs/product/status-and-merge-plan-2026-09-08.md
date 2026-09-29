# Status and complete PR merge plan

Dated 8 September 2026. GitHub audit completed at **04:37:49 UTC**. Assessment only: no merge, approval, retargeting, closure, push, commit, provider activation, or deployment was performed.

## Executive decision

The project is a credible **supervised local research-to-proposal prototype**, not yet a production self-evolving research organization. The current code can retrieve bounded research leads, preserve evidence, build context, compare frozen data policies, and produce inert proposals. It cannot yet generate and independently validate scientific improvements, update accepted skills, or operate an authenticated production control plane end to end.

The existing foundation merge train is **#121 -> #122 -> #123 -> #124 -> #125 -> #126 -> #127 -> #128 -> #129 -> #130 -> #131**, conditional on the pre-merge gates below. Do not merge all open PRs. **Zero PRs have unconditional merge readiness established by this audit.** #121 is the first review candidate, not an automatic merge recommendation.

The newer sourcing, read-only evidence replay, experiment lifecycle, UI observation adapter and safety fixes exist in the dirty local integration only. They are not contained in the unchanged remote PR heads. Merging through #131 will not ship those later changes; they need separate reviewed changes after reconciliation.

## 1. Evidence and current-state identity

- Protected default branch observed: `main` at `6dbe1a1d868eab51a3bc9011b0f55e2891513e40`.
- Local integration ancestor/HEAD: `c6cd52017b247804373339e1c3c103d42554b0a1`, the #131 head.
- Later local implementation: uncommitted; no exact release commit or production attestation exists.
- All 35 current open PR heads match the August 25 and September 7 observations.
- The [public metadata snapshot](evidence/github-pr-status-2026-09-08.json) records every current title, head/base SHA, check, dependency and disposition. It is an observation, not authority.
- Detailed semantic backlog findings are carried forward from the [August 25 audit](pr-audit-2026-08-25.md) because the heads are unchanged. This turn refreshed metadata, checks, reviews, rules and dependencies; it did not independently re-review every line of all 35 diffs.

The public snapshot is a selected projection of the private query receipt, not a byte-identical copy. Private response bodies, local runtime locators, credentials and sealed data are excluded. GitHub state can change after the timestamp; re-query exact heads before action.

## 2. What works and what is missing

| Area | Implemented or measured | Remaining boundary |
| --- | --- | --- |
| Corpus | 17 skills, generated inventory, claims/mechanisms and structural validators | Release changes must keep prose, registry, claims, fixtures and inventory consistent |
| arXiv | Explicit mechanism/facet lanes, relevance/recency, versions and shared daily reservations | Independent relevance/claim-support assessment, broader primary coverage |
| Company research | Bounded DeepMind, Hugging Face and Microsoft Research publisher windows | Not exhaustive company-topic search or independent corroboration |
| X/Twitter | Enriched parsing and staged queries | Authenticated contract, entitlement, resource billing and canary unverified |
| Primary evidence | Selected allowed HTML pages, immutable raw capture, inert text and offline re-extraction | No PDF fallback, automatic crawling or scientific adjudication |
| Context | Explicit skill packing and separate discovery packets with exact byte/provenance/omission accounting | No measured semantic ranking or downstream context effectiveness |
| Experiments | Two frozen JSON packet policies, recomputed outcomes, verified resume, inert proposal/rejection | No model-generated hypotheses, executable search or accepted promotion |
| Agents/prompts | Typed builder/verifier prompt compilation | Compilation is not model execution; operational agent manifests and independence remain absent |
| State/scheduling | Local scheduler and separate journal prototypes; bounded Codex heartbeat | No unified accepted work/result owner, portable daemon, transactional effect lifecycle or demonstrated uptime |
| UI | Real read-only local observation view; separate fixture controls | No hosted authentication, authoritative commands, experiment review/pause/recovery API |
| Deployment | Local supervised execution and runbooks | Clean installation, hostile-worker isolation, restore, live provider and production canary gates |
| Open source/paper | Repo-native code, synthetic fixtures, architecture and evaluation protocol | Publishable exact release, licensed real-data export, frozen preregistration and independent semantic results |

Working-tree SPEC-000–003 revision-1 headers say `amended`; the README's adoption table is historical. Operational owners such as SPEC-004/005/016/017/019/025 remain draft. A working-tree status is not proof of protected-main acceptance.

## 3. Actual execution evidence

### Discovery, not scientific findings

| Population | Completed run records | Request attempts | Complete captures | Captured bytes | Raw leads |
| --- | ---: | ---: | ---: | ---: | ---: |
| Initial local pilot | 7 | 25 | 25 | 93,177 | 24 |
| Three source campaigns | 13 | 13 | 12 | 1,254,683 | 118 |
| Combined retained discovery | **20** | **38** | **37** | **1,347,860** | **142** |

These are raw occurrences, including repeated source windows across days, not 142 distinct research insights. Capture counts exclude incomplete responses and do not measure all transferred bytes.

The September 8 daily campaign used six attempts and produced six complete captures, 59 work records, and a 130,695-byte packet selecting 41 records with 18 explicit omissions. The previously timed-out memory-interference lane returned three unreviewed leads. Different inputs and selection counts do not establish a policy improvement.

Primary reading is separate: three selected URL attempts produced two durable captures totaling 399,641 bytes. One response exceeded the cap; one original parse failed. The failures remain. Offline re-extraction yielded 67,251 bytes of arXiv article text and 7,540 bytes of Microsoft main text without new requests. Those sidecar articles are not inputs to the current discovery-packet experiment.

### Frozen packet experiment

On the retained 56-work case, compact provenance changed selected-work coverage from **2 to 15 at 64 KiB**, and **29 to 42 at 128 KiB**. At 256 KiB, both retained all 56 works; bytes changed from 214,203 to 189,526. Selected text and expanded provenance were preserved.

The forward direction produced an inert proposal; reversing the two known policies produced rejection. There were two development cases, three budgets, and two policies, not a representative sample of independent research needs. No new retrieval/model/paid calls occurred inside this experiment. See [full results and denominators](portable-harness-results.md).

### Verification scope

| Evidence | Recorded outcome | Limitation |
| --- | --- | --- |
| Latest full Python suite | 1,078 passed; 225.740 s; Python 3.12.9 | Prior frozen-source run, not rerun during this documentation turn |
| Publication/inventory/product-readiness suite | 143 passed separately | Overlaps other suites; do not add counts |
| Lifecycle portability checks | 37 passed on Python 3.11.0 and 37 on 3.12.9 | Same machine; not cross-version manifest replay or clean Linux validation |
| Dated SDK/schema/UI checks | 82 SDK, 22 TypeScript schema, 38 UI tests passed | September 7 local receipts, not today's remote PR CI |
| UI verification | Build/standalone smoke; browser journey over seven actual rows | Current 20-row file verified, but no new 20-row browser journey this turn |
| Activation and Stage 0 | 23 deterministic activation cases; Stage 0 checks passed | No live model routing; Stage 0 executed zero benchmark scenarios |
| Prior prospective secret scan | Zero findings over 708 present publication-candidate files | Not Git index/history; new documentation needs its own checks |

The latest source/runtime identity and all 11 portable-verification evidence links were rechecked. Source code was not changed during this documentation task. New documentation validation is reported separately at handoff; it does not inherit a new full-suite attestation.

### Long-running observation status

Four completed scheduled receipts exist: one fresh daily campaign and three offline cycles. The latest completed at **03:49:35 UTC**; the last fresh source observation completed at **01:54:17 UTC**. The 20-row view's generation time reflects offline verification, not new retrieval.

The observed source span is 16,102 seconds between first/last source timestamps, not continuous uptime. Missed cycles are not inferred. The configured heartbeat is active, hourly, with 72 scheduled occurrences; it is a Codex development mechanism, not OS cron or an always-running product agent. The source cache retains today's reservations. No additional fresh campaign is eligible before 9 September UTC.

Product model and paid-call counters remain zero. These counters exclude Codex engineering assistance and the separate literature lookup used to write the architecture paper.

## 4. Merge preconditions

Current GitHub observations: 35 open PRs, 11 drafts, nine conflicts, 23 with no returned check records, and zero approved review records. #132 has failed validation. #133 has an `action_required` workflow despite an empty check rollup. #100 has two unresolved review threads.

The effective main ruleset requires PRs and resolved threads, but **does not require any passing status check or approval**. Administrator bypass remains enabled. Merge, squash and rebase methods are all allowed; auto-merge is disabled. A classic-protection 404 does not mean there is no protection: the repository ruleset is active.

Before the train, the maintainer should:

1. Enforce the correct required GitHub Actions validation check with up-to-date branch requirements and no automation bypass.
2. Preserve ancestry through merge commits for this stack. Do not squash or rewrite the train without rebuilding descendant bases/diffs and rerunning their evidence.
3. Record exact-head human review. Do not interpret zero approved review records as permission. If there is only one reviewer identity, document the temporary review procedure instead of silently creating an impossible self-approval rule.
4. Re-run checks against the exact current head and intended target base. Existing train check records are dated August 15–16.
5. Keep parent proposal branches available until descendants are deliberately retargeted and checked.
6. After each merge, retarget only the next child to `main`, inspect the new diff, mark ready when reviewed, and obtain fresh validation. Do not bulk-merge from an old green rollup.
7. Keep merge, publication and production activation as separate decisions.

No rule or GitHub setting was changed in this task.

## 5. The foundation PRs to merge conditionally, in order

All eleven are ancestry-linked; each child's advertised base SHA equals its preceding parent's current head. These are the intended foundation train, not all of the local product.

| PR and exact current title | Head prefix | Depends on | Current state | Purpose |
| --- | --- | --- | --- | --- |
| [#121: feat(governance): publish and enforce the specification program](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/121) | `aed122474c31` | Current main | Open, non-draft; recorded checks have no failure | Specification program and lifecycle enforcement |
| [#122: feat(orchestration): add supervised long-horizon bootstrap briefs](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/122) | `0030fdbf8da0` | #121 | Draft; recorded checks have no failure | Supervised long-horizon bootstrap briefs, not an autonomous runtime |
| [#123: docs(spec-003): authorize classification invariant amendment](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/123) | `48e17e8b7de6` | #122 | Draft; recorded checks have no failure | SPEC-003 classification-invariant amendment decision |
| [#124: docs(spec-000): authorize authority vocabulary amendment](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/124) | `c91780589ed7` | #123 | Draft; recorded checks have no failure | SPEC-000 authority-vocabulary amendment decision |
| [#125: fix(benchmarks): contain Cursor SDK and harden evidence](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/125) | `c50cc4cdbc0c` | #124 | Draft; recorded checks have no failure | Cursor SDK containment and evidence hardening, not live activation |
| [#126: test(benchmarks): add private manifest resume substrate](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/126) | `7c0c92d20244` | #125 | Draft; recorded checks have no failure | Private manifest/resume substrate |
| [#127: docs(spec-001): authorize snapshot identity amendment](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/127) | `ec6f25c60902` | #126 | Draft; recorded checks have no failure | SPEC-001 snapshot-identity amendment decision |
| [#128: docs(spec-002): authorize projection-boundary amendment](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/128) | `d1fc8c2e3d7c` | #127 | Draft; recorded checks have no failure | SPEC-002 projection-boundary amendment decision |
| [#129: fix(governance): require promoted revision predecessors](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/129) | `f5f1dda3e0f4` | #128 | Draft; recorded checks have no failure | Promoted-predecessor requirement |
| [#130: Extract authority contract and bind evaluator provenance](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/130) | `54580840f755` | #129 | Draft; recorded checks have no failure | Authority contract extraction and evaluator provenance |
| [#131: Harden offline authority vocabulary semantics](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/131) | `c6cd52017b24` | #130 | Draft; recorded checks have no failure | Authority-vocabulary semantic hardening |

#121 publishes the program and lifecycle machinery; it does not accept every draft operational specification. #122 supplies supervised briefs, not a running organization. The amendment-decision PRs authorize specific contract lifecycle changes, not all future implementations.

## 6. Rebuild or reconcile these fixes instead of merging stale heads

These six PRs are **not** recommended as additional direct merges. Their useful concerns overlap newer local corrections. Prepare narrow replacement changes after the foundation train, retaining attribution and regression tests.

| PR and exact current title | Current state | Reason / disposition |
| --- | --- | --- |
| [#109: Fix path traversal and arbitrary file deletion in pipeline_template.py](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/109) | Open | Historical patch misses item-identifier traversal and CI test discovery. Verify consolidated local containment replacement. |
| [#110: Fix shell injection and unsafe secret handling in hosted agents image build example](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/110) | Open | Historical patch does not cover executable and all credential/shell surfaces. Verify consolidated local argv/credential hardening as a separate exact-head change. |
| [#81: fix: remove GitHub token from git clone URL in sandbox_manager.py](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/81) | Open | Historical patch still exposes credentials through shell/process/helper surfaces. Cover in consolidated hosted-agent hardening. |
| [#112: Add cost, request, token, and rate-limit safeguards to API loops and judge examples](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/112) | Open | Historical patch lacks mandatory worst-case reservations and retry accounting. Verify prepared bounded replacement and remaining TypeScript-judge gap. |
| [#113: Fix Windows import crash in loop_common by making fcntl optional](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/113) | Open | Historical patch uses a process-local lock. Rebuild or verify the prepared Unix-only fail-closed alternative with multiprocess tests; no Windows portability claim. |
| [#92: Maintenance: Update dependencies and refine interleaved thinking example](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/92) | Open | Historical dependency changes superseded and evaluator only warned around eval. Verify prepared narrow bounded-AST replacement; do not merge historical patch wholesale. |

Do not merge #81 and #110 independently on top of a replacement credential boundary. Likewise, the current local calculator and path fixes are not equivalent to the historical proposal heads. The Unix-only lock policy does not establish Windows support, and process-local example reservations are not a durable paid-provider accounting system.

## 7. Optional candidates to hold

These are not required to launch the core research-to-proposal MVP.

| PR and exact current title | Current state | Reason / disposition |
| --- | --- | --- |
| [#133: Add rendered UI finish gate skill](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/133) | Open | Historical audit requires exact-diff review, approved Actions execution, generated inventory and activation/effectiveness evidence. Current workflow run is action_required; no successful current validation. |
| [#132: Add deliberative-writing-loop example: inference-time persona writing harness](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/132) | Draft | Draft with failed generated-inventory test. Historical audit also flags provider/budget/resume and CI-discovery gaps. Do not treat inventory regeneration alone as readiness. |
| [#36: docs: add AdaL to compatible platforms list](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/36) | Open | Historical platform compatibility claim has no fixture or platform evidence. |

#133 requires exact-diff review before approving contributor Actions execution; workflow approval itself is not merge approval. #132's inventory failure is not its only historical design concern. #36 needs platform conformance evidence before the compatibility claim is accepted.

## 8. Remaining backlog: review for closure or bounded salvage

Recommendation only. No PR was closed. Historical semantic reasons below are not newly reproduced vulnerabilities.

| PR and exact current title | Current state | Reason / disposition |
| --- | --- | --- |
| [#111: Fix stale researcher-OS baseline numbers in README, AGENTS, and plugin metadata](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/111) | Conflict | Historical audit rejects copied volatile counts in favor of generated inventory; current PR also conflicts. |
| [#100: Publish xhigh evidence and harden validation paths](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/100) | Conflict | Conflicting historical 83-file alternate paid-runner rewrite; two unresolved review threads remain. Do not merge wholesale; salvage only independently evaluated fixtures if approved. |
| [#95: Add Linked API linkedin skill](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/95) | Open | Historical audit identifies token-handling, unpinned tooling and external-action authority gaps; not required for the research harness. |
| [#89: Add internal repo-contributor skill as project knowledge base](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/89) | Open | Historical audit identifies duplicated stale repository instructions. |
| [#88: Add context receipts skill](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/88) | Conflict | Conflicting ad hoc receipt authority model; reconcile needs with accepted event/artifact contracts. |
| [#83: fix: validate custom install path in install.sh to prevent path traversal](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/83) | Open | Historical path restriction is not the actual containment boundary and relies on nonportable realpath behavior. |
| [#82: fix: tighten production dependency ranges from ^ to ~ in package.json](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/82) | Open | Changing ranges alone does not establish reproducible dependency resolution. |
| [#80: fix: add YAML frontmatter to llm-as-judge agent files](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/80) | Open | Historical frontmatter patch risks registering documentation/index files as agents. |
| [#72: Add session-handoff skill for cross-session task continuity](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/72) | Conflict | Conflicting mutable handoff system duplicates accepted event/snapshot state and has historical missing-command/race concerns. |
| [#55: Improve multi-agent-patterns skill and add skill review workflow](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/55) | Conflict | Historical workflow runs unpinned code with write authority; current PR also conflicts. Do not enable pending security review. |
| [#52: feat: adding a context benchmarking-skill](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/52) | Conflict | Historical benchmark lacks secret isolation, hard budgets/timeouts and valid stated-effect measurement; current PR conflicts. |
| [#40: Apply context engineering refactor to sales, copywriter, sentinel, solo-maker, and solo plugins](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/40) | Conflict | Conflicting large business-automation scope with credential/effect and integration risks; not a research-harness prerequisite. |
| [#38: Add 78 Composio SaaS app automation skills via Rube MCP](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/38) | Open | Historical README promotion points to unvendored/unvalidated external automation skills. |
| [#24: feat: Add Solution Architecture skill with comprehensive reference ma…](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/24) | Conflict | Conflicting vendor-specific architecture skill with historical integration/overlap issues. |
| [#17: fix: expand marketplace to list individual skills for proper discovery](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/17) | Conflict | Historical marketplace patch superseded by explicit bundled skill registration; current PR conflicts. |

All 35 currently open PRs appear exactly once across Sections 5–8. Historical #94, “Preserve source provenance and add Xquik adapter,” is absent from current lists; both direct API lookups return 404. Its current disposition is unknown/inaccessible, not presumed merged or closed.

## 9. Local improvements still needing new reviewable changes

No new PR numbers exist for these later uncommitted slices. This is a proposed packaging plan, not a claim that PRs were created or authorization to create them.

| Slice | Deliverable | Dependency / gate |
| --- | --- | --- |
| Example and legacy safety corrections | Separate narrow changes for path containment, hosted credentials, bounded calculator, fail-closed locking and example budgets | Final train base; each issue gets focused adversarial tests; keep legacy activation disabled |
| Dependency and zero-call benchmark maintenance | Current locks, containment and CI-discovered tests | Do not reopen live SDK execution in a maintenance change |
| Local observation and source harness | Campaign lanes, feeds, primary HTML, shared reservations, strict capture replay and packing | Publish as supervised prototype; no accepted scientific or production authority |
| Read-only observation UI | Loopback adapter, real run visibility and host/path guards | Remain read-only; authentication/commands are a separate accepted slice |
| Data-policy experiment | Pure evaluator, frozen policies, complete comparison, inert proposal and failure tests | Data-only development surface; no candidate-code execution |
| Event/journal and owner integration | Accepted contracts, reducer/result application and migration/shadow parity | Resolve specification dependency/lifecycle gates before claiming implementation authority |
| Paper and operating docs | Architecture, evidence limitations, protocol, deployment/recovery design | Release-safe export and exact-candidate validation; no private captures |
| Future provider/evaluation/promotion | One budgeted adapter, isolated execution, independent study and reversible reviewed release | Not currently implemented or activated; requires separate accepted contracts and authorization |

Do not put every slice into one giant “production ready” PR. A useful release separates reproducible local tooling from future autonomous authority.

## 10. Production and paper exit gates

The next milestones are: accepted work/evidence/evaluation/promotion ownership; a constrained provider/executor boundary; clean install and verified restore; independently judged source-to-claim/report changes; representative sealed downstream evaluations; authenticated operator commands; and a real, bounded production canary.

The [architecture paper](research-harness-architecture-paper.md) is suitable as a technical draft describing current mechanisms and limitations. It is not submission-ready evidence of self-evolution. The [preregistration proposal](portable-harness-paper-protocol.md) still needs frozen sample size, practical effect thresholds, budgets and final-set commitments. The [operations design](research-harness-operations.md) answers where agents should run, how scheduling/results/interaction should work, and which boundaries must exist first.

## 11. Verification of this documentation handoff

- 24 product-readiness/public-repository tests passed in 0.022 seconds.
- Strict repository validation passed with zero errors/warnings; generated inventory still matches 339 artifact records and 311 declared input snapshots.
- Reference platform compatibility passed for 17 skills and four local layouts. The first invocation could not find the already-installed reference CLI; supplying the existing virtual environment's executable path resolved it without installing or changing dependencies.
- The production-readiness declaration is valid and remains blocked. No production flag was enabled.
- Structural checks verified 36 local Markdown links, balanced code fences, JSON parsing, and exact 35-PR coverage/title/URL correspondence. A separate reviewer checked train heads, dependencies and readiness caveats against the live query receipt.
- Gitleaks reported zero findings within `docs/product/`. This is a scoped documentation scan, not a new repository-history or full publication-candidate attestation.
- Source/runtime identity still matches the prior full-suite receipt. No model, retrieval campaign, live benchmark or full Python suite was rerun for this documentation task.

Markdown was structurally checked; no rendered PDF or exhaustive visual-layout review is claimed. The documentation and private verification receipts remain local and uncommitted.
