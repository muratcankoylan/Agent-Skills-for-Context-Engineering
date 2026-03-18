---
description: Get a personalized weekly coaching session based on your pipeline, outreach, and win-loss patterns
argument-hint: "[focus area] or leave blank for full review"
allowed-tools: Read, Write, Glob
model: sonnet
---

# /coach

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

Your personal sales coach. Reviews your activity, identifies skill gaps, and gives you a concrete plan for this week.

## Usage

```
/coach                              # Full weekly coaching review
/coach deals                        # Focus on deal-specific coaching only
/coach outreach                     # Focus on outreach and messaging
/coach [company]                    # Coaching on a specific deal
/coach skills                       # Identify and practice skill gaps
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                          COACH                                   │
├─────────────────────────────────────────────────────────────────┤
│  ALWAYS (works standalone)                                       │
│  ✓ Pipeline analysis: where are deals stuck and why?            │
│  ✓ Skill gap identification from patterns                       │
│  ✓ Personalized coaching plan for this week                     │
│  ✓ Practice session assignment (roleplay, email review, etc.)   │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                      │
│  + CRM: Analyze activity data and engagement signals            │
│  + Email: Review sent outreach for effectiveness patterns       │
│  + Transcripts: Analyze call recordings for coaching signals    │
└─────────────────────────────────────────────────────────────────┘
```

---

## What to Expect

The coach reviews:

1. **Pipeline** — Deals stuck at the same stage for 14+ days. For each, a root cause hypothesis and a specific action.
2. **Outreach** — Response rates, quality signals from recent emails.
3. **Win-Loss Patterns** — If you have post-mortems, the coach identifies recurring skill gaps across them.
4. **Methodology Execution** — Are you following your defined sales process consistently?

The output is always:
- **1 deal to focus on** (with specific coaching notes)
- **1 skill to practice** (with a specific practice session)
- **1 habit to build** (a repeatable behavior to install this week)

---

## Skill Practice Routing

When the coach identifies a skill gap, it routes you to the right practice:

| If the issue is... | The coach sends you to... |
|--------------------|--------------------------|
| Deals dying after discovery | `roleplay-dojo-agent` — Discovery persona |
| Price objections | `objection-library` — Price category + roleplay |
| Outreach not converting | `email-coach` — Review last 3 emails |
| Champion not developing | `champion-builder` — PACT assessment on top deal |
| Negotiation breaking down | `negotiation-advisor` + `roleplay-dojo-agent` |

---

## Example Output

```
# Coaching Session: Week of [Date]

---

🔴 Deal Focus: GlobalTech ($80K — Proposal Stage, 18 days stuck)

What I see: No activity in 18 days after proposal sent.
Champion (Director of IT) has gone quiet.
No Economic Buyer ever identified.

Hypothesis: Access Gap. Champion doesn't have the authority
to push this through without executive sponsorship.

This week: Run /champion-builder GlobalTech.
PACT score will tell you if you need to go around or above them.

---

🟡 Skill Practice: You've lost 3 deals to "timing" in the last 60 days.

In each case, no Compelling Event was identified in discovery.

Practice: Run /coach roleplay — Discovery persona, CFO character.
Focus specifically on the "Why Now" questioning sequence.
Goal: Get comfortable asking "What happens if you do nothing for
another 6 months?" before closing a discovery call.

---

🟢 Habit: You're ending calls without documented next steps.

7 of your last 12 call notes have no explicit next step recorded.

This week: Before you close every call, say: "Let me confirm
what we're both doing next — I'll [X] and you'll [Y] by [date]."
Write it down immediately after.

---

Quick Wins Today:
☐ Bump email to Acme (silent 11 days)
☐ Add next step to 3 missing call notes
☐ Schedule the GlobalTech champion check-in
```

---

## Related Agents & Skills

- **sales-coach-agent** — The underlying agent powering this command
- **roleplay-dojo-agent** — Practice sessions for skill development
- **objection-library** — Targeted objection handling practice
- **email-coach** — Outreach effectiveness review
- **champion-builder** — Deal-specific champion development
- **win-loss** — Feed the coach better data by running post-mortems regularly
