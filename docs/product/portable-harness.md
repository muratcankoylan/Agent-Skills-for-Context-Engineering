# Portable research improvement harness

Status: local development implementation plus proposed production architecture. This is an open-source component of Agent-Skills-for-Context-Engineering, not a Codex extension. It is not an accepted autonomous production runtime. See the [working plan](portable-harness-plan.md), [paper protocol](portable-harness-paper-protocol.md) and [dated verification results](portable-harness-results.md).

## Product and architecture

The product turns a research need into traceable source evidence, a falsifiable improvement hypothesis, a frozen candidate, an independently evaluated result and a reviewable repository change. Minimal oversight should mean reviewing exceptions and meaningful evidence, not trusting an agent's success narrative. Authority to publish, merge or deploy stays outside the candidate.

```text
research need -> bounded source retrieval -> immutable evidence/context
                                            |
                                            v
                                   hypothesis + experiment plan
                                            |
                                  restricted candidate proposal
                                            |
                                  freeze + isolated evaluation
                                            |
                              full results + comparison + report
                                            |
                             authority gate -> reviewed promotion
                                            |
                           regression monitoring / rollback evidence
```

This is the target flow. The current implemented vertical slice begins with an existing source campaign and ends with an inert data-policy proposal. It neither generates a research hypothesis nor applies a code/skill change. Reports retain failed and rejected variants. Codex, another agent runtime, CI or a terminal can operate the same CLI without becoming the authority boundary.

| Responsibility | Existing implementation | Production boundary still required |
| --- | --- | --- |
| Source acquisition | Bounded arXiv/company feeds and primary-text capture; strict X adapter | Live X access/entitlements and source-specific operational validation; licensing/retention |
| Context | Deduplicated work identities, full provenance, bounded packets, replay | Independently labeled relevance/coverage and downstream effectiveness |
| Proposal/search | Two predeclared JSON packet policies, finite enumeration | Accepted work/experiment contracts and bounded model adapter |
| Candidate integrity | Explicit editable surface, frozen tree, content-addressed bytes | Externally enforced worker isolation for executable candidates |
| Evaluation | Fixed deterministic score reconstruction and preservation checks | Sealed evaluation service, independent semantic labels, exposure accounting |
| State | Locked private intent/outcome/result files, verified resume | Accepted experiment lifecycle owner and recovery semantics |
| Interaction | CLI JSON/Markdown; existing local read-only observation UI | Authenticated experiment review/control UI; permissions and audit |
| Promotion | Inert proposal only | Human-accepted policy, independently authenticated promotion, rollback |

Use one coordinator and one durable state owner first. Add a queue or archive search only after measurement shows it pays for scheduling complexity. Multiple agent roles do not imply independent evaluation if they share an editable workspace, credentials or leaked tests.

## Research-informed choices

Search, candidate representation and evaluation should be independently replaceable, as in [ADAS](https://arxiv.org/html/2408.08435v2). We chose finite data-policy enumeration before model-driven archive search because the latter's incremental value here is unknown.

Protect measurement inputs as well as grader code: [DGM's reported reward-hacking failure](https://arxiv.org/html/2505.22954v2) makes that boundary consequential. The current evaluator reconstructs scores rather than accepting candidate-authored metrics. Start with machine-checkable properties, consistent with [AlphaEvolve's stated evaluation constraint](https://arxiv.org/html/2506.13131v1), without treating structural preservation as research quality.

An evaluator can itself improve, but only as a separate candidate evaluated against independently maintained anchors between fixed experiments. [RQGM](https://arxiv.org/pdf/2606.26294) motivates that separation; its preliminary findings do not establish this project's effectiveness. Log feedback exposure: a fixed hidden test is not immune to adaptive overfitting, as studied by [Dwork et al.](https://arxiv.org/html/1506.02629v2).

## Implemented experiment contract

`researcher/scripts/research_experiment.py` owns pure policy/dataset validation, packet evaluation and exact score reconstruction. `researcher/scripts/research_evolution.py` owns private persistence, candidate freezing, import/replay and CLI progression. Neither imports or executes candidate code. No model credentials are needed.

The editable policy is exactly `{"schema":"packet-policy/v1","compact":false}` or its true variant. The declared path `researcher/experiments/packet-policy.json` exists only inside each frozen candidate, not as a live configuration changed by this runner. Both policies are evaluated on all predeclared case/budget pairs. More selected works wins; at equal coverage, fewer packet bytes wins. Any regression rejects the variant; any unavailable comparison yields insufficient evidence. Equal results produce no improvement. This ordering is a development objective, not a relevance grader.

Every successful packet must preserve original text for selected works, complete expanded provenance, lane/failure visibility and the selected/omitted partition. If a complete reference packet cannot be constructed within the reference ceiling, the evaluation fails instead of claiming preservation. Group labels do not assert statistical independence.

Before effects, the plan bounds logical evaluation rows and input bytes. `max_seconds` is a cooperative run-invocation budget checked between bounded phases, including replay/report generation, not a process watchdog. Initial CLI input import is outside it; individual phases can overrun before the next check. Repeated deterministic verification work is not a new experimental sample and does not consume the logical-row count. Executable workers will require hard wall/CPU/memory/process/egress limits before activation.

The manifest binds input, policy, provenance, implementation/schema files and dependency/runtime identity. Resume rejects changed identities. An intent without an outcome is unknown, not retry permission. Verification replays frozen results and, for imported campaigns, the original locally captured evidence. Keep those original private captures available. Missing, malformed or aliased storage fails closed. This is integrity against accidental or cooperative mutation, not protection against a hostile process with the same OS user privileges.

All new experiment records are explicitly private and `authority: none`. Native candidate/freeze structures are reused, but no new accepted event kind, provider grant, production epoch or promotion is created. The local epoch label is a manifest binding, not a deployed release.

## Run locally without Codex

Use a clean repository checkout and Python environment with the repository's pinned development requirements. Current execution uses Unix file locks; Linux/macOS are targets, Windows is not verified. Run the checked-in deterministic fixture suite first:

```sh
python3 -m unittest researcher.scripts.tests.test_research_experiment researcher.scripts.tests.test_research_evolution
```

For actual previously captured source campaigns, supply absolute unaliased paths and a fresh ignored private runtime directory. These commands replay local bytes and make no new HTTP/model calls:

```sh
python3 researcher/scripts/research_evolution.py plan \
  --campaign /absolute/path/to/completed-campaign \
  --baseline-policy docs/product/packet-policy-baseline.json \
  --max-evaluations 6 --max-seconds 60
python3 researcher/scripts/research_evolution.py run \
  --campaign /absolute/path/to/completed-campaign \
  --baseline-policy docs/product/packet-policy-baseline.json \
  --max-evaluations 6 --max-seconds 60 \
  --runtime-dir /absolute/path/to/private-experiment
python3 researcher/scripts/research_evolution.py verify \
  --runtime-dir /absolute/path/to/private-experiment
```

Two campaigns require twelve logical rows at the default three byte budgets. `--input` instead accepts the strict fixture dataset contract and labels it unverified development input. The checked-in tests construct public synthetic examples and exercise the CLI from outside the checkout using the absolute script path. Fake source digests in fixtures never become verified capture provenance.

The CLI emits JSON on stdout, progress/errors on stderr, and writes `manifest.json`, private CAS, both `attempts/*/outcome.json`, `result.json` and `report.md`. `proposal_ready` means only that the bounded comparison favors the candidate. All candidate material remains inside that experiment directory. Do not publish private captures, absolute paths or manifests; prepare a licensed/redacted release projection separately.

## Production deployment and operator model

Recommended first deployment is a dedicated single-tenant Linux worker with encrypted persistent storage, a single coordinator writer, off-host backups and a separate read-only UI/API. This is an engineering recommendation, not provisioned infrastructure. Choose hosting based on measured isolation, region/data-retention and cost requirements; the product must not depend on a particular hosting/model vendor.

Source adapters run with scoped retrieval credentials and outbound allowlists. Future proposers run as bounded provider jobs. Executable candidates run in disposable unprivileged sandboxes with a read-only evaluator, no repository/cloud credentials and controlled tool/egress access. The release service alone holds repository write credentials. The coordinator records intent before dispatch, checks terminal outcomes before retry, and quarantines unknown outcomes. A scheduled tick admits eligible work under explicit budgets; it is not permission to merge or re-run uncertain paid jobs.

Keep deployment outside the data-only runner. Current launchd legacy entry points stay inert. The existing local observation schedule is a development aid and not the portable product scheduler. Do not use Codex heartbeats as the distributed orchestration layer. The current UI is useful for observed evidence, not an implemented experiment control plane. Add experiment comparison, all failures, next action, budgets, provenance, stop/recovery and rollback state after accepted owner contracts exist.

## Release sequence and acceptance gates

1. Accept work, experiment, evaluation and promotion ownership through the specification process; reuse canonical schemas rather than creating a parallel authority.
2. Package the provider-neutral coordinator and verify installation/CLI/state recovery in clean Linux and macOS environments. Prove lock behavior, interrupted-write recovery and backup restore. Do not label a local test run a soak test.
3. Accept one independently authenticated provider adapter and one isolated executor. Test cancellation, timeouts, duplicate delivery, denied tools, malformed output, missing receipts, credential isolation and cost ceilings before any model loop.
4. Run the preregistered, independently evaluated paper protocol on unseen research needs and downstream tasks. Require cost-adjusted improvement and acceptable human-review burden; report null/negative outcomes.
5. Add reviewed reversible promotion for a narrow data/document surface, with exact previous/new digests and rollback tests. Expand to code only after its own evidence and authorization. No autonomous merge is currently enabled or authorized.
6. Canary scheduled operation under explicit budgets, monitor stalled intents and missing outcomes, rehearse rollback/restore, then expand duration and scope. Scope and quantitative acceptance thresholds must be fixed before the canary.

The next uncertainty is not how many agents to launch. It is whether independently judged source-to-skill changes improve held-out task performance at an acceptable cost and review burden. That experiment must precede a claim of self-evolving research effectiveness.
