# Codex documentation and implementation audit

Date: 2026-09-29. Status: review findings, not release approval.

## Decision

The SDK choice and basic lifecycle are consistent with the documented Python
integration. The current implementation is not ready for an unrestricted
production-readiness claim. Four actionable findings remain: an incomplete
machine-configuration boundary, inaccurate token-detail telemetry, and two
operator recipes that no longer match the implementation.

This was a read-only runtime review with three independent reviewers. No runtime
code, credentials, provider configuration, PRs, services, or deployment state were
changed. The report is the only repository artifact added by this review. No paid
provider calls were made. Existing tests were rerun; new adversarial probes were
executed in disposable local environments. They are not yet regression tests in CI.

The official documentation was used to choose what to test, not as a substitute
for testing. A documented capability is not automatically enabled or appropriate
for this product.

## Reviewed implementation

- Checkout: `agent-skills-local-production`, branch `codex/local-production-rehearsal`.
- HEAD: `c6cd52017b247804373339e1c3c103d42554b0a1` plus the existing local integration.
- SDK and bundled CLI runtime: `0.159.0`, both independently checked.
- Current SDK implementation digest: `sha256:bf20e1fc185c7cec1f96f967866fb62e752e1b86bdd94dbe3220826a7c42d46b`.
- Core review surfaces: `codex_worker.py`, `codex_gateway.py`, `codex_campaign.py`,
  `codex_traces.py`, `codex_preflight.py`, `recovery_bundle.py`, Organization,
  pipeline/evaluation callers, deployment launcher/templates, CI, and operator docs.
- The digest above is the implementation digest produced by `CodexCampaign`, not
  a digest of the entire dirty worktree or a published release.

The supported initial profile is fresh, tool-free SDK threads with deterministic
retrieval outside the model. Researcher, critic, editor, and evaluation tasks are
separately orchestrated roles. This is not SDK-native subagent delegation, native
MCP tool use, autonomous shell execution, or automatic publication.

## Findings

### F1. P1: Close machine configuration before SDK startup

Location: [`codex_worker.py`](../../researcher/service/codex_worker.py), `_config`
at lines 242-272 and `_effective` at lines 306-330. Related:
[`codex_preflight.py`](../../researcher/service/codex_preflight.py), initialization
at lines 185-201; [`deploy/launch.py`](../../researcher/service/deploy/launch.py).

Private `HOME` and `CODEX_HOME` do not remove system configuration. The worker
disables selected features and verifies thread fields, but does not establish
that every loaded configuration layer is reviewed. Codex documents both system
defaults and separately enforced managed requirements. A local override must not
be assumed to override administrator policy. [Configuration precedence](https://learn.chatgpt.com/docs/config-file/config-basic#configuration-precedence),
[managed configuration](https://learn.chatgpt.com/docs/enterprise/managed-configuration).

Executed adversarial probes against the actual pinned worker:

| Injected container-local configuration | Observed effect | Worker result |
|---|---|---|
| System `config.toml` with inert MCP startup and `notify` commands | Both marker commands executed | `completed` |
| System `requirements.toml` pinning hooks on with a managed `SessionStart` hook | Hook marker executed despite local `features.hooks=false` | `completed` |
| System trace exporter pointing at an inert loopback collector | One observed `/v1/traces` POST, 735,676 bytes | `completed` |

The lead reviewer independently reran the managed-hook probe and observed the
same result, with one synthetic model request. The marker is named
`ambient-mcp-started`, but in this variant it was written by the hook, not MCP.

The telemetry variant also configured a metrics exporter, but metrics emission
was not observed. A synthetic prompt substring was not found in the captured
trace payload. Neither observation proves general prompt confidentiality.
`otel.exporter`, `otel.trace_exporter`, and `otel.metrics_exporter` are separate
settings; disabling the first does not disable the others. [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference),
[sample configuration](https://learn.chatgpt.com/docs/config-file/config-sample).

All probes used a non-root Linux ARM64 container, read-only root/source mounts,
all capabilities dropped, no-new-privileges, resource limits, and `--network none`.
Model traffic and the collector were loopback fixtures. No provider credential was
supplied. The immutable dependency image was:

`sha256:cca85eb9853e38a3007394a004e8fdbf95036c5630d3fb2787a46abb5f70e748`

This proves a deployment-configuration admission gap, not compromise of the
reviewed clean image. It requires a native host or image/mount configuration that
contains the injected settings. The model gateway cannot intercept command
execution at startup/completion or client-side telemetry outside its endpoint.

Required repair:

1. Define and verify the complete permitted configuration sources before SDK
   initialization. Refuse incompatible native/managed environments; do not bypass
   or overwrite administrator policy.
2. Bind the deployed immutable configuration namespace to the release identity.
   A file-existence check alone is not protection against hostile same-UID mutation.
3. Explicitly disable notifications and each exporter as defense in depth, then
   verify effective settings. These flags alone do not close managed overrides.
4. Promote all three probes to zero-network deployment regression tests, requiring
   refusal before any marker, collector request, or provider admission.

### F2. P2: Preserve observed token details instead of fabricating zeros

Location: [`codex_gateway.py`](../../researcher/service/codex_gateway.py),
`validate_stream` lines 156-168 and `sdk_stream` lines 175-183.

The gateway discards cache-read, cache-write, and reasoning token details from
the provider receipt. Its synthetic SDK stream then reports zero cached and
reasoning tokens. The campaign compares input/output totals only, so it accepts
the inaccurate detail fields.

Executed deterministic reproduction:

| Field | Synthetic provider response | SDK-visible replay |
|---|---:|---:|
| Input tokens | 20 | 20 |
| Cached input tokens | 8 | 0 |
| Cache-write input tokens | 6 | omitted |
| Output tokens | 10 | 10 |
| Reasoning output tokens | 7 | 0 |
| Total tokens | 30 | 30 |

This invalidates detailed cache/reasoning telemetry and prevents credible
cache-efficiency measurements. It does not demonstrate a budget escape: the
current conservative input rate includes the highest ordinary/cache-write rate,
and output accounting retains the total including reasoning. Current model
pricing and cache accounting were checked separately. [GPT-6 Sol pricing](https://developers.openai.com/api/docs/models/gpt-6-sol),
[prompt caching and usage](https://developers.openai.com/api/docs/guides/prompt-caching).

Required repair: validate, persist, and replay observed detail counts; represent
missing data explicitly rather than as measured zero. Version the durable receipt
contract and preserve compatibility with historical totals-only records. Test
nonzero details, missing details, invalid types, impossible subtotals, replay,
SDK agreement, and recovery. Keep conservative reservations separate from cost
estimates and invoices.

### F3. P2: Remove the retired live-research recipe

Location: [`service/README.md`](../../researcher/service/README.md), lines 168-190.

The current setup section still instructs an operator to configure model routes,
enqueue `evidence-transfer`, and run `researcher.service work --live`. However,
[`workflow.py`](../../researcher/service/workflow.py), lines 316-317, refuses new
built-in model execution with
`NATIVE_AGENT_EXECUTION_RETIRED_USE_CODEX_ORGANIZATION`. The earlier README warning
does not make this later executable recipe valid for new research.

Required repair: separate retrieval-only operations from historical receipt
compatibility, and route new research through the documented Organization plus
`CodexCampaign` flow. Add a secret-free documentation smoke test that follows the
new recipe into a synthetic SDK research turn. Do not revive the retired native
backend merely to make the old instructions work.

### F4. P2: Make native provisioning include the mandatory SDK closure

Location: [`DEPLOYMENT.md`](../../researcher/service/DEPLOYMENT.md), lines 120-128.

The numbered native provisioning recipe installs only the application venv.
It omits creation of the SDK venv and placement of its required lock. Meanwhile,
the launcher always validates `RESEARCH_CODEX_DEPENDENCY_LOCK`, and the systemd
templates reference that lock and the separate SDK interpreter. Following this
recipe alone cannot satisfy the launcher.

[`deploy/CODEX_RUNTIME.md`](../../researcher/service/deploy/CODEX_RUNTIME.md)
contains the separate SDK prerequisites, but the primary numbered recipe must
include or explicitly sequence them. Required repair: make the two-venv/lock setup
unambiguous, distinguish tool-free versus native-tool support, and test the exact
provisioning recipe in an empty non-root reference environment without credentials.

## What aligned with the documentation

- Python SDK selection avoids an unnecessary TypeScript service. The official
  Python package is documented as stable and includes a pinned CLI dependency.
  [SDK](https://learn.chatgpt.com/docs/codex-sdk).
- SDK-managed local initialization, thread/turn startup, event routing, explicit
  denial callbacks, and local structured-output validation match the inspected
  pinned package. Raw remote app-server transport has a different maturity and
  deployment contract. [App server](https://learn.chatgpt.com/docs/app-server).
- Provider credentials stay outside the SDK child. The fresh subprocess
  compensates for SDK environment merging. This does not establish host file
  secrecy against a process with the same UID. [Non-interactive automation](https://learn.chatgpt.com/docs/non-interactive-mode).
- A committed response receipt is written before model output reaches the SDK.
  Unknown outcomes retain reservations and do not authorize replacement turns.
  Restores remain paused. Local process termination is not claimed as proof of
  remote cancellation.
- `approval_policy=never` with a restrictive sandbox is intentional. Missing
  automatic approval review is not itself a defect; product-side approval review
  is not protection for arbitrary custom tools. [Agent security](https://learn.chatgpt.com/docs/agent-approvals-security),
  [custom-harness safeguards](https://learn.chatgpt.com/docs/cyber-safety/recommended-configuration).
- Native web search is explicitly disabled. Hosted search, command networking,
  MCP, and client telemetry are separate surfaces, not one shared network switch.
  [Web search](https://learn.chatgpt.com/docs/web-search).
- No removed `codex mcp-server` dependency was found in this integration. External
  MCP tools and hosting Codex as an MCP server are different capabilities.
  [Removal notice](https://learn.chatgpt.com/docs/mcp-server).
- GitHub CI validates candidates without production secrets. The official Action
  is not required to use the SDK, and hosted Codex cloud is not the deployment
  target of this standalone service. [GitHub Action](https://learn.chatgpt.com/docs/github-action),
  [Codex cloud](https://learn.chatgpt.com/docs/cloud).

## Product completeness beyond SDK compliance

These are material gaps against the intended living research organization, not
evidence that the SDK itself is malfunctioning:

1. **Cross-run research learning is not wired into the SDK pipeline.** The bounded
   `Store.prior_feedback` archive and `Store.candidate_seen` exact-byte suppression
   still have their production callers in the retired native `workflow.py`.
   The SDK researcher receives the current evidence/corpus packet, and
   `research_pipeline.py` proceeds from a new proposal directly to candidate
   review. Organization deduplicates source-job identity, not identical proposals
   produced by different daily jobs. The next slice should bind verified prior
   hypotheses to researcher-only context and suppress identical frozen candidate
   bytes before repeating expensive evaluation. Keep gold labels and judge
   feedback out of the researcher archive; exact duplication is not semantic
   novelty detection.
2. **Publication is deliberately disconnected.** Organization rejects publication
   capabilities and the evaluated path ends at `evaluated_not_accepted`. A
   separately authorized, source-bound proposal handoff is still needed for the
   intended reviewable PR loop. Automatic merge is not implied.
3. **The UI does not yet show the complete organization.** The implemented
   `apps/control-center/lib/service-reader.server.ts` reads one Store status
   projection. It does not combine Organization outcomes, SDK reconciliation,
   candidate dossiers, and evaluation evidence. The UI README also retains an
   older proposed launchd/GKE architecture. A combined authenticated read model
   and explicit pause/reconciliation workflow are needed before calling this a
   complete operator interface.
4. **Skill effectiveness and native skill routing are different experiments.**
   Current paired evaluation explicitly supplies frozen skill text. That can test
   the supplied content, but cannot measure native description routing,
   progressive reference loading, or agent-driven retrieval. Those require
   separate controlled evaluation arms. [Skill loading](https://learn.chatgpt.com/docs/build-skills).

## Avoiding false-positive migrations

Rolling documentation uses `collabToolCall`, while the pinned generated schema
uses `collabAgentToolCall`. The implementation matches its pinned schema. Do not
rename event types from current docs without upgrading and testing the runtime.

Current skill docs recommend `.agents/skills`. A credential-free discovery probe
against `0.159.0` found the test skill in both `.agents/skills` and `.codex/skills`,
one enabled skill in each case. Therefore the latter README path was not reported
as a broken installation. Canonical-path modernization and a Codex-specific plugin
packaging test remain useful follow-up work. The repository's generic
`.plugin/plugin.json` recipe was not proven equivalent to current Codex plugin
packaging by this audit. [Build skills](https://learn.chatgpt.com/docs/build-skills),
[plugins](https://learn.chatgpt.com/docs/plugins).

The pinned model was not changed merely because another model exists. No SDK,
dependency, permission-profile, or transport upgrade was made speculatively.

## Verification performed in this review

| Check | Observed result | Scope |
|---|---|---|
| Worker, SDK traces, SDK recovery suites | 66 passed, zero skips, 27.966 seconds | Real pinned SDK with synthetic loopback responses |
| Campaign, adversarial gateway, pipeline, Organization, preflight suites | 58 passed, zero skips, 38.750 seconds | Real pinned SDK where opted in; deterministic/loopback fixtures |
| Ambient MCP plus notification probe | Both commands executed | Negative evidence for configuration isolation |
| Managed hook probe plus independent rerun | Hook executed in both runs | Negative evidence for managed-layer isolation |
| Ambient OTel probe | Local trace POST observed | Negative evidence for exporter isolation |
| Token-detail projection probe | Nonzero details replaced/omitted | Negative evidence for telemetry fidelity |
| Skill discovery probe | Both directory spellings discovered | No inference, thread, or turn |

The two suite selections are disjoint: **124 tests passed**. Their success does
not negate the newly reproduced failures. Earlier 997-test and Linux rehearsal
results remain dated evidence in the migration report; they were not rerun in
full or represented as fresh results here. No live model-quality test, connector
canary, provider-invoice reconciliation, hosted CI run, production soak, or PR
publication was performed.

Reproduction commands for the existing suites, from the reviewed checkout:

```sh
CODEX_WORKER_TEST_PYTHON=/absolute/pinned-sdk-venv/bin/python \
  .venv/bin/python -B -m unittest \
  researcher.service.tests.test_codex_worker \
  researcher.service.tests.test_codex_traces \
  researcher.service.tests.test_codex_recovery -q

CODEX_WORKER_TEST_PYTHON=/absolute/pinned-sdk-venv/bin/python \
  .venv/bin/python -B -m unittest \
  researcher.service.tests.test_codex_campaign \
  researcher.service.tests.test_codex_gateway_adversarial \
  researcher.service.tests.test_codex_pipeline \
  researcher.service.tests.test_codex_organization \
  researcher.service.tests.test_codex_preflight -q
```

Use a clean environment with no provider credentials. The supervisor environment
must include the repository's reference validator. Running without the explicit
SDK interpreter can skip integration tests and is not equivalent evidence.

## Documentation coverage and limitations

The complete official [documentation index](https://learn.chatgpt.com/docs/llms.txt)
was surveyed. It combines ChatGPT, desktop, Codex, administration, and separate
security products. This audit examined **43 relevant documentation pages** below,
plus the current model-pricing and prompt-caching references. Full Markdown pages
were fetched; large configuration references were reviewed for applicable fields,
not certified line-by-line for unrelated UI settings. This is not a claim to have
validated every feature in the entire combined documentation collection.

| Review area | Pages under `https://learn.chatgpt.com/docs/` |
|---|---|
| SDK/lifecycle | `codex-sdk`, `app-server`, `non-interactive-mode`, `feature-maturity`, `mcp-server` |
| Configuration | `config-file/config-basic`, `config-file/config-advanced`, `config-file/config-reference`, `config-file/config-sample`, `config-file/environment-variables` |
| Authentication/security | `auth`, `permissions`, `permission-modes`, `sandboxing`, `sandboxing/auto-review`, `agent-approvals-security`, `enterprise/managed-configuration`, `cyber-safety/recommended-configuration` |
| Instructions/extensions | `agent-configuration/agents-md`, `agent-configuration/subagents`, `agent-configuration/rules`, `agent-configuration/speed`, `build-skills`, `skills-and-plugins`, `plugins`, `extend/mcp`, `hooks`, `web-search` |
| Product/automation | `open-source`, `github-action`, `third-party/github`, `cloud`, `cloud/internet-access`, `environments/cloud-environment`, `long-running-work` |
| Local workflows | `codex/cli`, `cli-customization`, `developer-commands`, `prompting`, `code-review`, `environments/modes`, `environments/local-environment`, `environments/git-worktrees` |

The `developer-commands` Markdown contains dynamic table placeholders. Its
available prose was reviewed; unrendered tables were not treated as verified flag
definitions. Version-sensitive behavior was checked against the installed SDK.

Not implementation dependencies and not separately audited: desktop/browser/voice
UX, pets, Sites, unrelated third-party workspace integrations, Windows/WSL setup,
ChatGPT organization administration beyond applicable managed configuration,
Bedrock authentication, and the separate Codex Security product. Their presence
in the index is not a requirement to install or enable them for this service.

## Ordered closure criteria

1. Repair F1 at the deployment/worker configuration boundary and add negative
   startup probes. Do not grant extra privileges or ignore managed policy.
2. Repair F2 with versioned usage receipts, migration/replay coverage, and accurate
   unknown-value semantics. Only then measure cache optimizations.
3. Repair F3/F4 and exercise the documented commands from clean environments.
4. Re-run the full deterministic release gates and hardened Linux SDK tests on
   the resulting frozen revision with zero skipped required tests.
5. Separately authorize and preregister a bounded live SDK canary using the
   existing cumulative budget authority. Record provider failures, real quality,
   latency, detailed usage, and recovery behavior before any larger soak.
6. Complete the cross-run archive, duplicate suppression, proposal handoff, and
   operator read model as individually tested capabilities before evaluating the
   broader self-improving-organization claim.

Tool grants, SDK-native delegation, autonomous publication, and broader cloud
operation remain separate staged architecture work. Enabling all Codex features
would not by itself deliver the intended self-improving research organization.
