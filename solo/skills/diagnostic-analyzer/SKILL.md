---
name: diagnostic-analyzer
description: >
  Analyzes patterns across multiple diagnostic responses for a given diagnostic.
  Surfaces aggregate signals, identifies ICP fit patterns, flags outliers, and
  produces actionable recommendations for the Solo user. Triggered by
  "/solo:diagnose results [name]", "analyze my diagnostic results",
  "what are my leads scoring", "show me the diagnostic patterns".
version: 1.0.0
bundle: diagnostics
triggers:
  - "analyze diagnostic"
  - "diagnostic results"
  - "review assessment scores"
tools:
  standalone: ["filesystem"]
  supercharged: ["tally"]
---

# Skill: Diagnostic Analyzer

A single diagnostic response tells you about one person. Ten responses tell you about a pattern. The analyzer surfaces what the pattern reveals — about your ICP, your messaging, your offer, and your pipeline.

## When to Use

- After collecting 5+ responses on a single diagnostic
- During weekly review (via `diagnostic-monitor-agent`)
- Before a product build decision (product validation diagnostics)
- When pipeline quality feels off and you want data to explain why

---

## Analysis Components

### Component 1: Score Distribution

**For each diagnostic, show:**

```markdown
## Score Distribution: [Diagnostic Name]
**Total responses:** [N] | **Period:** [date range]

| Band | Respondents | % | Avg score |
|------|-------------|---|-----------|
| 🟢 High (66–100) | [N] | [X%] | [avg] |
| 🟡 Medium (36–65) | [N] | [X%] | [avg] |
| 🔴 Low (0–35) | [N] | [X%] | [avg] |

**Overall average:** [X] / 100
**Median:** [X]
**Range:** [min] – [max]
```

**What to flag:**
- If > 60% are Low → your diagnostic is reaching the wrong people, or the problem isn't real enough
- If > 70% are High → your diagnostic may be too easy, or you're only reaching pre-qualified people
- If the distribution is trimodal (peaks in all three bands) → you likely have 3 distinct sub-segments

---

### Component 2: Dimension Breakdown

**For each dimension, show the average score across all respondents:**

```markdown
## Dimension Averages

| Dimension | Avg score | % of max | Interpretation |
|-----------|-----------|----------|---------------|
| [Dim 1] | [X]/[max] | [X%] | 🟢 Healthy across respondents |
| [Dim 2] | [X]/[max] | [X%] | 🟡 Mixed — worth watching |
| [Dim 3] | [X]/[max] | [X%] | 🔴 Consistently weak |
| [Dim 4] | [X]/[max] | [X%] | |
```

**What consistently low dimensions reveal:**

| Diagnostic type | Low dimension | Likely interpretation |
|----------------|--------------|----------------------|
| Lead | Problem Clarity | Your marketing is attracting too-early buyers — they haven't defined the problem yet |
| Lead | Budget Reality | Wrong ICP segment — targeting too small or too early-stage |
| Client | Goal Progress | Delivery gap — something about how you work needs examining |
| Client | Value Perception | Communication gap — results aren't being attributed to your work |
| Product | Willingness to Pay | Problem exists but isn't painful enough to pay for |
| Self | Differentiation | Positioning work needed before growing |

---

### Component 3: Segment Analysis

**Group respondents by band and look for patterns within each group:**

```markdown
## High-Band Respondents ([N] people)

Common characteristics:
- [Dimension X] average: [X%] (highest across all segments)
- [Dimension Y] average: [X%]
- Most common answer on [key question]: "[Option]"

What this tells you: [2-3 sentence interpretation]

→ ICP match: [High / Medium / Low] — [brief reason]

## Low-Band Respondents ([N] people)

Common characteristics:
- [Dimension X] average: [X%] (lowest)
- Most common answer on [key question]: "[Option]"

What this tells you: [2-3 sentence interpretation]

→ These respondents need: [education / different service / different timing]
```

---

### Component 4: Question-Level Heatmap

**Show which specific questions are getting the strongest/weakest answers:**

```markdown
## Question Heatmap

| Question | Avg score | % picking score 0 | % picking score 4 |
|----------|-----------|-------------------|-------------------|
| [Q1 text abbreviated] | [X]/4 | [X%] | [X%] |
| [Q2] | | | |
[...]

**Most revealing questions (highest variance):**
[List questions where answers are most spread — these are the real discriminators]

**Least revealing questions (everyone scores the same):**
[Questions where 80%+ of respondents picked the same option — consider replacing]
```

---

### Component 5: Pipeline Impact (Lead Diagnostics)

**For lead diagnostics, connect score to pipeline outcomes:**

```markdown
## Pipeline Impact

| Cohort | Respondents | Proposals sent | Converted | Conversion rate |
|--------|-------------|----------------|-----------|----------------|
| 🟢 High band | [N] | [N] | [N] | [X%] |
| 🟡 Medium band | [N] | [N] | [N] | [X%] |
| 🔴 Low band | [N] | [N] | [N] | [X%] |

**Key finding:** [What the conversion data reveals about which band is worth pursuing]

**Recommendation:** [Adjust pipeline stage routing / change CTA for medium band / etc.]
```

*Note: Requires cross-referencing response files with pipeline.md. Run automatically by `diagnostic-monitor-agent` weekly.*

---

### Component 6: Trend Analysis (Over Time)

**When 3+ weeks of data exist, show trend:**

```markdown
## Score Trend Over Time

| Week | Responses | Avg score | Band distribution |
|------|-----------|-----------|-------------------|
| [W1] | [N] | [X] | 🔴[N] 🟡[N] 🟢[N] |
| [W2] | [N] | [X] | |
| [W3] | [N] | [X] | |

**Trend:** [Improving / Declining / Stable] — [interpretation]

If improving: Your diagnostic is reaching a better-fit audience over time,
or respondents' actual situations are improving.

If declining: Traffic source quality may be degrading, or seasonal effects.
```

---

### Component 7: Synthesis and Recommendations

**Always end with 2–3 concrete actions:**

```markdown
## What This Data Suggests

**Finding 1:** [The most important pattern]
→ Action: [Specific thing to change or do]

**Finding 2:** [Second pattern]
→ Action: [Specific action]

**Finding 3:** [Third pattern, if applicable]
→ Action: [Specific action]

## Recommended Diagnostic Updates

Based on [N] responses, consider updating:
- [ ] Replace [Q] — [X%] of respondents picked the same option (not discriminating)
- [ ] Adjust [band] threshold — most [high/medium] scorers are [behaving differently than expected]
- [ ] Add a [dimension] — several respondents mentioned [theme] in the notes that isn't captured
```

---

## Analysis by Diagnostic Type

### Lead Diagnostics → Pipeline Quality Analysis

Primary question: **Are high-scoring leads converting better than low-scoring ones?**

If yes → the diagnostic is working. Consider tightening the CTA for Medium to filter further.
If no → either the questions aren't measuring fit, or the score threshold is wrong.

Secondary question: **Which dimension best predicts conversion?**

The dimension with the highest correlation to Closed Won is the one to weight more heavily in the next iteration.

### Client Diagnostics → Retention Risk Analysis

Primary question: **What do low-scoring clients have in common?**

Look for patterns: industry, project type, engagement length, contract size, how they came in. The pattern reveals the clients to be more selective about accepting.

Secondary question: **Are you running health checks early enough?**

If churn is happening before the diagnostic reveals it, the cadence is too infrequent or the questions aren't detecting the right early signals.

### Product Validation Diagnostics → Build/No-Build Signal

Primary question: **Is the average score above 55?**

- > 60 across 30+ respondents → strong signal to build
- 45–60 → real problem, but not urgent enough — validate the urgency dimension specifically
- < 45 → problem exists but isn't actionable — pivot the audience or problem framing

Secondary question: **Which dimension scores are lowest — and why?**

If Willingness to Pay is low even when Pain Acuity is high → price sensitivity issue, not demand issue. If Current Solution Dissatisfaction is low → alternatives are working well enough. These are different problems with different solutions.

---

## Save

Analysis report: `data/1-Projets/diagnostics/[slug]/analysis-[date].md`

## Integration Points

- **`diagnostic-monitor-agent`**: runs this skill weekly for all active diagnostics
- **`monday-morning-agent`**: receives diagnostic summary in Monday briefing if configured
- **`sales-pipeline`**: cross-reference lead scores with pipeline outcomes
- **`business-health-advisor`**: client health diagnostic data feeds into overall health scan
- **`diagnostic-builder`**: analysis recommendations feed into next diagnostic iteration
