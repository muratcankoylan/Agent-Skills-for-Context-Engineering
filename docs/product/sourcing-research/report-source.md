# Research sourcing: evidence-led harness revision

Status: local supervised implementation, not production activation. Research reviewed September 7, 2026. This is the canonical design/research source; see the [measured execution results](results-2026-09-07.md). “Sources” means research content, not contact enrichment.

## Objective and decision

Improve the chain from a research question to inspectable primary evidence. Transport success, candidate discovery, semantic relevance, claim support and independent corroboration are separate outcomes. More HTTP requests or more agents do not establish improvement.

The existing path used one literal arXiv query sorted by submission time, discarded useful source metadata, did not integrate company feeds, and could not read a selected primary page. We retain the existing private capture store, deterministic parser replay and local scheduler. We add explicit query lanes and a bounded evidence packet, not a new vector database, model router or always-running service.

The working hypotheses were: (H1) explicit mechanism-oriented queries can expose different relevant work; (H2) recency-only search misses useful older work; (H3) social and company posts are best treated as leads to primary evidence; (H4) claim verification needs more than an abstract. H1 remains a semantic experiment, not a measured result of this implementation.

## Evidence that changed the design

| Primary source | Finding and limits | Design consequence |
| --- | --- | --- |
| [LitSearch, Ajith et al., 2024](https://arxiv.org/html/2407.18940v2) | Full-text methods, tables and limitations reviewed. Citation expansion helped some weaker retrieval configurations but not all stronger ones; citation-derived query construction affected measured gains. The benchmark is a bounded ML/NLP corpus with incomplete relevance coverage. | Preserve the original query control. Do not make citation expansion the default or claim every linked paper is relevant. Full-paper reading for support is a different task from document ranking. |
| [CSFCube, Mysore et al., 2021](https://arxiv.org/html/2103.12906v3) | Full-text protocol and appendices reviewed. Background, method and result relevance differ; a shared topic is not necessarily a shared mechanism. Multiple queries can share an underlying paper, and annotation disagreement matters. | Record each lane's mechanism/facet. Evaluate by underlying information need, not by counting paraphrases as independent trials. Citation edges are discovery hints. |
| [Query2doc, Wang et al., 2023](https://arxiv.org/html/2303.07678v2) | Full-text experiments reviewed. Generated expansion had mixed cross-domain effects; removing the original query could hurt. Pseudo-documents can contain factual errors and add latency. | No hidden model-generated expansion, new paid API, or factual pseudo-evidence. Explicit operator-selected variants remain inspectable and separately ablatable. |
| [arXiv API manual](https://info.arxiv.org/help/api/user-manual.html) and [API terms](https://info.arxiv.org/help/api/tou.html) | Title/abstract scope, sort variants, metadata and paging are documented. APIs require a single connection and request spacing; identical daily queries should be cached. Metadata and paper-content redistribution have different permissions. | Preserve versions and separate publication/update dates. Shared campaign cache and policy reservation, no unbounded parallel fetching. Store full text privately; do not republish it. |
| [X endpoint reference](https://docs.x.com/x-api/posts/search-recent-posts) versus [X data dictionary](https://docs.x.com/x-api/fundamentals/data-dictionary) | Official pages disagree on `post.fields`/`note_post` versus `tweet.fields`/`note_tweet`. Entities expose outbound URLs; long-form text is distinct from the short post body. | Preserve old default wire behavior, support strict optional aliases, request rich fields only in the explicit enriched legacy path, and label that contract live-unverified. No automatic alternative-dialect retry. |
| [X pricing](https://docs.x.com/x-api/getting-started/pricing) and [search introduction](https://docs.x.com/x-api/posts/search/introduction) | Search is limited by window/access and bills returned resources, not merely request count. | Staged queries do not execute. Authenticated testing needs an accepted adapter, resource-based cost reservation and explicit credential provisioning. |

Primary full-text readings informed the comparison, not an assertion that these methods are best for this corpus. The separate claim ledger identifies facts, reported results and engineering judgments.

## Alternatives and unresolved gaps

| Approach | Benefit | Why selected or deferred |
| --- | --- | --- |
| Explicit query/facet lanes + existing connectors | Small, auditable, cheap to compare, no new inference surface | Selected. A bounded candidate pool is useful even before semantic grading exists. |
| Automatic citation snowballing | May find differently worded work | Deferred until a verified citation source and matched-budget ablation exist. Citation membership is not a relevance label. |
| LLM query expansion or reranking | Potential semantic recall/ranking benefit | Deferred under the current zero-call boundary; requires drift controls and measured benefit. |
| New dense index over papers | Reusable semantic search | Deferred. Index freshness, licensing, embeddings and operations are unjustified before measuring the simpler path. |

The current harness has no exhaustive company-site search, authenticated X canary, PDF fallback, automated scientific adjudication, or accepted skill promotion. Missing HTML or an unsupported page boundary is an explicit failure, not an excuse to invent evidence. Feeds are bounded publisher windows, not search engines. Hugging Face includes community/partner material; publisher affiliation is not independent verification.

## Implemented data path

```text
explicit question + skill IDs + purpose-labeled query lanes
  -> bounded plan and source budget
  -> shared private cache + arXiv reservation/spacing
  -> existing scheduler/captured-observation pipeline per lane
  -> replay-verified leads, publication/version metadata
  -> exact-identity pooling + lane-round-robin whole-work selection
  -> provenance index + bounded discovery packet + explicit omissions
  -> operator selects a discovered primary URL
  -> bounded inert HTML extraction + raw capture + extracted-text spans
  -> researcher/evaluator handoff, with no acceptance authority
```

ArXiv work versions share a work identity while each original version and occurrence remains recorded. Unrelated papers are not merged by title similarity. Repeated appearances are not independent corroboration. Outbound URLs remain untrusted pending leads. Packet selection is budgeted round-robin, not a learned relevance ranking.

RSS/Atom enrichment selects full inline content when present, handles XML Base, and records truncation and content scope. It does not equate a blog's HTML with the underlying paper. Primary reads select a single article/main boundary, exclude executable/navigation content, never run JavaScript, never follow outbound links, and bind both raw bytes and extracted-text spans. Extracted spans are not raw-HTML byte offsets.

The checked-in brief opts into `compact: true`, producing a `local-research-discovery/v2` packet. Each occurrence references shared lane/source provenance instead of repeating it. `expand_discovery_provenance` reconstructs the original work index exactly; selected work text is unchanged. The default remains v1 for existing callers and frozen packet identities. Byte accounting is incremental and exact, with whole-work omissions recorded explicitly. These are context-capacity and packing-cost improvements, not semantic-ranking improvements.

## Operational use

Run from the integration checkout with its Python environment. Inspect `example-brief.json` before execution; variants are deliberate research hypotheses, not generated keyword lists.

```sh
python researcher/scripts/research_sourcing.py plan --brief docs/product/sourcing-research/example-brief.json
python researcher/scripts/research_sourcing.py run --brief docs/product/sourcing-research/example-brief.json --runtime-dir researcher/runtime/my-sourcing-campaign --live-public
python researcher/scripts/research_sourcing.py read --runtime-dir researcher/runtime/my-sourcing-campaign --url https://arxiv.org/html/EXACT-DISCOVERED-ID --live-public
python researcher/scripts/research_sourcing.py reextract --runtime-dir researcher/runtime/my-sourcing-campaign --url https://arxiv.org/html/EXACT-DISCOVERED-ID
```

The runtime parent must already exist. Campaign/cache directories must be owner-only. `read` accepts only a verified discovered URL or the HTML representation of the exact discovered arXiv version, then applies its separate strict host/path/DNS policy. The placeholder above is not a valid fetch target.

`reextract` has no network path. It writes a separate artifact binding the original read result and retained capture to the current parser. This is how the observed arXiv duplicate-tooltip false rejection was repaired without erasing the failure or downloading the paper again. A response rejected at the byte cap may have no complete capture and cannot be recovered this way. Duplicate attributes used by URL, visibility or charset logic still fail; unused presentation duplicates are tolerated.

Inspect `manifest.json`, lane intent receipts, `result.json`, `discovery-packet.json`, and optional `articles/<url-digest>/result.json`. Child runs live in `researcher/runtime/source-discovery-cache/`; each contains captures, source checkpoints, context pack, scheduler state and an inert handoff. With unchanged inputs, implementation and context, a repeated completed campaign verifies and reuses evidence. Historical captures remain separately replayable after code changes; the old campaign identity is never rewritten. Lost artifacts and unknown request outcomes stop instead of triggering an invisible repeat request.

The shared gate coordinates campaigns using the same cache on this machine. It cannot coordinate an unrelated client or another host. Low-level connector/pipeline APIs remain supervised primitives and do not themselves enforce the campaign-wide daily policy. Recurring research must use the campaign entry point and the same cache. The legacy launchd loop remains inert. No cloud deployment or UI mutation was activated by this revision.

## Verification and evaluation protocol

First execute deterministic tests for input/schema bounds, URL safety, query/cursor binding, metadata parsing, replay/tamper rejection, missing-checkpoint resume, failed/empty sources, concurrency, clock rollback, raw/extracted evidence linkage, and packet budget/omissions. Run the strict repository/platform and generated-inventory gates.

Then run a small credential-free live campaign. Record exact queries/sorts, source times, HTTP attempts, captured bytes, raw/unique/selected works, omitted candidates, and failures. Cache replay is zero fresh retrieval. Primary-page reads are evidence acquisition, not proof of their claims. Such a smoke test establishes integration behavior, not an unbiased quality improvement.

For the semantic study, freeze the union of control/variant candidates and have blinded reviewers assign facet relevance with a narrow rubric: unrelated, topical-only, useful mechanism, directly actionable mechanism with appropriate evidence. Retain a separate support assessment. Include no-answer, same-topic/wrong-method and different-wording/same-method cases. Compare original query, facet query, recency and optional citation expansion at matched request and review budgets. Report judged precision/nDCG, known-target recall where gold coverage permits, unjudged fraction, reviewer disagreement, unique useful works per review minute, latency and cost. Split and resample by underlying information need or failure family, not paraphrase or repeated execution. Pre-register a useful effect size before running paid ranking experiments.

## Research record

Research used official API/terms pages, primary full-text papers and verified publisher feeds, with separate code and failure-path review. Parallel Search was authenticated through stored OAuth; one search request was made for this engineering investigation. It is not a product-pipeline model call or a benchmark run. The bounded raw search result is `/tmp/source-harness-research-20260907.json`; private verification receipts retain source links and the final implementation identity. No credential value was printed.

Official feed evidence: [Google DeepMind feed](https://deepmind.google/blog/rss.xml), [Hugging Face feed](https://huggingface.co/blog/feed.xml) and [Microsoft Research feed](https://www.microsoft.com/en-us/research/feed/). Direct availability, freshness and article parseability still require the recorded live checks. OpenAI News was inspected but not enabled because the observed response exceeded the current pipeline cap. Anthropic's research page was inspected; no official feed was established in this investigation.
