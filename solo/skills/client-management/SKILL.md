---
name: client-management
description: >
  Manages a client contact database with interaction history, deal tracking, and
  relationship health scoring. Triggers on "add a client", "client list",
  "client dashboard", "show me [client]", or "update [client]".
version: 1.0.0
bundle: client-work
triggers:
  - "add a client"
  - "client list"
  - "client dashboard"
  - "show me [client]"
  - "update [client]"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Client Management

Provides local CRM functionality through individual client files in `data/1-Projets/clients/`. Each client gets a comprehensive card tracking contact details, deal history, meeting notes, revenue, and relationship health.

## Client Card Structure

Each client file at `data/1-Projets/clients/[client-slug].md` follows the template in `references/client-template.md`. The template includes:

### Sections
1. **Contact Information** — name, role, email, phone, LinkedIn, company, source
2. **Deal Information** — status, service, value, stage, dates, next action
3. **Deal History** — table of all past and current engagements
4. **Meeting Notes** — chronological log of interactions
5. **Revenue Summary** — lifetime value, invoices, payment history
6. **Relationship Health** — scoring based on contact recency, responsiveness, satisfaction

## Operations

### Adding a Client
1. Ask for: name, company, email, role, source (referral/inbound/outreach)
2. Create `data/1-Projets/clients/[client-slug].md` from template
3. Set initial status to "Prospect"
4. Set "First Contact" to today
5. If a deal is involved, also update `data/1-Projets/pipeline.md`

### Reviewing a Client
1. Read the client file
2. Present a formatted dashboard showing:
   - Contact details
   - Current deal status and next action
   - Last 3 interactions
   - Revenue summary
   - Relationship health score with color (Green/Yellow/Red)

### Logging an Interaction
1. Append to the Meeting Notes section with date, type, and summary
2. Update "Last Contact" date
3. Update relationship health score based on recency

### Updating Deal Stage
1. Update the Stage field in the client card
2. Update `data/1-Projets/pipeline.md` to match
3. If stage = "Signed", trigger creation of project folder in `data/1-Projets/`

## Relationship Health Scoring

| Signal | Green | Yellow | Red |
|--------|-------|--------|-----|
| **Last contact** | < 7 days | 7-14 days | 14+ days |
| **Responsiveness** | Replies within 24h | Replies in 2-3 days | 4+ days or ghosting |
| **Satisfaction** | Positive feedback, engaged | Neutral, passive | Complaints, disengaged |
| **Invoice status** | All paid on time | 1 overdue | 2+ overdue |

**Overall score:** Worst signal determines the color. One Red = overall Red.

## Supercharged Mode

If `~~CRM` is connected:
- Fetch client data from CRM first, merge with local file
- Offer to push interaction logs back to CRM
- Pull activity data (emails, meetings) for health scoring

## Key References

- **`references/client-template.md`**: Full client card template
