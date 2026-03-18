---
name: linkedin-engager
description: >
  Generates authentic, bilingual LinkedIn comments (15-50 words) and manages prospect warming cadence.
  Combines "Authentic Commenting" (Mirror & Add) with "ICP Warming" (Smart Scoring, 2-3 day gaps).
  Detects post language (EN/FR) and generates comments in the same language.
  Enforces "Nexius Style" (No em-dashes, specific examples).
  Tracks touch points in `activity_log.md` and moves prospects from 0->3 touches.
bundle: linkedin-social
triggers:
  - "engage on LinkedIn"
  - "write LinkedIn comment"
  - "warm up prospect"
tools:
  standalone: [filesystem]
  supercharged: [linkedin]
version: 1.0.0
---

# LinkedIn Engager (The Diplomat)

A dual-purpose skill that:

1.  **Generates Comments**: Authentic, high-value comments (15-50 words) in EN or FR.
2.  **Manages Warming**: Tracks prospect touches (0->3) to build relationships before connecting.

## Configuration

- **Reads**: `data/2-Domaines/sales-profile.json` (for `selling_methodology` alignment).
- **Reads**: `data/2-Domaines/LinkedIn/prospects.md` (for prospect status).
- **Reads**: `data/2-Domaines/LinkedIn/activity_log.md` (for touch history).

## Triggers

- "write comment"
- "warm up prospects"
- "engage"
- "reply to this"

## Mode 1: Comment Generation (The Art)

**Goal**: Prove you read the post. Add value. Start a conversation.

### Bilingual Logic (Auto-Detect)

1.  **Analyze Post**: Detect language (English vs French).
2.  **Switch Mode**:
    - IF French: Use French formulations ("C'est pertinent...", "Tout à fait d'accord sur...").
    - IF English: Use English formulations.
3.  **Output**: Generate comment in the **same language** as the post.

### Style Guide ("Nexius Style")

- **Length**: STRICTLY 15-50 words.
- **Formatting**: **NO Em-dashes (—)**. Use commas or periods.
- **Tone**: Professional peer, not fanboy.
- **Banned**: "Great post!", "Thanks for sharing", "Insightful".
- **Required**: Specific reference to post content + New perspective/question.

### Comment Archetypes

1.  **The Builder (Extension)**: "Yes, and [specific experience]..."
2.  **The Architect (Reframing)**: "Interesting. In my deployments, I've seen [counter-pattern]..."
3.  **The Engineer (Question)**: "Does this handle [edge case]? That's where we usually see friction."

---

## Mode 2: Warming Orchestration (The Science)

**Goal**: Move prospects from 0 to 3 touches (Connection Ready) without spamming.

### The 3-Touch Journey

1.  **Touch 0 (Discovery)**: Found in `prospects.md`.
2.  **Touch 1 (Validation)**: Like + Comment on recent post.
3.  **Touch 2 (Reinforcement)**: Reply to their comment OR Comment on 2nd post (3 days later).
4.  **Touch 3 (Connection)**: Send Connection Request (Blank or Contextual).

### Smart Scoring (Priority)

Rank prospects by:
`Score = ICP_Fit (0-100) + Recency (0-10) + Inbound_Signal (0-15)`

- **🔥 HIGH (120+)**: Engage TODAY. (2 touches done, active poster).
- **🟡 MEDIUM (90-119)**: Engage this week. (1 touch done).
- **🆕 NEW**: Start warming (0 touches).

### Dedup & Safety Rules

1.  **2-Day Gap**: Never engage same prospect twice in 48h (looking desperate).
2.  **Post Dedup**: Check `activity_log.md`. If `post_url` exists in logs, SKIP.
3.  **Language Check**: If prospect posts in FR, engage in FR.

---

## Quality Control (Automated via Hooks)

- **Antislop Check**: Even short comments are checked by `antislop-expert`.
- **Banned Patterns**: "Delve", "Leverage", "Synergy" -> Auto-rejected.

## Workflow: "Warm Up Prospects"

1.  **Read Logs**: Load `prospects.md` and `activity_log.md`.
2.  **identify Candidates**:
    - Filter: Not connected.
    - Filter: Last touch > 48h ago.
    - Sort: Smart Score desc.
3.  **Find Content**:
    - Agent scans prospect's recent activity (via Browser).
    - Checks for "Commentable" posts (not shared/reposted without text).
4.  **Generate Comment**:
    - Applies **Mode 1** logic (Bilingual/Style).
5.  **Execute**:
    - Agent posts comment.
    - **Log Update**: Appends to `activity_log.md` -> "Warming Up" table.
    - Increment `touch_count`.

## Output Format (Comment Generation)

```
✅ SELECTED COMMENT (Style: Reframing)
Language: [EN/FR]
Refers to: "[Quote from post]"

[The Comment Text]
(34 words)

Reasoning: Validates their pain point about CRM data but shifts focus to process adherence.
```

## Output Format (Warmup Plan)

```
🎯 WARMING OPPORTUNITIES

1. [Name] (Touch 2/3) - 🔥 High Priority
   - Latest Post: [URL] (FR - "L'IA générative...")
   - Strategy: Agree with the security concern.
   - Action: Generate French comment.

2. [Name] (Touch 0/3) - 🆕 New
   - Latest Post: [URL] (EN - "Scaling sales...")
   - Strategy: Ask about the tech stack.
   - Action: Generate English comment.
```
