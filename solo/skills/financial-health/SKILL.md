---
name: financial-health
description: >
  Tracks monthly revenue, profit margins, and runway. Generates financial dashboards
  from invoice data. Triggers on "revenue report", "am I profitable", "financial health",
  "monthly P&L", or "how much did I make".
version: 1.0.0
bundle: revenue-ops
triggers:
  - "financial health"
  - "revenue report"
  - "profit margin"
  - "runway"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Financial Health

Provides a dashboard of your business finances by reading invoice data and calculating key metrics. Used by `/solo:invoice report` and `/solo:weekly-review`.

## Revenue Calculation

### Data Source
Scan all `.md` files in `data/1-Projets/invoices/`:
- Parse the **Status** field (Draft, Sent, Paid, Overdue)
- Parse the **Total Due** amount
- Parse the **Date of Issue** and **Due Date**

### Metrics

| Metric | Calculation |
|--------|------------|
| **Revenue (Paid)** | Sum of Total from invoices with Status = Paid in period |
| **Revenue (Invoiced)** | Sum of Total from all invoices issued in period |
| **Outstanding** | Sum of Total from invoices with Status = Sent |
| **Overdue** | Sum of Total from invoices past Due Date and not Paid |
| **Collection Rate** | Paid / Invoiced x 100% |
| **Avg Days to Pay** | Mean of (Paid Date - Issue Date) across paid invoices |

## Profit & Loss Report

Generate monthly P&L in this format:

```markdown
# Profit & Loss — [Month Year]

## Revenue
| Source | Amount |
|--------|--------|
| Client work (paid invoices) | [X] |
| Retainer income | [X] |
| Other income | [X] |
| **Total Revenue** | **[X]** |

## Expenses
| Category | Amount |
|----------|--------|
| Software & tools | [X] |
| Coworking / office | [X] |
| Marketing & ads | [X] |
| Professional services (accounting, legal) | [X] |
| Travel & meals | [X] |
| Other | [X] |
| **Total Expenses** | **[X]** |

## Summary
| Metric | Value |
|--------|-------|
| **Net Profit** | [Revenue - Expenses] |
| **Profit Margin** | [Net Profit / Revenue x 100]% |
| **Effective Hourly Rate** | [Net Profit / Hours Worked] |
```

Expense data must be provided by the user or pulled from ~~accounting if connected.

## Revenue Dashboard (Weekly Review)

Quick summary for the weekly review:

```
Revenue Snapshot — [Date]
- Month-to-date revenue (paid): [X]
- Monthly target: [X] — [X% achieved]
- Outstanding invoices: [X] ([N] invoices)
- Overdue invoices: [X] ([N] invoices)
- Pipeline value: [X] (from sales-pipeline)
- Weighted pipeline: [X] (value x stage probability)
```

## Runway Calculation

| Input | Source |
|-------|--------|
| Current cash balance | User-provided |
| Average monthly expenses | User-provided or last 3 months |
| Average monthly revenue | Last 3 months of paid invoices |

**Formula:**
- If profitable: runway = sustainable (revenue > expenses)
- If burning cash: `runway = cash / (expenses - revenue)` months

## How to Read Invoice Data

1. List all `.md` files in `data/1-Projets/invoices/`
2. For each file, parse the structured fields (Invoice Number, Status, Dates, Total)
3. Filter by date range for the requested period
4. Group by status for the dashboard
5. Sum by month for trend analysis

## Integration Points

- **`invoice-generator`**: Provides the raw invoice data
- **`sales-pipeline`**: Provides pipeline value for forecasting
- **`pricing-strategy`**: Provides rate card for effective rate analysis
- **`weekly-review`**: Consumes the revenue snapshot

## Key References

- **`references/pricing-models.md`**: Comprehensive pricing model guide with rate calculations and templates
