---
name: linkedin-analytics
description: Deep-dive intelligence on content performance. Transforms raw metrics into strategic insights (Keep, Stop, Start).
model: sonnet
bundle: content-strategy
triggers:
  - "analyze my LinkedIn performance"
  - "what content is working"
  - "LinkedIn metrics"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# LinkedIn Analytics (The Data Scientist)

Numbers tell a story. This skill translates "Likes" and "Views" into actionable strategy. It answers the question: "Is my content strategy actually working?"

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Engagement Rate Calculation                                  │
│  ✓ Format Performance Analysis (Carousel vs Text vs Video)      │
│  ✓ Topic Resonance Mapping                                      │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~puppeteer-mcp / ~~linkedin-mcp)        │
│  + Browser Investigation: Scrapes public profile stats.         │
│  + Competitor Spy: Analyzes top-performing posts of rivals.     │
│  + Real-Time Fetch: grabs latest metrics without API keys.      │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠 Triggers

- "Analyze my LinkedIn performance"
- "Why did this post fail?"
- "Investigate this competitor's strategy"
- "What is my engagement rate this month?"

## 🛠 Agent Instructions

### Before Analyzing

1.  **Load Context Profiles**:
    - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/business-profile.json` (Goals).
    - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/analytics-history.json` (Past Performance).
2.  **Choose Data Source**:
    - _If `puppeteer-mcp` is active_: Use `browser_navigate` to fetch real-time data from the profile URL.
    - _If `linkedin-mcp` is active_: Use API to fetch stats.
    - _Else_: Ask user to paste the "Analytics" text or screenshot.

---

## 📊 The Analysis Matrix

### Metric 1: The "Scroll-Stop" (Views vs. Clicks)

- **Formula**: `Clicks / Views`
- **Meaning**: Is the Hook working?
- **Action**: If low, rewrite hooks. Use `antislop-expert` to punch them up.

### Metric 2: The "Resonance" (Likes/Comments vs. Views)

- **Formula**: `(Likes + Comments) / Views` (Engagement Rate)
- **Meaning**: Is the content valuable?
- **Action**: If low, improve the Payload (Body). If high but low views, improve availability/timing.

### Metric 3: The "Virality" (Shares/Reposts)

- **Meaning**: Is this identity-affirming?
- **Action**: Optimize for "Public Utility" (Guides, Lists).

---

## 🔄 Routine Workflows

### The "Monday Morning Review"

1.  **Fetch**: Last 7 days of posts.
2.  **Sort**: Best to Worst.
3.  **Diagnose**:
    - "Why did Post A win?" (e.g., Controversial hook).
    - "Why did Post B lose?" (e.g., Posted Friday PM, weak formatting).
4.  **Update Strategy**: "Do more of A, less of B."

### The "Competitor Investigation" (Browser Mode)

1.  **Navigate**: Go to Competitor's "Posts" tab.
2.  **Scrape**: Identify top 3 posts by reaction count.
3.  **Reverse Engineer**:
    - What hooks did they use?
    - What time did they post?
    - What topics are they covering?

---

## 📝 Output Format

```markdown
# 📈 Performance Intelligence Report

**Period**: Last 30 Days
**Overall Grade**: B+

## 🏆 The Winners (Re-purpose these!)

1. **[Post Title]**
   - 👁️ Views: 15,200
   - 💬 Engagement: 4.5%
   - 💡 _Why it won_: The "How-to" structure combined with a personal failure story.

## 📉 The Losers (Learn from these)

1. **[Post Title]**
   - 👁️ Views: 800
   - 💡 _Why if failed_: The hook was vague ("Thoughts on AI"). No clear value prop.

## 🧭 Strategic Directives (Next 30 Days)

### START (New Experiments)

- Try "Carousel" format for technical guides.

### STOP (Resource Drains)

- Stop posting "Generic Motivational Quotes".

### CONTINUE (Double Down)

- Keep writing "Contrarian Takes" on SaaS Pricing.
```

---

## 🔬 Sentinel Integration (when installed)

```python
SENTINEL_ROOT = "${CLAUDE_PLUGIN_ROOT}/../sentinel-v8"
sentinel_installed = file_exists(f"{SENTINEL_ROOT}/.claude-plugin/plugin.json")
```

Skip this section entirely if `sentinel_installed` is False. LinkedIn Analytics works identically without it.

### Trigger condition
Two activation points — pre-publish and post-analysis. Both are opt-in; user must explicitly enable prediction tracking.

### What to run

**Pre-publish — calibration prediction (opt-in)**

When a post is finalized in `linkedin-post` or `linkedin-scheduler`, optionally prompt:

> "Track your prediction? State expected impressions and confidence (e.g. '500 impressions, 60% confident'). Takes 5 seconds, builds your content intuition over time."

If user agrees, record via `calibration-coach`:
```json
{
  "decision": "LinkedIn post: [first 8 words of post]",
  "prediction": "[N] impressions within 7 days",
  "confidence": [stated_confidence],
  "review_date": "[publish_date + 7 days]",
  "resolved": false,
  "context": { "format": "[post format]", "topic": "[topic]", "day": "[day of week]" }
}
```

**Post-analysis — SM2 check (attribution)**

Load bias SM2 from `../sentinel-v8/domains/strategy-marketing/biases.yaml`.

When linkedin-analytics produces a Keep / Stop / Continue recommendation, apply one check before finalizing each recommendation:

> "What else changed in the [period] that could explain this result?"

Require one alternative explanation per major conclusion. Example:
- "Contrarian posts performed 3x better" → alternative: "You posted them on Tuesday; your standard posts go out Friday. Day-of-week may explain the difference."

Flag any recommendation that attributes performance to a single variable without ruling out confounders.

**Calibration review (when 10+ predictions resolved)**

Run `calibration-coach` analysis:
`python3 ../sentinel-v8/skills/decision-hygiene/scripts/calibration.py --ledger ../sentinel-v8/data/decision-ledger.json --filter linkedin`

Output:
- Your content prediction accuracy over time
- Where you're systematically wrong: "You overestimate personal story posts by 40%, underestimate how-to posts by 25%"
- One actionable recommendation for improving your content intuition

### Output format addition

**If predictions are tracked**, add to the analytics output:

```
## Prediction Accuracy (Sentinel)

Posts tracked: [N] | Resolved: [N]
[If enough data]:
  Your accuracy pattern:
  - [Format/topic] posts: you predict [X], typically get [Y] ([over/under] by [Z%])
  - Best-calibrated: [format] posts
  Recommendation: [one specific calibration adjustment for next month]

Attribution check on top recommendation:
"[Keep/Stop/Continue recommendation]"
→ Alternative explanation considered: [what else could explain this]
→ Confidence in recommendation: [High if alternatives ruled out / Medium if not]
```

### Standalone output (Sentinel not installed)
Standard performance analysis with Keep / Stop / Continue recommendations and 30-day strategic directives. No change.
