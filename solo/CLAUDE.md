# Solo Plugin — Context Memory

<!-- ═══════════════════════════════════════════════════════════
     ZONE 1 — STATIC CONFIG (never changes between sessions)
     Fully cacheable. Do not place dynamic content in this zone.
     ═══════════════════════════════════════════════════════════ -->

## Ecosystem Detection

Solo is the core plugin. At the start of every session, detect which addon plugins are installed by checking for their plugin files relative to Solo's root:

- `${CLAUDE_PLUGIN_ROOT}/../sales/.claude-plugin/plugin.json` → Sales addon
- `${CLAUDE_PLUGIN_ROOT}/../copywriter/.claude-plugin/plugin.json` → Copywriter addon
- `${CLAUDE_PLUGIN_ROOT}/../sentinel-v8/.claude-plugin/plugin.json` → Sentinel addon

Announce detected addons in the first response of each session:
- If sales installed: "Sales addon detected — pipeline and deal intelligence active."
- If copywriter installed: "Copywriter addon detected — content calendar and publishing active."
- If sentinel installed: "Sentinel active — structured decision hygiene enabled."

## Shared DNA (Single Source of Truth)

These files live in Solo and are read by all installed addons. Solo creates them on /solo:start.

| File | Path | Used by |
|------|------|---------|
| business-profile.json | data/2-Domaines/business-profile.json | Solo + Sales + Copywriter |
| voice-dna.json | data/2-Domaines/voice-dna.json | Solo + Sales + Copywriter |
| icp.json | data/2-Domaines/icp.json | Solo + Sales + Copywriter |
| content-calendar.md | data/2-Domaines/content-calendar.md | Solo (reads) + Copywriter (writes) |
| clients/ | data/1-Projets/clients/ | Solo (manages) + Sales (writes signals) |

If DNA files are empty or missing: prompt user to run /solo:start first.

## Cross-Plugin Data Flows

Solo receives from Copywriter (when installed):
- /copywriter:plan writes content calendar to data/2-Domaines/content-calendar.md
- blog-agent writes publish records to data/4-Archives/content/[slug]-[date].md
- monday-morning-agent and weekly-digest-agent read both paths automatically

Solo receives from Sales (when installed):
- signal-trapper-agent appends signals to data/1-Projets/clients/[Company].md
- pipeline-guardian-agent reads data/1-Projets/active-deals/ (shared path)

Solo provides to all addons:
- /solo:start creates all three DNA files in the canonical schema
- data/ is the shared filesystem root for the entire ecosystem

## Language & Localization

- Check: data/2-Domaines/business-profile.json → business_profile.language_preference
- If "fr": ALL outputs (reports, emails, proposals, content) must be in French
- If "en": ALL outputs in English
- If missing: default English, then ask user preference

## Sentinel Integration (Decision Hygiene)

Decision ledger path (shared across ecosystem): `../sentinel-v8/data/decision-ledger.json`

Skills that invoke Sentinel automatically when installed:

| Skill | Trigger point | Sentinel agents invoked |
|-------|--------------|------------------------|
| idea-test | After GO/LEARN MORE verdict | failure-finder, questioner |
| launch-planner | Before D-14 calendar generation | failure-finder, reality-checker, calibration-coach |
| pricing-strategy | Before rate card save | reality-checker, sentinel-reframe |
| tam-sam-som-calculator | After SOM calculation | reality-checker, questioner |

## Token Budget

| Category              | Target  | Max     |
|-----------------------|---------|---------|
| System + DNA refs     | 2,000   | 3,000   |
| Active skill content  | 3,000   | 5,000   |
| Tool outputs (recent) | 4,000   | 8,000   |
| Message history       | 5,000   | 10,000  |
| Reserved buffer       | 2,000   | —       |

Trigger context compression when message history exceeds 10,000 tokens.

## Observation Masking

Tool outputs that are 3+ turns old AND whose purpose has been served:
- Replace with: `[Ref: <tool_name> result turn N — key finding: <1 sentence>]`
- Never mask: current turn outputs, DNA file reads, active client data
- Always mask: repeated glob results, boilerplate template reads already used

## Context Compression

At 70-80% utilization, generate an Anchored Iterative Summary:

### Session Intent
### Files Modified
### Decisions Made
### Current State
### Next Steps

## Degradation Indicators

### Failure Symptoms
- **Lost-in-middle**: Information placed in context middle receives 10-40% lower recall accuracy
- **Context poisoning**: Degraded output quality, tool misalignment, persistent hallucinations — usually from contradictory or stale content accumulating
- **Confusion**: Agent contradicts prior tool outputs or misapplies instructions from 3+ turns ago
- **Context clash**: Two valid-but-conflicting facts in context with no versioning — agent oscillates

### Model-Specific Degradation Thresholds
| Model | Degradation Onset | Severe Degradation |
|-------|-------------------|-------------------|
| Claude Sonnet 4.6 | ~80K tokens | ~150K tokens |
| Claude Opus 4.6 | ~100K tokens | ~180K tokens |

### Recovery Protocol
1. If poisoning suspected: identify the offending turn, truncate to before it
2. Restart with verified-only information; flag the discard explicitly
3. Never retry the same prompt on a poisoned context — it will reproduce the same failure
4. If confusion persists after truncation: start fresh session, pass only the 3 most critical facts

### Prevention
- Compress at 70-80% before reaching degradation onset
- Validate retrieved documents before adding to context
- Segment long-running tasks at logical boundaries
- Keep a single source of truth per fact — no duplicates at different versions

**Solo-specific**: Degradation most common when multiple clients are active in one session. Symptom: mixing client data — financial figures or contact info crossing client boundaries. Load only the active client's data slice per session.

## Memory Layers

Five-layer memory architecture. Use the simplest layer that solves the problem.

| Layer | Persistence | Implementation | When to Use |
|-------|-------------|----------------|-------------|
| **Working** | Context window only | System prompt scratchpad | Always — optimize with attention-favored positions (start/end) |
| **Short-term** | Session-scoped | In-memory / temp files | Intermediate tool results, conversation state |
| **Long-term** | Cross-session | Key-value files (data/) | User preferences, domain knowledge, entity registries |
| **Entity** | Cross-session | Entity registry (data/) | Identity consistency — same person/company across sessions |
| **Temporal KG** | Cross-session + history | Graph with validity dates | Facts that change over time; prevents context clash |

**Solo memory mapping:**
| Layer | What lives here |
|-------|----------------|
| Working | Active client or task being worked this turn |
| Short-term | Current session context (proposals, calls, notes) |
| Long-term | `data/2-Domaines/` DNA files, `data/1-Projets/clients/`, `data/1-Projets/active-deals/` |
| Entity | Clients + companies (same entity across pipeline, invoices, and comms) |

Start with filesystem memory (already implemented via PARA structure). Add complexity only when retrieval quality degrades.
Consolidate client archives quarterly. Never discard — revenue history and deal history matter for forecasting.

## Context Isolation Protocol

Sub-agents exist to isolate context, not to anthropomorphize roles.
Each sub-agent should operate in clean context focused on its specific subtask.

### Isolation Mechanisms
1. **Full context delegation** — Sub-agent receives entire context. Use when sub-agent needs full history.
2. **Instruction passing** — Sub-agent receives only task-specific instructions + minimal context. Use for most cases.
3. **File system handoff** — Sub-agent reads/writes shared files. Use when state must persist beyond the call.

### Handoff Rules
- Pass the minimum context needed for the sub-task (not the entire conversation)
- Include: task description, relevant facts only, output format expected
- Exclude: conversation history, other sub-agent outputs, unrelated tool results
- Validate sub-agent output before incorporating into parent context
- Use `forward_message` pattern when sub-agent response should go directly to user

### Token Economics
| Architecture | Token Multiplier |
|--------------|-----------------|
| Single agent | 1× |
| Single agent + tools | ~4× |
| Multi-agent | ~15× |

**Solo-specific handoffs:**
- `client-lifecycle-agent`, `invoice-reminder-agent`: receive client ID + relevant data slice only — never the full client roster
- `monday-morning-agent`, `weekly-digest-agent`: read shared filesystem paths directly (file system handoff)
- `diagnostic-monitor-agent`: receives diagnostic ID + new responses only, not full session history

## Anti-Patterns

### Context Management
- **Stuffing everything into context**: Load only what the current task needs. Long contexts are expensive and degrade performance.
- **Not compressing before degradation**: Compression at 90% is too late — apply at 70-80% to stay ahead of degradation.
- **Masking critical observations**: Never mask the most recent turn, active task observations, or current reasoning chain.
- **No consolidation strategy**: Unbounded memory growth degrades retrieval quality over time.

### Multi-Agent
- **Anthropomorphizing sub-agents**: Sub-agents isolate context; they don't simulate org charts. Structure by context boundary, not by role name.
- **Supervisor synthesis errors**: Supervisors paraphrase sub-agent responses and lose fidelity. Use `forward_message` for direct pass-through when possible.
- **No output validation**: Always validate sub-agent output before incorporating into parent context.
- **Unbounded execution**: Set time-to-live limits on all agent invocations.

### Information Management
- **Duplicate facts at different versions**: Keep one source of truth per fact. Multiple versions cause context clash.
- **Ignoring temporal validity**: Facts go stale. Without validity tracking, outdated information poisons responses.
- **Coherence as quality signal**: Coherent-sounding responses can be wrong. Use structured verification, not fluency.

**Solo-specific**: Never load all client data at session start. Load only the active client's data slice. The PARA structure exists precisely for this — use it as the retrieval boundary.

## Skills Discovery Protocol

On session start: reference bundle names + descriptions only. Load full skill content only when a specific skill is activated. Never load all 44 skills simultaneously.

Skill bundles (load by name, fetch content on activation):

| Bundle | load_priority | Skills |
|--------|--------------|--------|
| core-identity | 1 (always pre-loaded) | business-profile-creator, voice-dna-creator, icp-creator, positioning-statement, para-organizer |
| client-work | 2 | client-management, client-onboarding, discovery-call, proposal-generator, scope-management, contract-templates |
| revenue-ops | 2 | invoice-generator, expense-tracker, financial-health, retainer-manager, pricing-strategy, product-pricing-model |
| sales-growth | 3 | sales-pipeline, draft-outreach, company-research, competitive-analyzer, exa-search-expert, reddit-research-insights, landing-page-builder |
| product-build | 3 | pipeline-orchestrator, prd-development, user-story, design-brief-generator, problem-statement, proto-persona |
| research-validate | 3 | user-discovery, tam-sam-som-calculator, customer-journey-map, idea-test |
| diagnostics | 4 | diagnostic-builder, diagnostic-runner, diagnostic-analyzer, tally-integration |
| operations | 4 | weekly-review, project-management, capacity-planner, business-health-advisor, launch-planner, antislop-expert |

## Glossary

| Term | Meaning |
|------|---------|
| PARA | Projects, Areas, Resources, Archives |
| DNA files | business-profile, voice-dna, icp — shared identity layer |
| Standalone | Solo works fully without addons |
| Ecosystem | All three plugins in same Cowork folder |

---

<!-- ═══════════════════════════════════════════════════════════
     ZONE 2 — SEMI-STATIC STATE (set once by /solo:start)
     Rarely changes. Update only when business profile changes.
     ═══════════════════════════════════════════════════════════ -->

## Me

[Waiting for onboarding via /solo:start. Run this command to initialize your business profile.]

---

<!-- ═══════════════════════════════════════════════════════════
     ZONE 3 — DYNAMIC SESSION MEMORY (per-session state)
     Always last. High churn — never cache this zone.
     ═══════════════════════════════════════════════════════════ -->

## Active Clients

- [No clients yet. Add one via /solo:clients add]

## Current Pipeline

- [No opportunities in pipeline.]

## Revenue Tracking

- **MRR:** $0
- **Quarterly Target:** $0
