# Security and maintenance PR audit: 29 September 2026

## Decision

Do not merge any of these eleven heads unchanged. Several address genuine defects,
but their fixes are incomplete, conflict with the integrated implementation, or
need a narrower replacement. This is a review recommendation, not approval to
close, retarget, publish or merge a PR. No GitHub mutation occurred.

GitHub metadata/diffs were read on 29 September, with a final head recheck around
06:45 UTC. All eleven were open, non-draft, had empty `statusCheckRollup` arrays
and empty `reviewDecision` fields. Empty checks mean **no check evidence observed**,
not passing CI. GitHub reported `CLEAN/MERGEABLE` for nine and
`DIRTY/CONFLICTING` for #100 and #111. These are reported mergeability fields,
not a tested merge result. Default branch `main` resolved to
`6dbe1a1d868eab51a3bc9011b0f55e2891513e40` in the final query.

The integrated checkout had HEAD
`c6cd52017b247804373339e1c3c103d42554b0a1` and extensive tracked/untracked changes.
Its stronger implementations are **local comparison evidence**, not proof they
are published on main or these PRs. Preparing a replacement requires an explicit
scoped commit/branch review; do not publish the entire dirty checkout.

## Exact reviewed heads and disposition

All target `main`. Each head below was unchanged in the final live recheck.

| PR and exact title | Head SHA | Disposition |
| --- | --- | --- |
| [#113 Fix Windows import crash in loop_common by making fcntl optional](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/113) | `b789fd4d7e91cd6d55950980237421b065e17589` | Supersede with fail-closed process-lock implementation. |
| [#112 Add cost, request, token, and rate-limit safeguards to API loops and judge examples](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/112) | `0b518ceb6810915faf90a3b32ab2ebde716ca5e5` | Split/rework; proposed caps are not enforced at each effect. |
| [#111 Fix stale researcher-OS baseline numbers in README, AGENTS, and plugin metadata](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/111) | `fb2262433d71da72ea115fc34c9750abbb688c89` | Supersede with generated inventory links; conflicting. |
| [#110 Fix shell injection and unsafe secret handling in hosted agents image build example](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/110) | `dd862b430bf1dda6d8ad84c19f239d2423fac0d6` | Supersede with scoped credential/build-boundary reference. |
| [#109 Fix path traversal and arbitrary file deletion in pipeline_template.py](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/109) | `8729b720f4a21fe48342eacc57291162d0dfeee2` | Supersede with all-segment containment and regression tests. |
| [#100 Publish xhigh evidence and harden validation paths](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/100) | `596c8f84eaa4ef89333fdfc4ee2ca042c0dcf540` | Split evidence, validation utilities and executor; conflicting. |
| [#92 Maintenance: Update dependencies and refine interleaved thinking example](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/92) | `1de8c919199c0f6baa8a5d02da43e1fb13d2e6ae` | Supersede obsolete runner lock changes and unsafe-eval comment. |
| [#83 fix: validate custom install path in install.sh to prevent path traversal](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/83) | `325c5c2e0e166a75c91c60b2d0535035f6fb57ad` | Rework portable installer and overwrite boundary. |
| [#82 fix: tighten production dependency ranges from ^ to ~ in package.json](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/82) | `d3185bf73dfca2366d388a1482bfa14f9595f334` | Hold for lockfile/compatibility evidence; not a security fix alone. |
| [#81 fix: remove GitHub token from git clone URL in sandbox_manager.py](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/81) | `87a516eea95b1cd4e92246162dcfc28c84125ae2` | Supersede; secret remains embedded in executable shell text. |
| [#80 fix: add YAML frontmatter to llm-as-judge agent files](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/80) | `e5fd0e3e4c3a689d3269ac951bc05c5075266717` | Small correction possible: quote index description and validate all four files. |

## Findings and scope read

### #113: import portability must not remove exclusion

Read the complete one-file diff and exact-head `loop_common.py` locking helpers.
`_lock_acquire` at lines 58–67 swallows `EACCES/EAGAIN`, then returns as if a lock
were acquired. The Windows fallback is only a `threading.Lock`; separately
scheduled processes do not share it. Atomic replacement does not serialize
read-modify-write transactions. A pure helper probe injected `EAGAIN` and
confirmed execution continued without a lock.

The integrated [lock implementation](../../researcher/scripts/loop_common.py)
allows import without `fcntl`, rejects unsupported mutations before creating
files, and propagates acquisition failure. Its process/alias/durability tests
were executed in the focused integrated batch below. Do not replace it with the
fallback or advertise Windows queue execution until actual interprocess locking
and filesystem semantics are implemented and tested.

### #112: post-call counters do not establish hard budgets

Read all eleven file diffs, including Python loop, TypeScript evaluator/tools,
configuration parsers and legacy HTTP retry path. Exact-head Python methods were
isolated for a credential-free probe: `run_single`, lines 511–539, executed two
fake calls with `max_requests=1`. Capture is charged after it returns; analysis
has no intervening gate. Capture may itself perform multiple provider requests,
retry attempts are not charged individually, and analysis/optimization token
usage does not enter `_record_usage`.

The TypeScript `checkBudget`/`recordUsage` separation likewise permits concurrent
oversubscription; pairwise position swapping performs two calls after one check.
Invalid or zero limits become `undefined` rather than denial. Timeout retries
can repeat an uncertain effect. The legacy HTTP ledger counts logical fetches,
not individual retry attempts, and even records dry-run requests. No new tests
are in this PR's file list.

The integrated Python example has a shared pre-effect
[attempt budget](../../examples/interleaved-thinking/reasoning_trace_optimizer/api_budget.py)
used by capture, analysis, optimization and skill generation. This is not an
account-wide dollar cap. The legacy loop is now inert and must stay so. The
TypeScript judge example remains a separate unmet work item: do not describe it
as fixed by the Python replacement or the service Campaign. Split the PR and add
per-attempt reservation, concurrency, malformed-config and unknown-outcome tests.

### #111: replace live count duplication, not just its current values

Read all three diffs. The PR embeds 22 mechanisms, 26 claims, 23 activation cases
and health 0.9221 in README, workspace memory and plugin description, without a
generated binding or dated health receipt. Current generated inventory reports
31 claims, and current docs distinguish dormant legacy code from the service.
Adding more duplicated live counts renews the same drift. Use
[the generated inventory](../../researcher/generated/corpus-summary.md), retain
historical scores with their dates, and reconcile the conflicting head without
restoring continuous-loop claims. No health rerun of this PR was performed.

### #110 and #81: removing the URL token is only one part of the boundary

Read the complete #110 reference diff and #81 manager diff. #81 interpolates
`password={token}` into `askpass_script`; despite its comment, it never installs
`GIT_ASKPASS`. The credential remains in command text passed to the build layer,
and `git credential approve` delegates persistence to ambient helper configuration.
Repository interpolation into shell strings also remains.

#110 uses a credential helper and mounts a named secret on the build sandbox, but
the same sandbox then runs repository-controlled install/build/test commands and
takes a snapshot without revocation, descendant cleanup or credential-absence
verification. The host clone path copies the ambient environment. This is not
an isolated clone-only credential boundary.

The integrated [manager](../../skills/hosted-agents/scripts/sandbox_manager.py)
and [reference](../../skills/hosted-agents/references/infrastructure-patterns.md)
instead require canonical repositories, argv commands, opaque operation-scoped
leases, lease closure before untrusted builds, fail-closed provider hooks and
quiescence before snapshots. The tests use fake adapters: they do **not** prove a
deployed credential broker or provider sandbox exists. These two PRs are related
surfaces of one replacement, not a dependency stack to merge unchanged.

### #109: the item path is still uncontrolled

Read both diffs and exact-head path helpers. `get_item_dir`, lines 179–184, still
joins an unvalidated `item_id`. Isolated probes confirmed an absolute item ID
replaces the batch root and `../../outside` escapes it. The batch regex uses
`match` with `$`, so a trailing newline also passes the supposed strict allowlist.
Added tests cover batch IDs, not these item paths or aliases.

Integrated [path helpers](../../skills/project-development/scripts/pipeline_template.py)
validate batch, item and leaf segments; reject existing symlink escapes and
unsafe configured ancestors; and preflight acquisition inputs. Relevant
regression tests passed below. Preserve the stricter implementation; do not
treat the PR's narrower fix as comprehensive deletion safety.

### #100: evidence publication is coupled to a different live executor

This is 83 changed files and 15 commits, not a small validation-path patch.
Read the file inventory, executable runner/control changes, comparator/promotion
logic, validation helpers/tests and report/methodology diffs. Long synthetic task
histories and every dependency-lock entry were not exhaustively audited. No live
benchmark, full PR test suite, raw historical result regrade or merge was run.

The new Codex/Headroom runner inherits `process.env`, sets a fixed operator home,
uses that runtime's configuration and forecasts zero marginal subscription cost.
Its invocation count does not prove a credential, tool, process-descendant or
cumulative spending boundary. `loadExistingResults` ignores malformed artifacts
and reruns them rather than reconciling uncertain calls, contrary to the current
strict manifest-bound execution contract. Restoring this executor would bypass
the legacy planners' zero-call boundary.

The comparison also fails vacuously: empty input produces zero planned/complete
pairs, and the file's `complete && !runtime_errors` expression marks the empty
comparison publication-eligible. A pure comparator probe reproduced that case.
Promotion logic consumes caller-supplied aggregates, deduplicates records into a
dictionary, and counts task IDs/replications without proving task independence.
It needs nonempty exact plan coverage, duplicate rejection, provenance validation,
recomputed metrics and task-grouped inference before scientific use.

Preserve the negative xhigh finding as a **reported historical observation** only
after its raw-data provenance and exposure history are reviewed. Extract benign
output-path/reference-validator improvements into a separate current-head patch
with tests. Do not import historical “accepted/canonical promotion evidence”
wording as present governance authority, and do not merge the active executor as
an incidental dependency of the report.

### #92: stale dependency update and no executable eval remediation

Read the three-file diff, manifest/lock dependency changes and calculator edit.
The code change adds a warning above `eval`; it does not remove it. The integrated
calculator now uses bounded parsed arithmetic and its regression suite passed.
The PR lock resolves Cursor SDK 1.0.18 with broad Undici/tar overrides, whereas
the integrated zero-call package pins SDK 1.0.28 and a scoped Undici 6.28.1 override.
Do not downgrade/re-expand that dependency surface by merging this old lock.
No fresh registry vulnerability audit or SDK execution was performed in this
review; the local pin is comparison evidence, not a claim of current CVE absence.

### #83: portable destination/overwrite policy is still missing

Read the complete installer diff and current surrounding overwrite/copy flow.
The new rule rejects any spaces or `..` substring, including legitimate custom
directory names, while “custom location” intentionally has no confinement root.
It adds GNU `realpath --canonicalize-missing` without a dependency check or
portable fallback. A sanitized system-PATH probe on this review host found no
`/usr/bin/realpath`; the script's `set -e` would stop that branch in such an
environment. The installer itself was not run and nothing was deleted.

Define supported destination and explicit overwrite semantics, reject dangerous
aliases/overlap, and test macOS/Linux paths, spaces, symlinks, existing targets and
cancellation with deletion mocked or confined to fixtures. The integrated
installer is unchanged, so this remains work to implement, not locally solved.

### #82 and #80: small independent examples still need real validation

Read both complete diffs and the current judge package/test layout. #82 changes
five runtime ranges from caret to tilde without a lockfile change or resolution,
typecheck or test evidence. A narrower range alone is neither reproducibility nor
a verified security upgrade; assess the resolved graph and compatibility, then
commit an appropriate lock/policy together. No dependency installation was run.

#80 adds frontmatter to four Markdown files. Its index description contains an
unquoted `: `, which is invalid YAML. Parsing the exact-head frontmatter with
PyYAML 6.0.3 produced `ScannerError`. Quote that value, parse all four documents,
and run the consuming loader's tests. This is a small repair candidate, but the
reviewed head is not valid as submitted. Neither example change is already
present in the integrated checkout.

## Executed evidence versus observed claims

- Exact-head offline probes used only reviewed AST-selected helpers/methods or
  data parsing, with `env -i`, fake provider callbacks and no network/credentials.
  They reproduced #80 invalid YAML, #109 item escapes/newline acceptance, #112
  two calls under a one-call cap, #113 lock-denial fallthrough, and #100 empty
  comparison eligibility. These are narrow counterexamples, not full PR suites.
- Integrated focused tests: **113 passed in 0.287 seconds**, comprising
  `test_loop_common_locking`, `test_pipeline_template_paths`,
  `test_example_api_budget`, `test_example_calculator` and
  `test_hosted_agents_sandbox_manager`. This validates the local replacement
  surfaces only. It does not validate the remote heads or a merged tree.
- PR descriptions' historical validation claims were read but not adopted as
  freshly executed evidence. No paid API, dependency install, external publishing,
  installer deletion or provider sandbox execution occurred.
- Raw metadata, complete diffs, final head receipt, probe script/results and the
  integrated test log are retained privately outside the checkout. Public evidence
  here consists of exact public heads, reproducible test names and scoped results.

## Merge topology and next change units

No requested PR targets another requested branch. Ten contain a single distinct
commit; #100 is its own 15-commit series. The observed commit lists contain no
other requested head. They are not an ordered #80→#113 stack. Overlapping files
and shared subject matter do not create a required merge dependency.

Recommended independently reviewed units: (1) locking; (2) all-segment pipeline
paths; (3) hosted manager plus its security reference; (4) parsed calculator plus
Python attempt budgets; (5) separate TS judge budget work; (6) current dependency
lock verification; (7) generated-metadata documentation; (8) portable installer;
(9) valid example frontmatter; (10) historical benchmark evidence separated from
runtime activation. Each needs a scoped clean branch, current-base validation
and maintainer approval. This audit does not authorize publication of local fixes.
