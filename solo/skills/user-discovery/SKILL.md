---
name: user-discovery
description: >
  End-to-end user research framework for solopreneurs: plan interviews, run sessions,
  extract insights, and map opportunities. Covers Mom Test, JTBD, Switch interviews,
  and Continuous Discovery habits.
  Trigger with "run a discovery session", "prepare an interview guide", "analyze my interview notes",
  "set up a discovery habit", "continuous discovery", "user research", or "interview script for [persona]".
version: 1.0.0
bundle: research-validate
triggers:
  - "user discovery"
  - "user research"
  - "interview framework"
tools:
  standalone: ["filesystem"]
  supercharged: ["tally"]
---

# Skill: User Discovery

Covers the full customer learning cycle — from designing the interview to extracting actionable opportunities. Use this before building anything new, validating a pivot, or investigating churn.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Custom interview script generator                            │
│  ✓ Insight extraction from raw notes                            │
│  ✓ Weekly discovery rhythm tracker                              │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~transcription / Fireflies)             │
│  + Auto-synthesis from call transcripts                         │
│  + Cross-session insight tracking and sentiment trends          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Preparation

### Define the Research Goal

Pick one goal per session — mixing goals produces muddled insights:

| Goal | When to use |
|------|-------------|
| **Problem validation** | Confirm the pain exists and how intense it is |
| **Jobs-to-be-Done** | Understand what the customer is trying to accomplish |
| **Churn investigation** | Learn why users left or switched competitors |
| **Prioritization** | Validate which problem to solve first |

### Select the Methodology

| Methodology | Best for | Core principle |
|---|---|---|
| **Mom Test** | Any validation interview | Ask about past behavior, never future intent |
| **JTBD (Switch)** | Understanding purchase decisions | Map the forces that caused them to switch |
| **Continuous Discovery** | Ongoing research habit | Weekly 30-min sessions with target users |

### Identify the Interviewee

Load `data/2-Domaines/icp.json` for fit criteria. Define:
- Role / job title, company size, or life situation
- Stage: early adopter vs. mainstream user
- Relationship: prospect, active user, or churned user

### Build the Interview Guide

**Warm-up (2 min)** — Low-threat, rapport-building
- "Can you tell me about your role and what your day looks like?"
- "How long have you been dealing with [problem area]?"

**Core Questions (15-20 min)** — Past behavior only
- ✅ "Tell me about the last time you faced this problem."
- ✅ "Walk me through what happened when that occurred."
- ✅ "What did you try before? Why didn't it work?"
- ❌ Never: "Would you use a feature that…?" (hypothetical)
- ❌ Never: "Don't you think it's frustrating when…?" (leading)

**Deep Dives (5-10 min)** — For each pain surfaced
- "How often does this happen?"
- "What's the business or personal impact?"
- "What workarounds do you use today?"

**Close (2 min)**
- "Is there anything important I didn't ask?"
- "Can you introduce me to someone else who has this problem?"

Save guide to: `data/1-Projets/[project]/discovery/interview-guide-[date].md`

---

## Phase 2: Execution

Guidelines for running the session:
- Talk less, listen more (aim for 80/20)
- Dig for specific stories, not general opinions
- Ask "Why?" up to 5 times to reach root cause
- Record (with consent) or take notes using the template in `references/scripts.md`

---

## Phase 3: Insight Extraction

After each session, parse notes to identify:

| Signal | Description |
|--------|-------------|
| **Pain points** | Specific obstacles the user described |
| **Workarounds** | Hacks or manual steps they use today |
| **Delighters** | Things that would genuinely make their day |
| **Quotable insights** | Verbatim language — use in problem statements and copy |
| **BANT signals** | Budget, Authority, Need, Timeline (for sales context) |

Output: save to `data/1-Projets/[project]/discovery/session-[date].md`

If the insight points to a sales opportunity, hand off to the `discovery-call` skill for follow-up processing.

---

## Phase 4: Opportunity Mapping

Group extracted insights into a ranked opportunity map:
- Cluster related pain points by theme
- Score each cluster by: frequency (how many users mentioned it) × intensity (how much they care)
- Top clusters = highest-priority opportunities to address

Save to: `data/1-Projets/[project]/discovery/opportunity-map.md`

Feed the top opportunities into the `problem-statement` skill to generate a crisp problem definition.

---

## Continuous Discovery Habit

To run discovery as an ongoing habit rather than a one-off project:

1. Define a standing research question for the current product cycle
2. Recruit 1-2 participants per week from your user base or target ICP
3. Run 30-minute sessions weekly using this skill
4. Extract 3-5 opportunities per session, update the opportunity map
5. Review the map every 4 weeks to reprioritize

---

## Success Criteria

A session is successful when it produces:
- At least 2 specific past stories with dates and context
- At least 1 genuine surprise (something you didn't expect)
- At least 3 verbatim quotes usable in a problem statement
- At least 1 revealed workaround or coping behavior

---

## References

- [Full Methodology Guide](./references/full-guide.md) — Mom Test, JTBD, Switch, bias list, success criteria
- [Interview Script Templates](./references/scripts.md) — Ready-made scripts by goal type
- [Mom Test Scoring Sheet](./references/mom-test.md) — Score sessions for signal quality
- [Continuous Discovery Habit Guide](./references/habit-guide.md) — Weekly cadence and tracking system
- [Discovery Worksheet](./references/worksheet.md) — Session note-taking template
