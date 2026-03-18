# Daily Briefing — Guide de Référence

## Output Format (Full Briefing)

```markdown
# Daily Briefing | [Day, Month Date]

## #1 Priority

**[Most important thing to do today]**
[Why it matters and what to do about it]

## Today's Numbers

| Open Pipeline | Closing This Month | Meetings Today | Action Items |
|---------------|-------------------|----------------|--------------|
| $[X]          | $[X]              | [N]            | [N]          |

## Today's Meetings

### [Time] — [Company] ([Meeting Type])
**Attendees:** [Names]
**Context:** [One-line: deal status, last touch, what's at stake]
**Prep:** [Quick action before this meeting]

*Run `call-prep [company]` for detailed meeting prep*

## Pipeline Alerts

### Needs Attention
| Deal | Stage | Amount | Alert | Action |
|------|-------|--------|-------|--------|
| [Deal] | [Stage] | $[X] | [Why flagged] | [What to do] |

### Closing This Week
| Deal | Close Date | Amount | Confidence | Blocker |
|------|------------|--------|------------|---------|
| [Deal] | [Date] | $[X] | [H/M/L] | [If any] |

## Email Priorities

### Needs Response
| From | Subject | Received |
|------|---------|----------|
| [Name @ Company] | [Subject] | [Time] |

### Waiting On Reply
| To | Subject | Sent | Days Waiting |
|----|---------|------|--------------|
| [Name @ Company] | [Subject] | [Date] | [N] |

## Suggested Actions

1. **[Action]** — [Why now]
2. **[Action]** — [Why now]
3. **[Action]** — [Why now]

*Run `call-prep [company]` before meetings | `call-follow-up` after calls*
```

---

## Quick Mode Output

Triggered by: "quick brief" or "tldr my day"

```markdown
# Quick Brief | [Date]

**#1:** [Priority action]

**Meetings:** [N] — [Company 1], [Company 2], [Company 3]

**Alerts:**
- [Alert 1]
- [Alert 2]

**Do Now:** [Single most important action]
```

---

## End of Day Output

Triggered by: "wrap up my day" or "end of day summary"

```markdown
# End of Day | [Date]

**Completed:**
- [Meeting 1] — [Outcome]
- [Meeting 2] — [Outcome]

**Pipeline Changes:**
- [Deal] moved to [Stage]

**Tomorrow's Focus:**
- [Priority 1]
- [Priority 2]

**Open Loops:**
- [ ] [Unfinished item needing follow-up]
```

---

## Execution Flow

### Step 1: Gather Context

**If connectors available:**
1. Calendar → Get today's external meetings (non-company attendees), pull time/title/attendees/description
2. CRM → Query open opportunities owned by you; flag closing this week, no activity 7+ days, slipped dates; get overdue + upcoming tasks
3. Email → Unread from opportunity contact domains; sent messages with no reply (3+ days)
4. Enrichment → Funding, hiring, news on open accounts (if available)

**If no connectors:**
1. "What meetings do you have today?"
2. "What deals are you focused on? Any closing soon or needing attention?"
3. "Anything urgent I should know about?"

### Step 2: Priority Scoring

```
1. URGENT:  Deal closing today/tomorrow, not yet won
2. HIGH:    Meeting today with high-value opportunity
3. HIGH:    Unread email from decision-maker
4. MEDIUM:  Deal closing this week
5. MEDIUM:  Stale deal (7+ days no activity)
6. LOW:     Tasks due this week

#1 Priority selection logic:
- Meeting with >$50K deal today → prep that
- Deal closing today → focus on close
- Urgent email from buyer → respond first
- Else → highest-value stale deal
```

### Step 3: Assemble Sections

Include sections based on available data:
1. **#1 Priority** — Always include
2. **Today's Numbers** — CRM connected only
3. **Today's Meetings** — Calendar or user input
4. **Pipeline Alerts** — CRM connected only
5. **Email Priorities** — Email connected only
6. **Suggested Actions** — Always include (top 3)

---

## Tips

1. **Connect calendar first** — Biggest time saver
2. **Add CRM second** — Unlocks pipeline alerts
3. **Even without connectors** — Tell me your meetings and I'll prioritize

## Related Skills

- **call-prep** — Deep prep for any specific meeting
- **call-follow-up** — Process notes after calls
- **account-research** — Research a company before first meeting
