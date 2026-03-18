---
name: daily-briefing
description: Start your day with a prioritized sales briefing. Works standalone when you tell me your meetings and priorities, supercharged when you connect your calendar, CRM, and email. Trigger with "morning briefing", "daily brief", "what's on my plate today", "prep my day", or "start my day".
bundle: pipeline-ops
triggers:
  - "morning briefing"
  - "daily brief"
  - "what is on my plate today"
tools:
  standalone: [filesystem]
  supercharged: [calendar, crm]
version: 1.0.0
---

# Daily Sales Briefing

Get a clear view of what matters most today. Works with whatever you tell me, and gets richer when you connect your tools.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                      DAILY BRIEFING                              │
├─────────────────────────────────────────────────────────────────┤
│  ALWAYS (works standalone)                                       │
│  ✓ You tell me: today's meetings, key deals, priorities         │
│  ✓ I organize: prioritized action plan for your day             │
│  ✓ Output: scannable 2-minute briefing                          │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                      │
│  + Calendar: auto-pull today's meetings with attendees          │
│  + CRM: pipeline alerts, tasks, deal health                     │
│  + Email: unread from key accounts, waiting on replies          │
│  + Enrichment: overnight signals on your accounts               │
└─────────────────────────────────────────────────────────────────┘
```

## Getting Started

**If no calendar connected:** "What meetings do you have today?"
**If no CRM connected:** "What deals are you focused on this week?"
**If connectors active:** I'll pull everything automatically.

## Connectors (Optional)

| Connector | What It Adds |
|-----------|--------------|
| **~~calendar** | Today's meetings with attendees, times, and context |
| **~~CRM** | Open pipeline, deals closing soon, overdue tasks, stale deals |
| **~~email** | Unread from opportunity contacts, emails waiting on replies |
| **~~enrichment** | Overnight signals: funding, hiring, news on your accounts |

> **No connectors?** Just tell me your meetings and deals.

## Modes

- **Full briefing** — Default. Full pipeline + meetings + email.
- **Quick mode** — "quick brief" or "tldr my day" — priority + 3 bullets.
- **End of day** — "wrap up my day" — completed meetings, tomorrow's focus.

See `references/briefing-guide.md` for output templates, priority scoring logic, execution flow, and section detail.
