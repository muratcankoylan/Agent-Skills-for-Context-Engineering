# PR review and publication package: 29 September 2026

Publication follow-up: the user subsequently approved these five draft updates.
They are now published and all fresh hosted checks passed. See the
[publication receipt](../pr-publication-2026-09-29.md) for #134 and #135–#138.
The package below intentionally retains its **prepublication** identities and
observations. Its offline check remains valid; its live comparison must now
detect the authorized head and PR-set changes. Statements of no remote mutation
below describe the preparation phase, not the later approved publication.

## Outcome

All 36 open PRs, including 12 drafts, have a head-pinned disposition in
[manifest.json](manifest.json). Three review agents split the core stack,
maintenance/security proposals, and community/examples; separate reviewers
checked the narrow transport and installer repairs. Review limits are explicit:
this is not exhaustive certification of the 599-file #40 import or every
external dependency. No remote head, base, draft flag, review, protection setting
or merge was changed. No commits or new publication branches were created.

The concrete updates are five apply-checked patch files, not another unbounded
working-directory export. They contain fifteen distinct files and no credentials,
runtime data, tracing imports or dependency on the unpublished service.

## Core merge sequence

```text
main@6dbe1a1
  -> #121 -> #122 -> #123 -> #124 -> #125 -> #126
  -> #127 -> #128 -> #129 -> #130 -> #131 -> #134 (+ transport repair)
  -> separately reviewed production implementation
```

This chain already exists remotely. Preserve it; no speculative rebase or base
change is needed. #121 must be a separate adoption interval. The gate rejects
current-main to whole-tip with four adoption findings, while exact-parent
transitions pass. After #121 actually lands, an independently reviewed cumulative
#122–#134 interval is mechanically possible, but has not been authorized or
created. An offline hypothetical base is not protected-default authority.

Historical green checks and GitHub's `MERGEABLE` field are not approval. None
of the core PRs has an approving review, and all except #121 remain drafts.
Require current head-bound hosted checks and independent review before merging.
Ancestry-preserving merges avoid silently invalidating descendants; a chosen
squash/rebase method requires deliberate restacking and fresh checks.

## Prepared changes

| Update | Exact patch base | Contents | Proposed remote action, not executed |
| --- | --- | --- | --- |
| [#134 transport repair](pr-134-transport.patch) | `9639dda3c5b2b6fb3ddfd88a3478c3dc90aa7c54` | Two files: accept create-only HTTP 201, retain strict framing and recovery identity, regression tests | Append commit to `codex/openai-agents-api-transport`; keep base #131 and draft status |
| [#83 installer replacement](pr-83-installer-replacement.patch) | `6dbe1a1d868eab51a3bc9011b0f55e2891513e40` | Installer plus 18 tests; no overwrite/deletion, descriptor-relative no-follow writes, bounded source, explicit partial-install failure | New attributed `codex/installer-no-overwrite` PR against current main, after fresh base check |
| [#80 metadata replacement](pr-80-frontmatter-replacement.patch) | `6dbe1a1d868eab51a3bc9011b0f55e2891513e40` | Four quoted YAML headers plus ten root-CI tests; exact original prompt-body hashes checked | New attributed `codex/judge-agent-frontmatter` PR against current main, after fresh base check |
| [#92 calculator replacement](pr-92-calculator-replacement.patch) | `6dbe1a1d868eab51a3bc9011b0f55e2891513e40` | Four files: bounded arithmetic evaluator, example wiring and 13 root-CI tests; no provider/dependency changes | New attributed `codex/bounded-example-calculator` PR against current main, after fresh base check |
| [#113 locking replacement](pr-113-locking-replacement.patch) | `6dbe1a1d868eab51a3bc9011b0f55e2891513e40` | Two files: optional Unix import, fail-closed advisory locks, legacy inode-lock interoperability and 14 root-CI tests | New attributed `codex/fail-closed-loop-locking` PR against current main, after fresh base check |

The four maintenance repairs are independent, not dependencies of each other or
of the service. They also apply cleanly after #134. #80 adds illustrative document
metadata, not auto-discovered agent registration or tool permissions. It does not
remediate the separate judge SDK/dependency migration. #83 deliberately refuses
upgrades over an existing installation; it never deletes user content and retains
a newly created partial destination on failure. Hostile same-UID source mutation
is outside its stated filesystem guarantee.

These replacements address reports from xiaolai's #80/#83 without overwriting
the contributor's branches or asserting their original implementations are safe.
Keep attribution and discussion links when publishing. Closing or marking old
PRs superseded needs a separate maintainer decision.

The #92 replacement addresses the calculator execution defect in RinZ27's
maintenance proposal. It does not import the old Cursor lock or claim to make the
entire optimizer example production-safe. Expressions are parsed into a bounded
arithmetic AST; Python object access, indexing and arbitrary calls are rejected.
The wiring tests exercise the actual calculator branch without importing the
example's environment loader or provider clients.

## Disposition of every remaining PR

| Group | PRs | Action |
| --- | --- | --- |
| Existing foundation chain | 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 134 | Preserve order; #134 patch prepared; independent acceptance and production follow-on closure still required |
| Narrow maintenance replacements prepared | 83, 80, 92 (calculator only), 113 | Publish separately only after specific approval and fresh CI |
| Broader maintenance revisions | 112, 111, 110, 109, 100, 82, 81 | Replace or split; do not import weaker spending checks, unsafe paths, secret-bearing shells or old executors |
| Relevant content revisions | 133, 88, 89 | Independent portable content/navigation proposals; update provenance and registration, not runtime prerequisites |
| Experimental writing harness | 132 | Keep draft; failed CI plus unresolved accounting/resume/repeated-judge defects |
| Independent or superseded proposals | 95, 72, 55, 52, 40, 38, 36, 24, 17 | Individual scope/rework/supersession decisions; never blanket-stack their executables into production |

Exact findings and inspection boundaries:
[core](../pr-refresh-core-2026-09-29.md),
[maintenance](../pr-refresh-maintenance-2026-09-29.md),
[community](../pr-refresh-community-2026-09-29.md).
The manifest has one entry per observed PR with its exact head/base, action,
reason and dependency edge. No entry asserts merge approval.

## Executed verification

All model/network clients in these tests are fakes. No funded API call occurred.
The following table is the earlier three-patch verification. The latest pass
adds the calculator and corrects the metadata artifact as described afterward;
the earlier counts are not asserted for the new patch bytes.

| Candidate and environment | Executed result |
| --- | --- |
| Exact #134 code with new regression tests, before fix | 42 tests: one failure and three errors, reproducing 201/header/recovery defects |
| #134 plus two-file repair, macOS Python 3.11.0 | 42 transport tests pass; 362 repository tests pass in 101.085 s |
| Independent transport review | Same 42 pass plus 15 mock-native adversarial probes; no actionable finding in changed boundary |
| Current main plus both maintenance replacements | 18 installer and nine metadata tests pass; full repository suite 175 pass in 6.237 s |
| Exact #134 plus all three patches | 389 repository tests pass in 100.549 s; 69 focused tests pass in 0.973 s |
| Same nine-file focused closure, native Linux ARM64, Python 3.12 | 69 pass in 0.371 s, network disabled, nonroot, read-only container root |
| Same focused closure, Linux AMD64 under Rosetta, Python 3.12.14 | 69 executed, three installer HOME-cleanliness assertions fail; no-op `/bin/bash -c 'exit 0'` independently reproduces `.cache/rosetta` creation |
| AMD64 transport and metadata subset, unchanged tests | 51 pass in 0.279 s; installer assertions were not weakened |
| Combined candidate deterministic gates | Reference validator: 17 skills/four layouts; strict repo: zero errors/warnings; inventory: 328 records/205 canonical sources; 23 activation cases pass |
| Patch composition | Forward apply-check on untouched #134 and reverse apply-check on resulting candidate both pass; diff whitespace check passes |
| Newer integration inventory and metadata regressions | 128 tests pass in 73.126 s after exact source-manifest registration; regenerated inventory and public update-package scanner pass |

Test counts overlap; do not add them as independent trials. Native Linux passed
the strict installer assertions. Rosetta ignored `XDG_CACHE_HOME`, so no test or
installer workaround was added. Native hosted AMD64 CI is still required for the
publication candidate. Container images used were the previously built
`context-research-runtime:release-candidate` and `:release-amd64`, with no pulls,
network, secrets, bind mounts or host sockets passed into the containers.
The inspected immutable image IDs were
`sha256:38f3946ce5f963777b8f7f65ed65f1e1b78e226a198298dfca731e6e9d1c639b`
(ARM64) and
`sha256:47e1b9df2e2c41441fb7721d6eb5ce459f92e4b1dacde0e0184f536597b935ca`
(AMD64), both configured for UID/GID `10001:10001`.

Private local reproduction directories are disposable evidence, not authority.
The durable recipe is the exact Git bases plus ordered, SHA-256-bound patches in
the manifest; no workstation locator is needed to reconstruct the candidate.
The nine-file combined candidate excludes the wider unpublished service.

The newer integration checkout additionally uses a closed supervised-source
manifest. Its final check correctly rejected the new metadata test until that
exact test path was registered in `build_inventory.py`. The registration and
derived inventory were refreshed together: 345 records and 321 declared inputs,
digest prefix `acb6b4978066`. This integration-only bookkeeping is not backported
into the independent main-based patch, whose older inventory contract already
passes. Future production slicing must carry the newer registry and projection
closure together. The four agent prompt bodies remain unchanged.

## Four-patch review and verification pass

Three reviewers refreshed all 36 PRs again. The core graph, all heads and bases,
and all twelve draft states were unchanged. New static #132 findings cover
import-time configuration ignoring the advertised env file, detector requests
outside budget admission and non-finite dollar caps; the full witnesses and
required regression cases are in the community report. No claim of exhaustive
review of the 599-file #40 proposal is made.

The #80 artifact was corrected after review found that its earlier serialization
removed a trailing blank line from every document. A new frozen-body regression
reproduced all four mismatches. The corrected artifact preserves each exact
main-branch body, including terminal whitespace, and now has ten tests. An
intermediate helper-based materialization repeated that normalization and was
also rejected; final combined verification imports the actual Git patch bytes
directly instead of translating its hunks. The regression was not weakened.

The calculator's independent review found that NUL and lone-surrogate JSON
strings escaped its typed parser failure. Two new regression methods reproduced
four failing subcases, both directly and through the actual tool branch. The
parser now normalizes `ValueError`, including `UnicodeEncodeError`, to
`CalculatorError`. The final calculator patch has thirteen tests. This does not
enable provider execution or change the example's other unresolved boundaries.

The new package checker was independently reviewed and repaired for default
branch renames, missing live state/base fields and Boolean/float identity
coercion. Its 34 deterministic tests pass; a fresh read-only live check confirms
36 PRs, twelve drafts and four registered patches. It does not evaluate CI or
infer release approval.

Final executed results in this pass:

| Exact scope | Result |
| --- | --- |
| Integration service tests, provider credentials removed | 850 passed in 103.107 s |
| Integration repository-script suite, provider credentials removed | 1,223 passed in 204.997 s |
| Integration deployment tests | 29 passed in 2.670 s |
| Corrected metadata-only candidate on exact main | 10 passed; body hashes, reference compatibility, strict validation and inventory passed |
| Final calculator-only candidate on exact main | 161 root-script tests passed in 5.449 s; 13 focused tests passed in 0.008 s; compatibility/strict/inventory passed |
| Exact #134 with all four final patches, focused closure | 83 passed in 1.074 s |
| Exact #134 with all four final patches, full root-script suite | 403 passed in 104.554 s; reference compatibility 17/four layouts, strict validation zero errors/warnings, inventory 328/205 passed |
| Same thirteen-file focused closure, native Linux ARM64/Python 3.12 | 83 passed in 0.405 s; network disabled, UID/GID 10001, read-only root, bounded memory/processes, no credentials or host mounts |
| Final four-patch composition | All forward and reverse apply-checks pass; whitespace check passes |
| Package checker and publication-file scan | 34 checker regressions pass; fresh live identities match all 36 PRs; eleven package/report/checker files scanned with zero public-boundary findings |

The native Linux run used the same immutable ARM64 image identity recorded in
the earlier table, addressed by digest rather than a mutable tag. The thirteen
source/test files were passed as an explicit archive. No image pull or dependency
installation occurred. Native hosted AMD64 CI remains a distinct publication
check, not inferred from this local ARM64 run or earlier Rosetta observations.

These are deterministic implementation checks with fake provider effects, not
funded research benchmarks, hosted GitHub runs or scientific effectiveness
measurements. Overlapping suites must not be summed as independent trials.

## Five-patch follow-up: locking portability and interoperability

The live GitHub inventory was rechecked again: all 36 open PR heads, bases and
twelve draft states match the manifest. The core stack needs no speculative
restacking. An independent reviewer also reconstructed the previous four-patch
candidate and passed its 83 focused tests before this fifth repair was added.

The #113 replacement addresses MozzamShahid's import-portability report without
substituting a thread mutex for an interprocess lock. Read helpers can import
without `fcntl`; queue locking and append calls then fail before creating paths.
All acquisition failures propagate, and a release failure after the protected
body reports that effects may have committed. An active body exception remains
the primary error. Generic atomic writers still require caller-held queue locks.

A real-process review reproduced a defect in the first replacement: a sidecar
alone did not coordinate with older writers holding the ledger-inode lock. The
final implementation holds both, and regressions verify exclusion with an older
writer through both the original path and a hard-link alias. Tests also reject
symlink, hard-linked and FIFO lock files. This is cooperative POSIX locking on a
trusted local filesystem, not Windows mutation support, a distributed lock or a
crash-durable journal. A target-inode lock failure may leave an empty new file;
file existence must never be interpreted as a completed write receipt.

The two-file patch deliberately excludes the integrated checkout's broader
queue initialization, strict-JSON, durability, path-identity and source-policy
changes. It enables no scheduler, network client, model, promotion or publication.
The final source and test hashes were independently frozen before packaging.

Executed evidence for the final fifth patch:

- Before implementation, ten test methods exposed missing-backend imports,
  ignored lock denial and absent release-uncertainty handling. The independent
  reviewer then reproduced the mixed-version exclusion failure with real
  processes; that additional failure was repaired rather than documented away.
- Final focused suite: 14 tests passed in 0.616 s; independent rerun passed in
  0.618 s. Four competing processes produced 48 unique records with no protected
  queue-body overlap. These are fixtures, not production load measurements.
- Exact-main replacement: all 162 root-script tests passed in 6.025 s. Reference
  compatibility passed for 17 skills/four layouts; strict validation reported zero
  errors/warnings; the existing 258/127 inventory remained valid. The first
  compatibility invocation lacked the installed validator on PATH; the corrected
  invocation used the existing installation, without installing a dependency.
- Exact #134 plus all five final patches applied cleanly. Its reference
  compatibility, strict validation and 328/205 inventory passed.
  The complete root-script suite passed 417 tests in 104.316 s.
- The fifteen-file focused closure passed 97 tests in 0.974 s on native Linux
  ARM64/Python 3.12, with network disabled, nonroot UID/GID 10001, read-only root,
  bounded memory/processes and no credentials or host mounts. It used the same
  immutable ARM64 image recorded above, with no pull or dependency installation.
- Fresh package consistency check: 36 PRs, 12 drafts and five hash-bound patches;
  production readiness remains false. Fresh hosted AMD64 CI and independent
  review on publication heads remain required.

These results do not retroactively turn the broader unmerged service into a
production release. The full-stack result and publication checks below must be
read with their exact candidate scope, not added together as independent trials.

## Publication and release conditions

1. Obtain specific approval for the named branch/PR actions. The #134 append-only
   update has been presented for approval; no response has been assumed.
2. Re-read live main, each affected head/base, and patch hashes. Stop on any
   mismatch. Start clean; do not use the dirty integration checkout as a staging
   source. Apply only one reviewed unit per commit and inspect its exact file list.
3. Preserve #134's five-file original addition, including its transport guide and
   pinned workflow. The integration checkout starts at #131 and does not contain
   those two files: a mirror/delete overlay would silently remove them.
4. Push append-only or create the specifically approved replacement branch; never
   force-push, alter foreign forks, merge, close, or remove draft state implicitly.
5. Run fresh hosted CI on the resulting heads. Existing root CI discovers all
   four new maintenance test modules; #134 retains its pinned Python 3.11/3.12 workflow.
6. Obtain independent review and enforce required checks/reviews before merge.
   Current ruleset observation has zero required approvals and no required status
   checks. Changing that policy requires separately scoped authorization.
7. The wider service needs clean, independently reviewed implementation slices,
   remote durable admission, private-state topology, cumulative-budget migration,
   hosted recovery, and separately credentialed publication canaries. These five
   repairs are not a claim that unattended production deployment is complete.

See [the updated deployment and release plan](../github-release-plan-2026-09-29.md)
for the full cloud boundary. Keep public PR CI secret-free and human merge intact.

## Repeatable package check

Run from the integration checkout:

```sh
python researcher/scripts/validate_pr_package.py --package docs/product/pr-updates-2026-09-29
python researcher/scripts/validate_pr_package.py --package docs/product/pr-updates-2026-09-29 --live
```

The first command is offline. The second uses read-only GitHub observations and
brackets the actual default branch name and OID around the PR inventory query.
Both validate complete PR coverage, exact base/head/draft identities, dependency
edges, patch hashes, patch counts and target bases. Missing live state, new or
removed PRs, changed branch/head/base identities and changed patch bytes fail.
The older saved inventory can omit its historical `state` field; a live query
cannot infer it. The command never pushes, merges, approves, marks ready or
executes patch code. Passing is a consistency result, not a signature, atomic
GitHub snapshot, CI result or publication authority. Recheck immediately before
any separately authorized publication.

## Runtime release boundary

The merge stack and these repairs do not yet deliver the entire requested agent
runtime. The local research pipeline still labels its backend
`bounded_native_responses`; the separate managed client calls the Agents API.
Neither is a Codex SDK implementation. Existing evaluation plans, cost admission,
recovery records and deployment isolation must be migrated and tested as one
coherent runtime change, not relabelled after merging a transport patch. Keep
that follow-on separate from the foundation stack and these maintenance repairs.
The existing $100 cumulative authority and retained unknown reservations must
survive any migration. No paid call or runtime activation was part of this PR
refresh. The [SDK migration plan](../codex-sdk-runtime-migration.md) records the
complete caller, evaluation, recovery and deployment acceptance matrix. A separate
credential-free worker proof is not part of these PR patches or evidence that
the production callers have migrated.

## Suggested PR text

**#134 additive update:** Fix valid session creation responses being rejected as
uncertain before retaining recovery identity. Accept HTTP 201 only on session
creation. Preserve strict decoding/framing validation while ignoring repeated
uninterpreted response headers. No retries, tracing dependency, budget-policy
change or activation. Three new regression methods and strengthened recovery
coverage; 42 focused tests pass. The official [create-session reference](https://developers.openai.com/api/reference/python/resources/beta/subresources/agents/subresources/sessions/methods/create)
shows a 201 response. Preserve base #131. Require fresh hosted checks on the new head.

**#83 replacement:** Addresses the installer safety concern raised in #83 with an
explicit new-destination-only policy. Existing files, directories and symlinks
are never overwritten or deleted. Supports literal spaces without GNU realpath;
validates bounded source files before effects and uses descriptor-relative
no-follow writes. Adds 18 root-CI regression tests. A failed partial installation
is retained for inspection; updates to existing installations remain deliberate
manual migration, not destructive overwrite.

**#80 replacement:** Addresses #80 with valid quoted metadata for four agent
documents, including the colon-containing index description. Original prompt
bodies remain byte-identical. Adds ten root-CI YAML regressions using the
already-locked PyYAML dependency. No runtime discovery directory, model or tool
permissions, judge-runtime migration or claim of production SDK safety is added.

**#92 partial replacement:** Replace unrestricted Python `eval` in the example
calculator with a small arithmetic AST evaluator. Bound expression length,
tree size/depth, integer magnitude, exponents and round precision; reject
non-finite results and non-arithmetic syntax. Thirteen deterministic tests include
the actual tool branch and rejection of Python object access. Do not import
unrelated dependencies, budget wiring or main-loop changes from the integration
checkout. This is calculator hardening, not an arbitrary-code sandbox or a
production endorsement of the full example.

**#113 replacement:** Keep read-side imports available without Unix `fcntl`, but
fail closed before queue locking or append side effects. Propagate acquisition
errors; preserve primary body errors; report release uncertainty without implying
that effects can be retried. Retain inode locking alongside pre-creation sidecars
for mixed-version writers and hard-link aliases. Fourteen credential-free tests
cover backend absence, lock errors, alias/special-file rejection and real-process
contention. No Windows mutation backend, live loop activation or journal guarantee
is added. Attribute the original portability report to #113.
