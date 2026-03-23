# Skills Improvement Analysis: Lessons from Anthropic's "Building Claude Code" Article

*Analysis date: 2026-03-17*
*Source: "Lessons from Building Claude Code: How We Use Skills" — Anthropic Team*

---

## What We're Already Doing Well

**Description field as trigger conditions** — 100% compliance. Every SKILL.md uses the "use when X" format the article recommends.

**Progressive disclosure via filesystem** — Our 3-level hierarchy (SKILL.md → references/ → scripts/) is textbook progressive disclosure. The article calls this out as a best practice.

**Composable scripts** — 12/13 skills include Python scripts with callable classes and functions.

**Not stating the obvious** — Skills focus on pushing Claude beyond defaults (e.g., U-shaped attention curves, observation masking, KV-cache tricks).

---

## The Big Gaps (Ordered by Impact)

### 1. Skills are knowledge-first, not action-first

The Anthropic team's 9 skill categories are overwhelmingly **operational** — verification, scaffolding, automation, runbooks, deployment. Our 13 skills are overwhelmingly **conceptual** — teaching Claude about context engineering principles.

The article says the most powerful thing you can give Claude is **code it can compose at runtime**, not knowledge it reads and internalizes. Our `scripts/` directories contain reference implementations (demonstration code), not composable helper libraries Claude would actually import and use during a task.

**The shift**: Our skills teach Claude *about* context engineering. The article suggests skills should help Claude *do* context engineering.

### 2. ~~No Gotchas sections (69% of skills)~~ — RESOLVED

> **Status**: Fixed in commit c847b20. All 13 skills now have standardized Gotchas sections (5-9 gotchas each). Template updated with canonical Gotchas section.

~~The article is unambiguous: *"The highest-signal content in any skill is the Gotchas section."* Only 4 of 13 skills had one. The root cause was our `template/SKILL.md` didn't include a Gotchas section — so new skills never got one by default.~~

### 3. No on-demand hooks

The article highlights on-demand hooks as a differentiator. Examples like `/careful` (blocks destructive commands) and `/freeze` (blocks edits outside a directory) show how hooks transform a knowledge skill into a guardrail. None of our skills use this.

For a context engineering marketplace, natural fits include:
- `/budget` — warns when context usage exceeds a threshold
- `/trace` — logs every tool call with token counts for post-hoc analysis
- `/compress` — auto-triggers compression when conversation gets long

### 4. No setup/config pattern

The article recommends a `config.json` pattern for skills needing user context. None of our skills use this. For example, `memory-systems` could ask which framework the user is using and store that preference.

### 5. No measurement infrastructure

The article describes using `PreToolUse` hooks to track which skills are popular and which are undertriggering. We have no way to know if skills are actually being activated correctly.

### 6. No `${CLAUDE_PLUGIN_DATA}` usage

The article emphasizes persistent data storage so skills can learn over time. Our skills are stateless — they forget everything between sessions.

---

## Strategic Recommendations

### Tier 1: Quick wins (high impact, low effort)

**A. Add Gotchas to template and all 9 missing skills**

Update `template/SKILL.md` to include a `## Gotchas` section. Then add gotchas to the 9 skills that lack them. These should capture real failure modes, not theoretical ones. Examples:
- `context-compression`: "Don't compress tool definitions — models need exact schemas"
- `multi-agent-patterns`: "Sub-agents sharing context via message passing doubles token cost vs. filesystem coordination"
- `context-optimization`: "Prefix caching breaks when system prompts change between turns"

**B. Add a marketplace curation flow**

Add a `sandbox/` directory for experimental skills. Update CONTRIBUTING.md to describe sandbox → traction → marketplace flow.

**C. Update SKILL.md template with article best practices**

Add sections for: Gotchas, Setup Requirements, Related Scripts, Storage Expectations.

### Tier 2: Structural enhancements (medium effort, high differentiation)

**D. Create 2-3 operational skills to complement knowledge skills**

| Proposed Skill | Category | What It Does |
|---|---|---|
| `context-debugger` | Runbook | Symptom → investigation → diagnosis for context failures |
| `agent-scaffolding` | Code Scaffolding | Generates boilerplate for new agent projects |
| `skill-creator` | Code Scaffolding | Meta-skill that helps create new skills following conventions |

**E. Make scripts composable, not demonstrative**

Transform scripts from "here's how you'd implement this" to "import this and use it":

```python
# Before (reference): Shows how compaction works
class ContextCompactor:
    """Example implementation..."""

# After (composable): Claude actually uses this
def compact_observation(output: str, max_tokens: int = 500) -> str:
    """Compact a tool observation to fit within token budget."""
```

**F. Add on-demand hooks to 2-3 skills**

Start with:
- `context-optimization` → hook that warns on large tool outputs
- `evaluation` → hook that auto-evaluates Claude's output quality
- `context-compression` → hook that monitors conversation length

### Tier 3: Ecosystem maturity (higher effort, long-term value)

**G. Add a usage measurement skill** — `PreToolUse` hook logging skill activations.

**H. Add config.json setup** to framework-dependent skills (memory-systems, multi-agent-patterns).

**I. Create a "skill composition" example** — showing how skills invoke each other.

**J. Add persistent learning via `${CLAUDE_PLUGIN_DATA}`** — skills that get better over time.

---

## The Meta-Insight

Our repository is currently a **textbook** — it teaches Claude how to think about context engineering. The Anthropic article reveals that the most impactful skills at Anthropic are **toolboxes** — they give Claude things to do, not things to know.

The strongest version of this repo is both: **knowledge skills that also include operational capabilities**. The knowledge foundation is what got us cited in academic papers. Layering actionable tooling on top (gotchas, hooks, composable scripts, persistent state) would make the skills dramatically more useful in practice.

---

## Audit Summary Table

| Criterion | Status | Score | Notes |
|-----------|--------|-------|-------|
| Gotchas Sections | CRITICAL GAP | 31% (4/13) | Highest-signal content per article |
| Description Format | PERFECT | 100% (13/13) | Trigger-condition format |
| Composable Scripts | STRONG | 92% (12/13) | Present but reference-grade |
| On-Demand Hooks | NOT IMPLEMENTED | 0% (0/13) | High differentiation opportunity |
| Config/Setup Pattern | NOT IMPLEMENTED | 0% (0/13) | Needed for framework-dependent skills |
| Persistent Storage | MINIMAL | 23% (3/13) | No `${CLAUDE_PLUGIN_DATA}` usage |
| Progressive Disclosure | COMPREHENSIVE | 100% (13/13) | SKILL.md → references/ → scripts/ |
| Templates/Assets | COMPREHENSIVE | 100% (13/13) | All have reference docs |

**Overall compliance: 65%** — Closing the Gotchas gap alone raises this to ~85%.

---

## Anthropic's 9 Skill Categories vs. Our Coverage

| Category | Coverage | Our Skills |
|----------|----------|------------|
| Library & API Reference | Moderate | memory-systems, tool-design |
| Product Verification | Moderate | evaluation, advanced-evaluation |
| Data Fetching & Analysis | Light | (interleaved-thinking example only) |
| Business Process & Automation | Light | (digital-brain example only) |
| Code Scaffolding & Templates | Light | project-development |
| Code Quality & Review | Moderate | evaluation, advanced-evaluation |
| CI/CD & Deployment | Light | hosted-agents |
| Runbooks | Light | context-degradation |
| Infrastructure Operations | Light | hosted-agents |
