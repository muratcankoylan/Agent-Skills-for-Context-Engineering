# Agent Skills for Context Engineering

A comprehensive, open collection of Agent Skills focused on context engineering and harness engineering principles for building production-grade AI agent systems. These skills teach the art and science of curating context, designing agent operating loops, and evaluating agent behavior across any agent platform.

[DeepWiki: Learn more here](https://deepwiki.com/muratcankoylan/Agent-Skills-for-Context-Engineering)

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

This installs all 15 skills in a single plugin. Skills are activated automatically based on your task context.

### Skill Activation Scenarios

| Skill | Activate When |
|-------|---------------|
| `context-fundamentals` | Establishing context-window mental models, planning agent architecture, or explaining how context components affect model behavior |
| `context-degradation` | Diagnosing attention failures, context poisoning, lost-in-middle behavior, or degraded agent performance across long sessions |
| `context-compression` | Preserving useful state while reducing conversation, tool-output, or trajectory size under context pressure |
| `context-optimization` | Improving token efficiency, retrieval precision, prefix reuse, masking, partitioning, or budget allocation for agent systems |
| `latent-briefing` | Sharing orchestrator trajectory with workers via task-guided KV cache compaction when the worker runtime is controllable and the models are compatible |
| `multi-agent-patterns` | Choosing coordination patterns, isolating context across agents, designing handoffs, or evaluating whether parallel agents are justified |
| `memory-systems` | Persisting cross-session knowledge, tracking entities over time, choosing memory frameworks, or designing retrieval and update semantics |
| `tool-design` | Defining agent-tool contracts, consolidating tool surfaces, improving descriptions, or making tool errors actionable |
| `filesystem-context` | Moving large or durable context into files, creating scratchpads, supporting just-in-time discovery, or coordinating agents through shared artifacts |
| `hosted-agents` | Running coding agents in remote sandboxes, background environments, warm pools, or multiplayer agent infrastructure |
| `evaluation` | Creating deterministic checks, rubrics, regression suites, production monitoring, or quality gates for agent behavior |
| `advanced-evaluation` | Using LLM judges, pairwise comparison, calibration, bias mitigation, or human-aligned quality assessment |
| `harness-engineering` | Designing autonomous loops with locked evaluators, editable surfaces, durable logs, novelty gates, rollback, and approval boundaries |
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
2. The host reads `.plugin/plugin.json` and discovers all 15 skills under `skills/`.
3. For project-local manual installs, copy skill directories into `.codex/skills/` or the host's documented Agent Skills directory.

### Using Individual Skills

Agent Skills require a **directory layout**, not a flat markdown file. Copy or symlink the skill folder into your project's skills directory:

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
```

Do not flatten `SKILL.md` into a single file at `.claude/skills/context-fundamentals.md`. That breaks relative `references/` paths and violates the Agent Skills directory spec used by Cursor, Claude Code, and Codex.

Available skills: `context-fundamentals`, `context-degradation`, `context-compression`, `context-optimization`, `latent-briefing`, `multi-agent-patterns`, `memory-systems`, `tool-design`, `filesystem-context`, `hosted-agents`, `evaluation`, `advanced-evaluation`, `harness-engineering`, `project-development`, `bdi-mental-states`

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

The [researcher](researcher/) directory is a file-based operating system for turning external research into skill changes. It exists so this repository can act as a compounding source of truth instead of an anthology.

### Measured router-benchmark results

The skill router (which decides whether the right skill gets loaded for a given task) has been benchmarked end-to-end against four frontier models via the [Cursor SDK](https://cursor.com/docs/sdk/typescript). Three full sweeps (50 prompts x 4 models x 3 replications = 600 calls each):

- Baseline: [`researcher/benchmarks/router/results-published/2026-05-15.md`](researcher/benchmarks/router/results-published/2026-05-15.md)
- After targeted description rewrites: [`researcher/benchmarks/router/results-published/2026-05-15-v2.md`](researcher/benchmarks/router/results-published/2026-05-15-v2.md) (includes delta-vs-baseline)
- After corpus-wide hardening: [`researcher/benchmarks/router/results-published/2026-05-19.md`](researcher/benchmarks/router/results-published/2026-05-19.md) (600/600 usable records, 0 format failures)

Per-skill effect size for the three skills the data flagged:

| Skill | Baseline top-1 | After rewrite | Delta |
| --- | --- | --- | --- |
| `context-fundamentals` | 0.255 | 0.489 | +23.4pp |
| `project-development` | 0.750 | 1.000 | +25pp (now perfect) |
| `tool-design` | 0.729 | 0.807 | +7.8pp |

Per-model top-1 accuracy after the corpus-wide hardening pass:

| Model | Top-1 | Top-3 |
| --- | --- | --- |
| gemini-3.1-pro | 0.920 | 0.933 |
| composer-2 | 0.913 | 0.947 |
| gpt-5.5 | 0.913 | 0.973 |
| claude-opus-4-7 | 0.840 | 0.933 |

Reproduce any of these numbers exactly via the runner under `researcher/benchmarks/sdk-runner/`.

### What it includes

- **Source registry** (`researcher/source-registry.md`): priority sources, exclusion rules, monitoring queries.
- **Rubrics** (`researcher/rubrics/`): content curation, skill change, harness change, pairwise skill revision.
- **Mechanism registry** (`researcher/mechanisms/registry.jsonl` + `ledgers/`): 16 accepted behavior changes used as the primary novelty signal, with append-only accepted/rejected ledgers for institutional memory.
- **Claim provenance** (`researcher/claims/index.jsonl`): 12 provenance-tracked claims with source URL, evidence strength, volatility, and last reviewed date.
- **Corpus index** (`researcher/corpus/index.json`): canonical machine-readable map of skills, activation scenarios, mechanism IDs, and claim IDs.
- **Run state machine** (`researcher/runs/<run-id>/run-state.json`): `initialized -> retrieved -> evaluated -> proposed -> novelty_checked -> validated -> pr_ready -> closed`.
- **Activation regression tests** (`researcher/fixtures/activation-cases.jsonl`): 19 deterministic prompts that catch skill-boundary confusion.
- **Adversarial benchmark harness** (`researcher/benchmarks/`): scenarios that try to game the loop (duplicate mechanisms, unretrieved evidence, wrong rubric math, self-approved rubric changes, weak-evidence novelty).
- **Continuous loop** (`researcher/scripts/loop_*.py` + `researcher/orchestration/launchd/`): inbox, source discovery, one-state-at-a-time advancement, daily ops, parked review queue, launchd service definitions.
- **Skill health gate** (`researcher/scripts/skill_health.py`): deterministic body-quality scoring; current strict corpus score is 0.9117 with 0 flagged skills.

### Operator commands

Install the reference validator once before running the platform-compatibility gate locally:

```bash
python3 -m pip install skills-ref
```

```bash
# Deterministic gates (also run in CI on every PR)
python3 -m unittest researcher.scripts.tests.test_skill_frontmatter
python3 researcher/scripts/validate_platform_compat.py --require-reference-validator
python3 researcher/scripts/validate_repo.py --strict
python3 researcher/scripts/skill_health.py --strict --no-history
python3 researcher/scripts/run_benchmarks.py
python3 researcher/scripts/check_activation_cases.py

# Per-run readiness (active runs only)
python3 researcher/scripts/validate_run.py --run-dir researcher/runs/<run-id>

# Continuous loop, manual
python3 researcher/scripts/loop_discover.py
python3 researcher/scripts/loop_step.py --allow-fetch
python3 researcher/scripts/loop_daily.py
python3 researcher/scripts/loop_status.py

# Continuous loop, daemon (macOS)
researcher/orchestration/launchd/install.sh    # install launchd jobs (10-min step, 12h discover, daily ops)
researcher/orchestration/launchd/uninstall.sh  # remove launchd jobs
```

See [researcher/runbooks/continuous-operation.md](researcher/runbooks/continuous-operation.md) for daemon details, budgets, and the human review surface.

### Guarantees

- The loop never invokes paid LLMs or makes outbound writes; HTTP retrieval is stdlib-only with a 1.5 MB cap and a 30-second timeout.
- Mechanism promotion requires a recorded human reviewer and a passing run-readiness check.
- All queue mutations are atomic (temp file + `os.replace`) and serialized via `fcntl` locks.
- Agents may prepare PRs after gates pass; merge and push remain human-controlled.

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

Feel free to contact [Muratcan Koylan](https://x.com/koylanai) for collaboration opportunities or any inquiries.

## License

MIT License - see LICENSE file for details.

## References

The principles in these skills are derived from research and production experience at leading AI labs and framework developers. Each skill includes references to the underlying research and case studies that inform its recommendations.
