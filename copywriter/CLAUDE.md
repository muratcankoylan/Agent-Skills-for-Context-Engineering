# Copywriter Studio Context (V2)

<!-- ═══════════════════════════════════════════════════════════
     ZONE 1 — STATIC CONFIG (never changes between sessions)
     Fully cacheable. Do not place dynamic content in this zone.
     ═══════════════════════════════════════════════════════════ -->

## Ecosystem Detection

At the start of every session, check whether Solo (core plugin) is installed:

```python
WRITER_ROOT = "${CLAUDE_PLUGIN_ROOT}"
SOLO_ROOT   = "${CLAUDE_PLUGIN_ROOT}/../solo"

solo_installed = file_exists(f"{SOLO_ROOT}/.claude-plugin/plugin.json")
```

**If Solo is installed (ecosystem mode):**
- Load DNA from: ../solo/data/2-Domaines/
- Write content calendar to: ../solo/data/2-Domaines/content-calendar.md
- Write publish records to: ../solo/data/4-Archives/content/
- Save drafts to: ../solo/data/1-Projets/ (shared PARA root)
- Announce: "Solo core detected — reading shared DNA, writing content outputs to Solo PARA structure."

**If Solo is NOT installed (standalone mode):**
- Load DNA from own: data/2-Domaines/
- Write calendar to: data/2-Domaines/content-calendar.md
- Write archives to: data/4-Archives/content/
- All features work independently

## Shared DNA Paths

| File | Ecosystem path | Standalone path |
|------|---------------|-----------------|
| business-profile.json | ../solo/data/2-Domaines/ | data/2-Domaines/ |
| voice-dna.json | ../solo/data/2-Domaines/ | data/2-Domaines/ |
| icp.json | ../solo/data/2-Domaines/ | data/2-Domaines/ |
| analytics-history.json | data/2-Domaines/ (always local) | data/2-Domaines/ |

If DNA files are empty or missing and Solo is installed: prompt user to run /solo:start.
If standalone and DNA is missing: prompt user to run /copywriter:start.

## Language Directive

**CRITICAL**: Check `business.language_preference` (from DNA path above).

- If `"fr"`: ALL output must be in French. Auto-translate source material.
- If `"en"`: Output in English.
- If `"bilingual"`: Match requested language, default to English.

## PARA Structure Paths

| Folder | Ecosystem path | Standalone path | Purpose |
|--------|---------------|-----------------|---------|
| PROJECTS | ../solo/data/1-Projets/ | data/1-Projets/ | Active writing assignments |
| AREAS | ../solo/data/2-Domaines/ | data/2-Domaines/ | Profiles and evergreen assets |
| RESOURCES | ../solo/data/3-Ressources/ | data/3-Ressources/ | Templates, research, transcripts |
| ARCHIVES | ../solo/data/4-Archives/ | data/4-Archives/ | Published work |
| INBOX | ../solo/data/0-Inbox/ | data/0-Inbox/ | Incoming content triggers |

## Anti-Slop Guard Word List

NEVER use: "delve", "tapestry", "landscape", "game-changer", "unleash", "elevate", "demystify", "revolutionize", "synergy", "leverage" (as verb).
ALWAYS use: Concrete nouns, active verbs, specific examples. Vary sentence length. Avoid "sandwich" paragraphs.
When Solo is installed, antislop hook runs centrally from Solo's hooks.json.

## Sentinel Integration (Decision Hygiene)

```python
SENTINEL_ROOT      = "${CLAUDE_PLUGIN_ROOT}/../sentinel-v8"
sentinel_installed = file_exists(f"{SENTINEL_ROOT}/.claude-plugin/plugin.json")
```

If installed, announce: "Sentinel active — content strategy decisions structured."

**Skills that invoke Sentinel automatically when installed:**

| Skill | Trigger point | Sentinel agents invoked |
|-------|--------------|------------------------|
| content-calendar-planner | Before cascade model runs | sentinel-diverge, strategy-marketing domain |
| linkedin-analytics | Before strategy recommendations | calibration-coach |

Decision ledger path: `../sentinel-v8/data/decision-ledger.json`

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
- Never mask: current turn outputs, DNA file reads, active draft data
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

**Copywriter-specific**: Degradation most common when generating multi-format content (post + newsletter + email) in one session. Symptom: voice drift — output starts sounding like generic AI copy. Reset voice context between formats.

## Memory Layers

Five-layer memory architecture. Use the simplest layer that solves the problem.

| Layer | Persistence | Implementation | When to Use |
|-------|-------------|----------------|-------------|
| **Working** | Context window only | System prompt scratchpad | Always — optimize with attention-favored positions (start/end) |
| **Short-term** | Session-scoped | In-memory / temp files | Intermediate tool results, conversation state |
| **Long-term** | Cross-session | Key-value files (data/) | User preferences, domain knowledge, entity registries |
| **Entity** | Cross-session | Entity registry (data/) | Identity consistency — same person/company across sessions |
| **Temporal KG** | Cross-session + history | Graph with validity dates | Facts that change over time; prevents context clash |

**Copywriter memory mapping:**
| Layer | What lives here |
|-------|----------------|
| Working | Draft being written this turn |
| Short-term | Research notes for current piece |
| Long-term | `data/2-Domaines/voice-dna.json`, `data/2-Domaines/content-calendar.md` |
| Entity | Brand voice + ICP (identity stays consistent across all content) |

Start with filesystem memory. Add complexity only when retrieval quality degrades.
Consolidate content archives monthly. Never pre-load full content history.

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

**Copywriter-specific handoffs:**
- `blog-agent`, `newsletter-agent`, `social-agent`: each receives voice-dna + ICP + task brief only, not prior content sessions
- `research-agent`: receives topic + ICP only, not full calendar context
- `wordpress-publisher`: receives final markdown + metadata only (file system handoff)

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

**Copywriter-specific**: Never generate multiple formats (LinkedIn + newsletter + email) in sequence without resetting voice context between formats. Each format = fresh voice context load.

## Skills Discovery Protocol

On session start: reference bundle names + descriptions only. Load full skill content only when a specific skill is activated. Never load all 20 skills simultaneously.

Skill bundles (load by name, fetch content on activation):

| Bundle | load_priority | Skills |
|--------|--------------|--------|
| identity-core | 1 (always pre-loaded) | business-profile-creator, voice-dna-creator, icp-creator |
| content-strategy | 2 | content-calendar-planner, linkedin-analytics, seo-blog-writer, title-brain |
| social-content | 2 | linkedin-post, linkedin-scheduler, twitter-thread, video-script-generator |
| long-form-conversion | 3 | newsletter-writer, sales-email-sequence, landing-page-copy |
| research-tools | 3 | exa-search-expert, reddit-research-insights, quote-extractor |
| content-ops | 4 | antislop-expert, social-media-bio-generator, wordpress-publisher |

---

<!-- ═══════════════════════════════════════════════════════════
     ZONE 2 — SEMI-STATIC STATE (set once by /copywriter:start)
     Rarely changes. Update only when copywriter profile changes.
     ═══════════════════════════════════════════════════════════ -->

## Copywriter Profile

[Waiting for onboarding via /copywriter:start. Run this command to initialize your copywriter profile.]

---

<!-- ═══════════════════════════════════════════════════════════
     ZONE 3 — DYNAMIC SESSION MEMORY (per-session state)
     Always last. High churn — never cache this zone.
     ═══════════════════════════════════════════════════════════ -->

## Content Calendar (Current Week)

- [No calendar yet. Run /copywriter:plan to generate.]

## Active Drafts

- [No active drafts.]

## Publishing Queue

- [No items queued for publishing.]
