---
description: "Create invoices, track payments, and monitor financial health"
argument-hint: "[create | status | report | remind]"
allowed-tools: Read, Write, Glob
model: sonnet
---

# /solo:invoice

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

Professional invoicing and financial tracking for solopreneurs. Generate invoices with auto-numbering, track payment status, monitor cash flow, and get automated payment reminders.

## Usage

```
/solo:invoice create       # Generate a new invoice
/solo:invoice status       # Check payment status
/solo:invoice report       # Monthly P&L report
/solo:invoice remind       # Send payment reminders
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                    INVOICE MANAGEMENT                             │
├──────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                        │
│  ✓ Invoice generation: Professional markdown invoices            │
│  ✓ Auto-numbering: INV-YYYY-NNN format                          │
│  ✓ Payment tracking: Draft/Sent/Paid/Overdue status             │
│  ✓ Financial reports: Monthly P&L and revenue dashboards         │
│  ✓ Late payment reminders: Escalating reminder templates         │
│  ✓ French micro-entrepreneur: TVA handling (art. 293 B)         │
├──────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                       │
│  + ~~invoicing (Stripe): Create and send invoices via Stripe    │
│  + ~~accounting: Sync with QuickBooks, Xero, or Wave             │
│  + ~~email: Auto-send invoices and reminders                     │
│  + ~~chat: Get notified when invoices are paid                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## /solo:invoice create

Generate a professional invoice for a client.

### What I Need From You

**Quick create** (I'll ask follow-up questions):

```
/solo:invoice create "Acme Corp"
```

**Full create** (provide all details):

```
/solo:invoice create
Client: Acme Corp
Service: Website redesign
Amount: $5,000
Type: Project (milestone payment)
Due: Net 30
```

### Interactive Flow

1. **Client Selection**
   - I'll search your client database
   - Or you can provide client details manually

2. **Billing Type**
   - **Hourly:** Time-tracked work (tasks × hours × rate)
   - **Project:** Fixed-fee deliverables or milestones
   - **Retainer:** Monthly recurring service

3. **Line Items**
   - For hourly: Tasks, hours, and rate per task
   - For project: Deliverables and their prices
   - For retainer: Monthly fee (pulled from client card)

4. **Payment Terms**
   - On receipt / Net 15 / Net 30 / Net 60
   - Payment method: Bank transfer / Stripe / PayPal

5. **Tax Handling**
   - Standard: 20% TVA (configurable)
   - Micro-entrepreneur: 0% with "TVA non applicable, art. 293 B du CGI"

### Output

```
✅ Invoice created: INV-2026-042

Invoice details:
  Client:        Acme Corp (Sarah Chen)
  Amount:        €5,000.00
  Tax (20% TVA): €1,000.00
  Total Due:     €6,000.00
  Due Date:      February 23, 2026 (Net 30)
  Status:        Draft

Invoice saved to:
  data/1-Projets/invoices/INV-2026-042.md

Next steps:
  1. Review the invoice
  2. Mark as sent: /solo:invoice send INV-2026-042
  3. Or edit manually in your editor

Quick actions:
  /solo:invoice status              # Check all invoices
  /solo:write email "Acme Corp"     # Draft invoice email
```

---

## /solo:invoice status

View payment status dashboard for all invoices.

### Usage

```
/solo:invoice status              # All invoices
/solo:invoice status --month      # This month only
/solo:invoice status --overdue    # Overdue only
```

### Output

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INVOICE STATUS — January 24, 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 FINANCIAL SNAPSHOT

Month-to-date revenue (paid): €12,500
Monthly target: €15,000 — 83% achieved
Outstanding invoices: €8,000 (3 invoices)
Overdue invoices: €2,000 (1 invoice) ⚠️

Collection rate: 85% (healthy: >90%)
Avg days to payment: 22 days (target: <30)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 BY STATUS

┌────────────┬────────┬──────────┬────────────────────────────┐
│ Status │ Count │ Amount │ Notes │
├────────────┼────────┼──────────┼────────────────────────────┤
│ Draft │ 1 │ €3,000 │ Not sent yet │
│ Sent │ 2 │ €6,000 │ Awaiting payment │
│ Paid │ 5 │ €12,500 │ ✓ Collected this month │
│ Overdue │ 1 │ €2,000 │ ⚠️ Action needed │
└────────────┴────────┴──────────┴────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 OVERDUE INVOICES (Action Required)

| Invoice      | Client   | Amount | Due Date | Days Late | Action        |
| ------------ | -------- | ------ | -------- | --------- | ------------- |
| INV-2026-035 | Beta Inc | €2,000 | Jan 10   | 14 days   | Send reminder |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟡 SENT (Awaiting Payment)

| Invoice      | Client    | Amount | Due Date | Days Left |
| ------------ | --------- | ------ | -------- | --------- |
| INV-2026-040 | Acme Corp | €6,000 | Feb 23   | 30 days   |
| INV-2026-038 | Gamma LLC | €3,500 | Feb 15   | 22 days   |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ PAID THIS MONTH (5 invoices)

| Invoice      | Client    | Amount | Paid Date | Days to Pay |
| ------------ | --------- | ------ | --------- | ----------- |
| INV-2026-039 | TechStart | €5,000 | Jan 22    | 18 days     |
| INV-2026-037 | Delta Co  | €2,500 | Jan 20    | 25 days     |
| INV-2026-036 | Epsilon   | €2,000 | Jan 18    | 20 days     |
| INV-2026-034 | Zeta Inc  | €1,500 | Jan 15    | 28 days     |
| INV-2026-033 | Theta LLC | €1,500 | Jan 12    | 15 days     |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RECOMMENDED ACTIONS:

1. Send payment reminder to Beta Inc (14 days overdue)
2. Follow up with Gamma LLC (due in 22 days, large invoice)
3. Mark INV-2026-041 as sent (currently in draft)

Quick commands:
/solo:invoice remind INV-2026-035 # Send reminder to Beta Inc
/solo:clients review "Beta Inc" # Check client relationship
/solo:invoice report # Full P&L report
```

---

## /solo:invoice report

Generate a monthly Profit & Loss report.

### Usage

```
/solo:invoice report              # Current month
/solo:invoice report --month Jan  # Specific month
/solo:invoice report --ytd        # Year-to-date
```

### What I Need From You

**Revenue:** Automatically calculated from paid invoices  
**Expenses:** You'll need to provide or I'll use estimates from previous months

### Output

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROFIT & LOSS REPORT — January 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 REVENUE

| Source             | Amount      | % of Total |
| ------------------ | ----------- | ---------- |
| Client work (paid) | €12,500     | 85%        |
| Retainer income    | €2,000      | 14%        |
| Other income       | €200        | 1%         |
| **Total Revenue**  | **€14,700** | **100%**   |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💸 EXPENSES

| Category              | Amount     | % of Revenue |
| --------------------- | ---------- | ------------ |
| Software & tools      | €450       | 3%           |
| Coworking / office    | €300       | 2%           |
| Marketing & ads       | €200       | 1%           |
| Professional services | €150       | 1%           |
| Travel & meals        | €100       | 1%           |
| Other                 | €50        | 0%           |
| **Total Expenses**    | **€1,250** | **9%**       |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 SUMMARY

| Metric                    | Value       | Status              |
| ------------------------- | ----------- | ------------------- |
| **Net Profit**            | **€13,450** | 🟢 Healthy          |
| **Profit Margin**         | **91.5%**   | 🟢 Excellent        |
| **Effective Hourly Rate** | **€168/hr** | (based on 80 hours) |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 TRENDS (Last 3 Months)

| Month    | Revenue | Expenses | Profit  | Margin |
| -------- | ------- | -------- | ------- | ------ |
| Nov 2025 | €10,200 | €1,100   | €9,100  | 89%    |
| Dec 2025 | €13,800 | €1,300   | €12,500 | 91%    |
| Jan 2026 | €14,700 | €1,250   | €13,450 | 91%    |

Trend: ↗️ Revenue up 6.5% month-over-month

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 INSIGHTS

✓ Strong profit margin (91.5%) — well above healthy threshold (>70%)
✓ Revenue trending upward — good momentum
✓ Low expense ratio (9%) — efficient operations
⚠️ Consider investing more in marketing to sustain growth

Runway: Sustainable (revenue > expenses)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Quick commands:
/solo:invoice status # Payment status
/solo:clients pipeline # Sales forecast
/solo:weekly-review # Full business dashboard
```

---

## /solo:invoice remind

Send payment reminders for overdue invoices.

### Usage

```
/solo:invoice remind INV-2026-035    # Specific invoice
/solo:invoice remind --all           # All overdue
```

### Reminder Escalation

I'll suggest the appropriate tone based on how overdue the invoice is:

| Days Overdue | Tone              | Template                       |
| ------------ | ----------------- | ------------------------------ |
| 1-7 days     | 😊 Friendly nudge | "Just checking in..."          |
| 8-14 days    | 📧 Firm follow-up | "Following up on payment..."   |
| 15-30 days   | ⚠️ Formal notice  | "Payment now overdue..."       |
| 30+ days     | 🛑 Final notice   | "Immediate action required..." |

### Output

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PAYMENT REMINDER — INV-2026-035
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Invoice: INV-2026-035
Client: Beta Inc (John Smith)
Amount: €2,000
Due Date: January 10, 2026
Days Late: 14 days
Tone: 📧 Firm follow-up

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUGGESTED EMAIL:

Subject: Following up on Invoice INV-2026-035

Hi John,

I hope this email finds you well. I'm following up on invoice INV-2026-035
for €2,000, which was due on January 10, 2026.

I understand that payments can sometimes slip through the cracks, so I wanted
to send a friendly reminder. If there are any issues with the invoice or if
you need any additional information, please let me know.

Could you please confirm the payment status and expected payment date?

Invoice details:

- Invoice number: INV-2026-035
- Amount due: €2,000
- Original due date: January 10, 2026

Thank you for your attention to this matter.

Best regards,
[Your name]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Actions:

1. Copy email above and send manually
2. Or use: /solo:write email "Beta Inc" --template payment-reminder
3. Update invoice status when paid: Mark as paid in the invoice file

Next escalation: If no response in 7 days, send formal notice
```

---

## What I Need From You

### For /solo:invoice create

- Client name (I'll look up details from your CRM)
- What you're invoicing for (service/deliverable)
- Billing type (hourly/project/retainer)
- Line items (tasks, hours, or deliverables)
- Payment terms (Net 15/30/60)

### For /solo:invoice status

- No input needed (scans all invoices)
- Optional: `--month` or `--overdue` flags

### For /solo:invoice report

- Revenue: Auto-calculated from invoices
- Expenses: You provide or I use last month's data
- Optional: Month or year-to-date flag

### For /solo:invoice remind

- Invoice number or `--all` for all overdue

---

## Agent Instructions

### /solo:invoice create

```python
# 1. Get client
client_name = get_argument() or ask("Which client?")
client_path = find_client_card(client_name)

if not client_path:
    create_new = ask_yes_no(f"Client '{client_name}' not found. Create new client card?")
    if create_new:
        invoke_command("/solo:clients add", client_name)
        client_path = find_client_card(client_name)
    else:
        client_data = ask_for_client_details()

client_data = parse_client_card(client_path)

# 2. Determine billing type
billing_type = ask_choice(["Hourly", "Project", "Retainer"])

# 3. Collect line items
if billing_type == "Hourly":
    line_items = []
    while True:
        task = ask("Task description (or 'done' to finish):")
        if task.lower() == "done":
            break
        hours = ask_number("Hours:")
        rate = ask_number("Hourly rate (€):", default=get_default_rate())
        line_items.append({"task": task, "hours": hours, "rate": rate, "total": hours * rate})

elif billing_type == "Project":
    line_items = []
    while True:
        deliverable = ask("Deliverable (or 'done' to finish):")
        if deliverable.lower() == "done":
            break
        amount = ask_number("Amount (€):")
        line_items.append({"description": deliverable, "amount": amount})

elif billing_type == "Retainer":
    monthly_fee = client_data.retainer_fee or ask_number("Monthly retainer fee (€):")
    line_items = [{"description": "Monthly retainer", "amount": monthly_fee}]

# 4. Calculate totals
subtotal = sum(item.get("total") or item.get("amount") for item in line_items)

is_vat_registered = ask_yes_no("Are you VAT registered?", default=True)
if is_vat_registered:
    vat_rate = ask_number("VAT rate (%)", default=20) / 100
    vat_amount = subtotal * vat_rate
    vat_note = None
else:
    vat_amount = 0
    vat_note = "TVA non applicable, art. 293 B du CGI"

total = subtotal + vat_amount

# 5. Payment terms
payment_terms = ask_choice(["On receipt", "Net 15", "Net 30", "Net 60"], default="Net 30")
issue_date = today()
due_date = calculate_due_date(issue_date, payment_terms)

# 6. Generate invoice number
invoice_number = generate_next_invoice_number()

# 7. Create invoice
template = read_file("solo/skills/invoice-generator/references/invoice-template.md")
invoice = populate_template(
    template,
    invoice_number=invoice_number,
    client=client_data,
    line_items=line_items,
    subtotal=subtotal,
    vat_amount=vat_amount,
    vat_note=vat_note,
    total=total,
    issue_date=issue_date,
    due_date=due_date,
    payment_terms=payment_terms,
    status="Draft"
)

invoice_path = f"data/1-Projets/invoices/{invoice_number}.md"
write_file(invoice_path, invoice)

# 8. Ask to mark as sent
mark_sent = ask_yes_no("Mark as 'Sent' now?", default=False)
if mark_sent:
    update_invoice_status(invoice_path, "Sent")

display_invoice_summary(invoice_number, client_data.name, total, due_date)
```

### /solo:invoice status

```python
# 1. Load all invoices
invoice_files = glob("data/1-Projets/invoices/*.md")
invoices = [parse_invoice(f) for f in invoice_files]

# 2. Filter by flag if provided
filter_flag = get_flag("--month", "--overdue")
if filter_flag == "--month":
    invoices = [inv for inv in invoices if inv.issue_date.month == today().month]
elif filter_flag == "--overdue":
    invoices = [inv for inv in invoices if inv.status == "Overdue" or (inv.status == "Sent" and inv.due_date < today())]

# 3. Calculate metrics
paid_invoices = [inv for inv in invoices if inv.status == "Paid"]
sent_invoices = [inv for inv in invoices if inv.status == "Sent"]
overdue_invoices = [inv for inv in invoices if inv.due_date < today() and inv.status != "Paid"]

metrics = {
    "paid_this_month": sum(inv.total for inv in paid_invoices if inv.paid_date.month == today().month),
    "outstanding": sum(inv.total for inv in sent_invoices),
    "overdue": sum(inv.total for inv in overdue_invoices),
    "collection_rate": len(paid_invoices) / len(invoices) * 100 if invoices else 0,
    "avg_days_to_pay": avg([inv.days_to_pay for inv in paid_invoices if inv.days_to_pay])
}

# 4. Group by status
by_status = group_by(invoices, key="status")

# 5. Display dashboard
display_invoice_status_dashboard(metrics, by_status, overdue_invoices, sent_invoices, paid_invoices)
```

### /solo:invoice report

```python
# 1. Determine period
period = get_flag("--month", "--ytd") or "current"
if period == "--month":
    month = ask("Which month? (e.g., Jan, February)")
    start_date, end_date = parse_month_range(month)
elif period == "--ytd":
    start_date = date(today().year, 1, 1)
    end_date = today()
else:
    start_date = date(today().year, today().month, 1)
    end_date = today()

# 2. Calculate revenue
invoices = load_invoices_in_range(start_date, end_date)
paid_invoices = [inv for inv in invoices if inv.status == "Paid"]

revenue = {
    "client_work": sum(inv.total for inv in paid_invoices if inv.type != "Retainer"),
    "retainer": sum(inv.total for inv in paid_invoices if inv.type == "Retainer"),
    "other": 0  # User can add manually
}
total_revenue = sum(revenue.values())

# 3. Get expenses
expenses = ask_for_expenses() or load_last_month_expenses()

total_expenses = sum(expenses.values())

# 4. Calculate profit
net_profit = total_revenue - total_expenses
profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0

# 5. Calculate effective hourly rate
hours_worked = ask_number("Hours worked this month:", default=estimate_hours_from_invoices(paid_invoices))
effective_rate = net_profit / hours_worked if hours_worked > 0 else 0

# 6. Get trends (last 3 months)
trends = calculate_revenue_trends(months=3)

# 7. Display P&L report
display_pl_report(revenue, expenses, net_profit, profit_margin, effective_rate, trends)
```

### /solo:invoice remind

```python
# 1. Get invoice
invoice_number = get_argument()
if invoice_number == "--all":
    invoices = find_all_overdue_invoices()
else:
    invoice = find_invoice(invoice_number)
    if not invoice:
        error(f"Invoice {invoice_number} not found")
        return
    invoices = [invoice]

# 2. For each overdue invoice
for invoice in invoices:
    days_overdue = (today() - invoice.due_date).days

    # Determine tone
    if days_overdue <= 7:
        tone = "Friendly nudge"
        template_key = "friendly"
    elif days_overdue <= 14:
        tone = "Firm follow-up"
        template_key = "firm"
    elif days_overdue <= 30:
        tone = "Formal notice"
        template_key = "formal"
    else:
        tone = "Final notice"
        template_key = "final"

    # Generate reminder
    reminder = generate_payment_reminder(invoice, tone, template_key)

    # Display
    display_reminder(invoice, days_overdue, tone, reminder)

    # Suggest next steps
    suggest_next_escalation(days_overdue)
```

---

## Error Handling

### Client Not Found

```
❌ Client not found: "Acme Corp"

Options:
  1. Create new client: /solo:clients add "Acme Corp"
  2. Search existing clients: /solo:clients review
  3. Provide client details manually
```

### No Invoices Found

```
📭 No invoices found

You haven't created any invoices yet.

Create your first invoice:
  /solo:invoice create
```

### Missing Expense Data

```
⚠️  Expense data needed for P&L report

I can calculate revenue from your invoices, but I need expense data.

Options:
  1. Provide this month's expenses now (I'll ask category by category)
  2. Use last month's expenses as estimate
  3. Skip expenses and show revenue-only report
```

---

## Tips

1. **Invoice immediately** — Don't wait. Create and send invoices as soon as work is delivered or milestones are hit.

2. **Track everything** — Even small invoices. They add up and you need accurate revenue data for taxes.

3. **Set clear payment terms** — Net 30 is standard, but consider Net 15 for new clients or large invoices.

4. **Follow up early** — Don't wait until 30 days overdue. Send a friendly reminder at 7 days.

5. **Use retainers** — Monthly retainers provide predictable cash flow and reduce invoicing overhead.

6. **Monitor collection rate** — Healthy is >90%. If yours is lower, tighten payment terms or require deposits.

7. **Know your effective rate** — Your hourly rate means nothing if you're spending unpaid time on admin. Track net profit ÷ hours worked.

---

## Integration with Other Commands

- **After closing a deal:** Use `/solo:invoice create [client]` to bill immediately
- **Before a client call:** Use `/solo:invoice status` to check if they're current on payments
- **Weekly planning:** Use `/solo:weekly-review` to see invoices alongside pipeline and tasks
- **Month-end:** Use `/solo:invoice report` for your P&L and tax prep

---

## Skills Used

This command uses these skills:

- `invoice-generator` — Invoice creation and numbering
- `financial-health` — Revenue calculation and P&L reporting
- `client-management` — Client data lookup
- `pricing-strategy` — Rate card and pricing models
