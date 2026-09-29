# LLM-as-a-Judge Skills

A standalone teaching example for direct scoring, rubric generation, and
position-swapped pairwise comparison. This is **not the production research
service**. That service lives in [researcher/service](../../researcher/service/).

## Execution status

Automatic live execution is disabled. Imports, `npm test`, and the legacy CLI
examples do not load `.env` or use ambient API keys. The legacy CLI examples
fail with an explicit migration message. A caller must construct and inject a
bounded `JudgeRuntime` to execute any provider call.

This package remains on AI SDK 4, which its
[official documentation](https://v4.ai-sdk.dev/docs/reference/ai-sdk-core/generate-text)
marks unsupported. The 2026-09-29 registry audit of the locked production graph
reported seven affected packages: five low, one moderate, one high. In particular,
the inherited `jsondiffpatch` version has a
[prototype-pollution advisory](https://github.com/advisories/GHSA-j4fx-xxwh-2485).
These dependency findings are not fixed by narrowing caret ranges to tilde ranges.
The lockfile preserves the tested graph; it is not a security clearance.

Do not deploy this package as a network service or supply production credentials.
Migrating to a supported SDK and re-running dependency, provider-contract, and
application tests is a separate release requirement. Production research runs
must use the repo-native service and its deployment/budget policy.

## Local safety boundary

Every tool and agent chat call goes through one runtime. A swapped comparison
consumes two separately admitted attempts. A generated-rubric workflow executes
rubrics sequentially, stops on a missing/invalid rubric, and only then scores.

`LocalAttemptBudget` creates an exclusive, fsynced slot **before** a provider
invocation. It never refunds a timeout, provider error, parse failure, or crashed
attempt. Independent cooperating processes using the same private directory
cannot admit more than its immutable attempt limit. A zero limit denies all work;
invalid, missing, corrupt, changed, or differently configured state fails closed.
Reopening the directory resumes the same budget. Creation never overwrites an
existing directory.

The runtime enforces input UTF-8 byte limits, an output-token request limit, an
abort signal, per-instance in-flight admission, `maxRetries: 0`, one SDK step,
and disabled SDK telemetry. It does not run model tools internally. Exported
`createEvaluationTools(runtime)` binds evaluation tools to the same runtime;
their calling/orchestrating agent must have its own bounded execution authority.

Important limits:

- This is an **attempt cap, not a dollar cap, token-accounting ledger, or
  account-wide spending limit**. Model prices, input tokenization, other API
  clients, and provider billing are not controlled here.
- The guarantee is scoped to cooperating callers and a trusted provider adapter
  that performs one request per SDK invocation. Arbitrary injected models or
  middleware can perform additional effects outside this contract.
- The ledger requires a trusted private local POSIX filesystem with reliable
  exclusive-create and file/directory fsync behavior. It is not a multi-host/NFS
  authority. Do not delete slots, roll back snapshots, share independent ledgers,
  or recreate the directory to resume a run.
- `maxConcurrent` applies to one runtime instance, not every process. The shared
  durable cap still limits total admitted attempts. Abort is not proof that the
  provider stopped or did not bill. A provider that ignores abort remains in
  flight until its promise settles; capacity is not released by a timeout race.
- These fake-provider tests verify orchestration and contracts, not judge
  accuracy, research quality, live endpoint compatibility, or production cost.

## Explicit construction

The library has no implicit live provider. For offline tests, inject a mock SDK
model. For a separately approved sandbox experiment after the dependency review,
the constructor shape is:

```typescript
import { JudgeRuntime, LocalAttemptBudget, EvaluatorAgent } from './src/index.js';

// Provision once in a trusted parent directory; creation refuses existing paths.
LocalAttemptBudget.create('/absolute/private/experiment-01', 3);

// On every subsequent process/run, reopen the same directory and the same limit.
const budget = new LocalAttemptBudget('/absolute/private/experiment-01', 3);
const runtime = new JudgeRuntime({
  model: explicitlyConstructedTrustedModel,
  budget,
  maxOutputTokens: 1024,
  maxInputBytes: 32_000,
  timeoutMs: 30_000,
  maxConcurrent: 1
});
const agent = new EvaluatorAgent({ runtime, temperature: 0 });
```

See [bounded-evaluation.ts](examples/bounded-evaluation.ts) for explicit OpenAI
provider construction without a top-level call or credential lookup. It is a
construction example, not a launch script or recommendation to use this
unsupported dependency graph.

Tools accept the same runtime as their second argument:

```typescript
await executeDirectScore(input, runtime);
await executePairwiseCompare(input, runtime);
await executeGenerateRubric(input, runtime);
```

Invalid inputs reject before spending. Unavailable or invalid tool judgments
return `success: false`; never treat their zero scores or `TIE` sentinel as
successful evaluations. Chat and failed generated-rubric workflows throw a
sanitized error. Output schemas reject mismatched/duplicate criteria, out-of-range
scores, and malformed rubrics. Swapped comparisons align criteria by name; when a
winner is required, position disagreement is a failed judgment, not an invented
winner. All criterion rubrics are included in the final scoring context.

## Verification

Use Node 24 for the recorded reproduction:

```sh
npm ci --ignore-scripts
npm test
npm run typecheck
npm run build
npm run lint
npm audit --omit=dev
```

Tests are deterministic and offline, have no test retries, and do not load
credentials. The final audit command currently fails for the known dependency
advisories above; this is expected evidence, not a suppressed gate.

Executed on 2026-09-29 with Node 24.19.0 after a clean offline
`npm ci --ignore-scripts`: **40 tests passed** (19 evaluation, 11 runtime,
10 ledger tests), source and test/example typechecks passed, TypeScript build
and ESLint passed. Twelve child processes produced exactly three admitted
effects under a three-attempt cap. All four legacy CLI entrypoints exited 1
with the disabled-execution message; importing the bounded constructor performed
no top-level work. No paid providers or credentials were used.

The 2026-09-29 before-fix fake-provider reproductions observed two calls from one
swapped comparison with no retry or output limits, and three actual SDK provider
invocations for one retryable failed score (two implicit retries). The replacement suite covers
per-pass admission, concurrent callers, independent processes, restart, timeout,
retryable error, corrupt policy, oversized input, malformed model output,
criterion alignment, zero weights, and generated-rubric workflow backpressure.

Resolved test graph: `ai 4.3.19`, `@ai-sdk/openai 1.3.24`,
`@ai-sdk/anthropic 1.2.12`, `zod 3.25.76`, `vitest 2.1.9`,
`typescript 5.9.3`. No dependency range was upgraded in this safety change.
The earlier 19 live tests and undated “production-ready” claims were replaced;
they were not a reproducible quality benchmark or evidence for this release.

## Structure

- `src/runtime/`: durable attempt admission and the sole SDK call boundary.
- `src/tools/evaluation/`: validated direct, pairwise, and rubric contracts.
- `src/agents/evaluator.ts`: shared-runtime workflows with backpressure.
- `tests/`: offline provider fixtures, fault cases, and multiprocess admission.
- `skills/`, `prompts/`, `tools/`, `agents/`: historical instructional material,
  not separately executable agents or a production deployment specification.

Background: [Eugene Yan's LLM evaluators survey](https://eugeneyan.com/writing/llm-evaluators/).
A generated rationale is not calibrated confidence, proof of correctness, or a
substitute for independent task-level evaluations.
