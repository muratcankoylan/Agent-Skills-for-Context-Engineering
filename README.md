# Agent Skills for Context Engineering

An open-source context-engineering skill corpus and a developing, repository-owned research harness. The skills are portable instructions; the harness collects research, preserves source evidence, prepares bounded skill proposals, and evaluates changes before human review.

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/muratcankoylan/Agent-Skills-for-Context-Engineering)

## Standalone research service (pre-release)

The [current architecture](docs/product/research-organization-architecture.md)
maps the implementation, evidence, missing connections and launch gates. This is
a standalone Python service, not a Codex task or desktop scheduler. The current
[GitHub deployment and merge plan](docs/product/github-release-plan-2026-09-29.md)
records the earlier private GitHub control plane, durable pre-effect admission,
managed Agents API and separately credentialed draft-PR publisher design. Its
36-PR inventory is a dated snapshot. The [Codex SDK migration](docs/product/codex-sdk-runtime-migration.md)
supersedes the target agent runtime, not the historical test evidence. The Linux
coordinator is the first SDK reference topology; the [Control Center](apps/control-center/README.md)
is currently loopback-only. No cloud deployment or unattended managed research
is claimed. The new [release rehearsal](.github/workflows/release-rehearsal.yml)
is secret-free CI, not a production scheduler.

| Path | Implemented scope | Boundary |
| --- | --- | --- |
| [Daily retrieval](researcher/service/DAILY_RETRIEVAL.md) | arXiv, company feeds, HN, X and OpenAlex; capture replay, bounded context digest and optional primary HTML excerpts | Observations, not qualified findings; zero model calls |
| [Codex SDK research](researcher/service/CODEX_SDK.md) | Pinned SDK threads for researcher, critic, editor and independent evaluation tasks; validated gateway receipts | No native shell/network tools; deterministic retrieval outside the model; no measured skill-effectiveness claim |
| [Agent-selected research actions](researcher/service/AGENT_ACTIONS.md) | Opt-in context inspection, exact captured-span reads, methods/transfer specialist and finish/stop loop | Four decisions and one specialist; harness-dispatched, not SDK-native tools or unrestricted full-paper browsing |
| [Budget authority](researcher/service/OPENAI_CAMPAIGN.md) | Shared cumulative reservations, commit-before-delivery gateway, immutable receipts and safe replay | Conservative estimates, not an invoice cap; no reset on runtime migration |
| [Organization coordinator](researcher/service/ORGANIZATION.md) | Repo-owned foreground scheduling from bounded retrieval to the shared-budget pipeline, with durable per-job outcomes | Explicit activation; no automatic publication, budget reset or invented evaluation dataset |
| [Candidate review](researcher/service/CANDIDATE_REVIEW.md) | Exact skill freeze, isolated full-checkout overlay, trusted inventory derivation and structural validators | No automatic acceptance; held-out dataset must be supplied independently |
| [Cross-run learning](researcher/service/RESEARCH_PIPELINE.md) | Verified researcher-only prior hypotheses; exact duplicate candidates avoid repeat evaluation under the same completed evaluation contract | No gold/answer leakage, semantic novelty claim, or automatic cross-version history migration |
| [Execution dossier](researcher/service/DOSSIER.md) | Private read-only evidence, research/critic/editor results, candidate/evaluation decisions and trace receipts | Local consistency checks, not scientific validation or public export |
| [Artifact-complete recovery](researcher/runbooks/service-recovery.md) | Consistent database, captures, candidate artifacts and explicit session/budget authority closure | Fresh paused restore; original writer must be fenced and later effects reconciled |
| [Managed compatibility](researcher/service/AGENTS_API.md) | Inspect, watch and cancel retained managed session identities | New default managed submissions retired; historical receipts keep their backend labels |
| [Operator UI](apps/control-center/app/service/page.tsx) | Real, authenticated server-side status reads for the Python service | Read-only, loopback-only; does not yet control managed sessions |
| [Private tracing](researcher/service/TRACING.md) | Operation/action spans, latency/usage metadata, SDK events, durable receipts and opt-in post-cycle Raindrop delivery | No raw content export; Linux templates are not installed; ingestion ACK is not dashboard readback |

The integrated model-execution path now uses the [Codex SDK](researcher/service/CODEX_SDK.md)
through the existing cumulative authority. Scheduled and manual pipelines use fresh
SDK threads, source-bound context, frozen candidate validation and gold-free
evaluation. New default native/managed model execution is refused; historical
receipt replay and managed observation/cancellation remain available. The gateway
admits one buffered, tool-free request per turn and commits its validated receipt
before delivering output to the SDK. Started turns without final receipts require
reconciliation, not automatic retry.

Real SDK tests use synthetic local upstreams and prove execution/recovery wiring,
not model quality. Linux tool-free execution and native-tool sandboxing are separate
gates. This implementation is local integration work, not a published SDK release,
cloud launch, autonomous skill acceptance or permission to spend.

[September 29 connector evidence](docs/product/connector-verification-2026-09-29.md)
records scoped API checks and the registered MCP bridge canary.
Those observations do not establish research quality or production readiness.
The separate [integration verification record](docs/product/research-integration-verification-2026-09-29.md)
tracks replay-to-managed preparation and regression checks, not a scientific win.
The [production exercise](docs/product/production-exercise-2026-09-29.md) records
live model/connector checks, failure-derived fixes and the compressed month simulation.
Start with the [service runbook](researcher/service/README.md),
[credential setup](docs/product/provider-credentials.md), and
[deployment gates](researcher/service/DEPLOYMENT.md). Filling keys does not start jobs.
The latest [Raindrop UI and release verification](docs/product/raindrop-ui-release-verification-2026-09-29.md)
records the corrected Event/trace contract, authenticated dashboard evidence from
two real five-turn research cycles, graceful shutdown repair, root-Event restart
gating and review-stack handoff.
The earlier [agentic harness transport report](docs/product/agentic-raindrop-verification-2026-09-29.md)
records actual SDK action-selection canaries, post-cycle cloud ingestion, discovered
failures and fixes, private operator outputs, and the unchanged cumulative budget.
Its transport acknowledgements did not establish visible Events; the newer report
corrects that boundary. Functioning orchestration is not demonstrated research quality.

The earlier [SDK and tracing verification report](docs/product/runtime-tracing-verification-2026-09-29.md)
records its fault tests, synthetic Raindrop ingress ACK, exact source identities and
the failing Linux native-write experiment. It distinguishes unpublished integration
work from the reviewed PR stack and does not claim a cloud launch.
The subsequent [SDK migration verification](docs/product/codex-sdk-migration-verification-2026-09-29.md)
records the integrated caller/gateway, recovery and final tool-free Linux evidence.
The earlier [research-organization closure](docs/product/research-organization-closure-2026-09-29.md)
records implemented SDK/learning/retrieval/trace fixes, 1,081 passing service tests,
actual-SDK cross-day scenarios, live research outputs and retained failures. It
separates local trace creation from the then-pending Raindrop delivery approval and makes
no claim that fixture results demonstrate better skills or month-long uptime.

## What is Context Engineering?

Context engineering is the discipline of managing the language model's context window. Unlike prompt engineering, which focuses on crafting effective instructions, context engineering addresses the holistic curation of all information that enters the model's limited attention budget: system prompts, tool definitions, retrieved documents, message history, and tool outputs.

The fundamental challenge is that context windows are constrained not by raw token capacity but by attention mechanics. As context length increases, models exhibit predictable degradation patterns: the "lost-in-the-middle" phenomenon, U-shaped attention curves, and attention scarcity. Effective context engineering means finding the smallest possible set of high-signal tokens that maximize the likelihood of desired outcomes.

## Recognition

This repository is cited in academic research as foundational work on static skill architecture:

> "While static skills are well-recognized [Anthropic, 2025b; Muratcan Koylan, 2025], MCE is among the first to dynamically evolve them, bridging manual skill engineering and autonomous self-improvement."
1. [Meta Context Engineering via Agentic Skill Evolution](https://arxiv.org/pdf/2601.21557), Peking University State Key Laboratory of General Artificial Intelligence (2025)
2. [Agent Harness Engineering: A Survey](https://openreview.net/pdf/f358711a95aaaf61fdeffd4ef3fc60fba9b8da57.pdf), CMU, Yale, JHU, NEU, Tulane, UAB, OSU, Virginia Tech, and Amazon (2026)

## Skills Overview

### Foundational Skills

These skills establish the foundational understanding required for all subsequent context engineering work.

| Skill | Description |
|-------|-------------|
| [context-fundamentals](skills/context-fundamentals/) | Understand what context is, why it matters, and the anatomy of context in agent systems |
| [context-degradation](skills/context-degradation/) | Recognize patterns of context failure: lost-in-middle, poisoning, distraction, and clash |
| [context-compression](skills/context-compression/) | Design and evaluate compression strategies for long-running sessions |

### Architectural Skills

These skills cover the patterns and structures for building effective agent systems.

| Skill | Description |
|-------|-------------|
| [multi-agent-patterns](skills/multi-agent-patterns/) | Master orchestrator, peer-to-peer, and hierarchical multi-agent architectures |
| [long-horizon-prompting](skills/long-horizon-prompting/) | **NEW** Write pseudo-formal task briefs for long-running autonomous agents and parallel orchestrations: exact success predicates, non-counting outcomes, audit-gated return conditions, effort floors, and diversity policies, modeled on the published GPT-5.6 Sol Ultra Cycle Double Cover prompt |
| [memory-systems](skills/memory-systems/) | Design short-term, long-term, and graph-based memory architectures |
| [tool-design](skills/tool-design/) | Build tools that agents can use effectively |
| [filesystem-context](skills/filesystem-context/) | Use filesystems for dynamic context discovery, tool output offloading, and plan persistence |
| [hosted-agents](skills/hosted-agents/) | **NEW** Build background coding agents with sandboxed VMs, pre-built images, multiplayer support, and multi-client interfaces |

### Operational Skills

These skills address the ongoing operation and optimization of agent systems.

| Skill | Description |
|-------|-------------|
| [context-optimization](skills/context-optimization/) | Apply compaction, masking, and caching strategies |
| [latent-briefing](skills/latent-briefing/) | Share task-relevant orchestrator state with workers via task-guided KV cache compaction when the worker runtime is controllable |
| [evaluation](skills/evaluation/) | Build evaluation frameworks for agent systems |
| [advanced-evaluation](skills/advanced-evaluation/) | Master LLM-as-a-Judge techniques: direct scoring, pairwise comparison, rubric generation, and bias mitigation |
| [harness-engineering](skills/harness-engineering/) | Design autonomous agent harnesses with locked metrics, durable logs, novelty gates, rollback, and human approval boundaries |
| [self-improvement-loops](skills/self-improvement-loops/) | **NEW** Build loops where the harness itself is the optimization target: RSI, meta-harness search, failure-driven self-edits, evolutionary scaffold search, and acceptance gates for self-modifying systems |

### Development Methodology

These skills cover the meta-level practices for building LLM-powered projects.

| Skill | Description |
|-------|-------------|
| [project-development](skills/project-development/) | Design and build LLM projects from ideation through deployment, including task-model fit analysis, pipeline architecture, and structured output design |

### Cognitive Architecture Skills

These skills cover formal cognitive modeling for rational agent systems.

| Skill | Description |
|-------|-------------|
| [bdi-mental-states](skills/bdi-mental-states/) | **NEW** Transform external RDF context into agent mental states (beliefs, desires, intentions) using formal BDI ontology patterns for deliberative reasoning and explainability |

## Design Philosophy

### Progressive Disclosure

Each skill is structured for efficient context use. At startup, agents load only skill names and descriptions. Full content loads only when a skill is activated for relevant tasks.

### Platform Agnosticism

These skills focus on transferable principles rather than vendor-specific implementations. The patterns work across Claude Code, Cursor, and any agent platform that supports skills or allows custom instructions.

### Conceptual Foundation with Practical Examples

Scripts and examples demonstrate concepts using Python pseudocode that works across environments without requiring specific dependency installations.

## Usage

### Usage with Claude Code

This repository is a **Claude Code Plugin Marketplace** containing context engineering skills that Claude automatically discovers and activates based on your task context.

### Installation

**Step 1: Add the Marketplace**

Run this command in Claude Code to register this repository as a plugin source:

```
/plugin marketplace add muratcankoylan/Agent-Skills-for-Context-Engineering
```

**Step 2: Install the Plugin**

Option A - Browse and install:
1. Select `Browse and install plugins`
2. Select `context-engineering-marketplace`
3. Select `context-engineering`
4. Select `Install now`

Option B - Direct install via command:

```
/plugin install context-engineering@context-engineering-marketplace
```

This installs all published skills in a single plugin. Skills are activated automatically based on your task context.

### Skill Activation Scenarios

| Skill | Activate When |
|-------|---------------|
| `context-fundamentals` | Establishing context-window mental models, planning agent architecture, or explaining how context components affect model behavior |
| `context-degradation` | Diagnosing attention failures, context poisoning, lost-in-middle behavior, or degraded agent performance across long sessions |
| `context-compression` | Preserving useful state while reducing conversation, tool-output, or trajectory size under context pressure |
| `context-optimization` | Improving token efficiency, retrieval precision, prefix reuse, masking, partitioning, or budget allocation for agent systems |
| `latent-briefing` | Sharing orchestrator trajectory with workers via task-guided KV cache compaction when the worker runtime is controllable and the models are compatible |
| `multi-agent-patterns` | Choosing coordination patterns, isolating context across agents, designing handoffs, or evaluating whether parallel agents are justified |
| `long-horizon-prompting` | Writing or evaluating the launch prompt for a long-running autonomous agent or parallel orchestration: success predicates, non-counting outcomes, persistence and stop rules, adversarial audit gates, and portfolio diversity policies |
| `memory-systems` | Persisting cross-session knowledge, tracking entities over time, choosing memory frameworks, or designing retrieval and update semantics |
| `tool-design` | Defining agent-tool contracts, consolidating tool surfaces, improving descriptions, or making tool errors actionable |
| `filesystem-context` | Moving large or durable context into files, creating scratchpads, supporting just-in-time discovery, or coordinating agents through shared artifacts |
| `hosted-agents` | Running coding agents in remote sandboxes, background environments, warm pools, or multiplayer agent infrastructure |
| `evaluation` | Creating deterministic checks, rubrics, regression suites, production monitoring, or quality gates for agent behavior |
| `advanced-evaluation` | Using LLM judges, pairwise comparison, calibration, bias mitigation, or human-aligned quality assessment |
| `harness-engineering` | Designing autonomous loops with locked evaluators, editable surfaces, durable logs, novelty gates, rollback, and approval boundaries |
| `self-improvement-loops` | Building loops that modify themselves: failure-driven harness self-edits, meta-harness search, evolutionary scaffold search, context mechanism evolution, and acceptance gates for self-modification |
| `project-development` | Deciding whether an LLM is appropriate, shaping batch pipelines, creating staged artifacts, or estimating operational cost |
| `bdi-mental-states` | Modeling beliefs, desires, intentions, rational action traces, or neuro-symbolic state transformations for agents |

<img width="1014" height="894" alt="Screenshot 2025-12-26 at 12 34 47 PM" src="https://github.com/user-attachments/assets/f79aaf03-fd2d-4c71-a630-7027adeb9bfe" />

### For Cursor, Codex, and Open Plugins

This repository ships as an [Open Plugins](https://open-plugins.com) plugin. Hosts discover skills from the repo-root `skills/` directory (each subdirectory contains a `SKILL.md` file). The manifest lives at `.plugin/plugin.json`.

**Cursor (recommended):**

1. Install from the [Cursor Plugin Directory](https://cursor.directory/plugins/context-engineering), or clone this repo and point Cursor at the plugin root.
2. Cursor reads `.plugin/plugin.json` and discovers the repo-root `skills/` directory through the Open Plugins manifest.
3. For project-local manual installs, copy skill directories into `.cursor/skills/`. Do not rely on repository symlinks; they are fragile on Windows and in plugin packaging.

**Codex / GitHub Copilot CLI / other Open Plugins hosts:**

1. Clone or add this repository as a plugin directory.
2. The host reads `.plugin/plugin.json` and discovers all published skills under `skills/`.
3. For project-local manual installs, copy skill directories into `.codex/skills/` or the host's documented Agent Skills directory.

### Using Individual Skills

Agent Skills require a **directory layout**, not a flat markdown file. Copy the skill folder into your project's skills directory:

```bash
# Example: add just the context-fundamentals skill to a Cursor project
mkdir -p .cursor/skills
cp -R skills/context-fundamentals .cursor/skills/

# Claude Code project-scoped install (same directory layout)
mkdir -p .claude/skills
cp -R skills/context-fundamentals .claude/skills/

# Codex project-scoped install
mkdir -p .codex/skills
cp -R skills/context-fundamentals .codex/skills/

# Generic Agent Skills repo-scoped install (Codex/OpenAI, Copilot CLI, Open Plugins hosts)
mkdir -p .agents/skills
cp -R skills/context-fundamentals .agents/skills/
```

Do not flatten `SKILL.md` into a single file at `.claude/skills/context-fundamentals.md`. That breaks relative `references/` paths and violates the Agent Skills directory spec used by Cursor, Claude Code, and Codex.

Available skills: `context-fundamentals`, `context-degradation`, `context-compression`, `context-optimization`, `latent-briefing`, `multi-agent-patterns`, `long-horizon-prompting`, `memory-systems`, `tool-design`, `filesystem-context`, `hosted-agents`, `evaluation`, `advanced-evaluation`, `harness-engineering`, `self-improvement-loops`, `project-development`, `bdi-mental-states`

### For Custom Implementations

Extract the principles and patterns from any skill and implement them in your agent framework. The skills are deliberately platform-agnostic.

## Examples

The [examples](examples/) folder contains complete system designs that demonstrate how multiple skills work together in practice.

| Example | Description | Skills Applied |
|---------|-------------|----------------|
| [digital-brain-skill](examples/digital-brain-skill/) | **NEW** Personal operating system for founders and creators. Complete Claude Code skill with 6 modules, 4 automation scripts | context-fundamentals, context-optimization, memory-systems, tool-design, multi-agent-patterns, evaluation, project-development |
| [x-to-book-system](examples/x-to-book-system/) | Multi-agent system that monitors X accounts and generates daily synthesized books | multi-agent-patterns, memory-systems, context-optimization, tool-design, evaluation |
| [llm-as-judge-skills](examples/llm-as-judge-skills/) | Production-ready LLM evaluation tools with TypeScript implementation, 19 passing tests | advanced-evaluation, tool-design, context-fundamentals, evaluation |
| [book-sft-pipeline](examples/book-sft-pipeline/) | Train models to write in any author's style. Includes Gertrude Stein case study with 70% human score on Pangram, $2 total cost | project-development, context-compression, multi-agent-patterns, evaluation |
| [interleaved-thinking](examples/interleaved-thinking/) | Reasoning trace optimizer that captures, analyzes, and converts agent failure patterns into generated skills | evaluation, advanced-evaluation, context-degradation, harness-engineering |
| [long-horizon-prompt-lab](examples/long-horizon-prompt-lab/) | Production-ready educational website: method guide, copyable task-brief template, four complete prompt rewrites, structural audits, and a caveated research/vendor reference catalog | long-horizon-prompting, harness-engineering, multi-agent-patterns, advanced-evaluation |
| [deliberative-writing-loop](examples/deliberative-writing-loop/) | Offline mock/deterministic research example for persona compilation, paragraph contracts, sentence-level critique, trace compaction, and a three-condition benchmark. Paid generation, judging, and detector execution are disabled; no live quality or cost result is claimed | context-compression, memory-systems, evaluation, advanced-evaluation, harness-engineering, long-horizon-prompting |

Each example includes:
- Complete PRD with architecture decisions
- Skills mapping showing which concepts informed each decision
- Implementation guidance

### Digital Brain Skill Example

The [digital-brain-skill](examples/digital-brain-skill/) example is a complete personal operating system demonstrating comprehensive skills application:

- **Progressive Disclosure**: 3-level loading (SKILL.md → MODULE.md → data files)
- **Module Isolation**: 6 independent modules (identity, content, knowledge, network, operations, agents)
- **Append-Only Memory**: JSONL files with schema-first lines for agent-friendly parsing
- **Automation Scripts**: 4 consolidated tools (weekly_review, content_ideas, stale_contacts, idea_to_draft)

Includes detailed traceability in [HOW-SKILLS-BUILT-THIS.md](examples/digital-brain-skill/HOW-SKILLS-BUILT-THIS.md) mapping every architectural decision to specific skill principles.

### LLM-as-Judge Skills Example

The [llm-as-judge-skills](examples/llm-as-judge-skills/) example is a complete TypeScript implementation demonstrating:

- **Direct Scoring**: Evaluate responses against weighted criteria with rubric support
- **Pairwise Comparison**: Compare responses with position bias mitigation
- **Rubric Generation**: Create domain-specific evaluation standards
- **EvaluatorAgent**: High-level agent combining all evaluation capabilities

### Book SFT Pipeline Example

The [book-sft-pipeline](examples/book-sft-pipeline/) example demonstrates training small models (8B) to write in any author's style:

- **Intelligent Segmentation**: Two-tier chunking with overlap for maximum training examples
- **Prompt Diversity**: 15+ templates to prevent memorization and force style learning
- **Tinker Integration**: Complete LoRA training workflow with $2 total cost
- **Validation Methodology**: Modern scenario testing proves style transfer vs content memorization

Integrates with context engineering skills: project-development, context-compression, multi-agent-patterns, evaluation.

## Researcher Operating System

The [researcher](researcher/) directory contains the corpus, schemas, evidence
tools, experiments and service implementation. Its target is an auditable
research-to-proposal loop. The active service, managed canary and supervised
legacy run tools have distinct state and authority boundaries; they must not be
described as one already-deployed autonomous organization.

The [portable research improvement harness](docs/product/portable-harness.md)
adds a provider-neutral, frozen data-policy experiment loop, with
[measured local results](docs/product/portable-harness-results.md) and a
[proposed paper protocol](docs/product/portable-harness-paper-protocol.md).
It produces reviewable private proposals, not autonomous merges or production
acceptance. The software is open source; operational evidence remains private.

### Historical measured router-benchmark results

The skill router (which decides whether the right skill gets loaded for a given task) has been benchmarked end-to-end against four frontier models via the [Cursor SDK](https://cursor.com/docs/sdk/typescript). Three full sweeps (50 prompts x 4 models x 3 replications = 600 calls each):

- Baseline: [`researcher/benchmarks/router/results-published/2026-05-15.md`](researcher/benchmarks/router/results-published/2026-05-15.md)
- After targeted description rewrites: [`researcher/benchmarks/router/results-published/2026-05-15-v2.md`](researcher/benchmarks/router/results-published/2026-05-15-v2.md) (includes delta-vs-baseline)
- After corpus-wide hardening: [`researcher/benchmarks/router/results-published/2026-05-19.md`](researcher/benchmarks/router/results-published/2026-05-19.md) (600/600 usable records, 0 format failures)

Per-skill effect size for the three skills the data flagged:

| Skill | Baseline top-1 | After rewrite | Delta |
| --- | --- | --- | --- |
| `context-fundamentals` | 0.255 | 0.489 | +23.4pp |
| `project-development` | 0.750 | 1.000 | +25pp on this historical fixture |
| `tool-design` | 0.729 | 0.807 | +7.8pp |

Per-model top-1 accuracy after the corpus-wide hardening pass:

| Model | Top-1 | Top-3 |
| --- | --- | --- |
| gemini-3.1-pro | 0.920 | 0.933 |
| composer-2 | 0.913 | 0.947 |
| gpt-5.5 | 0.913 | 0.973 |
| claude-opus-4-7 | 0.840 | 0.933 |

These are dated historical results. The current package under
`researcher/benchmarks/sdk-runner/` can validate a dry-run plan but has no live
executor, so it cannot reproduce the sweeps in this revision.
They measured description routing, not the effectiveness of the current research
service, full skill bodies, primary-source selection, or autonomous improvement.

### What it includes

Current counts and compatibility status are generated in the [live corpus inventory](researcher/generated/corpus-summary.md). Dated benchmark and release reports retain their original snapshot counts.

- **Source registry** (`researcher/source-registry.md`): priority sources, exclusion rules, monitoring queries.
- **Rubrics** (`researcher/rubrics/`): content curation, skill change, harness change, pairwise skill revision.
- **Mechanism registry** (`researcher/mechanisms/registry.jsonl` + `ledgers/`): historically accepted behavior changes and accepted/rejected ledgers. New service proposals cannot promote themselves into this registry.
- **Claim provenance** (`researcher/claims/index.jsonl`): provenance-tracked claims with source URL, evidence strength, volatility, and last reviewed date.
- **Corpus index** (`researcher/corpus/index.json`): canonical machine-readable map of skills, activation scenarios, mechanism IDs, and claim IDs.
- **Run state machine** (`researcher/runs/<run-id>/run-state.json`): `initialized -> retrieved -> evaluated -> proposed -> novelty_checked -> validated -> pr_ready -> closed`.
- **Activation regression tests** (`researcher/fixtures/activation-cases.jsonl`): deterministic prompts that catch skill-boundary confusion.
- **Adversarial scenario catalog** (`researcher/benchmarks/`): closed descriptions and golden gate mappings for attacks such as duplicate mechanisms, unretrieved evidence, wrong rubric math, self-approved rubric changes, and weak-evidence novelty. These are design inputs until isolated executable fixtures invoke the named gates.
- **Supervised legacy loop** (`researcher/scripts/loop_*.py` + `researcher/orchestration/launchd/`): local migration inputs for manual candidate bookkeeping, status over explicit run-state transitions, reduced health checks, and parked review. Network retrieval, accepted closure, mechanism promotion, and launchd activation are disabled. These files confer no autonomous or production authority.
- **Skill health gate** (`researcher/scripts/skill_health.py`): deterministic body-quality scoring. Published scores remain dated evidence; local runs produce ignored runtime reports.
- **Public export boundary** (`governance/export-policy.yaml` + `researcher/scripts/validate_export.py`): allowlisted projections from private or restricted records into reviewable public staging trees without publishing private source locators or digests.
- **Schema and artifact contract** (`researcher/schemas/` + `researcher/scripts/artifact_store.py`): digest-pinned cross-runtime schemas, typed IDs, private bindings, exact-byte CAS, candidate freeze receipts, and Python/TypeScript conformance.
- **Autonomous-organization specification program** ([`docs/specs/README.md`](docs/specs/README.md)): machine-checked implementation contracts from the durable control substrate through evidence, evaluation, meta-harness improvement, governance, and deployment.

### Operator commands

Install the validation dependencies once before running local gates:

```bash
python3 -m pip install --require-hashes -r requirements-dev.txt
```

```bash
# Deterministic gates (also run in CI on every PR)
python3 -m unittest researcher.scripts.tests.test_skill_frontmatter
python3 researcher/scripts/validate_platform_compat.py --require-reference-validator
python3 researcher/scripts/validate_public_repo.py
python3 researcher/scripts/validate_spec_lifecycle.py \
  --base-ref origin/main \
  --promoted-ref origin/main
python3 researcher/scripts/validate_repo.py --strict
python3 researcher/scripts/skill_health.py --strict --no-history
python3 researcher/scripts/run_benchmarks.py
python3 researcher/scripts/check_activation_cases.py

# Per-run readiness (active runs only)
python3 researcher/scripts/validate_run.py --run-dir researcher/runs/<run-id>

# Supervised legacy loop, manual
python3 researcher/scripts/loop_status.py --initialize-runtime
python3 researcher/scripts/loop_discover.py
python3 researcher/scripts/loop_step.py
python3 researcher/scripts/loop_daily.py
python3 researcher/scripts/loop_status.py

# Inert launchd migration entry points (macOS)
researcher/orchestration/launchd/install.sh    # fails closed; activation is not authorized
researcher/orchestration/launchd/uninstall.sh  # remove launchd jobs
```

See [researcher/runbooks/continuous-operation.md](researcher/runbooks/continuous-operation.md) for the fail-closed boundary, consumed local limits, and human review surface.

### Current legacy boundary

- The supervised legacy loop never invokes paid LLMs and has no network retrieval path. Its launchd installer and wrappers fail closed. Production activation requires a future specification-owned implementation and deployment evidence.
- Runtime queue ledgers are ignored local state and must be created explicitly. Missing, malformed, or inconsistent ledgers fail closed; the tools do not silently repair them.
- Legacy runs cannot close as `accepted`, and `research_loop.py promote-mechanisms` always fails closed. Run-local proposals and readiness reports grant no acceptance or registry authority.
- Queue writers use atomic replacement and `fcntl` locks for local coordination. This is not a loss-proof journal, scheduler, or production queue.
- Agents may prepare candidate changes only within the user's authorization. Push and merge remain explicitly human-controlled.

## Star History
<img width="3664" height="2808" alt="star-history-2026526" src="https://github.com/user-attachments/assets/c9f88769-21b8-4762-9472-d4cf1fe1c802" />

## Structure

Each skill follows the Agent Skills specification:

```
skill-name/
├── SKILL.md              # Required: instructions + metadata
├── scripts/              # Optional: executable code demonstrating concepts
└── references/           # Optional: additional documentation and resources
```

See the [template](template/) folder for the canonical skill structure.

## Contributing

This repository follows the Agent Skills open development model. Contributions are welcome from the broader ecosystem. When contributing:

1. Follow the skill template structure
2. Provide clear, actionable instructions
3. Include working examples where appropriate
4. Document trade-offs and potential issues
5. Keep SKILL.md under 500 lines for optimal performance

Feel free to contact [Muratcan Koylan](https://x.com/muratcan) for collaboration opportunities or any inquiries.

## License

MIT License - see LICENSE file for details.

## References

The principles in these skills are derived from research and production experience at leading AI labs and framework developers. Each skill includes references to the underlying research and case studies that inform its recommendations.
