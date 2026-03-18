---
name: content-calendar-planner
description: Strategic content planning for LinkedIn, Blog, and Newsletter. Orchestrates themes, repurposing workflows, and platform distribution based on business goals. Trigger with "plan my content for [month]", "build a content calendar", "what should I post this week", or "create my content strategy".
model: sonnet
bundle: content-strategy
triggers:
  - "plan my content for [month]"
  - "build a content calendar"
  - "what should I post"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# Content Calendar Planner (The Strategist)

The "Editor-in-Chief" of your content operation. Designs a strategic narrative that moves your audience from Awareness to Conversion using the Pillar-Cluster (Cascade) model.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (Core Planning)                                     │
│  ✓ Theme/Pillar Development                                     │
│  ✓ Cross-Platform Repurposing Logic                             │
│  ✓ 30-Day View & Weekly Breakdown                               │
│  ✓ Alignment with Business Goals                                │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (With Optional Tools)                             │
│  + Trend Injection: Integrate seasonal/industry events          │
│  + Launch Alignment: Sync with product releases                 │
│  + Resource Linking: Point to existing assets in `data/`        │
└─────────────────────────────────────────────────────────────────┘
```

## Load Strategic Context

Anchor every calendar in the user's reality before planning:

- **Business Goals**: `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/business-profile.json` (What are we selling this month?).
- **Audience Needs**: `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/icp.json` (What problems do they need solved?).
- **Voice DNA**: `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/voice-dna.json` (Ensure format matches style).
- **Constraints**: Frequency per platform, solo or team, primary channel (Blog or Newsletter as "Source of Truth").

## Workflow

1. **Assess** — "What one belief should the audience have by month end?" Check `business-profile.json` for current priority.
2. **Ideate** — Generate 10 raw ideas (3 how-to, 3 opinion, 2 case studies, 2 personal stories). Filter through `icp.json` pain points.
3. **Cascade** — Hero asset (long-form blog/newsletter) → Social splinters (LinkedIn/Twitter, 24-48h after Hero) → Short-form signals (daily notes/tweets).
4. **Assemble** — Place Heroes first (Tue/Thu). Schedule Splinters next. Fill gaps with curated/personal content.
5. **Mix Check** — 40% value, 30% proof, 20% personal, 10% sales. Adjust if skewed.

Output: Markdown table grid + production to-do list.

See `references/strategy.md` for the full Cascade Architecture, daily grid template, output format, and anti-patterns.

---

## 🔬 Sentinel Integration (when installed)

```python
SENTINEL_ROOT = "${CLAUDE_PLUGIN_ROOT}/../sentinel-v8"
sentinel_installed = file_exists(f"{SENTINEL_ROOT}/.claude-plugin/plugin.json")
```

Skip this section entirely if `sentinel_installed` is False. Content Calendar Planner works identically without it.

### Trigger condition
Activate **before** the Cascade model runs — specifically between the "Assess" step and the "Ideate" step. Sentinel must run before topics and channels are locked in, not after.

### What to run

**Step 1 — sentinel-diverge (perspective expansion before ideation)**

Invoke `sentinel-diverge` on the proposed monthly theme or content focus.

Generate 5 perspectives before any topic list is created:
1. **Skeptical reader** — "This person has seen 200 posts on this topic. What makes yours worth reading?"
2. **Your best client** — "Does this month's content address anything they're actively struggling with right now?"
3. **Competitor watching you** — "If a direct competitor saw this calendar, what would they do differently to outflank it?"
4. **New subscriber (first touchpoint)** — "Someone finds your content for the first time. What impression does this month create?"
5. **Search intent lens** — "What are people actually typing into Google when they have this problem?"

Present the 5 perspectives. Ask: "Which perspective shifted your thinking?" Let the answer refine the theme before ideation begins.

**Step 2 — SM1 check (channel selection)**

Load bias SM1 from `../sentinel-v8/domains/strategy-marketing/biases.yaml`.

For each channel in the proposed mix, require:
- Evidence of past performance on this channel (impressions, clicks, conversions — anything real)
- If no past data exists: flag as "assumed ROI, no evidence"

Flag any channel being added because of a trend, a tool feature, or a competitor's success — without the user's own performance data to support it.

**Step 3 — SM7 check (KPI selection)**

Load bias SM7 from the same file.

Review the proposed KPIs for the calendar. For each metric, ask:
> "What is the correlation between [this metric] and revenue or client acquisition?"

Flag any metric that cannot be connected to a business outcome (impressions, likes, follower count as primary KPIs).

Require at least one revenue-adjacent metric: email signups, DM conversations, consultation bookings, link clicks to offer pages.

**Step 4 — campaign pre-mortem (after calendar is assembled)**

After the calendar grid is built, run a lightweight pre-mortem using the strategy-marketing template at `../sentinel-v8/domains/strategy-marketing/templates/campaign-premortem.md`.

> "It's 3 months later. The content calendar underdelivered — fewer leads, lower engagement than expected, no meaningful business impact. What happened?"

Generate 3 failure modes specific to content:
- Topics were right but distribution was wrong (great posts, wrong platform, wrong time)
- Volume was maintained but quality dropped (quantity target overrode content quality)
- Calendar was planned but not executed (planning completed, publishing stalled at week 2)

### Output format addition

Insert a **Content Strategy Audit** section before the calendar grid:

```
## Content Strategy Audit (Sentinel)

Theme stress-test — perspective that shifted thinking:
"[the perspective and what it revealed]"

Channel hygiene:
✅ [channel] — evidence-based ([metric])
⚠️  [channel] — assumed ROI, no personal data yet. Consider starting with 2 posts before committing full month.

KPI check:
✅ [revenue-adjacent metric]
⚠️  [vanity metric] — track separately, don't optimize for it

Pre-mortem top risks:
1. [failure mode] → Prevention: [specific action in week 1]
2. [failure mode] → Prevention: [specific action]
```

Calendar grid follows immediately after.

### Standalone output (Sentinel not installed)
Standard Cascade model: assess → ideate → cascade → assemble → mix check. No change.
