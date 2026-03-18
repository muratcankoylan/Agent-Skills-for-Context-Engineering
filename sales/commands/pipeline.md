---
description: "Manage Deals, Forecasts, and Deal Reviews"
argument-hint: "[review | forecast | stale | board-deck]"
allowed-tools: Read, Write, Glob
model: sonnet
---

# /sales:pipeline

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

The **Pipeline Tracker** acts as your fractional VP of Sales. It audits deal health, forecasts revenue with weighted probabilities, and prepares you for board/team reviews.

It operates in **Hybrid Mode**:

- **Offline**: Reads `data/1-Projets/active-deals/`.
- **Online**: Syncs with CRM (HubSpot, Pipedrive) if connected.

---

## Usage

```
/sales:pipeline review       # Full Deal Health Audit
/sales:pipeline forecast     # Revenue Projection (Commit vs Upside)
/sales:pipeline stale        # "Fix or Kill" Analysis (Deals >14 days inactive)
/sales:pipeline board-deck   # Generate slides text for QBR/Weekly meeting
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                    PIPELINE GUARDIAN                              │
├──────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                        │
│  ✓ Health Scoring: Velocity, Recency, and Depth analysis         │
│  ✓ Markdown Tracker: Local deal management in PARA structure     │
│  ✓ Risk Detection: Auto-flagging of stale or single-thread deals │
│  ✓ Review Prep: Auto-generated agenda for deal reviews           │
├──────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                       │
│  + ~~CRM: Bi-directional sync with HubSpot/Pipedrive             │
│  + ~~email: Scan inbox for "Ghosting" signals                    │
│  + ~~calendar: Auto-schedule "Rescue Calls" for at-risk deals    │
└──────────────────────────────────────────────────────────────────┘
```

---

## /sales:pipeline review

**The Monday Morning Audit.**

### Output Example

```markdown
PIPELINE HEALTH CHECK — Feb 13, 2026

SCORES

- Total Pipeline: $185,000
- Weighted Forecast: $62,500
- Average Health Score: 72/100

CRITICAL RISKS (Action Required)

| Deal      | Value | Risk Factor     | Recommendation                                                   |
| :-------- | :---- | :-------------- | :--------------------------------------------------------------- |
| Acme Corp | $45k  | Single-Threaded | You only know Sarah. Action: Ask Sarah for intro to CFO.         |
| Beta Inc  | $15k  | Stale (14d)     | No reply to proposal. Action: Send "Breakup Email".              |
| Gamma Co  | $80k  | Push Date       | Close date changed 3x. Action: Re-qualify valid business reason. |

HEALTHY DEALS

- Delta Ltd ($25k): Contract in legal. Close expected Feb 28.
- Epsilon ($10k): Demo scheduled with decision maker.

Suggestion: Run `/sales:negotiate` on Acme Corp to fix the single-threading?
```

---

## /sales:pipeline forecast

**The Revenue Call.**

### Output Example

```markdown
Q1 FORECAST (Conservative View)

| Category | Deals Included | Total Value | Weighted |
| :------- | :------------- | :---------- | :------- |
| COMMIT   | Delta, Zeta    | $45,000     | $42,500  |
| UPSIDE   | Acme, Gamma    | $125,000    | $50,000  |
| PIPE     | Beta, Epsilon  | $25,000     | $5,000   |
| TOTAL    |                | $195,000    | $97,500  |

TARGET ANALYSIS

- Quota: $100,000
- Forecast (Commit + Upside): $92,500
- Gap: -$7,500

Strategy: You are slightly short.

1. Pull Gamma ($80k) forward? (Low probability)
2. Converting Beta ($15k) is safer. Focus there.
```

---

## Agent Instructions

### Health Scoring Algorithm

```python
def calculate_deal_health(deal):
    score = 100

    # 1. Activity Decay
    days_since_touch = (today - deal.last_activity).days
    if days_since_touch > 7: score -= 10
    if days_since_touch > 14: score -= 20

    # 2. Stakeholder Risk
    if deal.contacts_count < 2 and deal.stage > "Discovery":
        score -= 20 # Single thread risk

    # 3. Velocity Risk
    if deal.time_in_stage > avg_time_in_stage[deal.stage]:
        score -= 15 # Stalled

    return score
```

### Stale Deal Remediation

If a deal is marked "Stale":

1.  **Check Phase**:
    - If Early Stage -> "Did I miss the mark" email.
    - If Late Stage -> "File Close" (Breakup) email.
2.  **Auto-Draft**: The agent should offer to draft this email immediately.
3.  **CRM Sync**: If connected, verify if activity happened but wasn't logged.

---

## Connectors (Advanced)

If you have `hubspot-sync` enabled in `.mcp.json`:

- The agent will pull `deal_stage`, `amount`, `close_date` from HubSpot.
- It will **Push** any changes you make in the Markdown files back to HubSpot.
- It will NOT overwrite your notes unless explicitly told to.

---

## Tips

1.  **Sandbagging**: Don't put deals in "Commit" until they are virtually signed. It's better to beat a low forecast than miss a high one.
2.  **The "Why"**: For every deal in Commit, strictly ask: "Why would they buy NOW?" If you can't answer, it's Upside.
3.  **Clean Data**: Garbage in, garbage out. If close dates are in the past, the forecast is useless.

---

## Skills Used

- `pipeline-guardian` — The health scoring engine.
- `financial-health` — The math module.
- `hubspot-sync` — The integration layer.
