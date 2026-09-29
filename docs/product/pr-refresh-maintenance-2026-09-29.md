# Maintenance and security PR refresh: 29 September 2026

## Decision and evidence boundary

Do not merge the eleven reviewed heads unchanged. Their complete diffs and head
SHAs are unchanged from the [earlier security review](pr-security-review-2026-09-29.md),
so its reproduced counterexamples still apply. What changed is the integrated
local replacement: installer safety, durable judge-attempt admission, and valid
agent-document frontmatter are now implemented and tested. They are not changes
to the contributor PRs or proof that the integrated dirty checkout is published.

Fresh read-only GitHub queries returned all eleven open and non-draft, targeting
`main`, with empty `statusCheckRollup` arrays and empty `reviewDecision` fields.
There is **no observed CI or review-approval evidence** for these exact heads.
Nine report `CLEAN/MERGEABLE`; #100 and #111 report `DIRTY/CONFLICTING`. These
fields do not establish tested merge readiness. The current `main` branch was
rechecked at `6dbe1a1d868eab51a3bc9011b0f55e2891513e40`, reported protected.
Protection metadata alone does not establish which policy checks are required.

All eleven heads belong to foreign forks. `maintainerCanModify=true` was reported
for each, but is not permission to overwrite a contributor's branch. Prefer an
attributed, current-main replacement with the smallest reviewed patch closure;
retain the original PR for discussion until the maintainer chooses disposition.
This refresh made no GitHub writes, push, commit, merge, close or retarget action.

## Exact refreshed heads

All complete diffs were byte-compared with the earlier audit's private receipts.
The last column names the minimum replacement, not an authorization or readiness
claim. File counts describe the remote PR, not the replacement.

| PR and exact title | Exact head SHA | Fork owner; files | Recommendation |
| --- | --- | --- | --- |
| [#113 Fix Windows import crash in loop_common by making fcntl optional](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/113) | `b789fd4d7e91cd6d55950980237421b065e17589` | MozzamShahid; 1 | Replace with fail-closed process locking; no Windows mutation claim. |
| [#112 Add cost, request, token, and rate-limit safeguards to API loops and judge examples](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/112) | `0b518ceb6810915faf90a3b32ab2ebde716ca5e5` | MozzamShahid; 11 | Split Python example and TypeScript judge admission; keep legacy loop inert. |
| [#111 Fix stale researcher-OS baseline numbers in README, AGENTS, and plugin metadata](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/111) | `fb2262433d71da72ea115fc34c9750abbb688c89` | MozzamShahid; 3 | Replace duplicated live counts with generated links; conflicting. |
| [#110 Fix shell injection and unsafe secret handling in hosted agents image build example](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/110) | `dd862b430bf1dda6d8ad84c19f239d2423fac0d6` | MozzamShahid; 1 | Coordinate with #81 replacement; clone-only lease and clean build/snapshot boundary. |
| [#109 Fix path traversal and arbitrary file deletion in pipeline_template.py](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/109) | `8729b720f4a21fe48342eacc57291162d0dfeee2` | MozzamShahid; 2 | Replace with all-segment containment and alias regression tests. |
| [#100 Publish xhigh evidence and harden validation paths](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/100) | `596c8f84eaa4ef89333fdfc4ee2ca042c0dcf540` | Lyti4; 83 | Separate historical evidence and utilities from executor activation; conflicting. |
| [#92 Maintenance: Update dependencies and refine interleaved thinking example](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/92) | `1de8c919199c0f6baa8a5d02da43e1fb13d2e6ae` | RinZ27; 3 | Preserve parsed calculator; assess current lock instead of importing stale lock. |
| [#83 fix: validate custom install path in install.sh to prevent path traversal](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/83) | `325c5c2e0e166a75c91c60b2d0535035f6fb57ad` | xiaolai; 1 | Narrow replacement now implemented: installer plus 18 fixture tests. |
| [#82 fix: tighten production dependency ranges from ^ to ~ in package.json](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/82) | `d3185bf73dfca2366d388a1482bfa14f9595f334` | xiaolai; 1 | Do not treat range narrowing as remediation; supported-SDK migration remains separate. |
| [#81 fix: remove GitHub token from git clone URL in sandbox_manager.py](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/81) | `87a516eea95b1cd4e92246162dcfc28c84125ae2` | xiaolai; 1 | Replace embedded secret/shell construction, together with matching #110 reference. |
| [#80 fix: add YAML frontmatter to llm-as-judge agent files](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/80) | `e5fd0e3e4c3a689d3269ac951bc05c5075266717` | xiaolai; 4 | Narrow replacement now implemented: quoted metadata plus root-CI YAML tests. |

## Findings and current local replacement

### #113: import portability is not process exclusion

The one-file patch still swallows lock denial and falls back to a process-local
thread mutex on Windows. Neither protects cross-process queue transactions.
The local [locking implementation](../../researcher/scripts/loop_common.py) keeps
unsupported platforms importable but rejects unsupported mutations and propagates
lock acquisition failure. `test_loop_common_locking` passed in this refresh.
An isolated [two-file replacement](pr-updates-2026-09-29/pr-113-locking-replacement.patch)
now extracts the import-capability and lock-exclusion boundary, not the entire
integrated queue rewrite. Fourteen tests cover missing backend, denial, release
uncertainty, special/aliased lock files and actual mixed-version process
contention. The sidecar and original ledger-inode flock are both retained; an
independent review reproduced and eliminated an earlier interoperability defect.
Exact-main full tests passed 162/162; the combined fifteen-file focused closure
passed 97/97 on native Linux ARM64 without network or credentials. See the
[package verification receipt](pr-updates-2026-09-29/README.md#five-patch-follow-up-locking-portability-and-interoperability)
for limits and identities. This is not a remote PR update. Actual
Windows interprocess/filesystem support remains unimplemented, not a core POSIX
service launch prerequisite.

### #112: separate three execution surfaces

The eleven-file patch still admits multiple effects behind one gate, records
some usage only after calls, permits concurrency races and omits retry-aware
reservation. Its legacy HTTP changes must not reactivate the inert loop.

1. The Python optimizer example already has a shared pre-effect
   [attempt budget](../../examples/interleaved-thinking/reasoning_trace_optimizer/api_budget.py).
   Its budget and parsed-calculator regressions passed again.
2. The TypeScript judge now has [LocalAttemptBudget](../../examples/llm-as-judge-skills/src/runtime/attempt-budget.ts)
   and an explicitly injected [JudgeRuntime](../../examples/llm-as-judge-skills/src/runtime/judge-runtime.ts).
   Exclusive, fsynced attempt slots precede SDK invocation; failed, unknown and
   interrupted attempts are not refunded. Pairwise passes reserve independently,
   SDK retries are disabled, and input/output/concurrency limits are explicit.
   Forty current offline tests passed again, including twelve cooperating
   processes admitting exactly three effects under a three-attempt cap.
3. Neither replacement is an account-wide dollar cap or multi-host authority.
   The repo-native production service has its own execution/budget contract;
   do not substitute this teaching example's ledger for it.

The TypeScript replacement is a coherent runtime/config/tool/test/docs unit,
not a one-file cherry-pick. Its unsupported SDK and known dependency advisories
remain. The [example README](../../examples/llm-as-judge-skills/README.md) records
the existing audit and forbids production credentials. No new registry audit or
paid provider call was performed in this refresh.

### #111: prevent the count drift mechanism

The three-file patch still duplicates snapshot counts and a health value without
binding them to generated inputs. Use the [generated corpus summary](../../researcher/generated/corpus-summary.md)
for current counts and dated benchmark receipts for historical results. The
remote branch conflicts; resolving that conflict alone would not fix the design.
Keep metadata edits separate from runtime release claims. No PR-head health
measurement was executed.

### #110 and #81: one security boundary across two surfaces

Both complete diffs remain unchanged. #81 moves a token from the clone URL into
shell text and an ambient credential-helper operation. #110 leaves the mounted
credential accessible through repository-controlled builds and snapshotting.
The local [manager](../../skills/hosted-agents/scripts/sandbox_manager.py) and
[reference](../../skills/hosted-agents/references/infrastructure-patterns.md)
instead require canonical repositories, argv-only commands, operation-scoped
opaque leases, closure before untrusted builds and quiescence before snapshotting.
The fake-adapter manager suite passed again. This is a tested reference contract,
not a deployed broker or proof of provider isolation. Package manager, reference,
tests and required corpus projections together; do not publish one old surface
beside a contradictory newer one.

### #109: the deletion boundary includes every segment

The two-file patch validates batch IDs but still accepts absolute/traversing item
IDs and permits a trailing newline through its regex. Local
[path helpers](../../skills/project-development/scripts/pipeline_template.py)
validate batch, item and leaf segments and reject alias escapes and unsafe
ancestors. Their regression suite passed again. Extract these containment changes
with their tests; broader pipeline execution changes need separate review.

### #100: no historical report requires activating its executor

This remains an 83-file, 15-commit series. Review scope is unchanged from the
earlier audit: file inventory, runner/control flow, comparator/promotion logic,
validators/tests and report/methodology changes, not exhaustive synthetic-history
or lock-entry validation. The demonstrated zero-pair publication eligibility,
unchecked aggregate/provenance/duplicate assumptions, inherited environment and
malformed-resume rerun behavior remain unresolved at this head.

Separate: (a) historical negative xhigh evidence after raw-data/exposure review;
(b) independently useful current-base validator fixes with regressions; (c) any
new executor as its own safety/authorization design. Do not import old accepted
promotion wording or zero-cost forecasts as present authority. This refresh did
not rerun a full PR suite, live benchmark, raw-result regrade or statistical study.

### #92 and #82: dependency cleanup is not a range-edit exercise

#92 changes three files; its calculator change remains only an `eval` warning.
Keep the locally tested bounded parsed arithmetic. Its SDK 1.0.18 lock and broad
overrides are stale relative to the local zero-call planner's exact SDK 1.0.28
and scoped Undici 6.28.1 override. These local pins are comparison evidence,
not a fresh vulnerability clearance.

#82 changes five manifest ranges without a corresponding tested resolution.
The judge's recorded SDK-v4 dependency audit still has seven affected packages,
including one high-severity finding. A supported-SDK migration and complete
compatibility/advisory review, or retirement of the example, remains real work.
It is not necessary to deploy this example to launch the separate research
service. Neither PR should silently downgrade or re-enable another runtime.

### #83: the local installer repair is now complete within its scope

The remote one-file patch still adds GNU-specific `realpath`, rejects legitimate
spaces and retains destructive overwrite behavior. The local
[installer](../../examples/digital-brain-skill/scripts/install.sh) now supports
literal paths with spaces on macOS/Linux using Python 3, and accepts only new
destinations. Existing entries are never removed or overwritten. Symlink,
traversal, broad-target and source-overlap checks precede copying; exclusive
creation protects competing cooperative installers. Source entries and total
copy size are bounded. An unexpected failure preserves a partial new destination
for inspection rather than deleting it or automatically overwriting it on retry.

The smallest replacement is that script plus
[18 fixture tests](../../researcher/scripts/tests/test_install_safety.py).
All passed in the refresh batch; the prior dated verification also records Linux
execution. No actual user installation or deletion was performed. This boundary
does not defend against a hostile same-UID actor replacing trusted source data.

### #80: valid document metadata, not runtime agent registration

The remote index description still contains an invalid unquoted `: ` scalar.
The local repair adds quoted `name` and `description` to exactly the existing
index, evaluator, orchestrator and research Markdown documents under
`examples/llm-as-judge-skills/agents/`. All four original bodies remain
byte-identical. No `.claude/agents` directory, model, permission or tool setting
was invented. These remain illustrative documents, not auto-discovered agents;
their embedded historical snippets were intentionally not rewritten.

The replacement includes
[nine PyYAML regression tests](../../researcher/scripts/tests/test_judge_agent_frontmatter.py)
in the existing root CI suite. They check all four documents, unique names,
closed metadata fields, actual string types, original malformed YAML, duplicate
fields, out-of-scope permissions and missing delimiters. It is independent of the
unpublished TypeScript runtime and package-lock changes. An initial Vitest-based
regression was removed in favor of this independently CI-gated patch closure.

## Executed verification and topology

- Fresh metadata and complete diffs: all eleven; all heads/diffs unchanged.
  Earlier exact-head counterexample probes are carried forward by byte identity,
  not described as newly executed full PR test suites.
- Current integrated Python selection: **140 tests passed in 1.058 s**, comprising
  locking, pipeline paths, Python attempt budget, parsed calculator, hosted
  manager, installer and frontmatter. Tests used fixture/fake-provider effects
  with credentials removed from the process environment.
- Current TypeScript judge selection in a fresh private workspace copied from
  the prior offline dependency installation: **40 tests passed in 784 ms**;
  source build/typecheck and ESLint passed. No dependency installation or live
  provider was needed. These are local replacement tests, not remote-head CI.
- The frontmatter-only suite separately passed **9 tests in 0.005 s**, Ruff
  passed, all four YAML documents parsed, and pre/post body hashes matched.
  Counts overlap; do not add them into a claim of independent experiments.
- Earlier broader verification is retained in the
  [dated engineering receipt](tracing-engineering-verification-2026-09-29.md).
  No scientific quality gain, account-level budget proof or cloud readiness
  follows from these deterministic tests.

No reviewed PR targets another reviewed branch. Ten are single-commit changes;
#100 has fifteen commits, none equal to another reviewed head. This is not a
numeric merge stack. #110/#81 share a security boundary; #112/#82/#80 share an
example but have separable patch closures. Installer and document metadata can
be independent current-main replacements. Locking, containment, hosted-reference
safety, calculator/attempt admission, dependency migration and historical
benchmark publication should retain separate validation and rollback scopes.

Only after a replacement is constructed on current main should its exact patch,
reference compatibility, strict repository validation, generated artifacts and
required CI be checked. Local success does not authorize publishing the entire
integration checkout or replacing contributor branches. Private raw receipts and
logs are retained outside the repository; no credentials or private runtime
records are included here.

## Follow-up refresh and isolated calculator replacement

A second fresh read-only query on 29 September confirmed all eleven exact heads
in the table, all complete diffs, and protected `main`
`6dbe1a1d868eab51a3bc9011b0f55e2891513e40` unchanged. All eleven remain open,
non-draft foreign-fork PRs with no returned checks or review decision. #100 and
#111 remain conflicting. Earlier findings remain applicable through exact diff
identity; this is not a new exhaustive audit or an execution of every PR head.

The next narrow replacement is [the four-file #92 calculator patch](pr-updates-2026-09-29/pr-92-calculator-replacement.patch),
prepared against that exact main. The remote patch adds a warning above `eval`
but leaves Python-object traversal reachable. This replacement implements the
security repair without importing #92's stale dependency lock or unrelated
local API-budget and optimizer-loop changes.

Its complete file closure is:

- `examples/interleaved-thinking/examples/03_full_optimization.py`: calculator
  import, supported-expression descriptions, and bounded evaluator call only.
- `examples/interleaved-thinking/reasoning_trace_optimizer/calculator.py`:
  stdlib AST evaluator with allowlisted arithmetic/functions, finite real-number
  results, and explicit expression, tree, integer, exponent and precision bounds.
- `examples/interleaved-thinking/tests/test_calculator.py`: thirteen deterministic
  tests, including structural wiring and the actual tool function's calculator
  branch. The test compiles only that reviewed function; it never imports the
  environment-loading example or invokes a provider.
- `researcher/scripts/tests/test_example_calculator.py`: exposes those same
  canonical tests to existing root unittest discovery, without new dependencies.

Verification performed on the isolated candidate:

- Before changing the call site, the eleven-test suite produced **two expected
  failures**: missing bounded-evaluator wiring and successful object access via
  `().__class__.__name__`. This counterexample executes no external command.
- A follow-up independent review found JSON-representable NUL and lone-surrogate
  strings escape `ast.parse` as `ValueError` and `UnicodeEncodeError` on Python
  3.11.0. Two added tests reproduced **four error subcases among 13 tests**,
  through both the evaluator and actual tool branch. The parser now converts
  `ValueError`, including its Unicode exception subclasses, to `CalculatorError`.
- After the complete repair, **13/13 focused tests passed in 0.008 s**. The exact-main
  Git clone's complete root-script suite passed **161/161 in 5.449 s**. These
  counts overlap; they are not independent experiments.
- Platform compatibility passed for **17 skills and four local layouts**;
  strict repository validation reported **zero errors and zero warnings**.
  Inventory check passed unchanged at **258 records and 127 canonical sources**,
  digest prefix `cdd6e53336fa`. These are exact-main patch measurements, not the
  larger integrated checkout's current counts. Ruff and Git whitespace checks
  passed for the focused closure.
- An initial plain-archive full-suite attempt had **seven errors among 159
  tests** because migration fixtures require Git-tracked public sources. The
  subsequent real Git-clone run above resolves that environment limitation;
  the failed archive run is not presented as passing evidence.
- `git apply --check` passed against the prepared combined workspace at #134
  head `9639dda3c5b2b6fb3ddfd88a3478c3dc90aa7c54`, with its transport, installer
  and frontmatter replacements present. That is an applicability check, not a
  claim that this review executed the combined stack's full test suite.

The patch contains **four files, 472 insertions and 21 deletions**; SHA-256
`f20307a46cb305d09e13afcf925847ecada54765d377eaa0717aef41e6f4587f`.
It adds no model/provider calls, does not touch a lockfile, and was tested with
credentials absent from the process environment. This bounds arithmetic in one
teaching tool; it is not a general Python sandbox or a production-readiness
claim for the entire example. Publish it, if authorized, as an attributed
current-main replacement rather than overwriting the contributor's fork. The
remaining containment, credential-broker, admission, dependency and historical
evidence work retains the separate dispositions above. No remote mutation or
commit was made by this refresh.
