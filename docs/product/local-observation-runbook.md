# Local observation runbook

Status: supervised engineering experiment, not a deployment activation

The current architecture and open gates are in [the September review](architecture-review-2026-09-07.md). This runbook retains the v2 local rehearsal instructions. For the newer captured-source/context/report path and actual local UI summaries, use [the research observation pipeline](research-observation-pipeline.md). Neither enables legacy launchd, models, promotions, contact enrichment, or GitHub writes.

## Run and inspect

From the integration repository, use Python 3.12 with the pinned validation dependencies installed. A run with no arguments creates a timestamped private directory beneath `researcher/runtime/`:

```sh
python researcher/scripts/local_rehearsal.py --help
python researcher/scripts/local_rehearsal.py \
  --query 'context engineering' --live-public
```

The live scenario observes arXiv for the first supplied query, repository commits through GitHub API and Atom, and a bounded Hacker News story window. Additional supplied queries currently exercise manual fixtures only. To evaluate different public queries, make separate runs. An empty bounded HN result is not a claim that the site contains no relevant work.

Read `rehearsal-report.json`, `input-manifest.json`, and the stage/prompt artifacts in the reported runtime directory. Check `harness_execution_ok` separately from `requested_connector_observations_ok`, each source's status and receipt, and the explicit blockers. A zero process exit indicates that the bounded harness completed, not that all sources were available, findings were useful, or the product is ready. `--require-ready` always exits nonzero for this preparatory runtime.

The three stages are serial dependencies: source observation, adversarial contract fixtures, and builder prompt compilation. Each predecessor must have a validated artifact before the successor is scheduled. Scheduler state is SQLite and all run files are private, ignored outputs. Successful replay verifies input, artifact, and scheduler bindings; it does not perform another retrieval.

For a replay, pass the same runtime directory, original `observed_at`, queries, and network flags. A changed source/configuration identity, missing artifact, or tampered receipt must fail. Use a fresh directory for a changed input or a fresh observation. Do not edit manifests to make a stale replay pass, and do not convert a v1 runtime in place.

## Bounded stress and real elapsed observation

```sh
python researcher/scripts/local_rehearsal.py \
  --query 'context engineering' \
  --soak-iterations 100 --max-seconds 60
```

This is offline repeated-cycle/replay stress. `--max-seconds` bounds admission of stress iterations, not live-provider request duration. It must not be described as 100 hours, a research-quality benchmark, or continuous process uptime.

The maintainer requested prolonged operation. A Codex task named **Context research local observation** is configured for 72 hourly wakes attached to the current task. It performs fresh bounded public observations and records actual timestamps, successes, failures, and input identities. It is separate from the repository scheduler and is dependent on Codex task execution availability. It does not install OS cron or an always-running daemon. Missed wakes must remain visible; do not synthesize backdated observations.

Each observation should record the start and finish time, actual elapsed span, query, source requests/bytes/yield/failures, source/code/config identities, model and paid call counts, and evidence locations. Append observations to a private, locked, atomic ledger or retain immutable per-run files and rebuild the summary from them. Never count replay as a new live cycle. Keep inactive time separate from execution time.

Pause or delete the named scheduled task in Codex to stop future observations. Interrupting a local invocation must propagate cancellation; a later matching replay may recover an abandoned lease and the artifact-before-completion crash gap. Recovery tests validate these mechanics, not a production service-level objective.

## Credentials and scientific execution

Do not paste secrets into reports or chat. Supply the location of an existing environment file or a Keychain-backed launcher when credentialed testing is needed. A credential's presence is not authorization to call a provider and does not implement the missing live adapter. The paid SDK path remains dry-run-only. The rehearsal never invokes a model, independent evaluator, or paper experiment.

X is opt-in in the legacy rehearsal and has a separate provider/credential boundary; it remains disabled in sourcing campaigns. Contact enrichment has no implementation. The observation pipeline captures exact discovery-response bytes. The [sourcing harness](sourcing-research/report-source.md) additionally reads explicitly selected primary HTML pages, without claiming complete paper verification or accepted scientific evidence. It can re-extract retained captures offline after a parser fix while preserving the original failure. Model-assisted research, independent critique, benchmark promotion, and deployment require their reviewed interfaces and accepted owner contracts before activation.

## Deployment direction

Keep the first supervised control plane local: one supervisor, one canonical transactional state boundary, immutable artifacts, and a read-only operator projection. The current scheduler and journal are not yet that unified boundary. The UI now has a separate opt-in `/observations` local summary view; the remaining control pages still render fixtures. Do not expose this pilot as a hosted control plane.

For a hosted beta, [the deployment proposal](deployment.md) separates a private authenticated UI/API, durable orchestration/state, and one isolated worker per untrusted attempt. Provider selection, residency, budget, accepted runtime contracts, and recovery/isolation evidence remain open gates. No cloud environment was activated by this review.
