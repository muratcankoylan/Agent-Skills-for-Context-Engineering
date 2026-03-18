---
name: retainer-manager
description: >
  Tracks retainer relationships including utilization, over/under-delivery, renewal
  timing, and churn risk. Triggers on "retainer status", "retainer review",
  "am I over-delivering", "retainer renewal", "retainer utilization", or
  "retainer health".
version: 1.0.0
bundle: revenue-ops
triggers:
  - "manage retainer"
  - "retainer utilization"
  - "retainer status"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Retainer Manager

Retainers are the most valuable revenue type for a solopreneur: recurring, predictable, and relationship-deepening. But unmanaged retainers become liabilities — you over-deliver (working for free), under-deliver (risking cancellation), or let them renew on autopilot without renegotiating scope that has crept beyond the original value.

This skill makes every retainer relationship visible and proactively managed.

## Retainer Data Structure

For each retainer, maintain a record at `data/1-Projets/clients/[client]-retainer.md`:

```markdown
# Retainer: [Client Name]

**Status:** Active / At Risk / Renewal Pending / Paused
**Monthly Fee:** €[X]
**Contract Period:** [Start date] → [End date or rolling]
**Renewal Date:** [Date]
**Auto-Renewal:** Yes / No / 30-day notice required

## Retainer Scope
[What is included each month — hours or deliverables]
- [Item 1]
- [Item 2]
- Monthly hours (if hours-based): [X] hours/month

## Monthly Utilization Log
| Month | Hours Used | Deliverables | Health | Notes |
|-------|-----------|--------------|--------|-------|
| [Month] | [X]h | [list] | 🟢/🟡/🔴 | |

## Relationship Health
- Last conversation (outside deliveries): [date]
- Satisfaction signals: [positive / neutral / negative]
- Expansion signals: [any mentions of more work?]
- Churn signals: [budget reviews, reorganization, reduced responsiveness?]

## Renewal Notes
[What to discuss at next renewal]
```

## Utilization Tracking

### For Hours-Based Retainers

Track monthly against the agreed hours:

| Utilization | Signal | Risk |
|-------------|--------|------|
| 90–110% of included hours | 🟢 Healthy | Client is getting full value |
| 70–90% | 🟡 Under-using | May question value at renewal |
| <70% for 2+ months | 🔴 Under-using | Renewal at risk |
| 110–130% | 🟡 Over-delivering | Working for free |
| >130% | 🔴 Severe over-delivery | Address immediately |

**Under-delivery action:**
When utilization drops below 70% for 2 months, proactively contact the client:
> "I've noticed we haven't used your full retainer capacity recently. I want to make sure you're getting full value. What are you working on right now where I could be most useful?"

This shows care, prompts work, and prevents silent non-renewal.

**Over-delivery action:**
When utilization exceeds 130%, flag immediately:
> "I've gone over this month's included hours. Let me know how you'd like to handle this: I can invoice the extra [X] hours separately, we can roll them forward, or we can discuss adjusting the retainer scope."

Never silently absorb over-delivery — it trains clients to expect unlimited work.

### For Deliverables-Based Retainers

Track what was agreed vs. delivered:

| Month | Agreed Deliverables | Delivered | Status |
|-------|--------------------|-----------|----|
| [Month] | [list] | [list] | ✅ / ⚠️ / ❌ |

Flag any month where agreed deliverables were not fully delivered — and communicate proactively before the client notices.

## Churn Risk Scoring

Score each retainer monthly (0–10):

| Signal | Weight | Green | Yellow | Red |
|--------|--------|-------|--------|-----|
| Payment on time | 2pts | Always | 1-7 days late | 8+ days late |
| Utilization level | 2pts | 80-110% | 60-80% or 110-130% | <60% or >130% |
| Communication responsiveness | 2pts | <24h reply | 1-3 days | 4+ days |
| Proactive engagement | 2pts | They initiate requests | Passive | Radio silence |
| Renewal timeline | 2pts | 90+ days away | 30-60 days | <30 days |

**Score interpretation:**
- 8–10: 🟢 Healthy
- 5–7: 🟡 Monitor closely
- <5: 🔴 At risk — action required

## Renewal Management

### Renewal Calendar

Track all retainer renewal dates in a single overview:

```
# Retainer Renewal Calendar

| Client | Monthly Fee | Renewal Date | Days Away | Risk Score | Action |
|--------|-------------|-------------|-----------|------------|--------|
| [Name] | €[X] | [date] | [X] | 8/10 | Prepare renewal proposal |
| [Name] | €[X] | [date] | [X] | 5/10 | Schedule check-in this week |
| [Name] | €[X] | [date] | [X] | 3/10 | At risk — intervention needed |
```

### Renewal Timeline

- **90 days before renewal:** Review retainer health score. Prepare notes on what's changed (scope, your rates, their needs).
- **60 days before renewal:** Schedule a "retainer review" conversation.
- **30 days before renewal:** Send renewal proposal with any adjustments.
- **14 days before renewal:** Confirm or negotiate terms.

### The Retainer Review Conversation (60 Days Out)

The goal is not to sell the renewal — it's to understand whether the retainer is still serving both parties.

**Your questions:**
- "How has the past [period] been? What's worked well?"
- "Is there anything about the scope or the way we work together that you'd want to change?"
- "What's on your plate for the next 6 months? Are there new areas where I could be more useful?"

**What you're listening for:**
- Hints of budget pressure (tighten terms, offer to adjust scope down)
- New needs (opportunity to expand scope and increase fee)
- Satisfaction issues not yet surfaced (better to hear them now)

### Renewal Proposal Structure

```
Subject: [Client] Retainer Renewal — [Period]

Hi [Name],

It's been [X months] working together, and I wanted to make sure the retainer
still makes sense for what you need.

**What we've done together:**
[Brief bullets of value delivered — use specific outcomes, not just tasks]

**What I'd propose for the next period:**
[Adjusted scope if anything has changed, or "same terms" if stable]
- Monthly fee: €[X] [same / adjusted from €X to €X because Y]
- Included: [scope items]
- Term: [period]

**Why I've adjusted [if applicable]:**
[Transparent reason — usually rates, scope expansion, or value delivered]

Let me know if you'd like to discuss before I send the updated agreement.

[Your name]
```

## The "Retainer or Project?" Decision

When a repeat client comes back for another project, present the retainer option:

**When to propose a retainer:**
- Client has used you for 2+ projects
- Their needs are ongoing (not a one-time transformation)
- The work pattern is monthly (maintenance, advisory, content, etc.)

**Retainer pitch script:**
> "I've noticed we've done [X] projects together over [period]. At this point, it might make more sense for both of us to structure this as a monthly retainer — you get priority access to my time and a lower effective rate, and I get predictability. Here's what that could look like: [€X/month for Y hours or Z deliverables]. Want me to put together a retainer proposal?"

## Integration Points

- **`invoice-generator`**: Monthly retainer invoices should be auto-templated
- **`financial-health`**: Retainer MRR feeds revenue forecasting
- **`client-lifecycle-agent`**: Triggers renewal action at 60 days
- **`business-health-advisor`**: Retainer coverage is a key health dimension
- **`capacity-planner`**: Retainer hours are baseline committed capacity each month

## Key References

- **`references/retainer-types.md`**: Four retainer models (hours, deliverables, access, advisory) with pros/cons and ideal client profiles
- **`references/renewal-negotiation.md`**: Scripts for rate increases, scope adjustments, and difficult renewal conversations
