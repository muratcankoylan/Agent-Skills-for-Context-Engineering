# Standalone research service: implementation and verification receipt

Date: 10 September 2026. Status: local pre-release implementation.
Production readiness remains **blocked**. This is neither a deployment receipt
nor an empirical claim that the service improves downstream research or skills.

## Scope and identity

Work was performed in the integrated `agent-skills-local-production` checkout,
not by installing a Codex automation. The checkout contains substantial earlier
uncommitted work. Its Git base is
`c6cd52017b247804373339e1c3c103d42554b0a1`; that commit does **not** contain the new
service. No branch, commit, push or merge was created in this iteration.

The final service work-manifest implementation digest is
`sha256:8d2fe08015017bf0bfdb2d844b670d6246368e490864a5a027f108f6388591d1`.
It covers the service/script Python source population, selected lockfiles, Python
version and selected installed dependency versions as defined by
`researcher/service/workflow.py::implementation`. It is not an exhaustive release
tree, container image, installed-wheel byte attestation or public export digest.

The runtime used Python 3.11.0. Optional MCP tests used installed MCP 1.30.0 and
httpx 0.28.1. The optional hashlock's SHA-256 is
`328d51bfeb5b526bbaeac4a259d98fc508929b13a5d297b46617ad267a35d1b6`.
The resolved environment passed the dependency compatibility check.

## Implemented changes

- A standalone CLI, foreground scheduler/coordinator, explicit configuration,
  private SQLite jobs/checkpoints/effect reservations, pause and inspection.
- Four logical roles with independently configured native model APIs: researcher,
  critic, skill editor and evaluator. Paid native calls have isolated credentials,
  an absolute process deadline, bounded configuration and progress events.
- Retained arXiv/official-feed acquisition and re-extraction, bounded corpus
  retrieval, exact quote checks, frozen candidate materialization and paired
  reversed-order development review.
- Registered MCP observation ingestion with strict tool/schema selection,
  pre-effect request/cost reservations, isolated execution and SDK-log suppression.
- Bounded same-baseline/schedule hypothesis history without prior judge answers;
  exact duplicate candidate suppression before repeat model reviews or delivery.
- An optional draft-only GitHub proposal/review-request adapter. No merge or
  protected-branch update path.
- Authenticated loopback operator API and server-side `/service` UI status reader.
  Fixture and real-service shells are distinguished; no browser credential or
  fallback to fabricated service status.
- Dependencies-only container and native systemd templates, explicit read-only
  release identity checks, and an optional hashlocked MCP install profile.

The preview does not implement every drafted constitutional owner. It cannot
self-accept a specification, merge its own changes or activate a cloud release.

## Executed verification

| Check | Observed result | What the result does not establish |
| --- | --- | --- |
| Existing researcher suite | 1,130 tests passed in 261.672 seconds | Live provider/cloud readiness |
| Standalone service suite | 204 tests passed in 10.733 seconds, no skips | Scientific effectiveness or public endpoint safety |
| Deployment preflight/static contracts | 10 tests passed | Docker build, Linux unit validity or cloud operation |
| Control center | 50 tests, TypeScript, production build and standalone server smoke passed | Public authentication, cloud ingress or command UI |
| Actual UI-to-service exchange | Built `/service` page read a real local SQLite-backed API with a fixture job; operator token absent from returned HTML | Live model execution; the job was explicitly synthetic |
| Installed MCP SDK | Real SDK protocol/schema/HTTP machinery exercised through MockTransport within the service suite | A live MCP endpoint or X provider account |
| Platform compatibility | 17 skills, four local install layouts passed with reference validator | Downstream usefulness of the new runtime |
| Strict repository validation | Zero errors, zero warnings | Acceptance of all draft specs |
| Skill health and activation fixtures | Strict health passed; 23 activation cases passed | Candidate-body effectiveness |
| Context-packing benchmark | Six deterministic coverage/budget/provenance cases passed, zero model calls | Semantic retrieval quality |
| Benchmark catalog | Three catalog checks passed; seven entries; zero scenarios executed by this command | A model benchmark run |
| Spec plan and generated inventory | Zero plan findings; 27 specs, 258 unassessed criteria; inventory check passed | Any lifecycle advancement |
| Ruff and whitespace | Passed for service code and final diff whitespace | Full security audit |

The first broad regression run failed on stale generated inventory and spec-plan
bindings. A subsequent run still encountered inventory drift after the CI edit.
The inputs were then frozen, generated artifacts refreshed, and the full
1,130-test suite rerun successfully. These failures were not discarded from the
work record or represented as initial success.

The public-repository boundary check **did not pass**: it reported
`FORBIDDEN_PRIVATE_PATH` and `TRACKED_PATH_ESCAPE` for
`researcher/reports/benchmark-history.jsonl`. That file was already deleted from
the worktree before this iteration, but remains in the Git index. Its intended
removal must be reconciled in the reviewed release change set; this iteration
did not restore potentially private history or stage unrelated changes.

## Live source-only canary

At 22:18 UTC, a bounded source probe used the query
“context engineering evidence transfer agents.” No model credential was used.

| Source | HTTP requests | Captured bytes | Normalized items | Captured-byte replay |
| --- | ---: | ---: | ---: | --- |
| arXiv title/abstract search | 1 | 16,404 | 6 | Passed |
| DeepMind official feed | 1 | 71,993 | 6 | Passed |

Both responses were HTTP 200 and not truncated. Captures and normalized evidence
remain private runtime artifacts. The probe retained its reservation and closed
as `SOURCE_PROBE_ONLY_NO_SKILL_PROPOSAL`; it is deliberately not a successful
skill-improvement job. It made zero paid model calls. Feed items were not labeled
for query relevance, and these observations do not establish full-paper retrieval,
novelty, source coverage or research quality.

The offline workflow was also exercised with distinct context-transfer, memory,
and tool-contract queries. A repeated fixture proposal was detected on the next
cycle after receiving bounded prior-hypothesis context. It stopped before a new
pair of judge calls or PR creation. No fixture modified a checked-out skill.

## Bugs discovered through the new tests

1. Duplicate headings and HTML-comment changes could defeat a rendered-section
   preservation check. Exact raw locked-section preservation now supplements
   Markdown structure checks.
2. Backward clock movement could reopen an earlier budget day. A persisted clock
   floor now denies backward budget/schedule progress.
3. Completed model responses unnecessarily required a credential to replay.
   Completed-effect lookup now precedes credential resolution.
4. Hash-only source acceptance failed to establish derivation from retained bytes.
   Actual connector extraction is replayed and compared before consumption.
5. A malformed MCP initialize response could make the actual SDK's ERROR logger
   echo a credential. Live MCP now executes in a child that suppresses SDK logs
   and discards incidental output. The reflected-credential regression passes.
6. JSON-escaped credentials could bypass literal output checks before model JSON
   parsing. Decoded strings and keys are now checked before response retention.
7. Unused malformed MCP registrations and impossible declared limits were accepted
   too late. Configuration admission now rejects them before dispatch.

Unknown remote outcomes remain quarantined rather than retried. Some MCP SDK
exception groups lose specific diagnostic codes; some invalid responses are
conservatively classified as unknown. Those limitations remain disclosed.

## Actual GitHub changes

Descriptions for [#121](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/121),
[#122](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/122),
[#125](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/125),
[#126](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/126),
[#130](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/130),
and [#131](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/131)
were updated with standalone-cloud alignment notes. All six were subsequently
read back; the notes were present and their previously observed head commits
unchanged. Original descriptions and historical test evidence were preserved.
The notes explicitly say this implementation is local, not already in those PRs.

The [PR plan](cloud-pr-plan-2026-09-10.md) separates foundation decisions from
new review units. This receipt is not an unconditional merge recommendation.

## Open gates and next bounded experiment

No configured native model key was available in this execution environment, no
live MCP endpoint was configured, and no cloud target was selected. Docker's
daemon was unavailable. No paid model, live MCP, sandbox draft-PR, container or
cloud canary was represented as executed.

The next experiment is a credentialed, concurrency-one research canary on a
reviewed configuration and fixed total budget: several needs including a null
case, exact source/support inspection, one supported candidate, a timeout case,
usage reconciliation, then a different compatible model route. GitHub should
remain disabled until a separate sandbox delivery/recovery canary.

Release still requires full candidate overlay validation and claim/mechanism/index
synchronization; held-out downstream outcome tests; accepted owner integration;
uncertain-effect reconciliation; authenticated cloud operation with egress and
memory limits; artifact-complete encrypted restore; and an actual multi-day soak.
Full-paper service retrieval and a validated X source remain unfinished. An
archive-search or research-superiority claim requires the separately predeclared
[research protocol](cloud-research-protocol.md), not this engineering receipt.

Both temporary UI/API test servers were stopped after the local integration
check. No recurring Codex automation was created or changed.
