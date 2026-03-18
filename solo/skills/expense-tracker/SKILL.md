---
name: expense-tracker
description: >
  Tracks business expenses locally and feeds them into P&L reports and profit margin
  calculations. Triggers on "log expense", "add expense", "what did I spend",
  "monthly expenses", "am I profitable", or "track cost".
version: 1.0.0
bundle: revenue-ops
triggers:
  - "track expense"
  - "add expense"
  - "log expense"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Expense Tracker

Provides the missing half of the `financial-health` skill. Every solopreneur can see their revenue (invoices); almost none track their expenses systematically. Without expenses, you can't calculate profit margin, effective hourly rate, or whether a project is actually worth taking.

## Data Location

All expenses stored in: `data/1-Projets/expenses/`

- One file per month: `expenses-YYYY-MM.md`
- Annual summary auto-generated: `expenses-YYYY-summary.md`
- Template: `references/expense-template.md`

## Expense Categories

| Category | What Goes Here | Tax-Deductible (FR) |
|----------|---------------|---------------------|
| **Software & Tools** | SaaS subscriptions, plugins, licenses | ✅ 100% |
| **Hardware** | Computer, peripherals, phone (pro use) | ✅ Pro-rated |
| **Home Office** | Desk, chair, office supplies | ✅ Pro-rated |
| **Marketing** | Ads, sponsorships, design assets | ✅ 100% |
| **Professional Services** | Accountant, lawyer, consultant fees | ✅ 100% |
| **Education** | Courses, books, conferences | ✅ 100% |
| **Travel & Transport** | Client meetings, coworking commute | ✅ With receipts |
| **Meals & Entertainment** | Client meals (with business purpose) | ✅ 50-75% |
| **Coworking / Office** | Desk rental, office space | ✅ 100% |
| **Subcontractors** | Freelancers hired for project delivery | ✅ 100% |
| **Banking & Finance** | Stripe fees, bank charges, FX costs | ✅ 100% |
| **Insurance** | Professional liability, health (self-employed) | ✅ |
| **Other** | Anything not covered above | Verify with accountant |

## Logging Process

### Quick Log (Single Expense)
When the user says "log expense [amount] for [description]":

1. Parse amount, category (infer if not stated), description, date (default: today)
2. Check if current month file exists at `data/1-Projets/expenses/expenses-YYYY-MM.md`
3. If not, create from `references/expense-template.md`
4. Append to the correct category table
5. Update the monthly subtotals
6. Confirm: "Logged €[X] under [Category]. Monthly [Category] total: €[Y]"

### Bulk Log (Multiple Expenses)
When the user pastes a list, CSV, or statement:
1. Parse each line for: amount, description, date
2. Auto-categorize using the category table above (ask if ambiguous)
3. Group by month if the list spans multiple months
4. Present a categorized summary before saving: "I found 14 expenses totaling €847. Does this look right?"
5. Save all confirmed expenses to the correct monthly files

### Recurring Expense Setup
For monthly subscriptions (most software):
1. Create an entry in `data/2-Domaines/recurring-expenses.json`
2. Auto-log at month start based on this file
3. Alert when a recurring expense hasn't been confirmed (card may have been declined)

## Monthly Summary Generation

At any time, or when called by `financial-health` or `weekly-review`:

```markdown
# Expense Summary — [Month Year]

## By Category

| Category | Budget | Actual | vs Budget |
|----------|--------|--------|-----------|
| Software & Tools | [X] | [Y] | [diff] |
| Professional Services | [X] | [Y] | [diff] |
| Marketing | [X] | [Y] | [diff] |
| Education | [X] | [Y] | [diff] |
| Other | [X] | [Y] | [diff] |
| **TOTAL** | **[X]** | **[Y]** | **[diff]** |

## Notable Expenses
[Any single expense >€200 listed individually]

## vs Last Month
- Total expenses: [X] vs [Y] last month ([+/-Z%])
- Biggest increase: [Category] (+[X])
- Biggest decrease: [Category] (-[X])
```

## Profitability Calculation

When called with "am I profitable" or from `financial-health`:

```
Revenue (paid invoices):     €[X]
Total Expenses:              €[Y]
─────────────────────────────────
Net Profit:                  €[Z]
Profit Margin:               [Z/X × 100]%
Effective Hourly Rate:       €[Z / hours worked]

Status: [🟢 Healthy / 🟡 Thin / 🔴 Burning Cash]
```

**Profit margin benchmarks for solopreneurs:**
- 🟢 Healthy: >50% (this is achievable; expenses should be low)
- 🟡 Thin: 30–50% (review software stack and subcontractor costs)
- 🔴 Burning cash: <30% (requires immediate action)

## Tax Preparation Mode

At year-end or on demand:
1. Generate annual expense summary by category
2. Flag non-deductible items (personal expenses accidentally logged)
3. Calculate estimated deductible total
4. Export as `data/4-Archives/tax-[year]/expense-report.md`

**French micro-entrepreneur note:** Actual expense deduction works differently under micro-entrepreneur regime (flat abatement applies instead). This export is most useful for freelancers with régime réel or EIRL/SASU structures.

## Budget Tracking

Set monthly budgets in `data/2-Domaines/expense-budgets.json`:

```json
{
  "software_tools": 200,
  "marketing": 150,
  "education": 100,
  "professional_services": 200,
  "other": 100
}
```

Alert when any category exceeds 90% of budget mid-month.

## Integration Points

- **`financial-health`**: Provides expense totals for P&L calculation — this skill is what finally makes profit margin computable
- **`weekly-review`**: Contributes weekly expense snapshot
- **`invoice-generator`**: Reads subcontractor expenses for project margin calculation
- **`pricing-strategy`**: Uses annual expense total for minimum rate calculation (Step 2)
- **`project-management`**: Per-project expense logging (subcontractors, tools purchased for a client)

## References

- **`references/expense-template.md`**: Monthly expense file format
- **`references/recurring-expenses-schema.md`**: Recurring expense configuration
- **`references/tax-categories-fr.md`**: French deductibility guide with CGI references
