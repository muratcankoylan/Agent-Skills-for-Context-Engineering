---
name: business-health-advisor
description: >
  Monthly strategic scan of business health beyond cashflow: client concentration,
  revenue trends, service profitability, capacity utilization, and solopreneur
  burnout signals. Triggers on "business health check", "monthly health report",
  "how is my business doing", "am I growing", "client risk", or "business diagnosis".
version: 1.0.0
bundle: operations
triggers:
  - "business health"
  - "monthly health check"
  - "health scan"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Business Health Advisor

`weekly-review` tells you what happened this week. This skill tells you whether your business is structurally sound. It answers the questions that week-to-week data obscures: Are you growing or just busy? Are you dependent on a client who could leave? Are you working more for less?

Run monthly (recommended: last working day of the month) or on-demand.

## Six Dimensions of Solo Business Health

### Dimension 1: Revenue Trend

**What it measures:** Direction of growth, not just current level.

**Data source:** `data/1-Projets/invoices/` — paid invoices, last 6 months

**Calculations:**

| Metric | Formula |
|--------|---------|
| MRR (current) | This month's paid invoices |
| 3-month moving average | (M-1 + M-2 + M-3) / 3 |
| 6-month moving average | (M-1 through M-6) / 6 |
| Month-over-month growth | (Current MRR - Last MRR) / Last MRR |
| Revenue trend | Compare 3M avg to 6M avg |

**Health signals:**

| Signal | Score |
|--------|-------|
| 3M avg > 6M avg + growing each month | 🟢 Growing |
| 3M avg ≈ 6M avg, consistent | 🟡 Stable (not scaling) |
| 3M avg < 6M avg or declining 2+ months | 🔴 Contracting |

---

### Dimension 2: Client Concentration Risk

**What it measures:** How exposed you are if one client leaves.

**Data source:** `data/1-Projets/clients/` — revenue by client, last 6 months

**Calculation:**
```
For each client: [client revenue] / [total revenue] = concentration %
```

**Health thresholds:**

| Concentration | Signal | Risk |
|---|---|---|
| No single client >30% of revenue | 🟢 Diversified | Low |
| One client = 30–50% of revenue | 🟡 Exposed | If they leave, revenue drops materially |
| One client >50% of revenue | 🔴 Dangerous | Single point of failure |
| Two clients >80% of revenue combined | 🔴 Critical | Any disruption is a crisis |

**Output:** Client concentration matrix showing each client's revenue share.

**Recovery prescription for 🔴:**
> "You have a single-client dependency. Even if the relationship is strong, you're one budget cut or one org change away from a revenue crisis. Your immediate priority is to build 2–3 new client relationships to reduce [Client X]'s share below 40% within 90 days."

---

### Dimension 3: Service Profitability

**What it measures:** Which work makes money per hour worked.

**Data source:**
- Revenue per service type: from invoices, categorized by service
- Hours per service type: from `data/1-Projets/[project]/time-log.md` (if tracked)
- Expense allocation: from `expense-tracker` for subcontractors and service-specific costs

**Calculation (per service type):**
```
Revenue per hour = Service Revenue / Service Hours
Net margin = (Service Revenue - Direct Costs) / Service Revenue
```

**Output table:**

| Service | Revenue | Hours | €/hour | Net Margin | Verdict |
|---------|---------|-------|--------|------------|---------|
| [Service A] | €[X] | [Y]h | €[Z] | [X%] | 🟢 High margin |
| [Service B] | €[X] | [Y]h | €[Z] | [X%] | 🟡 OK |
| [Service C] | €[X] | [Y]h | €[Z] | [X%] | 🔴 Below target rate |

**When time tracking isn't available:** Use the capacity-planner's project actuals or ask user to estimate.

**Health signal:** Any service generating <75% of your target hourly rate is a candidate for repricing or discontinuation.

---

### Dimension 4: Pipeline Health Trend

**What it measures:** Whether future revenue is being built while delivering current work.

**Data source:** `data/1-Projets/pipeline.md` — weighted pipeline over time

**Metrics:**
- Current weighted pipeline value
- Pipeline coverage ratio: weighted pipeline / monthly revenue target
- New leads added per month (last 3 months)
- Time to close (avg days from lead to signed)

**Health thresholds:**

| Pipeline Coverage | Signal |
|---|---|
| >3× monthly target | 🟢 Strong coverage |
| 1.5–3× monthly target | 🟡 Adequate |
| <1.5× monthly target | 🔴 Thin pipeline — revenue risk in 60–90 days |
| 0 new leads in 30 days | 🔴 Prospecting has stopped |

**The key insight:** Revenue dips always lag pipeline dips by 60–90 days. A weak pipeline today is a cash flow crisis in Q+2.

---

### Dimension 5: Capacity Utilization

**What it measures:** Whether you're optimally loaded — not over, not under.

**Data source:** `capacity-planner` skill output

**Metrics:**
- Billable utilization rate: billable hours / available hours
- Revenue per hour (effective): total revenue / total hours worked
- Overload events: weeks where committed > available (last 3 months)

**Health thresholds:**

| Utilization | Signal |
|---|---|
| 70–85% billable utilization | 🟢 Optimal |
| 85–100% | 🟡 Near capacity — little buffer for new opportunities |
| >100% | 🔴 Overloaded — quality or deadlines at risk |
| <60% | 🟡 Underfull — need more work or a rate increase |
| <40% | 🔴 Underfull — business development emergency |

---

### Dimension 6: Solopreneur Wellbeing Signals

**What it measures:** Early warning indicators for burnout and unsustainable work patterns.

**Data source:** Pattern analysis across project files, weekly reviews, and client data

**Signals scanned:**

| Signal | Detection Method | Risk |
|--------|-----------------|------|
| Same blocker for 4+ weeks in weekly reviews | Scan review notes | Structural problem being ignored |
| No vacation or break in 90+ days | Scan project calendar | Burnout approaching |
| Working evenings/weekends repeatedly | Time log patterns if tracked | Unsustainable pace |
| 0 wins logged in 3+ weekly reviews | Scan review notes | Motivation / morale at risk |
| Increasing overdue items trend | Project/invoice data | Capacity or scope problem |
| Revenue same but hours increasing | Capacity + revenue data | Doing more for less |

**This is the hardest dimension** because the data is qualitative. The advisor presents patterns and asks directly:
> "I've noticed [X] in your recent reviews. How are you actually doing? Is the pace sustainable?"

---

## Monthly Health Report Output

```markdown
# Business Health Report — [Month Year]

## Overall Score: [X/6 dimensions healthy]

## 1. Revenue Trend
- Current MRR: €[X]
- 3M average: €[X] | 6M average: €[X]
- Trend: [🟢 Growing / 🟡 Stable / 🔴 Contracting]
- MoM change: [+/-X%]

## 2. Client Concentration
- Total active clients: [N]
- Largest client: [name] — [X%] of revenue
- Status: [🟢 Diversified / 🟡 Exposed / 🔴 Dangerous]
- [If 🔴: specific recommendation]

## 3. Service Profitability
| Service | €/hour | vs. Target | Signal |
|---------|--------|------------|--------|
[Table]

## 4. Pipeline Health
- Weighted pipeline: €[X] ([X× monthly target])
- New leads this month: [N]
- Avg close time: [X] days
- Status: [🟢 / 🟡 / 🔴]

## 5. Capacity Utilization
- Billable utilization: [X%]
- Effective hourly rate: €[X]
- Status: [🟢 Optimal / 🟡 Near full / 🔴 Overloaded / 🟡 Underfull]

## 6. Wellbeing Signals
[Qualitative patterns detected, or "No warning signals this month."]

---

## Strategic Priorities for [Next Month]

Based on this month's scan, focus on:

1. **[Priority 1]** — [Rationale from health dimensions]
2. **[Priority 2]** — [Rationale]
3. **[Priority 3]** — [Rationale]

---

## Trend vs. Last Month
[3-line comparison of how each dimension has changed]
```

Save to `data/4-Archives/health-reports/health-[YYYY-MM].md`

## Integration Points

- **`financial-health`**: Revenue data including now expenses (via `expense-tracker`)
- **`expense-tracker`**: Expense data for profit margin calculation
- **`capacity-planner`**: Utilization and effective hourly rate
- **`sales-pipeline`**: Pipeline coverage and lead velocity
- **`client-management`**: Client revenue distribution
- **`weekly-review`**: Wellbeing signal pattern detection
- **`business-health-agent`**: Monthly automated version of this skill (see agents/)

## Key References

- **`references/health-benchmarks.md`**: Solopreneur benchmarks for all 6 dimensions
- **`references/growth-diagnosis.md`**: Decision trees for common health patterns (growing but unprofitable, stable but overloaded, etc.)
