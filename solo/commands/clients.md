---
description: "Manage clients and sales pipeline — track deals, log interactions, monitor health"
argument-hint: "[add | review | pipeline | follow-up]"
allowed-tools: Read, Write, Glob
model: sonnet
---

# /solo:clients

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

Your local CRM — manage client relationships, track deals through your pipeline, and never miss a follow-up. Each client gets a comprehensive card with contact details, deal history, meeting notes, and relationship health scoring.

## Usage

```
/solo:clients add          # Add a new client or prospect
/solo:clients review       # View client dashboard
/solo:clients pipeline     # See your full sales pipeline
/solo:clients follow-up    # Check overdue actions
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                    CLIENT MANAGEMENT                              │
├──────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                        │
│  ✓ Client cards: Markdown files in PARA structure                │
│  ✓ Deal tracking: Stage, value, next action, close date          │
│  ✓ Interaction log: Meeting notes with timestamps                │
│  ✓ Health scoring: Auto-calculated from contact recency          │
│  ✓ Pipeline view: All deals with risk flags                      │
├──────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                       │
│  + ~~CRM: Sync with HubSpot, Close, or other CRM                 │
│  + ~~email: Pull interaction history automatically               │
│  + ~~calendar: Track meetings and follow-up reminders            │
│  + ~~chat: Get notified of overdue follow-ups                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## /solo:clients add

Add a new client or prospect to your CRM.

### What I Need From You

**Quick add** (I'll ask follow-up questions):

```
/solo:clients add "Sarah Chen from Acme Corp"
```

**Full add** (provide all details):

```
/solo:clients add
Name: Sarah Chen
Company: Acme Corp
Role: VP of Product
Email: sarah@acme.com
Source: LinkedIn outreach
Deal: Website redesign, $15K, Discovery stage
```

### Interactive Flow

1. **Basic Info**
   - Name (required)
   - Company (required)
   - Role
   - Email
   - Phone (optional)
   - LinkedIn URL (optional)

2. **Source**
   - How did you meet? (Referral / Inbound / Outreach / Event / Other)
   - Referrer name (if applicable)

3. **Deal Info** (optional, can add later)
   - Service/product
   - Estimated value
   - Current stage (Prospect / Discovery / Proposal / Negotiation)
   - Expected close date

### Output

```
Client added: Sarah Chen

Client card created at:
  data/1-Projets/clients/sarah-chen-acme-corp.md

Next steps:
  - Schedule discovery call
  - Send intro email
  - Research Acme Corp's needs

Quick actions:
  /solo:clients review "Sarah Chen"     # View full profile
  /solo:prospect research "Acme Corp"   # Research the company
  /solo:write proposal "Sarah Chen"     # Draft proposal
```

---

## /solo:clients review

View a comprehensive dashboard for a specific client.

### Usage

```
/solo:clients review "Sarah Chen"
/solo:clients review acme    # Partial match works
```

### Output

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLIENT: Sarah Chen
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONTACT INFORMATION
Company: Acme Corp
Role: VP of Product
Email: sarah@acme.com
LinkedIn: linkedin.com/in/sarahchen
Source: LinkedIn outreach (Jan 15, 2026)

CURRENT DEAL
Service: Website redesign
Value: $15,000
Stage: Proposal -> Negotiation
Close Date: Feb 28, 2026 (15 days away)
Next Action: Follow up on proposal questions (Due: Jan 25)

DEAL HISTORY
| Date | Service | Value | Status |
|------------|------------------|---------|-------------|
| Jan 2026 | Website redesign | $15,000 | In progress |

RECENT INTERACTIONS (Last 3)
Jan 22 | Call | 30min discovery call - discussed pain points
Jan 20 | Email | Sent proposal with 3 package options
Jan 18 | LinkedIn | Initial outreach, positive response

REVENUE SUMMARY
Lifetime Value: $15,000 (projected)
Invoices Sent: $0
Invoices Paid: $0
Outstanding: $0

RELATIONSHIP HEALTH: HEALTHY
Last Contact: 2 days ago (Healthy)
Responsiveness: Replies within 24h (Healthy)
Satisfaction: Engaged, asking good questions (Healthy)
Invoice Status: N/A - no invoices yet

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUGGESTED ACTIONS:

1. Follow up on proposal questions (overdue by 1 day)
2. Send case study examples
3. Schedule contract review call

Quick commands:
/solo:clients log "Sarah Chen" # Log an interaction
/solo:invoice create "Sarah Chen" # Create invoice
/solo:write email "Sarah Chen" # Draft follow-up email
```

---

## /solo:clients pipeline

View your full sales pipeline with deal stages, risk flags, and weekly action plan.

### Usage

```
/solo:clients pipeline              # All deals
/solo:clients pipeline --active     # Active deals only
/solo:clients pipeline --risks      # Show only at-risk deals
```

### Output

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SALES PIPELINE — January 24, 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUMMARY
Active Deals: 5
Total Value: $67,000
Weighted Pipeline: $32,600 (based on stage probability)
Avg Deal Size: $13,400
Avg Deal Age: 18 days

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BY STAGE

| Stage       | Deals | Value   | Weighted | % Pipeline |
| :---------- | :---- | :------ | :------- | :--------- |
| Discovery   | 2     | $22,000 | $4,400   | 33%        |
| Proposal    | 1     | $15,000 | $6,000   | 22%        |
| Negotiation | 1     | $20,000 | $12,000  | 30%        |
| Verbal      | 1     | $10,000 | $8,000   | 15%        |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RISK FLAGS (3 deals need attention)

| Client         | Value   | Risk          | Days | Action         |
| -------------- | ------- | ------------- | ---- | -------------- |
| TechStart Inc  | $20,000 | Stale         | 16   | Re-engage ASAP |
| Beta Solutions | $12,000 | Past close    | -5   | Update date    |
| Gamma LLC      | $10,000 | Single-thread | 22   | Multi-thread   |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WEEKLY ACTION PLAN

Priority 1: Close Gamma LLC ($10K, Verbal stage)
-> Send contract today
-> Follow up on legal review
-> Target close: Jan 31

Priority 2: Re-engage TechStart Inc ($20K, Negotiation)
-> No contact in 16 days - send check-in email
-> Offer to address any concerns
-> Risk of going cold

Priority 3: Move Acme Corp to Negotiation ($15K, Proposal)
-> Follow up on proposal questions
-> Schedule contract review call
-> Target close: Feb 28

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PIPELINE HEALTH: GOOD

- Active deals: 5 (healthy range: 3-8)
- Pipeline value: 2.2x monthly target
- Deal velocity: 18 days avg (target: <15 days) [ATTENTION]
- New deals this week: 2

Recommendation: Focus on closing Gamma LLC and re-engaging TechStart.
Your pipeline is healthy but watch for deals getting stuck.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Quick commands:
/solo:clients review "TechStart" # View at-risk client
/solo:write email "TechStart" # Draft re-engagement email
/solo:weekly-review # Full business dashboard
```

---

## /solo:clients follow-up

Show all overdue actions and clients you haven't contacted recently.

### Usage

```
/solo:clients follow-up
```

### Output

```markdown
OVERDUE FOLLOW-UPS — January 24, 2026

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

URGENT (Overdue by 3+ days)

1. Sarah Chen (Acme Corp) — $15K deal
   Due: Jan 21 (3 days overdue)
   Action: Follow up on proposal questions

   Quick fix:
   /solo:write email "Sarah Chen" --template follow-up

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SOON (Due in next 3 days)

2. Gamma LLC — $10K deal
   Due: Jan 26 (2 days)
   Action: Send contract for signature
3. Beta Solutions — $12K deal
   Due: Jan 27 (3 days)
   Action: Schedule kickoff call

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GOING COLD (No contact in 14+ days)

4. TechStart Inc — $20K deal
   Last contact: Jan 8 (16 days ago)
   Status: Negotiation stage
   Risk: Deal may be stalling

   Suggested action:
   Send a "breakup email" to re-engage or qualify out

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUMMARY:

- 1 urgent overdue action
- 2 actions due this week
- 1 client going cold

Recommended: Block 1 hour today to clear urgent follow-ups.
```

---

## What I Need From You

### For /solo:clients add

- Client name and company (required)
- Contact info (email, role, LinkedIn)
- How you met (source)
- Deal details if applicable (service, value, stage)

### For /solo:clients review

- Client name or company (I'll fuzzy match)

### For /solo:clients pipeline

- No input needed (shows all active deals)
- Optional: `--active` or `--risks` flags

### For /solo:clients follow-up

- No input needed (scans all clients for overdue actions)

---

## Agent Instructions

### /solo:clients add

```python
# 1. Gather client information
client_info = interactive_form([
    ("name", "Client name", required=True),
    ("company", "Company", required=True),
    ("role", "Role/Title", required=False),
    ("email", "Email", required=False),
    ("phone", "Phone", required=False),
    ("linkedin", "LinkedIn URL", required=False),
    ("source", "How did you meet?", choices=["Referral", "Inbound", "Outreach", "Event", "Other"]),
])

# 2. Ask about deal
has_deal = ask_yes_no("Is there an active deal or opportunity?")

if has_deal:
    deal_info = interactive_form([
        ("service", "Service/Product", required=True),
        ("value", "Estimated value ($)", required=True),
        ("stage", "Current stage", choices=["Prospect", "Discovery", "Proposal", "Negotiation", "Verbal"]),
        ("close_date", "Expected close date", required=False),
    ])
else:
    deal_info = None

# ... [Rest of logic] ...
```

---

## Skills Used

- `client-management` — Client card creation and management
- `sales-pipeline` — Deal tracking and risk scoring
- `draft-outreach` — Follow-up email suggestions
- `financial-health` — Revenue tracking integration
