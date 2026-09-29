# Managed Agents API implementation and launch verification

Observation date: 10 September 2026, America/Toronto; final checks completed after
00:00 UTC on 11 September. Disposition: developmental implementation, not a
production release or evidence that autonomous skill evolution improves outcomes.

## Outcome and scope

The preferred product runtime is OpenAI's managed Agents API. The repository owns
research evidence, experimental design, candidate identity, permissions and
publication. The application is ordinary open-source repository code, not a Codex
desktop automation. The [architecture and research protocol](openai-agents-research-architecture.md)
sets the target; the [canary runbook](../../researcher/service/AGENTS_API.md) documents
the implemented entry point and its limits.

There are three different delivery states:

| Surface | Actual state |
| --- | --- |
| Published change | Draft PR #134 contains the transport, its 39 tests, credential-free CI, package initializer and transport documentation only |
| Integrated local change | Context compiler, durable single-session runner, paired planner/scorer, tests, draft specifications, machine plan and architecture documentation |
| Live operation | No paid Agents session, live model benchmark, unattended managed loop or cloud deployment performed in this iteration |

The integrated checkout remains a dirty development tree with substantial work
predating this iteration. Its base commit alone does not identify those changes
and it is not an approved release. Only the deliberately isolated transport
closure was published. No PR was merged or existing branch rewritten.

## Implementation

| Module | Contract and important limits |
| --- | --- |
| `researcher/service/openai_agents.py` | Fixed-origin stdlib transport; bounded worker and parsing; explicit credential; no redirects or automatic retries; preserves safe known session ID after later decode failure; create/retrieve/list/cancel only |
| `researcher/service/agents_context.py` | Compiles exact selected skill baselines and hashed evidence into a request bounded to 128 KiB; validates literal citations, cross-role references and one inert scoped edit; no filesystem writes or publication |
| `researcher/service/agents_runtime.py` | Private atomic/locked packet and submission ledger; one create attempt per directory; durable remote locator; saved-turn/item recovery; explicit cancellation uncertainty and terminal-output validation |
| `researcher/service/agents_evals.py` | Three-condition randomized paired plan, exact result binding, deterministic scoring and failure-inclusive reporting; no model executor or independent-effectiveness certificate |

The initial request has `environment.type=none`, no tools, no vaults and no
subagents by default. An explicitly bounded subagent treatment can be configured,
but collaborators in one session do not qualify as independent evaluators.
Structured output contains research, critique and an optional proposal. A valid
result still awaits independent evaluation; it does not freeze, apply, accept,
publish or merge the proposed edit.

The official API contracts materially changed the implementation: managed
sessions can outlive the caller, cancellation acknowledgement is not stop proof,
saved records differ from a replayable stream, and no hard per-session cost cap
was established in the reviewed create contract. The runner therefore does not
reuse the native-provider single-response spending formula. See the architecture's
primary-source citations rather than treating this report as provider policy.

## Verification actually executed

All tests below used deterministic inputs or local test servers. They made zero
paid provider calls. Counts overlap where component suites are part of larger
suites; do not sum every row into an independent test count.

| Check | Result | Measurement boundary |
| --- | --- | --- |
| Repository Python suite | 1,130 passed in 205.322 s | Existing research, provenance, authority, inventory and harness regressions |
| Final integrated service suite | 332 passed in 18.491 s | Includes 39 transport, 23 context, 41 runtime and 25 evaluation tests; remainder existing service tests |
| Deployment-contract suite | 10 passed in 0.017 s | Packaging and preflight contracts, not an executed cloud deployment |
| Control-center UI suite | 50 passed in 5.257 s | Existing fixture/native-service UI contracts; not a managed-session UI acceptance test |
| Exact isolated PR transport suite | 39 passed locally | Same transport/test bytes as the integrated checkout |
| PR #134 hosted CI | Python 3.11 and 3.12 transport checks plus repository validation passed | Head `9639dda3c5b2b6fb3ddfd88a3478c3dc90aa7c54` |
| Strict repository validation | 0 errors, 0 warnings, 17 skills | Structural/content invariants, not semantic effectiveness |
| Platform compatibility | 17 skills, 4 local installation layouts passed | Reference validator was present on the successful run |
| Skill health | 0 flagged; corpus score 0.9221 | Static rubric, no new model-based skill score |
| Activation fixtures | 23 passed, 0 failures | Existing declared activation cases |
| Context packing fixtures | 6 passed | Deterministic coverage, bytes, omission and provenance checks only |
| Benchmark catalog | 3 checks passed; 7 entries; 0 scenarios executed | Catalog consistency is not scenario execution |
| Specification plan | 27 specs, 261 criteria; zero check findings | All criteria remain unassessed; no acceptance was inferred from planning |
| Inventory | 340 artifact records, 315 declared input snapshots; check passed | Declared-input digest prefix `6d429ea0af52` |
| Ruff and selected whitespace checks | Passed | New modules/tests and touched tracked documentation |

An initial service-suite invocation could not bind local test servers inside the
sandbox and reported 16 errors. A specifically permitted localhost test run passed;
the final post-review run above also passed. An initial isolated compatibility
check lacked the reference-validator executable on PATH; it passed after explicit
environment selection. These unsuccessful setup attempts are not hidden as passes.

### Failure drills added or strengthened

- Lost create response leaves durable intent and forbids another create attempt.
- A safe returned session ID survives malformed response fields or interruption
  after creation and is available for cancellation/reconciliation.
- Configuration changes, including boolean/integer substitutions inside policy
  and output schemas, cannot pass equality checks.
- Identity/configuration drift discovered by direct observation quarantines the
  known session and requests cancellation against the original locator.
- Polling failure, local deadline and watch exhaustion attempt cancellation;
  clock rollback cannot disable emergency cancellation.
- Cancellation acknowledgement, unknown cancellation outcome and observed terminal
  work remain different states. A failed session without history or a cancelled
  root with a running child does not prove all work stopped.
- Duplicate pages/cursors, wrong-turn output, malformed or fabricated citations,
  unsupported proposals, scope violations and changed result/plan bytes fail.
- Transient read failure permits read-only recovery, not unconditional create retry.

## Offline CLI and comparison smoke

An additional process-level smoke prepared a private synthetic packet using the
real compiler/ledger and read it through CLI `status`. A CLI run with a deliberately
unset credential name returned `OPENAI_API_KEY_UNAVAILABLE`; state remained
`prepared` with no remote ID. No create intent or network call occurred.

The scorer smoke used four public synthetic tasks, three arms and three
replications, producing 36 planned rows. Known gold answers passed 36/36. After
injecting a fabricated citation and removing one row, it reported 34 passes and
one missing result while retaining a planned denominator of 36. These are oracle
wiring checks, not agent runs, statistical observations or research success rates.

| Artifact identity | Digest |
| --- | --- |
| Synthetic plan | `sha256:50e78b7c91c4267ac54fb4ecfc85d2b816828d44905837d0b76dacb276c8a7f8` |
| Gold-answer comparison | `sha256:fad45f85643ab35b88435d8afe96f513dec60bbd255647712ec668e6be948af4` |
| Faulted comparison | `sha256:539b32286d7fbabd3d0067eef1f3211caed254d919d6589c6b032cca6ca160ec` |

Public fixture IDs can reveal task intent; the fixture is not a blinded dataset.
Before a scientific study, sequester held-out source/task families, remove
answer-bearing metadata, separate editable target text from the skill treatment,
freeze outcomes after pilot/power analysis, and include usage uncertainty and all
failed submissions. The current planner/scorer does not verify an externally
declared live execution or establish evaluator independence.

## Pull requests

[Draft PR #134: feat(runtime): add bounded OpenAI Agents API transport](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/134)
is stacked on #131. Its hosted receipts are the
[transport CI run](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/actions/runs/34544934850)
and [repository validation run](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/actions/runs/34544934795).
Green checks do not approve this PR or its predecessor train for merge.

The following existing descriptions were updated and then read back exactly.
All recorded heads remained unchanged; their original descriptions were preserved
with an appended runtime-direction section:

| PR | Unchanged head prefix | Scope of update |
| --- | --- | --- |
| [#121](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/121) | `aed122474c31` | Managed primary runtime and draft-versus-accepted distinction |
| [#122](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/122) | `0030fdbf8da0` | Bootstrap briefs are development inputs, not production scheduling |
| [#125](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/125) | `c50cc4cdbc0c` | Legacy Cursor benchmark limits are not the new product runtime |
| [#126](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/126) | `7c0c92d20244` | Preserve ambiguity/resume evidence without claiming owner integration |
| [#130](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/130) | `54580840f755` | Managed subagents do not confer evaluator/publication authority |
| [#131](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/131) | `c6cd52017b24` | Offline foundation and narrow transport follow-on |

The earlier inventory returned 35 open PRs before #134 was created. This iteration
does not claim a fresh code-level review or metadata update for every unrelated
open PR. The [reoriented PR plan](cloud-pr-plan-2026-09-10.md) preserves their
historical dispositions and the new delivery sequence.

## Launch blockers and next sequence

1. **Live protocol canary:** make an application project key available through
   `OPENAI_API_KEY`, with Agents read/write and Responses write permissions. Confirm
   an isolated project's hard spending control and approved public-data retention.
   Then run one supervised environment-free session and real recovery/cancel drills.
2. **Publish the integration closure:** isolate the reviewed research primitives,
   compiler/ledger and their dependencies in subsequent PRs. Do not publish the
   entire pre-existing dirty tree or claim #134 contains those components.
3. **Scientific evaluation:** connect fresh-session execution to the frozen paired
   plan, verify exposure separation and result/usage receipts, pilot the hypothesis,
   then preregister and run the independent held-out comparison.
4. **Source/tool integration:** connect arXiv, company research and an explicitly
   authorized X provider through a narrow source broker. Distinguish abstracts,
   full-text evidence and outages; test replay, limits and prompt-injection effects.
5. **Owner and operator integration:** global admission and session inventory,
   authenticated managed-session UI, unknown-create investigation, retention/deletion,
   source-to-frozen-candidate workflow, scoped GitHub App and notification outboxes.
6. **Cloud release:** review host/region/image/configuration, complete restart,
   off-host restore and rollback drills, verify cost and emergency-stop behavior,
   then obtain explicit human activation of the exact release.

No scoped application key was found in the process or either project-local `.env`
location inspected. No key value was logged. Do not paste a key into chat. A local
deadline is not a hard cloud spending ceiling, and a stopped supervisor does not
prove the remote session stopped. Production remains blocked, not silently enabled.

## Source identity for reproduction

Integrated base commit: `c6cd52017b247804373339e1c3c103d42554b0a1`, with local changes.
Measured implementation digest, Python 3.11.0 and installed dependency versions:
`sha256:f40d887fbceebb7ad710d259b7b64bf6cf6e49275a900bcee436b0e2a5e10a1f`.
This is the existing service implementation fingerprint, not a SPEC-003 freeze,
clean release commit, complete environment attestation or production authority.

| File | Exact SHA-256 |
| --- | --- |
| `researcher/service/openai_agents.py` | `38add7a3ca642a947fea2bab2d82bf9fb5f8e103ad18755d7d297a1e9fbb8f20` |
| `researcher/service/agents_context.py` | `9429236ab0d72302d2ee28e8783f558c38674f8e4979070a6cfa31a881d13394` |
| `researcher/service/agents_runtime.py` | `a8fa334ce0133518e648480a792f0f392de7f33882ed5583b91772e19cd13b12` |
| `researcher/service/agents_evals.py` | `f3ec092ed57d33e06319d8e9aa9e1b5d5324e7b4d8a1e3e1d0bda2e766398a6e` |
| `docs/product/spec-execution-plan.json` | `4c2d325dd6215794ff990af6c4b4239b5068063ed3e2636606a2f91f44bb5a84` |

For reproduction, run the commands in the canary runbook and the table's named
test suites with pinned dependencies. Private command logs are operational
receipts, not a published scientific dataset. A future release must publish a
reviewed source closure and reproducible evaluation artifacts separately.
