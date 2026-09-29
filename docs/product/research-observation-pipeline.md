# Captured research observation pipeline

Status: local, supervised, observation-only implementation. Not an activated research organization.

For multi-source research use the [sourcing harness and research record](sourcing-research/report-source.md). `research_sourcing.py` adds explicit query lanes, shared caching/spacing, publisher feeds, identity pooling and selected primary HTML reads. This page describes its lower-level per-lane observation primitive, which does not itself enforce campaign-wide arXiv policy.

## Executable path

```text
explicit question + skill selection + bounded source configuration
  -> context pack with byte budget, source hashes and explicit omissions
  -> one locally leased observation work order
  -> bounded source adapters -> private immutable HTTP response captures
  -> source checkpoints -> offline parser verification
  -> report.md + structured research-handoff.json
  -> verified, read-only local UI summary
```

`researcher/scripts/research_pipeline.py` composes existing local scheduler primitives with `research_context.py`, `source_connectors.py`, and `research_evidence.py`. SQLite owns completion of this observation work order. Its result binds the exact observation artifact; that artifact binds the context, source checkpoints, report and handoff. It does not accept organization work, research claims, a mechanism, or a skill update. The separate organization event journal is not silently dual-written.

The pipeline has no model executor. Its prompt packet is inert data intended for a separately authorized researcher and independent critic. The final status is `awaiting_researcher` or `partial`, never `research_accepted`. A complete transport observation can contain zero relevant leads. An abstract is not full-paper evidence. Report assembly is not scientific synthesis.

## Run locally

Use Python 3.12 with the repository's pinned validation dependencies. Create the private parent once, then select a fresh child for each new observation:

```sh
mkdir -p researcher/runtime
python researcher/scripts/research_pipeline.py observe \
  --runtime-dir researcher/runtime/context-memory-observation \
  --query 'agent memory context compression' \
  --skill context-fundamentals --skill context-optimization \
  --source arxiv --arxiv-scope title_abstract --live-public
```

An identical invocation verifies or resumes that run. A changed implementation, query, source configuration or context pack requires a new directory. Never edit manifests to make old inputs match. Missing/tampered completed artifacts fail instead of being silently regenerated. After a process dies during retrieval, the written intent makes the external outcome explicitly unknown. Automatic duplicate retrieval is refused; inspect captures and choose a new run if another observation is warranted. A crash after durable output but before scheduler completion can resume without retrieving again.

ArXiv, GitHub and Hacker News observations are limited to three leads, eight HTTP attempts, one page, 500,000 response bytes, 15 seconds and two redirects. Registered publisher feeds instead allow twenty entries, one attempt and no redirects under the same byte/time caps. Providers can still fail or return incomplete data. No automatic provider retry sleeps, query fan-out or model calls occur in this primitive. A timed-out capture worker may finish an unreferenced immutable orphan; it cannot mutate an already-published source record.

Supported pipeline sources:

| Source | Meaning of the observation |
| --- | --- |
| `arxiv` | Bounded query over arXiv discovery metadata and abstracts, not downloaded full papers |
| `github` | Latest commits from this repository; the research question is not a GitHub search query |
| `hacker_news` | Local filtering of a bounded current story window, not exhaustive site search |
| `deepmind`, `huggingface`, `microsoft_research` | Registered publisher-feed windows; no provider-side topic query or claim of exhaustive company coverage |

The underlying connector module also provides generic RSS/Atom and gated X adapters. This pipeline deliberately does not expose arbitrary URL fetching, X, contact enrichment, private resources, or credential-bearing connectors. Adding a source requires a narrow adapter, budgets, capture/replay tests and explicit data/credential policy. Do not treat a nonempty source result as relevance or novelty evidence. `--include-provenance` opts arXiv into enriched metadata; `--arxiv-sort relevance|submittedDate|lastUpdatedDate` separates relevance, submission recency and updates. Defaults preserve historical parser output for replay.

arXiv search scope and matching are explicit: `--arxiv-scope all|title_abstract` and `--arxiv-match terms|phrase`. Defaults preserve all-field conjunctive terms. Title/abstract scope excludes author/comment/journal-only matches; phrase matching is narrower and can lose relevant paraphrases. These use the API's [documented field, Boolean and phrase operators](https://info.arxiv.org/help/api/user-manual.html#51-details-of-query-construction), not a topical keyword blacklist. In automated runs, space arXiv requests by at least three seconds and reuse a given query's daily capture unless a deliberate new development observation is needed. The [API manual](https://info.arxiv.org/help/api/user-manual.html#3311-title-id-link-and-updated) describes daily feed updates; repeated hourly requests are not evidence of new research.

## Inspect actual observations

Publish completed live runs to one private summary file:

```sh
python researcher/scripts/research_pipeline.py publish-view \
  --run-dir researcher/runtime/context-memory-observation \
  --output researcher/runtime/local-observation-view.json
```

Publication verifies completed artifacts and response bodies. It cannot trigger retrieval or resume an unfinished work order. Fixture runs are rejected. Historical completed outputs retain their original code/context identity; display does not imply they were produced by today's revision.

Build and start `apps/control-center` with a verified Node 22 runtime, then configure the server-only file adapter:

```sh
npm run build
HOSTNAME=127.0.0.1 PORT=3100 \
RESEARCH_OBSERVATIONS_ENABLED=1 \
RESEARCH_OBSERVATION_FILE=/absolute/private/path/local-observation-view.json \
npm start
```

Open `http://127.0.0.1:3100/observations`. The default is disabled. The app rejects non-loopback request hosts, invalid/oversized/aliased files, duplicate/unknown fields and false model/production claims. It displays current/stale/missing/invalid status, actual timestamps, lead/capture/context counts and unresolved work. More than two hours old is stale. Captured response bodies, filesystem locations and credentials are not exposed. Keep credentials out of the operator query itself; the query is deliberately visible in this private UI.

Other UI routes remain clearly labeled fixtures. There are no live mutation buttons, public ingress, authentication system, promotion controls or deployment activation. Loopback restriction is local containment, not hosted authorization.

## Verification and the improvement loop

```sh
python -m unittest researcher.scripts.tests.test_research_pipeline
python -m unittest researcher.scripts.tests.test_research_evidence
python -m unittest researcher.scripts.tests.test_source_connectors
python -m unittest researcher.scripts.tests.test_research_context
python researcher/scripts/research_context.py --benchmark
```

The context benchmark measures explicit selection, whole-section packing, overlap deduplication, source binding and failure behavior. It does not measure semantic retrieval, model routing, research novelty or skill effectiveness. Source replay verifies that derived leads match captured bytes, not that provider statements are true. Checksums provide local tamper evidence, not authenticity against an operator who can rewrite every artifact and database.

`source_files` counts local corpus/provenance files, not independent research sources. `claims_retained` counts registry records, not supported claims. The byte budget covers `model_context`, not the entire prompt or token window; section omissions preclude claiming complete skill activation. Discovery redirects and HTTP-date rate limits currently lack enough retained metadata for exact offline replay, so those sources retain captures but fail explicitly rather than publishing unverifiable leads.

For a real skill experiment, use the handoff to define a falsifiable mechanism, existing-corpus overlap, counterevidence and baseline/candidate/control tasks. Freeze the editable surface and scoring inputs before an independently executed evaluation. Preserve negative and inconclusive outcomes. Only a separately reviewed proposal may update all required skill/corpus/claim/mechanism/activation surfaces. No public skill text should change just to make a synthetic benchmark green.

The paid Cursor runner remains zero-call until its existing provider/authorization gates are satisfied. Credential presence alone is not readiness. Supply an existing environment-file location or Keychain launcher, never paste secret values. This observation pipeline does not call a substitute model provider to bypass those gates.

## Scheduling, deployment and stopping

The Codex task **Context research local observation** is the currently configured hourly wakeup mechanism. It is not OS cron, launchd activation or continuous process uptime. Each wake can create one fresh run, verify it and rebuild the local view. Count actual fresh runs and elapsed observation times, not replay executions or promised schedule occurrences. Pause that Codex task to stop future observations; stop the UI process to stop serving the view.

The immediate deployment target is this supervised local pilot: deterministic Python work and the read-only Next server on loopback. Untrusted source text is data, never executed code. Keep model/tool execution disabled until an accepted isolated executor and provider contract exist. The hosted direction and unresolved decisions are in [deployment.md](deployment.md): authenticated private control plane, one canonical state boundary, isolated untrusted attempts, typed result return, measured canary, backup/restore and rollback. No cloud environment or hosted service is activated by this slice.
