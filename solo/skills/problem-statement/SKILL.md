---
name: problem-statement
description: >
  Formulate user-centric problem statements that frame pain points empathetically.
  Uses "I am... I'm trying to... but... because..." framework. Triggers on "problem
  statement", "define the problem", or "user pain point".
version: 1.0.0
bundle: product-build
triggers:
  - "write problem statement"
  - "formulate problem"
  - "define the problem"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Problem Statement

Creates clear, empathetic problem statements that frame user pain from their perspective. Transforms discovery insights into concise, actionable problem definitions that guide product decisions.

## When to Use

- After discovery interviews (synthesize learnings)
- Before ideation (frame the problem to solve)
- In PRDs (define what problem the feature solves)
- For stakeholder alignment (get everyone focused on the same problem)

## Problem Statement Framework

### The Narrative Format

```
I am [persona]
I'm trying to [goal/job to be done]
But [obstacle/frustration]
Because [root cause]
Which makes me feel [emotion]
```

**Example:**

```
I am a solopreneur designer
I'm trying to send professional invoices quickly
But I spend 30+ minutes per invoice formatting and calculating
Because my current tool (Excel) requires manual work
Which makes me feel frustrated and unprofessional
```

### The One-Sentence Format

```
[Persona] struggles with [problem] which causes [impact]
```

**Example:**

```
Solopreneur designers struggle with time-consuming invoice creation
which causes lost billable hours and delayed payments.
```

## Problem Statement Template

```markdown
# Problem Statement: [Short Title]

**Date:** [Date]  
**Based on:** [Source: interviews, surveys, analytics]  
**Confidence:** [Low/Medium/High]

---

## The Problem (Narrative)

I am **[persona]**  
I'm trying to **[goal/job to be done]**  
But **[obstacle/frustration]**  
Because **[root cause]**  
Which makes me feel **[emotion]**

---

## The Problem (One-Sentence)

[Persona] struggles with [problem] which causes [impact].

---

## Evidence

**From Discovery:**

- [Quote 1 from user interview]
- [Quote 2 from user interview]
- [Data point from analytics/survey]

**Frequency:**

- [How many users mentioned this?]
- [How often does this happen?]

**Impact:**

- [Time lost, money lost, frustration level]
- [Quantify if possible]

---

## Current Workarounds

Users currently solve this by:

1. [Workaround 1] — [Why it's not ideal]
2. [Workaround 2] — [Why it's not ideal]
3. [Workaround 3] — [Why it's not ideal]

---

## Success Criteria

We'll know we've solved this problem when:

- [Metric 1] reaches [target]
- [Metric 2] reaches [target]
- Users say [specific feedback]

**Example:**

- Invoice creation time drops from 30 minutes to 5 minutes
- 80% of users send invoices within 24 hours of completing work
- Users say "This saves me hours every week"

---

## Related Problems

- [Related problem 1]
- [Related problem 2]

---

## Next Steps

- [ ] Validate with 5+ more users
- [ ] Prioritize against other problems
- [ ] Ideate solutions (after validation)
```

## Example Problem Statements

### Example 1: Solopreneur Invoicing

```markdown
# Problem Statement: Time-Consuming Invoice Creation

**Date:** 2026-02-13  
**Based on:** 12 user interviews with solopreneur designers  
**Confidence:** High (validated with 12/12 users)

---

## The Problem (Narrative)

I am a **solopreneur designer**  
I'm trying to **send professional invoices quickly after completing client work**  
But **I spend 30-45 minutes per invoice formatting, calculating, and customizing**  
Because **my current tool (Excel or Google Sheets) requires manual work for every invoice**  
Which makes me feel **frustrated and unprofessional when invoices are delayed**

---

## The Problem (One-Sentence)

Solopreneur designers struggle with time-consuming invoice creation which causes lost billable hours and delayed payments.

---

## Evidence

**From Discovery:**

- "I spend more time creating invoices than I'd like to admit. It's embarrassing." — Sarah, Freelance Designer
- "I put off invoicing because it's such a pain. Then I forget and get paid late." — Mike, Design Consultant
- "I wish there was a button that just... made the invoice. I don't want to think about it." — Emma, UX Designer

**Frequency:**

- 12/12 users mentioned invoice creation as a pain point
- Average time per invoice: 35 minutes
- Frequency: 2-4 invoices per week = 2-3 hours/week lost

**Impact:**

- **Time:** 2-3 hours/week = 100-150 hours/year lost
- **Money:** At $100/hour, that's $10K-15K in lost billable time annually
- **Cash flow:** Delayed invoices = delayed payments (avg 7 days later)

---

## Current Workarounds

Users currently solve this by:

1. **Excel/Google Sheets templates** — Requires manual formatting, calculation, and customization every time
2. **Stripe Invoicing** — Better but limited customization, no client management
3. **Full accounting software (QuickBooks)** — Overkill for solopreneurs, expensive, complex

---

## Success Criteria

We'll know we've solved this problem when:

- Invoice creation time drops from 35 minutes to <5 minutes
- 90% of users send invoices within 24 hours of completing work
- Users say "This saves me hours every week" or "I don't dread invoicing anymore"

---

## Related Problems

- Cash flow unpredictability (late payments)
- Client management (tracking who owes what)
- Time tracking (knowing what to invoice for)

---

## Next Steps

- [x] Validated with 12 users
- [ ] Prioritize against other problems (use impact × frequency scoring)
- [ ] Ideate solutions (auto-numbering, templates, client data pre-fill)
```

### Example 2: Content Planning

```markdown
# Problem Statement: Inconsistent Content Publishing

**Date:** 2026-02-13  
**Based on:** 8 user interviews with solopreneur creators  
**Confidence:** Medium (need more validation)

---

## The Problem (Narrative)

I am a **solopreneur creator**  
I'm trying to **publish content consistently (3x/week)**  
But **I often miss deadlines or publish sporadically**  
Because **I don't have a system to plan, draft, and schedule content**  
Which makes me feel **guilty and like I'm failing at content marketing**

---

## The Problem (One-Sentence)

Solopreneur creators struggle with inconsistent content publishing which causes lost audience growth and engagement.

---

## Evidence

**From Discovery:**

- "I know I should post 3x/week, but I only manage 1-2x. I feel like I'm always behind." — Alex, Solopreneur Coach
- "I have ideas, but no system to turn them into published posts. So they just sit in my notes." — Jordan, Consultant

**Frequency:**

- 6/8 users mentioned inconsistent publishing
- Target: 3x/week, Actual: 1-2x/week
- Missed posts per month: 4-8

**Impact:**

- **Audience growth:** Slower than competitors who publish consistently
- **Engagement:** Lower reach when posting is sporadic
- **Guilt:** Constant feeling of "I should be posting more"

---

## Current Workarounds

Users currently solve this by:

1. **Notion content calendar** — Requires manual planning, no reminders
2. **Posting when inspired** — Inconsistent, reactive
3. **Batching content** — Works for 1-2 weeks, then falls apart

---

## Success Criteria

We'll know we've solved this problem when:

- Users publish 3x/week consistently (90%+ hit rate)
- Content is planned 2-4 weeks in advance
- Users say "I never miss a post anymore" or "Content feels effortless now"

---

## Related Problems

- Idea generation (running out of content ideas)
- Repurposing content (turning one piece into multiple formats)
- Measuring performance (knowing what content works)

---

## Next Steps

- [ ] Validate with 10+ more users
- [ ] Quantify impact (audience growth difference between consistent vs. inconsistent publishers)
- [ ] Ideate solutions (content calendar, reminders, batching workflow)
```

## Writing Good Problem Statements

### ✅ Good Examples

**User-centric:**

- "Solopreneurs struggle with time-consuming invoice creation which causes lost billable hours"
- "New users struggle with setup complexity which causes 40% drop-off in first session"

**Specific and measurable:**

- "Designers spend 35 minutes per invoice (2-3 hours/week) on manual formatting"
- "60% of users abandon onboarding at the payment step"

**Includes emotion:**

- "Which makes me feel frustrated and unprofessional"
- "Which makes me feel overwhelmed and likely to give up"

### ❌ Bad Examples

**Solution-focused (not problem-focused):**

- "We need an invoicing feature" ❌ (that's a solution, not a problem)
- "Users want dark mode" ❌ (what problem does dark mode solve?)

**Too vague:**

- "Users are frustrated" ❌ (frustrated with what?)
- "Onboarding is hard" ❌ (hard how? for whom?)

**Company-centric (not user-centric):**

- "We need to increase revenue" ❌ (that's your problem, not the user's)
- "Our competitor has this feature" ❌ (so what? does it solve a real user problem?)

## Problem Statement Checklist

Before finalizing a problem statement, verify:

- [ ] **User-centric** — Written from the user's perspective, not the company's
- [ ] **Specific** — Clear who, what, and why (not vague or generic)
- [ ] **Evidence-based** — Backed by discovery interviews, data, or research
- [ ] **Measurable** — Includes quantifiable impact (time, money, frequency)
- [ ] **Emotional** — Captures how the problem makes users feel
- [ ] **Actionable** — Clear enough to guide solution ideation
- [ ] **Validated** — Confirmed with 5+ users (not just one person's opinion)

## Integration Points

- **`discovery-call`**: Discovery interviews provide raw material for problem statements
- **`/solo:build discover`**: Problem statements are the output of the Discover phase
- **`prd-development`**: PRDs start with a problem statement
- **`validation-checkpoint`**: Validate problem statements before building solutions

## Key References

- **`references/template.md`**: Complete problem statement template
- **`references/examples.md`**: 10 example problem statements across different domains

## Tips

1. **Start with the narrative** — The "I am... I'm trying to... but..." format helps you think from the user's perspective
2. **Include quotes** — Real user quotes make the problem tangible
3. **Quantify impact** — Time lost, money lost, frequency — make it concrete
4. **Validate before building** — Talk to 5-10 users to confirm the problem is real
5. **One problem at a time** — Don't try to solve multiple problems in one statement
6. **Focus on the problem, not the solution** — Resist the urge to jump to "we need feature X"
