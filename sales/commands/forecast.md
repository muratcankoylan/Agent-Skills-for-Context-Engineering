---
description: Generate a weighted sales forecast with best/likely/worst scenarios, commit vs. upside breakdown, and gap analysis
argument-hint: "<period>"
allowed-tools: Read, Write, Glob
model: sonnet
---

# /forecast

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

Generate a weighted sales forecast with risk analysis and commit recommendations.

## Usage

```
/forecast
```

Then provide your pipeline data and targets.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        FORECAST                                  │
├─────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                       │
│  ✓ Upload CSV export from your CRM                              │
│  ✓ Or paste/describe your pipeline deals                        │
│  ✓ Set your quota and timeline                                  │
│  ✓ Get weighted forecast with stage probabilities               │
│  ✓ Risk-adjusted projections (best/likely/worst case)           │
│  ✓ Commit vs. upside breakdown                                  │
│  ✓ Gap analysis and recommendations                             │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                      │
│  + ~~CRM: Pull pipeline automatically, real-time data             │
│  + ~~analytics: Historical win rates by stage, segment, deal size │
│  + ~~activity: Signals for risk scoring                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## What I Need From You

### Step 1: Your Pipeline Data

**Option A: Upload a CSV**
Export your pipeline from your CRM (e.g. Salesforce, HubSpot). I need at minimum:

- Deal/Opportunity name
- Amount
- Stage
- Close date

Helpful if you have:

- Owner (if team forecast)
- Last activity date
- Created date
- Account name

**Option B: Paste your deals**

```
Acme Corp - $50K - Negotiation - closes Jan 31
TechStart - $25K - Demo scheduled - closes Feb 15
BigCo - $100K - Discovery - closes Mar 30
```

**Option C: Describe your territory**
"I have 8 deals in pipeline totaling $400K. Two are in negotiation ($120K), three in evaluation ($180K), three in discovery ($100K)."

### Step 2: Your Targets

- **Quota**: What's your number? (e.g., "$500K this quarter")
- **Timeline**: When does the period end? (e.g., "Q1 ends March 31")
- **Already closed**: How much have you already booked this period?

---

## Output

```markdown
# Sales Forecast: [Period]

**Generated:** [Date]
**Data Source:** [CSV upload / Manual input / CRM]

---

## Summary

| Metric                | Value                |
| --------------------- | -------------------- |
| **Quota**             | $[X]                 |
| **Closed to Date**    | $[X] ([X]% of quota) |
| **Open Pipeline**     | $[X]                 |
| **Weighted Forecast** | $[X]                 |
| **Gap to Quota**      | $[X]                 |
| **Coverage Ratio**    | [X]x                 |

---

## Forecast Scenarios

| Scenario        | Amount | % of Quota | Assumptions                  |
| --------------- | ------ | ---------- | ---------------------------- |
| **Best Case**   | $[X]   | [X]%       | All deals close as expected  |
| **Likely Case** | $[X]   | [X]%       | Stage-weighted probabilities |
| **Worst Case**  | $[X]   | [X]%       | Only commit deals close      |

---

## Pipeline by Stage

| Stage       | # Deals | Total Value | Probability | Weighted Value |
| ----------- | ------- | ----------- | ----------- | -------------- |
| Negotiation | [X]     | $[X]        | 80%         | $[X]           |
| Proposal    | [X]     | $[X]        | 60%         | $[X]           |
| Evaluation  | [X]     | $[X]        | 40%         | $[X]           |
| Discovery   | [X]     | $[X]        | 20%         | $[X]           |
| **Total**   | [X]     | $[X]        | —           | $[X]           |

---

## Commit vs. Upside

### Commit (High Confidence)

Deals you'd stake your forecast on:

| Deal   | Amount | Stage   | Close Date | Why Commit |
| ------ | ------ | ------- | ---------- | ---------- |
| [Deal] | $[X]   | [Stage] | [Date]     | [Reason]   |

**Total Commit:** $[X]

### Upside (Lower Confidence)

Deals that could close but have risk:

| Deal   | Amount | Stage   | Close Date | Risk Factor |
| ------ | ------ | ------- | ---------- | ----------- |
| [Deal] | $[X]   | [Stage] | [Date]     | [Risk]      |

**Total Upside:** $[X]

---

## Risk Flags

| Deal   | Amount | Risk                                     | Recommendation                    |
| ------ | ------ | ---------------------------------------- | --------------------------------- |
| [Deal] | $[X]   | Close date passed                        | Update close date or move to lost |
| [Deal] | $[X]   | No activity in 14+ days                  | Re-engage or downgrade stage      |
| [Deal] | $[X]   | Close date this week, still in discovery | Unlikely to close — push out      |

---

## Gap Analysis

**To hit quota, you need:** $[X] more

**Options to close the gap:**

1. **Accelerate [Deal]** — Currently [stage], worth $[X]. If you can close by [date], you're at [X]% of quota.
2. **Revive [Stalled Deal]** — Last active [date]. Worth $[X]. Reach out to [contact].
3. **New pipeline needed** — You need $[X] in new opportunities at [X]x coverage to be safe.

---

## Recommendations

1. [Specific action for highest-impact deal]
2. [Action for at-risk deal]
3. [Pipeline generation recommendation if gap exists]
```

---

## Stage Probabilities (Default)

If you don't provide custom probabilities, I'll use:

| Stage                     | Default Probability |
| ------------------------- | ------------------- |
| Closed Won                | 100%                |
| Negotiation / Contract    | 80%                 |
| Proposal / Quote          | 60%                 |
| Evaluation / Demo         | 40%                 |
| Discovery / Qualification | 20%                 |
| Prospecting / Lead        | 10%                 |

Tell me if your stages or probabilities are different.

---

## If CRM Connected

- I'll pull your pipeline automatically
- Use your actual historical win rates
- Factor in activity recency for risk scoring
- Track forecast changes over time
- Compare to previous forecasts

---

## Tips

1. **Be honest about commit** — Only commit deals you'd bet on. Upside is for everything else.
2. **Update close dates** — Stale close dates kill forecast accuracy. Push out deals that won't close in time.
3. **Coverage matters** — 3x pipeline coverage is healthy. Below 2x is risky.
4. **Activity = signal** — Deals with no recent activity are at higher risk than stage suggests.

---

## 🔬 Sentinel Integration (when installed)

```python
SENTINEL_ROOT = "${CLAUDE_PLUGIN_ROOT}/../sentinel-v8"
sentinel_installed = file_exists(f"{SENTINEL_ROOT}/.claude-plugin/plugin.json")
```

Skip this section entirely if `sentinel_installed` is False. /forecast works identically without it.

### Trigger condition
Two activation points:
1. **At forecast generation** — record each Commit deal as a calibration prediction
2. **At forecast review** (`/forecast --review` or end-of-period) — run calibration analysis

### What to run

**At generation — calibration-coach (prediction recording)**

For each deal classified as **Commit** (high confidence), invoke `calibration-coach` to record:

```json
{
  "decision": "Deal: [company name] — [amount] — [stage]",
  "prediction": "Will close by [close_date]",
  "confidence": [user_stated_confidence_or_stage_default],
  "review_date": "[close_date or period_end]",
  "resolved": false,
  "context": {
    "stage": "[stage]",
    "amount": "[amount]",
    "period": "[forecast period]"
  }
}
```

Write to `../sentinel-v8/data/decision-ledger.json`.

After recording, add one line to the forecast output per Commit deal:
`[Company] — $[X] — [stage] — [X%] confidence — recorded for calibration`

**At review — calibration-coach (accuracy analysis)**

Run: `python3 ../sentinel-v8/skills/decision-hygiene/scripts/calibration.py --ledger ../sentinel-v8/data/decision-ledger.json --filter forecast`

Output includes:
- Total forecasted vs actual closed (by period)
- Brier score for deal-level predictions
- Calibration pattern: "Your Negotiation-stage calls are [X%] overconfident"
- One actionable recommendation: e.g. "Reduce Negotiation-stage confidence from 80% to [X%] based on your actual close rate"

**reality-checker (on stage probability defaults)**

If user is using the default stage probabilities (80/60/40/20/10), add a one-time reality check:

> "These are industry defaults. Your actual close rates may differ significantly."

Invoke `reality-checker` with reference class: "B2B [product/service] deals at [deal size range]"
- Provide base rate estimates for stage-to-close rates with confidence levels
- Source: Gong win rate benchmarks, SaaS sales benchmarks, industry reports

After 10+ resolved predictions, replace defaults with user's own historical rates automatically.

### Output format addition

**In the forecast output**, add a Calibration section after the Commit list:

```
## Forecast Calibration (Sentinel)

Commit deals recorded: [N] predictions logged to decision ledger
[If review mode]:
  Resolved predictions this period: [N]
  Your stated confidence vs actual close rate:
    Negotiation stage: stated [X%] → actual [Y%] ([over/under]confident by [Z%])
    Proposal stage:    stated [X%] → actual [Y%]
  Brier score: [X] ([interpretation: excellent / decent / needs work])
  Recommendation: [one specific calibration adjustment]
```

### Standalone output (Sentinel not installed)
Standard weighted forecast with scenarios, Commit/Upside breakdown, gap analysis, risk flags. No change.

---

## 🛡️ Sentinel Integration

```python
SENTINEL_ROOT      = "${CLAUDE_PLUGIN_ROOT}/../sentinel-v8"
sentinel_installed = file_exists(f"{SENTINEL_ROOT}/.claude-plugin/plugin.json")
```

**Trigger**: After weighted forecast table is generated.
**Standalone mode**: Forecast runs as normal. Skip Sentinel sections.

### If Sentinel installed — Calibration layer on every forecast

**Step A — Record predictions in decision ledger**

For every deal classified as COMMIT (>70% confidence), write to `../sentinel-v8/data/decision-ledger.json`:

```json
{
  "id": "<uuid>",
  "date": "<today>",
  "decision": "Deal close: [deal name] — [amount]",
  "prediction": "Will close by [close date]",
  "confidence": <stage_probability as 0.0-1.0>,
  "review_date": "<close date + 7 days>",
  "resolved": false,
  "plugin": "sales/forecast",
  "stage": "<current stage>",
  "amount": <deal amount>
}
```

For UPSIDE deals (40–70%), record with lower confidence values.

**Step B — Calibration review** (run when `--review` flag or quarter-end detected)

Invoke calibration-coach (`../sentinel-v8/agents/calibration-coach.md`):

```bash
python3 "../sentinel-v8/skills/decision-hygiene/scripts/calibration.py" \
  --ledger "../sentinel-v8/data/decision-ledger.json" \
  --filter "plugin:sales/forecast"
```

Output:
- Brier score for resolved deal predictions
- Pattern: "You called [N] deals at 80%+ confidence. [X] closed. Your Negotiation-stage calls are overconfident by [Y]%."
- Recommendation: "Reduce your Negotiation-stage probability to [X]% based on your actual close rate."

**Step C — reality-checker on Commit deals**

For any deal marked COMMIT with >80% confidence, run a quick reality check:
- Reference class: `"[deal size range] deals at [stage] in [industry] — close rate in [timeline]"`
- Verify at: Gong win-rate benchmarks, Salesforce State of Sales report
- Flag if confidence exceeds historical base rate for that stage/size combination

**Output integration** — append after Recommendations:

```markdown
## Forecast Calibration (Sentinel)

**Predictions recorded**: [N] deals logged to decision ledger
**Review date**: [latest close date + 7 days]

[If review run]:
**Your calibration score**: Brier [X] — [interpretation]
**Pattern identified**: [specific overconfidence/underconfidence pattern]
**Adjustment**: [specific recommendation, e.g., "Reduce Negotiation-stage confidence from 80% to 60%"]
```

### `/forecast --review` command extension

When user runs `/forecast --review [period]`:
1. Read decision ledger filtered to `plugin:sales/forecast`
2. Run calibration-coach analysis
3. Show: predictions made vs outcomes, Brier score, stage-level calibration breakdown
4. Produce ONE actionable adjustment to stage probabilities for next forecast
