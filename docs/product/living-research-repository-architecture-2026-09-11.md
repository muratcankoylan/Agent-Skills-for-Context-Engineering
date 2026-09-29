# Toward a Living Research Repository

Agent Skills for Context Engineering

Architecture, research agenda and launch roadmap

11 September 2026 | Working architecture brief | Revision 1

## Executive abstract

We are extending an open-source collection of context-engineering skills into a research-to-improvement system. Its purpose is to discover relevant evidence, transfer that evidence into useful agent instructions, test proposed changes, and prepare auditable pull requests. The repository becomes a durable record of accepted knowledge and rejected hypotheses; a separately deployed harness performs the research and evaluation work.

The central design is a repo-owned control plane with managed model execution. Deterministic software owns scheduling, budgets, evidence identity, permissions and release gates. Agents perform bounded research, criticism and editing. Independent evaluation measures whether a frozen candidate improves downstream tasks. Humans retain merge and production-activation authority.

The integrated development corpus contains 17 skills, a mechanism registry, provenance records, evaluation fixtures and a 27-specification program. A native service preview implements a source-to-proposal workflow. A separate OpenAI Agents API canary implements request compilation, remote-session observation and recovery. These paths are not yet one production product. Live connector failures, incomplete evaluation integration, budget containment and deployment recovery remain launch blockers.

The research hypothesis is that evidence-aware context transfer, retained failure history and independently evaluated updates can improve a skill repository more reliably than unstructured research or unchecked self-editing. This is a hypothesis, not a demonstrated autonomous-discovery result. The next milestone is one supervised, reproducible evidence-to-evaluation-to-draft-PR cycle, followed by a failure-inclusive pilot and an explicitly approved cloud canary.

> Current position: an open-source research-system preview with substantial local engineering, narrow empirical evidence, and explicit production gates. Not a Codex automation, a deployed autonomous organization, or a completed research paper.

Repository: [Agent-Skills-for-Context-Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering). The current repository license is MIT. Collection version 2.5.0 is not a runtime release attestation.

<!-- pagebreak -->

## 1. How to read this brief

This document combines a product narrative, engineering architecture, research protocol and dated delivery ledger. It is a non-normative synthesis: it does not accept a specification, authorize spending, activate a service, or approve a merge. The specification lifecycle and repository governance remain controlling.

| Reader | Start with | Decision this supports |
| --- | --- | --- |
| Researcher | Sections 4-8 and 12-13 | What is novel enough to test, what is reproducible, and what remains unproven? |
| Investor or partner | Sections 2-3 and 14-16 | What product is being built, what assets exist, and what evidence reduces execution risk? |
| Engineer or operator | Sections 5-11 and 15-18 | What owns state, what may run, where are the interfaces, and what blocks release? |
| Maintainer or contributor | Sections 9, 15 and appendices | What can be proposed, reviewed, accepted and safely published? |

### Evidence labels

**Implemented** means code exists in the inspected integrated checkout. **Recorded verification** means a dated test or experiment receipt exists; it was not necessarily rerun for this brief. **Live-observed** means an actual external interaction was recorded. **Proposed** means intended design without completed integration evidence. **Blocked** identifies an unmet acceptance condition. These are descriptive labels, not normative specification states.

### Snapshot boundaries

Public GitHub metadata was refreshed at 04:33 UTC on 11 September 2026. Default-branch `main` was `6dbe1a1d868eab51a3bc9011b0f55e2891513e40`. The integrated local checkout was based on `c6cd52017b247804373339e1c3c103d42554b0a1` with substantial uncommitted additions. Those additions cannot be attributed to that base commit or assumed present on GitHub.

Three independent audits supported this brief: inventory and research claims; architecture and operational boundaries; public PR metadata. Fresh inventory and specification-plan checks passed. No paid model session, deployment, credential inspection or remote write was performed for the document. Most runtime verification cited below is from the September 10 receipt, not a new full-suite run.

Repository-relative paths identify the inspected local source tree. Some referenced development files are not yet published. A reproducibility release must include their reviewed dependency closure and exact identities. PR titles and check metadata describe proposals, not proof that their claims are correct.

<!-- pagebreak -->

## 2. Product thesis and scope

Context engineering is the deliberate selection, organization and transfer of information that an agent needs to act well. A skill makes reusable guidance discoverable and executable across tasks. A research harness is the surrounding software that supplies evidence, limits actions, records outcomes and tests whether changes help.

The problem is not a shortage of papers or agent frameworks. It is the cost of turning a noisy, changing research stream into reliable operational guidance. A paper may be relevant but methodologically weak. A useful technique may fail outside its benchmark. An instruction rewrite may improve discoverability while degrading task execution. A repository can accumulate impressive-looking advice without becoming more useful.

Our proposed product closes that loop: research produces a specific mechanism and a testable candidate; evaluation determines whether to retain, reject or investigate it; the result becomes durable knowledge for the next cycle.

### Two independently releasable surfaces

| Surface | What users receive | What it does not own |
| --- | --- | --- |
| Agent Skills Distribution | Reviewed skills, references, activation examples, compatibility checks and versioned evidence | Private job state, credentials, provider sessions or deployment authority |
| Research Harness and Control Center | Open-source coordinator, adapters, research workflows, evaluation tools and operator interface | Automatic scientific certification, human merge authority or provider infrastructure |

The first operator is the repository maintainer. Engineers consume the skills or run their own harness; researchers inspect methods and contribute evidence or evaluations. Private deployment means organization-specific state and credentials, not closed-source harness software.

### What “self-evolving” means

The system may propose changes to skills, retrieval policies, prompts and selected harness components under a fixed editable-surface policy. It must preserve evidence, evaluate the exact candidate and present an intelligible review packet. It may learn that a hypothesis failed and stop pursuing it. It cannot rewrite its own permission boundary, modify sealed evaluations, raise its budget, approve its release or merge itself.

The first release excludes general-purpose agent hosting, weight training, autonomous social posting, unrestricted web actions, multi-tenant billing and multi-region high availability. These do not prove the central value proposition and would enlarge the operational surface prematurely.

<!-- pagebreak -->

## 3. What exists in the repository

The integrated inventory is internally consistent, but it is not a release manifest for protected main. Counts below are the inspected candidate inventory, not a claim that every artifact is published or operational. [R1, R2]

| Asset | Recorded inventory | Interpretation |
| --- | --- | --- |
| Skill collection | 17 skills; version 2.5.0 | Reusable context and harness guidance, with packaging compatibility checks |
| Mechanism encyclopedia | 22 records; 28 accepted-ledger events; 1 rejected event | Records and ledger events are different units; acceptance history is retained |
| Claim provenance | 27 claims | A place to bind quantitative or volatile statements to evidence |
| Activation and routing | 23 activation cases; 56 current router prompts | Structural and routing fixtures, not full task-effectiveness coverage |
| Effectiveness and adversarial catalog | 1 effectiveness task; 7 adversarial entries | Early coverage; catalog enumeration alone executes no attacks |
| Specification program | 27 specs; 261 criteria | Four amended local revisions and 23 drafts; every criterion currently unassessed |
| Design support | 11 ADRs; 1 authority contract; 7 orchestration briefs | Durable engineering decisions and proposed operating contracts |

Fresh inventory checking reconciled 340 artifact records and 315 declared input snapshots. The inventory digest covers declared inputs, not every runtime byte or security property. Fresh specification-plan checking found no consistency errors; all 27 specifications still have recorded blockers.

### Three distinct delivery states

**Public main:** the default-branch source is what downstream users can reliably obtain without selecting a proposal. **Open PRs:** 36 proposed changes exist, including a stacked governance/runtime strand. **Integrated development:** service, managed runtime, UI and evaluation additions are being assembled locally. A successful local test cannot make these surfaces equivalent.

The repository has strong foundations for auditability: typed records, artifact hashing and freezing, append-only evidence history, generated inventories, source replay, deterministic validation and explicit lifecycle transitions. It does not yet have accepted, operational implementations of the entire specification program.

Existing package descriptions and historical notes sometimes describe an autonomous continuous operating system. The legacy launchd loop is now inert. This brief intentionally uses the narrower current status rather than carrying those older descriptions forward.

<!-- pagebreak -->

## 4. Target system: ownership before agent count

The target architecture puts one accountable coordinator between external services, model execution and public effects. Models can suggest actions; the control plane decides whether an action is admissible. The following is the intended integrated topology, not a diagram of a deployed service.

```architecture
External evidence: scholarly APIs, company research, web, X
                 |
                 v
Source broker -> private captures -> context compiler
                                      |
                                      v
Operator -> coordinator + budget/state -> managed research agents
                    |                            |
                    v                            v
             audit and results <- frozen candidate
                                      |
                                      v
                       independent evaluation
                                      |
                                      v
                         publication gate -> draft PR
                                               |
                                               v
                                      human merge -> skills
```

| Owner | Responsibilities and invariant |
| --- | --- |
| Repository and human maintainers | Accepted public source, governance, releases; model output grants no authority |
| Coordinator | Job identity, admission, leases, scheduling, reservations and recovery; one active owner per work item |
| Source and context boundary | Capture bytes, provenance, query coverage, omissions and budgeted context; external text is data, not policy |
| Execution adapter | Explicit model and tool configuration, remote IDs, lifecycle observation; no silent backend fallback |
| Evaluator | Exact candidate identity, isolated tasks, outcome measurements; author memory is not evaluator evidence |
| Delivery adapter | Redacted review artifact and scoped GitHub operation; no arbitrary agent-generated credential-bearing request |
| Control Center | Status, evidence and authorized operator commands; not a separate state authority |

The native SQLite store, managed canary ledger and historical event-journal prototype must not become three competing production sources of truth. The next integration must name one owner contract and explicitly migrate or project the others. Provider session history is execution evidence, not the organization's durable memory. [R3-R5]

<!-- pagebreak -->

## 5. Retrieval: from a lead to defensible evidence

Discovery and evidence acquisition are separate stages. Search results and social posts nominate work. Selected primary sources support claims. A hash proves that retained bytes have not changed; it does not prove that a source is authentic, relevant or scientifically correct.

| Source | Present position | Proposed production role |
| --- | --- | --- |
| arXiv | Collector exists; latest direct request received HTTP 429 | Resolve identified papers and retrieve permitted primary text with caching and rate-aware scheduling |
| Company research | DeepMind, Hugging Face and Microsoft feeds captured and replayed | Discovery plus query-driven retrieval of primary articles and linked papers |
| Scholarly indexes | OpenAlex and Semantic Scholar strategy proposed | Queryable discovery, identifiers, citation expansion and fallback coverage |
| Parallel | Search/extract and asynchronous deep-research integration proposed | Bounded web discovery, extraction and research tasks with cost and provenance receipts |
| X | Adapter library exists; not registered in the service workflow | Explicitly scoped social discovery, with original author/time/URL and corroboration requirements |
| MCP | Optional registered read tools in native design; compatibility unresolved | Narrow allowlisted retrieval contracts, not arbitrary tools inherited from a developer desktop |

The proposed scholarly strategy is index-first discovery, then identifier resolution and selected primary-text retrieval. It avoids treating arXiv's endpoint as the sole search service. Coverage, freshness, quotas, licenses and price still need provider-specific validation; no new scholarly index integration is claimed here.

### Proposed evidence contract

Each retained item needs a stable source identifier, canonical URL or scholarly ID, retrieval time, adapter/version, capture digest, media type and permission/projection classification. Each excerpt additionally needs exact byte/span identity, evidence depth, truncation status and its relationship to the original capture. A work-level record should distinguish title, abstract, article body and selected full-paper text.

The broker must bound response bytes, time, redirects and retries; preserve 429, outage and no-answer outcomes distinctly; and prevent credential-bearing or private-network requests outside policy. Duplicate works should merge by durable identifiers where possible, preserving version and source lineage instead of silently conflating revisions.

A research dossier must report what was searched, what was found, what was excluded and why. More retrieved tokens are not inherently more evidence. The next source milestone is query-relevant primary excerpts with explicit omissions, not a higher RSS lead count. [R6, R7]

<!-- pagebreak -->

## 6. Context transfer and institutional memory

The context compiler should turn a research question, baseline skill and selected evidence into a bounded, inspectable request. Its job is not merely summarization. It must preserve the information required to judge a claim while exposing what was lost.

### Three layers of memory

| Layer | Stored information | Retrieval purpose |
| --- | --- | --- |
| Public knowledge | Accepted skills, mechanisms, claims, references and activation examples | Reuse reviewed guidance and identify gaps or contradictions |
| Private run evidence | Captures, selected excerpts, requests, remote IDs, candidate freezes and evaluation receipts  | Replay and audit a particular attempt without exposing secrets or restricted content |
| Experimental history | Accepted and rejected hypotheses, failure classes and measured comparisons | Avoid repeated failed edits and generate new, testable priorities |

Current corpus retrieval is lexical. A vector database is not yet justified by measured failure. The preferred progression is a reliable lexical baseline, explicit metadata filters and citation/identifier expansion, followed by a hybrid retrieval experiment if it improves task-level coverage at acceptable cost. Content-addressed artifacts preserve identity; they are not themselves a search engine.

### What the compiler should transmit

The minimum packet contains the exact task, permitted edit surface, immutable skill baseline, selected evidence with provenance, uncertainty and contradiction notes, output schema, stopping conditions and evaluation boundary. Retrieval scores and source popularity should not be confused with confidence in a scientific claim. Progressive disclosure can expose additional bounded evidence through a source broker after the zero-tool canary is reliable.

The managed implementation already validates baseline/evidence digests, selected spans and a 128 KiB request ceiling. It does not establish source authenticity. Capture replay must be verified before preparation. Its current projection drops summary-kind and truncation qualifiers, an important open defect: two equal strings may have very different evidentiary scope. [R4, R6]

A historical mechanical replay retained 42 rather than 29 works within 131,072 bytes. This demonstrates a packing trade-off on two development-visible campaigns, not better relevance, reasoning or discovery. A production compiler must measure both retained information and downstream usefulness; byte efficiency alone is insufficient. [R8]

<!-- pagebreak -->

## 7. Agent roles, prompts and execution paths

Roles define responsibilities, not a requirement for separate persistent agents or services. Parallelism is useful only where it produces independent evidence or reduces latency enough to justify added cost and coordination.

| Role | Input and output | Authority |
| --- | --- | --- |
| Researcher | Question and evidence -> claims, mechanisms, limitations and proposed experiments | May reason over scoped evidence; cannot certify a change |
| Critic | Claims and source support -> contradictions, unsupported inferences and failure cases | May reject or request more evidence; cannot change policy |
| Skill editor | Accepted work scope and baseline -> bounded candidate diff | May edit granted surfaces only |
| Independent evaluator | Frozen candidate and controlled tasks -> outcome report | No author memory or mutable candidate; no merge permission |
| Deterministic coordinator | Job, receipts and policy -> transitions and effects | Owns admission and side effects, not scientific judgment |

Prompts should be versioned compilation inputs: objective, input contract, evidence rules, non-goals, output schema, tool policy and stop conditions. A role name alone does not create independence. Prompt-injection defenses must live in tool and data boundaries as well as instructions. Effective model and tool configuration must be retained with each run.

### Native preview versus managed canary

The native service calls researcher, critic and editor roles, freezes a proposal, and runs two reviews with reversed presentation order. It includes optional draft-PR delivery. These reviews test a narrow model preference, not independently demonstrated downstream effectiveness. Model calls are sequential in the current workflow.

The managed path currently puts research, critique and one scoped proposal into a single session using one explicit model. Default configuration has no external tools, environment, vault or subagents. The compiler permits bounded subagents, but the default is zero. Returned work remains `awaiting_independent_evaluation`; it cannot automatically freeze, publish or accept a skill change.

The OpenAI Agents API supplies managed execution, including optional child agents and MCP tools. It does not supply this repository's governance, scheduler or evaluator. Children inherit MCP configuration and credentials and share the configured environment; native subagents do not support application function tools. Source-broker design must respect this distinction. The desktop's tools are not automatically connected to the cloud harness. [R4, W1, W2]

<!-- pagebreak -->

## 8. Models, lifecycle and financial containment

The intended model policy is explicit, versioned and benchmark-driven. “Use the latest model” is not a reproducible configuration. Availability checks establish catalog access, not successful inference, tool entitlement or research quality.

| Proposed model | Proposed use | Proposed reasoning setting |
| --- | --- | --- |
| `gpt-6-astra` | Baseline research and selective difficult review | Medium baseline; high only as a measured condition |
| `gpt-5.6-terra` | Candidate lower-cost workhorse | Medium |
| `gpt-5.6-luna` | Triage and narrow classification | Low |

This is the working experimental roster, not a deployed routing policy or measured price-quality ranking. The managed compiler currently requires an explicit model but does not pin all proposed reasoning or service-tier settings. Those controls and returned effective configuration must be reconciled before comparisons. Independent evaluators must use separate sessions; different model names alone do not establish independence. [R4, R9]

### Remote execution invariants

The canary records a private submission intent and allows at most one creation attempt per state directory. If creation outcome is unknown, it does not retry blindly. Saved remote IDs support observation and recovery. A cancellation acknowledgment does not prove remote work has stopped; root and subordinate work must be observed in terminal states.

The default observer uses a 120-second deadline, 24 polls and five-second polling. These are local observation limits, not a hard remote runtime or dollar cap. A crashed observer cannot enforce a local timer. Per-directory identity is also not global admission control.

Before recurring managed work, the coordinator needs a shared reservation ledger covering roots, children, tools, retries and uncertain outcomes. Unreconciled work keeps its reservation and blocks unsafe duplicate admission. Provider-side spending controls must be verified independently; an application acknowledgment or alert is insufficient.

Official usage reporting is best effort and may be missing or change. It includes multiple model calls and delegated work, not simply one request equals one inference. Record reservations, observed usage and eventual billing separately. Never turn missing usage into zero cost or claim an exact bill from incomplete token telemetry. [W3]

<!-- pagebreak -->

## 9. From research to a skill release

The intended unit of improvement is an exact, reviewable candidate tied to evidence and evaluation. A report saying “this is better” is not a promotion record.

```lifecycle
Nominate -> Capture -> Research -> Propose -> Freeze
                                            |
                                            v
                                  Independent evaluation
                                     /             \
                                 Reject          Qualify
                                   |                |
                         Failure memory        Draft PR
                                                    |
                                              Human review
                                                    |
                                          Merge and release
```

The existing research-run helper tracks `initialized -> retrieved -> evaluated -> proposed -> novelty_checked -> validated -> pr_ready -> closed`. That historical workflow state is not the managed-session lifecycle or proof of the target independent candidate-evaluation gate. Each state machine needs a clear owner and an explicit integration mapping; names must not substitute for receipts.

### A complete review packet should contain

- The research question, selected primary evidence, omitted coverage and contradictory findings.
- Baseline and candidate digests; exact changed paths; edit-surface authorization; reproducible freeze receipt.
- Mechanism explanation, affected tasks, expected benefit and conditions under which it should fail.
- Deterministic validation, independent task results, uncertainty, regressions, cost and failed attempts.
- Public projection manifest, required reviewer decisions, rollback instructions and unresolved limitations.

A skill is a multi-surface artifact. A completed update must reconcile its description, activation and integration prose, mechanism registry, quantitative claims, corpus index, activation fixtures and generated inventory. Improving a description can change routing while leaving the body ineffective; both surfaces require their own tests.

Native draft publication is a capability preview. Its report still identifies missing full-overlay, held-out evaluation and metadata-synchronization gates. Publication must remain disabled until the boundary repairs and candidate qualification path are verified. The managed canary does not publish at all.

Human merge and deployment activation are separate decisions. Public export must project approved content and exclude private source locators, credentials and operational state. A public artifact reference identifies content; it does not grant access or authority. [R3-R5, R10]

<!-- pagebreak -->

## 10. Deployment and operator experience

The initial deployment recommendation is one dedicated Linux host with local persistent storage. This is a reference topology, not a selected provider, purchased machine or executed deployment. It minimizes distributed-state complexity while the research loop is still being validated.

```deployment
Operator via restricted authenticated access
                    |
          Control Center + loopback API
                    |
          One durable coordinator
             /                 \
     Local SQLite          Private artifacts
                    |
        Explicit outbound adapters
        /           |              \
   Source APIs   Managed agents   GitHub delivery
```

The host should run a pinned, read-only release under a dedicated non-root identity. Operational state and secrets remain outside agent context, but approved queries, skill text and evidence are transmitted to the model provider. Self-hosting the coordinator does not keep inference data local. SQLite requires local persistent disk, not NFS, object-store mounts or ephemeral layers. Preserve the approved repository Git identity; expose no host home directory, SSH keys or Docker socket to agents.

Existing templates cover the native service using a foreground coordinator with Linux/systemd or container packaging. Its scheduler owns recurring admission; adding a second cron loop would create duplicate ownership. The managed canary is not wired to that scheduler. The old launchd research loop remains disabled. [R11]

### Interface and delivery

There is an authenticated loopback service API and a read-only Next.js Control Center view for native service status. Managed sessions are currently CLI-operated and absent from that UI. Existing address validation assumes loopback; a container bridge or public reverse proxy requires an explicit configuration and authentication review.

The proposed managed run dossier shows query and source coverage, context omissions, role progress, remote lifecycle, candidate diff, evaluation status, budget reservations versus observed usage, and required operator action. Pause, cancel and retry must have distinct semantics. “Cancel requested” must never be displayed as “stopped.”

Results should arrive as private run artifacts and an operator-visible report; qualified public changes arrive as draft PRs. Notifications should summarize meaningful completion, failures and decisions with a link to the dossier, not expose raw private evidence. Notification integration and managed UI actions are still planned.

<!-- pagebreak -->

## 11. Security, recovery and operational limits

The threat model includes malicious retrieved text, misleading scientific evidence, credential reflection, ambiguous external outcomes, duplicate execution, excessive spend, compromised dependencies and unauthorized publication. It also includes ordinary outages and human confusion about whether a run has actually stopped.

| Risk | Required boundary | Current limitation |
| --- | --- | --- |
| Prompt injection or tool misuse | Treat sources as data; narrow tools and edit surfaces; validate effects independently | Prompt rules are not an OS or network sandbox |
| Credential exposure | Explicit credential injection to trusted adapters; reject secret reflection before requests and persistence | Synthetic GitHub probes found failing boundary cases; no real leak was demonstrated |
| Unknown remote execution | Persist intent and remote identity; reconcile before retry | Canary recovery exists; global managed admission is missing |
| Unbounded expenditure | Shared reservations plus verified provider containment | Local timers and cancellation requests do not impose a hard session cost cap |
| False improvement | Frozen candidate, independent tasks and failure-inclusive results | Current paired reviews and scorer fixtures do not establish effectiveness |
| State loss | Consistent database and artifact backup; isolated restore test | Native service backup covers SQLite only; separate journal-prototype recovery does not close the managed-service gap |

MCP is a protocol boundary, not a blanket permission grant. Native output bounds apply after SDK parsing, and DNS checks are not socket-pinned: deployment still needs process memory limits and private/metadata-address egress blocking. Managed service-origin requests come from provider infrastructure, so local servers are not automatically reachable. Tool contracts and service/environment origins require explicit review. [W2]

Before managed execution, approve provider retention, residency and permitted data classes. Document how prompts, evidence and session artifacts expire or are deleted, including remote reconciliation and any provider limitations.

A first operational release needs encrypted off-host backup of the complete artifact closure and state needed to resume safely. Restore must be exercised in isolation, with remote sessions and publication effects reconciled before reopening admission. Recovery-point and recovery-time targets should be selected by the operator and then measured; neither is established today.

Upgrade procedure: stop admission, record active work, reconcile or drain external sessions, preserve recoverable state, deploy a pinned candidate and run canaries. Rollback must account for schema compatibility and already-created external effects. Reverting source does not undo a PR or cancel a provider session.

Availability is initially single-host and supervised. No high-availability, multi-region, secure hostile-code execution or disaster-recovery guarantee should appear in launch materials before it is tested.

<!-- pagebreak -->

## 12. Research questions and evaluation design

The publishable contribution should be an experimentally supported method for improving reusable agent knowledge, not a diagram with more agents. Four falsifiable questions organize the work.

| Hypothesis | Comparison capable of falsifying it | Primary evidence |
| --- | --- | --- |
| Loss-aware context transfer improves grounding | Same evidence and budget, with versus without scope/omission-preserving compilation | Supported claims and downstream task success, not context length alone |
| Retained failure history improves research efficiency | Same task families with versus without prior rejected mechanisms | Valid candidate yield and repeated-failure rate per unit cost |
| Independent evaluation reduces false promotion | Author self-review versus separate frozen-task evaluation | False acceptance against calibrated human or objective outcomes |
| Selective routing reduces cost without material quality loss | Explicit fixed baseline versus predeclared routing policy | Task success under a preregistered non-inferiority margin and total cost |

### Experimental discipline

Start with a development pilot to estimate variance, failure frequency and cost. Before examining held-out results, freeze task families, practical-effect thresholds, exclusions, sample-size rationale, model configurations and analysis code. Use task-family or research-need grouping rather than treating correlated subagent calls as independent samples.

For candidate effectiveness, compare no-skill, current-skill and candidate-skill arms on matched tasks. Freeze candidate bytes before execution. Use fresh evaluator sessions without author memory, controlled sources and randomized or counterbalanced order. Blind semantic judges where practical and calibrate against trusted examples; prefer deterministic graders for objective outcomes.

Separately test the improvement process against a fixed incumbent, frozen-archive selection and budget-matched random search. Include archive-creation and exposure costs. Skill-arm comparisons alone cannot show that the research process beats these simpler alternatives.

Report invalid, missing, cancelled and failed attempts in the planned denominator. Separate first-attempt reliability from repaired availability. Use paired effect sizes and uncertainty intervals appropriate to grouped data. Report per-skill and per-task-family outcomes; aggregate accuracy can hide a damaging regression. Predeclare how multiple comparisons and adaptive exploration will be handled.

A month-equivalent accelerated replay cannot establish uptime, real-world novelty or long-term adaptation. Live web studies also face changing indexes and incomplete training-data visibility. Publish these limitations, plus capture policy, model/provider drift, judge bias and human review effort. Broader prior-art synthesis, independent replication and a powered held-out study remain work required before a scientific publication. [R12]

<!-- pagebreak -->

## 13. Evidence we have, and what it supports

The September 10 verification receipt reports the following. Counts overlap and must not be summed into a unique-test total. These suites were not rerun for this brief. [R9]

| Recorded check | Result | Valid conclusion |
| --- | --- | --- |
| Researcher Python suite | 1,130 tests | Broad deterministic behavior coverage at the recorded source state |
| Integrated service suite | 332 tests | Local contracts, including fake managed transports and runtime states |
| Deployment contracts | 10 tests | Template and configuration checks, not a Linux deployment |
| Control Center | 50 tests | UI behavior coverage, not integrated managed operation |
| Packaging and repository validation | 17 skills; four layouts; strict checks without warnings | Structural consistency and supported format compatibility |
| Static skill health | 0.9221 | Rubric-based structural score, not semantic effectiveness |
| Managed evaluation smoke | 36 gold-answer fixture rows | Planner/scorer wiring, not 36 model trials |

Fresh document-time inventory and specification checks passed. Managed module and plan hashes were also checked against the earlier receipt. These checks narrow source drift; they do not extend the earlier test claims to every local file.

### Historical routing evidence

The May 19 report records 600 usable records after retries across four models and 15 skill descriptions: Gemini 0.920, Composer 0.913, GPT-5.5 0.913 and Claude Opus 4.7 0.840 top-1 routing accuracy. It did not load skill bodies. It is not a benchmark of today's 17-skill corpus, the current 56-prompt fixture, or managed agents. Historical reproduction commands also depend on runners that are now disabled for paid calls. [R13]

The 29-to-42 retained-work packing result is a retrospective mechanical measurement on two known campaigns. It supports a specific byte-budget result, not autonomous research quality. Current Stage 3 effectiveness coverage remains one task; composition and sustained repository improvement are not established. [R8]

No managed paid session, cloud launch, month-long production observation, independently validated skill improvement or autonomous scientific discovery is established by these receipts. A catalog validator that enumerates seven adversarial entries does not execute seven attacks; a separate deterministic mutation executor must be distinguished from the catalog check.

<!-- pagebreak -->

## 14. Live connector findings and the $100 pilot

The September 10 connector preflight found real integration gaps despite substantial offline coverage. Independent OpenAI model/session-list reads returned HTTP 200, but the actual adapter rejected a legal non-framing duplicate response header. No managed session was created. Three synthetic GitHub credential-reflection tests and one transport regression test failed alongside 309 distinct existing passing tests. These are reproducible blockers, not proof of an actual credential leak. [R6]

Four source requests returned 18 company-feed leads; arXiv returned 429 and zero leads. Eleven of the 18 leads were title-only. Microsoft supplied six embedded articles, two truncated, and its text alone exceeded the native evidence ceiling. These were replayable captures, not a demonstrated primary-paper pipeline. Anonymous MCP initialization/listing exposed five tools without output schemas; an offline contract test confirmed rejection of that shape before invocation. No live tool was called. Connectivity, compatibility and useful research are different tests.

### Bounded campaign proposal

The user-approved $100 benchmark budget should fund a pilot, not be presented as an already enforced platform limit. The requested “month” is 30 logical research days across varied queries and failures, not 30 days of real-time cloud availability. No allocation below has been spent or admitted by this document.

| Planning allocation | USD | Purpose |
| --- | --- | --- |
| Boundary and inference canary | 5 | Establish a small valid run and observable lifecycle |
| Source coverage and retrieval | 20 | Compare query coverage, primary evidence depth and cost |
| Collaboration conditions | 25 | Compare zero versus bounded delegation at matched budgets |
| Independent task evaluation | 25 | No-skill/current/candidate development pilot |
| Targeted optimization | 10 | Change the measured bottleneck, then rerun the same cases |
| Uncertainty reserve | 15 | Failed calls, tools and reconciliation uncertainty |
| Total planning ceiling | 100 | Conditional on verified financial containment |

Scenarios should include contradictory papers, duplicate versions, empty results, 429s, timeouts, truncated papers, malicious source instructions, stale skills, provider failure, restart during create, cancellation ambiguity and a candidate that improves routing but worsens task quality. The schedule must preserve logical time separately from real request and billing time. Existing missed-slot coalescing is not a month-replay engine.

Do not start the campaign until transport, credential reflection, evidence scope and spending controls pass their gates. A pilot can choose the next experiment; it cannot promise sufficient statistical power for the final paper.

<!-- pagebreak -->

## 15. Delivery roadmap and measurable gates

The roadmap is ordered by dependencies and evidence, not calendar promises. The first objective is one complete supervised vertical slice. Functional owners below are required responsibilities, not a claim that a staffed team exists.

| Stage and owner | Deliverable | Exit evidence |
| --- | --- | --- |
| 0. Reconcile release surface; maintainer | Reviewed dependency closure for local code and stacked PRs | Exact candidate identity, public/private boundary review, clean reproducible source |
| 1. Repair boundaries; runtime/security | Safe actual transport and publication adapter | Live read succeeds; ambiguous framing still rejected; secret-reflection tests fail closed before effects |
| 2. Qualify evidence; retrieval engineer | Query-aware scholarly/web pipeline with retained scope | Replayable captures, usable primary excerpts, 429/no-answer/truncation receipts across distinct queries |
| 3. One managed canary; runtime/operator | Coordinator-owned session lifecycle and accounting | Zero-tool run, recoverable IDs, observed terminal cancellation, global duplicate prevention, verified spend containment |
| 4. Independent evaluation; research lead | Frozen three-arm development study | Separate evaluator sessions, leakage checks, failure-inclusive analysis and pilot-derived study design |
| 5. Qualified proposal; maintainer/eval | Full candidate validation and draft delivery | All skill surfaces synchronized; exact freeze; approved sandbox PR and uncertain-outcome recovery drill |
| 6. Cloud canary; operator/security | Pinned single-host deployment and managed UI | Authenticated access, pause/restart tests, complete encrypted backup and isolated restore |
| 7. Research and release; maintainer/research | Public methods, artifacts and approved scheduling | Reviewed results and limitations; license/privacy checks; explicit human launch decision |

Stages can overlap only where interfaces are stable. Source experiments do not need public GitHub writes; UI design does not need paid agent runs; transport fixes do not require broad runtime autonomy. Expand permissions only after the narrower path produces evidence.

### Launch criteria

Operational launch requires known ownership for every state transition, observable external work, bounded admission, qualified publication, complete recovery and an operator who can intervene. Research publication additionally requires honest baseline comparisons, reproducible artifacts and conclusions limited to measured outcomes. A software preview can be released before a research paper, provided its capability and maturity are labeled accurately.

The 261 specification criteria remain unassessed. This roadmap does not mark them implemented or accepted. Each stage must generate evidence for the relevant criterion IDs and follow the specification lifecycle. No meaningful overall completion percentage can be inferred from file counts or passing tests.

<!-- pagebreak -->

## 16. Open-source strategy and product economics

The durable asset is the combination of useful skills, mechanism-level provenance, failed and successful experiments, interoperable records, and a reproducible improvement process. Agent orchestration alone is unlikely to differentiate the project. The product must demonstrate that maintainers can obtain more defensible improvements per hour and per dollar.

### What should be public

The intended public release includes the skill collection, harness/control-center code, schemas, adapter contracts, deterministic tests, approved example configurations and operating documentation. Research releases should additionally include the study protocol, task definitions that can be shared, analysis code, model configuration, lineage manifests, negative results and permitted source projections.

Credentials, operator identity data, private captures, billing records, hidden evaluation answers and live state remain private. The MIT code license does not automatically license third-party paper text or X content for redistribution. Export decisions need source-specific rights and attribution checks. A self-hosting user should be able to supply credentials through documented configuration without depending on Codex or the maintainer's accounts.

### Adoption and value hypotheses

The first adoption test is whether an external engineer can install the corpus and reproduce one documented result. The second is whether a researcher can evaluate a candidate without trusting the original author's report. The third is whether an operator can run, inspect, stop and recover the harness with bounded cost.

Hosted operations, organizational integrations or support may become commercial offerings, but no pricing, revenue, customer traction or market-size claim is established here. Before choosing a business model, measure repeated use, reviewer workload, time to accepted improvement, reproducibility success and operating cost.

Useful unit economics include cost per qualified candidate, cost per accepted improvement, human review minutes, primary-evidence yield per query, and failure/recovery overhead. A high rejection rate can be healthy if the system cheaply eliminates weak ideas; a high PR count alone is not success.

### Scaling decision

Keep one coordinator and local storage until measurements identify a bottleneck. Add worker capacity, durable queues, hybrid search or multi-tenant controls only when their benefit exceeds operational complexity. The scientific and product advantage should come from better learning and evidence transfer, not unnecessary infrastructure.

<!-- pagebreak -->

## 17. Specification program

The specification program is broader than the initial release. Its lifecycle is `draft -> architecture_reviewed -> accepted -> implemented -> verified -> operational`, with explicit amendment and retirement states. A PR check or a local implementation cannot skip those transitions. [R2]

| Wave | Specifications | Responsibility |
| --- | --- | --- |
| Foundation | SPEC-000 constitution; 001 inventory; 002 public/private boundary; 003 schemas and artifact identity | Define governance, identity and safe publication |
| Durable control | SPEC-004 event journal; 005 scheduling/leases/recovery; 006 commands; 007 GitHub lifecycle; 008 observability | Give work and effects one durable owner |
| Evidence and context | SPEC-009 sources; 010 retrieval; 011 evidence graph; 012 context compiler; 013 roles; 014 runtime/protocol adapters; 015 notifications | Turn research inputs into bounded agent work and visible results |
| Evaluation and release | SPEC-016 eval registry; 017 runner; 018 candidate archive; 019 promotion | Measure exact candidates before accepting public changes |
| Bounded evolution | SPEC-020 meta-harness lab; 021 adaptive routing; 022 collaborative evolution | Optimize using recorded evidence under fixed constraints |
| Product operation | SPEC-023 governance; 024 control plane; 025 deployment | Open-source contribution, operator UX and cloud operation |
| Deferred research | SPEC-026 training/RL lab | A separate future decision; not current weight training |

<!-- pagebreak -->

## 18. Engineering handoff

These entry points separate public knowledge, private execution state and proposed operating contracts. Begin with the README and runbook for the selected path; do not assume the native and managed commands share an integrated lifecycle.

| Path in the integrated source tree | Purpose |
| --- | --- |
| `skills/`, `SKILL.md`, plugin manifests | Public skill bodies and distribution |
| `researcher/corpus/`, `researcher/mechanisms/`, `researcher/claims/` | Knowledge inventory and provenance |
| `researcher/service/` | Native coordinator, store, adapters and managed canary modules |
| `researcher/service/agents_context.py` | Managed request/context compilation |
| `researcher/service/agents_runtime.py` | Submission ledger, observation, recovery and cancellation |
| `researcher/service/agents_evals.py` | Three-arm planner/scorer, not a live study executor |
| `apps/control-center/` | Operator UI; managed integration pending |
| `researcher/benchmarks/`, `researcher/scripts/` | Fixtures, historical results and deterministic tools |
| `docs/specs/`, `docs/product/`, `governance/` | Normative contracts, design records and projection rules |

Older filenames or history may refer to previous runtimes. Naming is not current execution evidence. Follow the managed/native boundary documented in this brief and the specific module contracts rather than assuming every earlier design is active.

### Reproducibility handoff

1. Identify the exact reviewed source and dependency closure. A base commit plus undocumented local modifications is not a reproducible release.
2. Run offline repository, schema, inventory and adapter fixtures before connecting a provider. Distinguish fixtures, captured-response replay and live calls in every report.
3. Create private operational state outside public exports. Select data classes, retention, provider configuration and financial controls before exposing approved context to inference.
4. Reproduce the zero-tool managed canary before enabling retrieval tools, delegation, scheduling or draft delivery. Add one capability at a time with fault tests and a rollback path.

An adapter contribution should include its input/output contract, credential boundary, timeout and response bounds, failure classification, deterministic fixtures and a small opt-in live canary. A model or prompt contribution should include exact configuration, target task family, baseline, counterexample and evaluation plan. Neither should silently change runtime defaults or bypass admission.

<!-- pagebreak -->

## Appendix A. Open PRs: governance and runtime strand

At the snapshot time there were 36 open PRs: 12 drafts, 27 reported mergeable and nine conflicting. Twenty-three had no reported check rollup. “Mergeable” is GitHub's conflict calculation, not a code-review verdict or launch recommendation. No required-check policy or full diff review was performed for this brief.

Current base/head branch names imply the following review strand. Commit ancestry and dependency correctness still require verification before integration:

`main -> #121 -> #122 -> #123 -> #124 -> #125 -> #126 -> #127 -> #128 -> #129 -> #130 -> #131 -> #134`

| PR | Exact title | Snapshot status |
| --- | --- | --- |
| [#121](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/121) | feat(governance): publish and enforce the specification program | Open; mergeable; reported checks pass, deployment skipped |
| [#122](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/122) | feat(orchestration): add supervised long-horizon bootstrap briefs | Draft; mergeable; checks pass |
| [#123](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/123) | docs(spec-003): authorize classification invariant amendment | Draft; mergeable; checks pass |
| [#124](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/124) | docs(spec-000): authorize authority vocabulary amendment | Draft; mergeable; checks pass |
| [#125](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/125) | fix(benchmarks): contain Cursor SDK and harden evidence | Draft; mergeable; checks pass |
| [#126](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/126) | test(benchmarks): add private manifest resume substrate | Draft; mergeable; checks pass |
| [#127](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/127) | docs(spec-001): authorize snapshot identity amendment | Draft; mergeable; checks pass |
| [#128](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/128) | docs(spec-002): authorize projection-boundary amendment | Draft; mergeable; checks pass |
| [#129](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/129) | fix(governance): require promoted revision predecessors | Draft; mergeable; checks pass |
| [#130](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/130) | Extract authority contract and bind evaluator provenance | Draft; mergeable; checks pass |
| [#131](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/131) | Harden offline authority vocabulary semantics | Draft; mergeable; checks pass |
| [#134](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/134) | feat(runtime): add bounded OpenAI Agents API transport | Draft; mergeable; three reported checks pass |

PR #134 contains the transport slice, not the integrated service, managed compiler, runtime ledger, evaluator or UI. Its head is `9639dda3c5b2b6fb3ddfd88a3478c3dc90aa7c54`. The known live-header failure still blocks treating offline green checks as readiness. Review the strand from its base, reconcile amendments, and revalidate exact candidates before asking for merge approval. This is a review sequence, not an instruction to merge all twelve PRs.

<!-- pagebreak -->

## Appendix B. Open PRs: maintenance and adjacent work

These proposals target `main`. Topic grouping is based on titles only; relevance, overlap and supersession require code review. A missing rollup means “no reported checks,” not “tests pass.”

| PR | Exact title | Snapshot status |
| --- | --- | --- |
| [#132](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/132) | Add deliberative-writing-loop example: inference-time persona writing harness | Draft; mergeable; validation failed |
| [#133](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/133) | Add rendered UI finish gate skill | Open; mergeable; no reported checks |
| [#113](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/113) | Fix Windows import crash in loop_common by making fcntl optional | Open; mergeable; no reported checks |
| [#112](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/112) | Add cost, request, token, and rate-limit safeguards to API loops and judge examples | Open; mergeable; no reported checks |
| [#111](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/111) | Fix stale researcher-OS baseline numbers in README, AGENTS, and plugin metadata | Open; conflicting; no reported checks |
| [#110](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/110) | Fix shell injection and unsafe secret handling in hosted agents image build example | Open; mergeable; no reported checks |
| [#109](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/109) | Fix path traversal and arbitrary file deletion in pipeline_template.py | Open; mergeable; no reported checks |
| [#92](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/92) | Maintenance: Update dependencies and refine interleaved thinking example | Open; mergeable; no reported checks |
| [#83](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/83) | fix: validate custom install path in install.sh to prevent path traversal | Open; mergeable; no reported checks |
| [#82](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/82) | fix: tighten production dependency ranges from ^ to ~ in package.json | Open; mergeable; no reported checks |
| [#81](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/81) | fix: remove GitHub token from git clone URL in sandbox_manager.py | Open; mergeable; no reported checks |
| [#80](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/80) | fix: add YAML frontmatter to llm-as-judge agent files | Open; mergeable; no reported checks |

Security-related titles deserve early triage, but a proposed fix is not evidence that the resulting code is safe. Reproduce the underlying issue on the intended integration base, inspect the patch, test the failure path and check whether later work already addresses it. #132 requires investigation of its failed validation. #111 needs conflict and current-inventory reconciliation rather than copying historical totals forward.

<!-- pagebreak -->

## Appendix C. Open PRs: community proposals

These also target `main`. They should be evaluated against the collection's context-engineering scope, maintenance burden, evidence quality and complete skill-surface validation. Expanding the number of skills or connectors is not by itself a launch dependency.

| PR | Exact title | Snapshot status |
| --- | --- | --- |
| [#100](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/100) | Publish xhigh evidence and harden validation paths | Open; conflicting; no reported checks |
| [#95](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/95) | Add Linked API linkedin skill | Open; mergeable; no reported checks |
| [#89](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/89) | Add internal repo-contributor skill as project knowledge base | Open; mergeable; no reported checks |
| [#88](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/88) | Add context receipts skill | Open; conflicting; no reported checks |
| [#72](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/72) | Add session-handoff skill for cross-session task continuity | Open; conflicting; no reported checks |
| [#55](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/55) | Improve multi-agent-patterns skill and add skill review workflow | Open; conflicting; no reported checks |
| [#52](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/52) | feat: adding a context benchmarking-skill | Open; conflicting; no reported checks |
| [#40](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/40) | Apply context engineering refactor to sales, copywriter, sentinel, solo-maker, and solo plugins | Open; conflicting; no reported checks |
| [#38](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/38) | Add 78 Composio SaaS app automation skills via Rube MCP | Open; mergeable; no reported checks |
| [#36](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/36) | docs: add AdaL to compatible platforms list | Open; mergeable; no reported checks |
| [#24](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/24) | feat: Add Solution Architecture skill with comprehensive reference ma… | Open; conflicting; no reported checks |
| [#17](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/pull/17) | fix: expand marketplace to list individual skills for proper discovery | Open; conflicting; no reported checks |

Titles are reproduced as returned by GitHub, including the ellipsis in #24. No PR was changed, closed, rebased, merged or approved during preparation of this brief. Before external distribution or any merge decision, refresh this appendix because PR state and check results are volatile.

<!-- pagebreak -->

## Appendix D. Sources and reproducibility notes

Repository evidence below is relative to the integrated checkout, not a guarantee that each path exists on current public main. The Markdown source preserves clickable local-relative links. A public release must publish a reviewed source snapshot so external readers can reproduce the same checks.

| ID | Primary repository evidence |
| --- | --- |
| R1 | [Generated corpus inventory](../../researcher/generated/corpus-summary.md), [license](../../LICENSE), collection manifests |
| R2 | [Specification lifecycle](../specs/README.md), [execution plan](spec-execution-plan.json), [delivery plan](living-organization-plan.md) |
| R3 | [Native service README](../../researcher/service/README.md), `researcher/service/workflow.py`, `store.py` |
| R4 | [Managed API contract and runbook](../../researcher/service/AGENTS_API.md), `agents_context.py`, `agents_runtime.py`, `agents_evals.py` |
| R5 | [Event journal scope](../../researcher/event_journal/README.md), schema registry and candidate-freezing implementation |
| R6 | [Connector preflight, September 10](connector-preflight-2026-09-10.md) |
| R7 | [Cloud service design](cloud-research-service.md), source adapter and capture/replay implementations |
| R8 | [Portable harness measured results](portable-harness-results.md) |
| R9 | [Managed integration verification, September 10](openai-agents-verification-2026-09-10.md) |
| R10 | [Public export policy](../../governance/export-policy.yaml), `researcher/scripts/validate_export.py` |
| R11 | [Deployment runbook](../../researcher/service/DEPLOYMENT.md), [Control Center](../../apps/control-center/) |
| R12 | [Proposed paper protocol](portable-harness-paper-protocol.md), [benchmark methodology](../../researcher/benchmarks/PLAN.md) |
| R13 | [Historical router report, May 19](../../researcher/benchmarks/router/results-published/2026-05-19.md), [archive limitations](../../researcher/benchmarks/router/results-published/README.md) |

Official API documentation was checked during preparation. Provider features and contracts may change; pin implementation behavior and retain effective configuration for each experiment.

- W1: [OpenAI Agents API: multi-agent execution](https://developers.openai.com/api/docs/guides/agents-api/multi-agent). Supports the described child-agent and inherited-tool boundaries, not our application integration status.
- W2: [OpenAI Agents API: MCP tools](https://developers.openai.com/api/docs/guides/agents-api/tools/mcp). Supports service/environment origin, tool allowlists and credential transport distinctions.
- W3: [OpenAI Agents API: observability](https://developers.openai.com/api/docs/guides/agents-api/observability). Supports best-effort usage, multi-call accounting and remote execution visibility limitations.

Public PR links in Appendices A-C are the primary source for the dated metadata snapshot. GitHub metadata was read without changing repository state. This document adds synthesis and proposed design, not new scientific experimental results. Its PDF is generated from this Markdown by `render_architecture_brief.py`; the PDF and source are a dated communication artifact, not an accepted specification or immutable release attestation.
