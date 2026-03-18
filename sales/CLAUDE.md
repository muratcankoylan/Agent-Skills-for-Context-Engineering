# Sales-Brain: Working Memory

<!-- ═══════════════════════════════════════════════════════════
     ZONE 1 — STATIC CONFIG (never changes between sessions)
     Fully cacheable. Do not place dynamic content in this zone.
     ═══════════════════════════════════════════════════════════ -->

## Ecosystem Detection

At the start of every session, check whether Solo (core plugin) is installed:

```python
SALES_ROOT = "${CLAUDE_PLUGIN_ROOT}"
SOLO_ROOT  = "${CLAUDE_PLUGIN_ROOT}/../solo"

solo_installed = file_exists(f"{SOLO_ROOT}/.claude-plugin/plugin.json")
```

**If Solo is installed (ecosystem mode):**
- Load DNA files from SOLO_ROOT: ../solo/data/2-Domaines/
- Write client signals to: ../solo/data/1-Projets/clients/
- Use ../solo/data/1-Projets/active-deals/ as the shared deal directory
- Announce: "Solo core detected — reading shared DNA, writing signals to Solo client files."

**If Solo is NOT installed (standalone mode):**
- Load DNA files from own data/2-Domaines/
- Write all data to own data/ directory
- All features work independently

## Shared DNA Paths

| File | Ecosystem path | Standalone path |
|------|---------------|-----------------|
| business-profile.json | ../solo/data/2-Domaines/ | data/2-Domaines/ |
| voice-dna.json | ../solo/data/2-Domaines/ | data/2-Domaines/ |
| icp.json | ../solo/data/2-Domaines/ | data/2-Domaines/ |
| sales-profile.json | data/2-Domaines/ (always local) | data/2-Domaines/ |

If DNA files are empty or missing and Solo is installed: prompt user to run /solo:start.
If standalone and DNA is missing: prompt user to run /sales:start.

## Language Directive

- Check: business_profile.language_preference (from DNA path above)
- If "fr": ALL artifacts (emails, scripts, plans) in French
- If "en": English
- Internal reasoning always in English

## Quality Control (Antislop)

- All draft content checked by antislop-expert skill
- Zero tolerance for: "delve", "tapestry", "demystify", "game-changer"
- When Solo is installed, antislop hook is managed centrally in Solo's hooks.json

## Sentinel Integration (Decision Hygiene)

```python
SENTINEL_ROOT      = "${CLAUDE_PLUGIN_ROOT}/../sentinel-v8"
sentinel_installed = file_exists(f"{SENTINEL_ROOT}/.claude-plugin/plugin.json")
```

If installed, announce: "Sentinel active — decision hygiene enabled for forecasts and deal decisions."

**Skills that invoke Sentinel automatically when installed:**

| Skill/Command | Trigger point | Sentinel agents invoked |
|--------------|--------------|------------------------|
| /forecast | After weighted forecast generated | calibration-coach, reality-checker |
| rfp-shredder | After GO/borderline score | questioner, failure-finder |
| negotiation-advisor | Before Phase 2 (strategy) | questioner, failure-finder |

Decision ledger path (shared across ecosystem): `../sentinel-v8/data/decision-ledger.json`

If Solo is also installed, use Solo's detection of Sentinel as primary.

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
- Never mask: current turn outputs, DNA file reads, active deal data
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

**Sales-specific**: Degradation most common in long deal-tracking sessions. Symptom: mixing CRM data from two different accounts in the same response. One deal = one focused session.

## Memory Layers

Five-layer memory architecture. Use the simplest layer that solves the problem.

| Layer | Persistence | Implementation | When to Use |
|-------|-------------|----------------|-------------|
| **Working** | Context window only | System prompt scratchpad | Always — optimize with attention-favored positions (start/end) |
| **Short-term** | Session-scoped | In-memory / temp files | Intermediate tool results, conversation state |
| **Long-term** | Cross-session | Key-value files (data/) | User preferences, domain knowledge, entity registries |
| **Entity** | Cross-session | Entity registry (data/) | Identity consistency — same person/company across sessions |
| **Temporal KG** | Cross-session + history | Graph with validity dates | Facts that change over time; prevents context clash |

**Sales memory mapping:**
| Layer | What lives here |
|-------|----------------|
| Working | Active deal being analyzed this turn |
| Short-term | Call notes for current session |
| Long-term | `data/deals/`, `data/contacts/`, `data/2-Domaines/` |
| Entity | Companies + people (CRM entities — same account across sessions) |

Start with filesystem memory. Add complexity only when retrieval quality degrades.
Consolidate at weekly intervals. Invalidate but don't discard — deal history matters.
Never pre-load all deals. Retrieve only the active deal's data slice.

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

**Sales-specific handoffs:**
- `win-loss-analyst-agent` receives: deal ID + outcome only (not full pipeline)
- `signal-trapper-agent` receives: trigger conditions only
- `pipeline-guardian-agent` reads shared deal directory directly (file system handoff)

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

**Sales-specific**: Never mix deal data from multiple accounts in one analysis. One deal = one focused session.

## Skills Discovery Protocol

On session start: reference bundle names + descriptions only. Load full skill content only when a specific skill is activated. Never load all 27 skills simultaneously.

Skill bundles (load by name, fetch content on activation):

| Bundle | load_priority | Skills |
|--------|--------------|--------|
| identity-tools | 1 (always pre-loaded) | icp-creator, voice-dna-creator, para-organizer |
| prospecting | 2 | account-research, competitive-intelligence, exa-search-expert, linkedin-prospector, outbound-sequence |
| pipeline-ops | 2 | client-management, daily-briefing, hubspot-sync, territory-planner |
| deal-execution | 3 | call-prep, create-an-asset, discovery-interview-prep, proposal-builder, rfp-shredder |
| deal-strategy | 3 | champion-builder, negotiation-advisor, objection-library, qbr-builder |
| linkedin-social | 3 | linkedin-creator, linkedin-engager, linkedin-orchestrator |
| coaching-quality | 4 | antislop-expert, email-coach, win-loss-analyzer |

---

<!-- ═══════════════════════════════════════════════════════════
     ZONE 2 — SEMI-STATIC STATE (set once by /sales:start)
     Rarely changes. Update only when sales profile changes.
     ═══════════════════════════════════════════════════════════ -->

## Sales Profile

[Waiting for onboarding via /sales:start. Run this command to initialize your sales profile.]

---

<!-- ═══════════════════════════════════════════════════════════
     ZONE 3 — DYNAMIC SESSION MEMORY (per-session state)
     Always last. High churn — never cache this zone.
     ═══════════════════════════════════════════════════════════ -->

## Active Deals Summary

- [No active deals yet.]

## Current Week Priorities

- [Run /sales:daily-briefing to populate.]

## Recent Signals Detected

- [No signals yet. Run /sales:start or connect Exa for daily scans.]
