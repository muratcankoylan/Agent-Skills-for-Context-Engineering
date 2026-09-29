# Research integration verification

Date: 2026-09-29 UTC. Status: implemented local integration slice, not production
release approval. No specification acceptance state is advanced by this report.

## Outcome

Daily discovery and managed research now have a capture-verified, prepare-only
handoff. Independent discovery lanes can finish useful collection after a source
failure without forgetting an uncertain effect or repeating its request. The
README and [architecture](research-system-architecture-2026-09-29.md) describe the
standalone repository-owned product and distinguish it from a desktop automation.

The managed path still stops before independent frozen evaluation and delivery.
No paid managed session, GitHub write, notification, deployment, or recurring
activation was performed in this verification. No scientific-quality or
downstream skill-effectiveness result is claimed.

## Implemented boundaries

| Change | Executable contract |
| --- | --- |
| Source failure isolation | Expected dependency failures become durable source gaps; later independent lanes can run; request/cost reservations remain; unknown effects force reconciliation |
| Restart behavior | Interrupted retrieval can continue never-attempted lanes; completed observations replay; failed/unknown effects never automatically repeat; completed partial reports stay terminal |
| Capture-verified handoff | A read-only SQLite snapshot binds manifest, report, checkpoints and completed effects; discovery and primary captures replay; report and context projections are rebuilt |
| Research eligibility | Exact selected job, completed collection, every discovery lane observed, no unresolved effects, at least one primary-text card, matching fixture class, bounded age |
| Context transfer | Discovery/primary excerpt scopes, byte hashes, truncation, omissions, non-exhaustive coverage and explicit parent-paper links survive; private capture locators do not enter the model request |
| Research brief | Mechanism, target failure, assumptions, task/population, baseline, confounders, counterevidence and falsifiable held-out test are explicit prompt requirements; missing evidence requires abstention |
| Freshness | Default maximum window age two days, configurable up to seven; preparation and initial session submission both check age; this is not proof of source publication freshness |
| Managed API | Session-create accepts documented HTTP 201; known remote identity survives effective-policy rejection; programmatic tool calling is explicitly disabled |
| Credential loading | Managed CLI accepts an explicit private `--env-file`; missing/blank selected credentials cannot fall back to ambient values |

`retrieval_handoff.py` does not call a provider, reserve model spend, repair a
partial job, freeze a proposal or publish. A new private destination is required;
existing packets are never silently replaced. Duplicate-create protection is
per SessionLedger directory, not yet global deduplication across preparations.

## Deterministic and local runtime verification

On the frozen implementation, the complete service suite passed **558 tests in
27.215 seconds** in one root run. An independent agent also covered all 558;
its initial sandbox blocked 16 localhost-bind tests, which passed in an authorized
loopback-only rerun. Those were environment restrictions, not silently skipped tests.

Additional independently run checks:

- Source connector/search/sourcing/article/evidence/pipeline suites: **210 passed**.
- Control Center: **51 passed**, typecheck passed, production build passed;
  standalone runtime smoke test verified **9 static assets** and stopped its server.
- Strict repository validation: **0 errors, 0 warnings, 17 skills**.
- Reference platform validation: **17 skills, 4 local installation layouts**.
- Skill health: no flagged skills. This is a deterministic hygiene measure,
  not a quality or task-effectiveness benchmark.
- Inventory regenerated and checked: **344 records, 317 declared inputs**.
  Its declared-input digest is not a complete release identity.
- Stage 0 command: **2 executable checks passed**, **7 catalog entries validated**,
  **0 catalog scenarios executed**. Activation fixtures reported **23 passing cases**.
- Ruff for changed runtime/test modules and `git diff --check` passed.
- Production-readiness declaration validates without findings and remains
  **`production_ready: false` / `readiness: blocked`**.

The complete repository-script suite passed **1,149 tests in 206.137 seconds**.
It includes the separately checked source/evidence suites. Expected injected
failure diagnostics appeared in the log; the unittest result was `OK`.
Test counts overlap where suites were run independently; do not sum them into an
invented total or interpret unit-test success as provider or scientific validation.

### New failure scenarios

The committed tests exercise source timeout followed by healthy lanes, paid-source
reservation retention, crash/restart around partial reports, shared unresolved
source slots, all-source unavailability, replay corruption, clock rollback,
pause/budget barriers and unchanged native model/MCP/GitHub behavior.

Handoff cases use actual adapters, retained response bytes, parsers and replay,
with offline transports. They cover changed source URLs, source/effect/checkpoint
disagreement, altered primary text, report rehashing, missing checkpoints,
unexpected effects, fixture/live mixing, stale or future windows, no primary
evidence, duplicate destination, invalid parent links and post-preparation expiry.
Two title-free primary articles retain distinct parent mappings. These are
mechanism tests, not semantic relevance labels.

## Retained real-source replay

The earlier live `agent memory` collection was consumed without another network
request. arXiv and Hugging Face captures plus the primary HTML capture replayed
under the current loader. The resulting managed packet contains:

- 15 selected discovery rows and 2 primary-text excerpts from one primary card;
- explicit bounded/unapplied-window and continuation qualifiers;
- 79,940 canonical request bytes;
- `fixture: false`, local phase `prepared`, and no submission timestamp.

No source/model reservation changed. The earlier real timeout job was rejected
with `RETRIEVAL_HANDOFF_INCOMPLETE`.

Private source report digest:
`sha256:22fd72f36e9cfd162f6d3e7c2100eff07bcc250bca7ee59c61d67662ce8c7f13`.
Prepared packet digest:
`sha256:0d3ec7394adbfbc4a88132bf9f7b4003cd1e6579b99e9b25bfd6d88d15cdbd7f`.
These are private artifact identity references, not public download URLs or
evidence acceptance. Runtime captures and packet files remain gitignored.

## Fresh live retrieval scenarios

Both scenarios used one bounded page each from arXiv, HN and Hugging Face, with
up to two primary reads. They shared one Store and the same daily limits:
10 source requests per day, 5 per job, no models, no paid sources, no MCP and no
GitHub. Model and credential call sites were injected to fail if reached.

| Query | Observed rows: arXiv / HN / HF | Selected discovery / omitted | Primary result | Research handoff |
| --- | --- | --- | --- | --- |
| `context engineering` | 10 / 2 / 6 | 13 / 5 | Selected arXiv HTML returned captured HTTP 404; zero cards | Rejected: `RETRIEVAL_HANDOFF_PRIMARY_REQUIRED` |
| `agent memory` | 10 / 4 / 6 | 16 / 4 | One replay-verified card, no primary gaps | Eligible: 18 evidence rows |

The unavailable primary target was `https://arxiv.org/html/2609.34997v1`.
No alternate URL, PDF or paid extractor was silently invoked. This is a useful
negative result: successful discovery does not guarantee usable primary text.

The ledger retained **7 source-request reservations, 0 model calls and 0 paid
microUSD reservations**. The repeated company-feed request reused its completed
capture. An idle drain followed by Store/process restart added no work or charge.
These measurements are a short local canary, not an uptime, recall, billing or
month-long production simulation.

Reproduction commands for the checked local surfaces, from the repository root:

```sh
.venv/bin/python -m unittest discover -s researcher/service/tests -q -b
.venv/bin/python -m unittest discover -s researcher/scripts/tests -q
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python researcher/scripts/validate_platform_compat.py --require-reference-validator
.venv/bin/python researcher/scripts/validate_repo.py --strict
.venv/bin/python researcher/scripts/build_inventory.py --check
.venv/bin/python researcher/scripts/skill_health.py --strict --no-history
.venv/bin/python researcher/scripts/run_benchmarks.py --json
cd apps/control-center
npm run verify
```

The UI requires its declared Node runtime and already installed dependencies.
Local API/runtime tests need loopback binding permission. These commands do not
constitute the separately authorized live managed-agent test. Live source tests
must keep one declared config, Store, request ceiling and exact query/window;
the [daily runbook](../../researcher/service/DAILY_RETRIEVAL.md) describes admission.

## Research-driven API corrections

The OpenAI documentation review changed implementation, not just prose:

- The current [create reference](https://developers.openai.com/api/reference/python/resources/beta/subresources/agents/subresources/sessions/methods/create)
  documents HTTP 201. Rejecting it before retaining the session identity could
  orphan an actually created remote session. Regression tests reproduce that path.
- The [programmatic tool calling guide](https://developers.openai.com/api/docs/guides/tools-programmatic-tool-calling#agents-api)
  requires explicit disabling; an empty tool list is not a no-execution guarantee.
- [Project/organization spending controls](https://developers.openai.com/api/docs/guides/spend-limits)
  can be enforced but may overshoot. They are not a caller-configurable exact
  session cap. A local deadline/cancel acknowledgement is not proof of remote stop.

Old prepared packets with the previous tool policy intentionally fail request
recompilation. Prepare a new packet before a new authorized run; never recreate an
already attempted or uncertain remote session as a migration shortcut.

## Remaining launch blockers and next experiments

1. **Primary acquisition fallback.** Predeclare a bounded alternate-candidate or
   provider-extraction experiment for unavailable HTML; preserve provenance,
   authorization, request/cost caps and format-fidelity limitations. Do not relax
   evidence gates merely to improve completion rate.
2. **Managed live canary and spend containment.** Confirm isolated project policy
   and explicit cost-risk approval, then supervise one session with no PTC,
   external tools, vault, environment or subagents. Retain actual lifecycle,
   usage and cancellation evidence. No paid session was authorized by this report.
3. **One admission owner.** Link managed ledger/packet identities to Store-owned
   admission and a cumulative account/campaign budget. Local directories must
   not multiply spending authorization or create duplicate research runs.
4. **Independent measurement.** Execute fixed held-out no-skill/current/candidate
   comparisons against frozen artifacts; calibrate relevance/entailment labels,
   report missing/failed attempts, cost and variance. Self-critique is not a judge.
5. **Publication and deployment.** Complete candidate/corpus overlay validation,
   explicit GitHub delivery test, managed operator views, artifact-complete restore,
   reviewed cloud host/security configuration and real elapsed soak.

No deployment host, release identity or unattended budget is selected by this
change. See the architecture's G0–G6 gates and the existing
[deployment runbook](../../researcher/service/DEPLOYMENT.md) for the staged path.
