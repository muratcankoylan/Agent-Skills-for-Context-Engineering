---
name: invoice-generator
description: >
  Generates professional invoices from project and client data with auto-numbering,
  multiple billing types, and payment tracking. Triggers on "create invoice",
  "invoice for", "bill [client]", or "generate invoice".
version: 1.0.0
bundle: revenue-ops
triggers:
  - "create invoice"
  - "invoice for"
  - "bill [client]"
  - "generate invoice"
tools:
  standalone: ["filesystem"]
  supercharged: ["stripe"]
---

# Skill: Invoice Generator

Automates invoice creation by pulling client and project data, applying the correct billing type, and saving a professional invoice with automatic numbering.

## Invoice Types

Support three billing models:

| Type | When to Use | Line Items |
|------|------------|------------|
| **Hourly** | Time-tracked work, ongoing support | Hours x rate per line item |
| **Project** | Fixed-fee engagements with defined deliverables | Milestone-based or lump sum |
| **Retainer** | Monthly recurring service agreements | Fixed monthly fee |

## Invoice Numbering

Format: `INV-YYYY-NNN`
- `YYYY` = year of issue
- `NNN` = sequential number, zero-padded (001, 002, ...)
- Auto-detect next number by scanning `data/1-Projets/invoices/` for existing files
- If no invoices exist, start at `INV-[current year]-001`

## Creation Process

### Step 1: Identify Client
- Check `data/1-Projets/clients/[client].md` for contact details
- Pull: company name, contact name, email, address
- If no client card exists, ask the user for details and offer to create one

### Step 2: Determine Line Items
- Ask: "What are you invoicing for?"
- For **hourly**: ask for tasks, hours per task, and hourly rate
- For **project**: ask for deliverables and their prices (or milestones)
- For **retainer**: use the agreed monthly fee from the client card

### Step 3: Calculate Totals
- Subtotal = sum of all line items
- Tax = subtotal x tax rate (default 20% TVA for French solopreneurs; configurable)
- If user is not VAT-registered (micro-entrepreneur), set tax to 0% and add "TVA non applicable, art. 293 B du CGI"
- Grand total = subtotal + tax

### Step 4: Set Payment Terms
- Default: Net 30
- Options: On receipt, Net 15, Net 30, Net 60
- Due date = issue date + payment terms
- Payment method: bank transfer (default), Stripe, PayPal

### Step 5: Generate and Save
- Populate `references/invoice-template.md` with all data
- Save as `data/1-Projets/invoices/INV-YYYY-NNN.md`
- Set status to "Draft"
- Ask: "Ready to mark as Sent, or keep as Draft?"

## Late Payment Reminders

Generate reminder messages at escalating thresholds:

| Days Overdue | Tone | Action |
|-------------|------|--------|
| 7 | Friendly nudge | Gentle reminder email |
| 14 | Firm follow-up | Request payment status confirmation |
| 30 | Formal notice | Pause work, reference contractual terms |
| 60+ | Final notice | Mention late payment penalties (if in contract) |

## Integration Points

- **`client-management`**: Pulls client contact details
- **`pricing-strategy`**: Pulls rates from rate card
- **`financial-health`**: Invoice data feeds revenue calculations
- **Supercharged (~~invoicing)**: Push invoice to Stripe as a draft

## Key References

- **`references/invoice-template.md`**: Standard invoice markdown template with reminder templates
