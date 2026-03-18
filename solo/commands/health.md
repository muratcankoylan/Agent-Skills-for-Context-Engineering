---
description: "On-demand business health check across all 6 dimensions"
argument-hint: "[full | revenue | clients | pipeline | capacity | retainers | wellbeing]"
allowed-tools: Read, Write, Glob
model: sonnet
---

# /solo:health

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

Run a strategic business health check at any time. Surfaces structural risks and growth patterns invisible in weekly operations.

## Usage

```
/solo:health              # Full 6-dimension scan
/solo:health revenue      # Revenue trend analysis only
/solo:health clients      # Client concentration risk only
/solo:health pipeline     # Pipeline coverage and lead velocity
/solo:health capacity     # Utilization and effective hourly rate
/solo:health retainers    # Retainer health and renewal calendar
/solo:health wellbeing    # Pattern detection across recent reviews
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                    BUSINESS HEALTH CHECK                          │
├──────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                        │
│  ✓ Revenue trend: 6-month direction of growth or contraction     │
│  ✓ Client concentration: single-client dependency risk           │
│  ✓ Pipeline coverage: is future revenue being built?             │
│  ✓ Recurring revenue: retainer stability score                   │
│  ✓ Wellbeing signals: burnout and overload pattern detection     │
├──────────────────────────────────────────────────────────────────┤
│  ENHANCED (with additional skills configured)                     │
│  + Profit margin: requires expense-tracker to be set up          │
│  + Capacity utilization: requires capacity-planner time logs     │
│  + Effective hourly rate: requires project time tracking         │
└──────────────────────────────────────────────────────────────────┘
```

---

## /solo:health (Full Scan)

**Reads from:**
- `data/1-Projets/invoices/` — revenue by month, last 6 months
- `data/1-Projets/expenses/` — expense data (if expense-tracker configured)
- `data/1-Projets/clients/` — revenue by client, retainer status
- `data/1-Projets/pipeline.md` — weighted pipeline value
- `data/3-Ressources/weekly-review-*.md` — last 8 weekly reviews for pattern detection
- `data/4-Archives/health-reports/` — previous health reports for trend comparison

**Output:** 6-dimension health report with overall score and prioritized strategic recommendations.

**When to run:**
- End of month (or let `business-health-agent` do it automatically)
- Before making a major business decision (taking a large project, raising rates, hiring a subcontractor)
- When something feels off but you can't identify what

---

## /solo:health revenue

Deep dive on revenue trend only.

**Shows:**
- Month-by-month revenue for last 6 months (table + ASCII trend)
- 3-month moving average vs 6-month moving average
- MoM and YoY growth rates
- Revenue by client (top 5)
- Revenue by service type (if tracked)
- Projected revenue for next month (based on pipeline + retainers)

**Growth diagnosis:** If revenue is contracting, cross-references `business-health-advisor/references/growth-diagnosis.md` to identify which pattern applies.

---

## /solo:health clients

Deep dive on client concentration and relationship health.

**Shows:**
- Client revenue distribution (table + concentration %)
- Concentration risk score
- Any client at >30% of revenue: named and flagged
- Client health scores (from `client-management`)
- Clients not contacted in 30+ days
- Retainer renewal dates in next 60 days

**If concentration is critical:**
> "⚠️ [Client X] represents [X%] of your last 6 months revenue. If they reduce or cancel, your monthly revenue drops by €[X]. Immediate action: open 3 new high-value prospect conversations."

---

## /solo:health pipeline

Deep dive on pipeline and business development health.

**Shows:**
- Weighted pipeline value vs monthly revenue target
- Pipeline coverage ratio (healthy = >3×)
- Deals by stage (how many at each stage)
- Average days in current stage (flags stuck deals)
- New leads per month — last 3 months (is prospecting active?)
- Close rate trend (if historical data available)
- Projected revenue from pipeline (expected close × probability × value)

**If pipeline is thin:**
> "Your pipeline covers [X×] your monthly target. At current close rates, this means [risk description]. Priority action: [specific outreach recommendation]."

---

## /solo:health capacity

Deep dive on capacity utilization and time allocation.

**Shows:**
- Current utilization rate (committed hours vs available hours)
- Active projects with hours remaining and deadlines
- Any overloaded weeks in the last month
- Effective hourly rate (if time logs exist)
- Comparison: target rate vs effective rate
- Forecast: when do current projects complete?

**Reads from:** `capacity-planner` skill data and project time logs.

---

## /solo:health retainers

Deep dive on retainer portfolio health.

**Shows:**
- All active retainers with monthly fee, utilization, health score
- Retainer MRR as % of total revenue
- Renewals in next 30/60/90 days
- Any retainer with under-utilization risk
- Any retainer with over-delivery problem

**Renewal alerts:**
- 🔴 Renewing in <30 days with health score <7: "Intervention needed"
- 🟡 Renewing in 30–60 days: "Schedule renewal conversation"
- 🟢 Renewing in >60 days: "Monitor"

---

## /solo:health wellbeing

Pattern scan across recent weekly reviews.

**What it looks for:**
- Same blocker appearing 3+ consecutive weeks (structural problem being avoided)
- 0 wins logged in 3+ of the last 4 reviews (low morale signal)
- Revenue flat + hours feeling high (working more for same outcome)
- Any 3+ week trend worth naming

**Note:** This dimension relies on consistent weekly review completion. If fewer than 4 recent reviews exist, it will note the limitation.

**The check-in question:**
> "Based on the last [N] weeks of reviews, I've noticed [pattern]. How are you doing? Is the current pace sustainable?"

---

## Saved Reports

Health reports are saved to `data/4-Archives/health-reports/health-[YYYY-MM].md`.

To compare two months:
```
/solo:health full
```
When a previous report exists, the full scan automatically includes a "vs last month" comparison.
