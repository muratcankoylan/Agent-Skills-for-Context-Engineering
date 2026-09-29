# PR publication and verification: 29 September 2026

The user explicitly approved five draft updates after reviewing their scope.
They are published, and every returned hosted check on each exact new head
completed successfully. Nothing was merged, closed, force-pushed or marked ready.
Contributor branches, repository protection policy and `main` are unchanged.

| Published draft | Scope and attribution | Exact head | Hosted result |
| --- | --- | --- | --- |
| [#134](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/134) | Additive HTTP 201 / recovery-identity transport repair; original #131 base retained | `16a93c6181163eadfa8ac962124b8ca4736ee345` | Validation and both Python 3.11/3.12 transport checks passed |
| [#135](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/135) | Fail-closed POSIX locking and import portability; attributed replacement for MozzamShahid's #113 | `fe0eb0c9418d050c48943f35df84b251dc0ee4b9` | Validation passed |
| [#136](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/136) | New-destination-only installer; attributed replacement for xiaolai's #83 | `9d1ab95fbba8e3e0a4c29cfa5372b885b36a1bcb` | Validation passed |
| [#137](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/137) | Valid agent-document frontmatter, byte-identical bodies; attributed replacement for xiaolai's #80 | `3aab627222e8541c56a6fbd1808da46b6f7e1836` | Validation passed |
| [#138](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/138) | Bounded arithmetic instead of Python `eval`; attributed partial replacement for RinZ27's #92 | `b3f20c60975261a010d02e8487194078f9cce608` | Validation passed |

The four new PRs independently target
`main@6dbe1a1d868eab51a3bc9011b0f55e2891513e40`. The original #113, #83, #80 and
#92 remain open and unchanged for discussion; their disposition is a separate
maintainer decision. Exact source and patch identities, check URLs and completion
times are in the [machine-readable receipt](pr-publication-2026-09-29.json).

## Review coverage and stack

Subagents reviewed all 36 previously open PRs, including twelve drafts, across
foundation, maintenance/security and community/example tracks. Coverage limits
and a head-pinned disposition for each remain in the
[prepublication package](pr-updates-2026-09-29/README.md). That review does not
certify every line of the 599-file #40 proposal or every external dependency.

After publication there are 40 open PRs and sixteen drafts. Read-only comparison
confirmed the other 35 original heads, bases and draft flags are unchanged.

Preserve the core sequence:

```text
main -> #121 -> #122 -> #123 -> #124 -> #125 -> #126
     -> #127 -> #128 -> #129 -> #130 -> #131 -> #134

main -> #135  (independent locking repair)
main -> #136  (independent installer repair)
main -> #137  (independent metadata repair)
main -> #138  (independent calculator repair)
```

#121 requires its own actual adoption interval. Descendant acceptance is not
granted by a hypothetical local merge. The four maintenance repairs can receive
independent human review; they are not chained by their PR numbers. Recheck
identities and checks after any base change. Green checks and draft publication
do not substitute for independent approval or authorization to merge.

## Executed verification

- The exact original #134 head plus all five reviewed patches passed **417
  root-script tests in 104.316 s**, reference compatibility for 17 skills/four
  layouts, strict validation with zero errors/warnings, and generated inventory.
- Its fifteen-file focused closure passed **97 tests in 0.974 s** on native
  Linux ARM64/Python 3.12, network-disabled, nonroot, read-only root, with bounded
  resources and no credentials or host mounts.
- The isolated locking replacement passed **162 root-script tests**. Its
  fourteen focused tests include actual cooperating processes, legacy writer
  interoperability, aliases, lock errors and backend absence. Independent review
  reproduced and repaired the intermediate inode-lock omission.
- Publication candidates reran their own focused suites: #134 42, #135 14,
  #136 18, #137 10 and #138 13 tests. Each commit contains only its reviewed
  patch. The broad dirty integration checkout was never staged for publication.
- Fresh hosted checks subsequently passed on all five exact published heads.
  #134 additionally passed its Python 3.11/3.12 transport matrix. These are
  individual hosted PR checks, not a hosted run of the hypothetical combined
  merge tree.

Counts overlap and must not be summed as independent experiments. No funded
provider call, live research benchmark or production deployment was performed.

## What is still a separate release

Broader maintenance proposals and community contributions retain their explicit
rework, scope or supersession dispositions. They were not blanket-stacked into
the supported runtime. In particular, #132 remains draft with accounting/resume
and evaluation defects; dependency upgrades, hosted credential isolation and
pipeline containment must retain their own coherent verification scopes.

The [Codex SDK runtime migration](codex-sdk-runtime-migration.md) remains a
separate implementation series: provider-request admission against the original
cumulative budget, every production role and evaluator, tool grants, immutable
candidate provenance, recovery, operator controls and cloud deployment.

Separate local work now includes a pinned SDK worker proof: fifteen tests passed,
including five real SDK/app-server tests against a local deterministic provider.
It is not part of any of these published patches. Its wire lacks
`max_output_tokens`, exposes native tools despite some disable settings, and has
no durable admission or host-mount isolation. Those observations define the next
engineering gates; they are not an SDK production-readiness claim. The public
boundary check subsequently required replacing a synthetic workstation-style
test path; all ten worker contract tests and the seven-file publication scan
passed after that nonfunctional fixture change.

## Reproduction record

The preparation manifest intentionally preserves the old 36-PR observation and
the original patch bases. Its offline check remains meaningful. Its `--live`
comparison must now reject the approved publication changes; do not rewrite
history to make that check appear current. This receipt records the transition.
Any future publication needs a fresh complete inventory and exact-head checks.
