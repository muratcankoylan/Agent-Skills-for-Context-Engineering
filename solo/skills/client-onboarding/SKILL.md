---
name: client-onboarding
description: >
  Runs a complete client onboarding sequence from signed contract to kickoff-ready.
  Creates all materials, sends structured communications, and sets up the working
  relationship for long-term retention. Triggers on "onboard new client",
  "client signed", "kickoff prep", "new project setup", or "welcome [client]".
version: 1.0.0
bundle: client-work
triggers:
  - "onboard client"
  - "new client setup"
  - "start client onboarding"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Client Onboarding

The moment a client signs is not the end of sales — it's the beginning of the relationship that determines whether they become a repeat client, a referral source, or someone who leaves a lukewarm review. A structured 7-step onboarding sequence makes a profound first impression and prevents the most common early-project failures.

## The 7-Step Onboarding Sequence

### Step 1: The Welcome Package (Day 0 — send within 2 hours of signing)

Immediate touchpoint that signals professionalism and organization.

**What to create:**
- Welcome email (from `references/welcome-email-template.md`)
- Project brief one-pager (summary of what you're building together)
- "Working With Me" guide (from `references/working-with-me-guide.md`)

**Welcome email content:**
- Confirm what was agreed (project, timeline, investment)
- Name the specific first milestone and its date
- Explain how to reach you and expected response time
- Name the one thing you need from them to get started
- Express genuine enthusiasm (specific to them — reference something from discovery)

### Step 2: Access & Tools Setup (Day 0–1)

Prevent the most common early delay: waiting for logins.

**Create a shared access checklist:**

| Tool | Purpose | Access Level | Status |
|------|---------|-------------|--------|
| [Project management tool] | Milestone tracking | Client view | ⬜ Pending |
| [Shared folder] | File delivery | Full access | ⬜ Pending |
| [Communication channel] | Day-to-day messages | Full access | ⬜ Pending |
| [Feedback tool] | Review and annotations | Full access | ⬜ Pending |

Log the checklist in the client's card: `data/1-Projets/clients/[client].md`

**Send a "Please send me" message** — don't wait for them to guess:
> "To get started, I need from you: [1] [2] [3]. Could you send these by [date]? Once I have them, I'll immediately begin [first deliverable]."

### Step 3: Kickoff Call (Day 1–3)

30-45 minute structured call. Use the kickoff agenda from `references/kickoff-agenda-template.md`.

**Agenda structure:**
1. **Realign on the goal** (5 min) — Why are they doing this? What does success look like in 6 months?
2. **Review scope** (10 min) — Walk through the proposal together. Confirm what's in and explicitly name what's out.
3. **Define deliverables** (10 min) — Make each deliverable concrete and countable.
4. **Set communication norms** (5 min) — How, when, where. See Step 4.
5. **Identify risks** (5 min) — What could slow this down? What do you need from them and when?
6. **Confirm next milestone** (5 min) — First deliverable, date, format it will arrive in.

**Kickoff call output:**
- Save notes to `data/1-Projets/clients/[client].md` under Meeting Notes
- Update project milestones in `data/1-Projets/[project]/README.md`
- Send a kickoff summary within 24 hours (see Step 5)

### Step 4: Communication Norms (Document During Kickoff)

Prevents the "why didn't you reply instantly" problem and the "I sent feedback to the wrong place" problem.

**Norms to establish:**

| Topic | Your Standard | Document in |
|-------|--------------|-------------|
| Primary channel | [Slack / Email / WhatsApp] | Client card |
| Response time | Within [24h / same business day] | Client card |
| Meeting cadence | [Weekly / Bi-weekly / On demand] | Project file |
| Feedback process | [Via [tool] / track changes / annotated PDF] | Project file |
| Emergency contact | [Phone / Urgent Slack channel] | Client card |
| Scope changes | Always via formal change request | Contract |

### Step 5: Kickoff Summary (Day 2–4)

Send a written summary within 24 hours of the kickoff call. This is not a thank-you email — it's a binding reference document.

**Summary structure:**
```
Subject: [Project Name] Kickoff Summary

Hi [Name],

Great call! Here's a summary of what we agreed:

**Project Goal:**
[One sentence on the desired outcome]

**Scope (what we're building):**
- [Deliverable 1] by [date]
- [Deliverable 2] by [date]
- [Deliverable 3] by [date]

**Not in scope:**
- [Item 1]
- [Item 2]

**First deliverable:** [Description] — arriving [date]

**I need from you:** [List any outstanding inputs]

**How we communicate:**
- Day-to-day: [channel]
- Feedback: [method]
- Meetings: [cadence]

Excited to get started!
[Your name]
```

Save to `data/1-Projets/clients/[client]/kickoff-summary-[date].md`

### Step 6: Early Win Delivery (First Milestone)

The first deliverable is disproportionately important for trust. It sets the template for the entire relationship.

**Standards for first delivery:**
- Deliver 1–2 days before the agreed date (never late on the first milestone)
- Deliver more than expected: add a short note explaining your thinking, a bonus observation, or a small extra
- Make the handoff easy: clear format, named files, brief explanation of what you're delivering and what you need back

**First delivery email structure:**
```
Subject: [Project Name] — [Milestone Name] ✅

Hi [Name],

Here's [milestone description] — a couple of days early!

**What I'm sending:**
[Brief description of what's attached / linked]

**What I'd love feedback on:**
1. [Specific question 1]
2. [Specific question 2]

**What happens next:**
Once you've reviewed, I'll [next step].

**How to give feedback:**
[Via [tool] / reply with comments / use the annotation feature]

Please review by [date] so I can keep the project on schedule.

[Your name]
```

### Step 7: Week 2 Check-In (Day 10–14)

Most client relationships deteriorate in silence. A proactive check-in before problems surface is always better than reacting after.

**Check-in trigger:** 10–14 days after kickoff.

**Check-in message:**
```
Hi [Name],

Just checking in as we close out our first two weeks together.

How's the collaboration feeling so far? Anything about the process you'd like to adjust?

I'm particularly curious if:
- The communication channel and cadence is working for you
- The feedback process makes sense
- The pacing feels right

If anything needs tweaking, much easier to adjust now than later.

Looking forward to [next milestone] on [date]!

[Your name]
```

Log response in client card under Meeting Notes.

## Onboarding Checklist

Save to `data/1-Projets/[project]/onboarding-checklist.md`:

```markdown
# Onboarding Checklist — [Client Name]

## Day 0
- [ ] Welcome package sent
- [ ] Access checklist created
- [ ] "What I need from you" email sent

## Day 1–3
- [ ] Kickoff call scheduled
- [ ] Tool access confirmed (or chased)

## Day 2–4
- [ ] Kickoff call completed
- [ ] Kickoff summary sent
- [ ] Communication norms documented in client card

## Week 2
- [ ] First milestone delivered (target: [date])
- [ ] First delivery email sent with feedback request
- [ ] Week 2 check-in sent
- [ ] Check-in response logged
```

## Onboarding Health Score

During `client-lifecycle-agent` runs, assess onboarding completion:

| Step | Complete? | Risk if Missing |
|------|-----------|----------------|
| Welcome package sent same day | ✅/❌ | First impression miss |
| Tool access confirmed | ✅/❌ | Delays first milestone |
| Kickoff call completed | ✅/❌ | Scope misalignment risk |
| Kickoff summary sent | ✅/❌ | No written reference for disputes |
| Communication norms set | ✅/❌ | Boundary violations likely |
| First milestone on-time | ✅/❌ | Trust takes 3× longer to rebuild |
| Week 2 check-in done | ✅/❌ | Issues fester in silence |

If score < 5/7 for a current active client: flag to user with recommendation to address gaps.

## Integration Points

- **`client-management`**: Onboarding steps logged to client card
- **`project-management`**: Project milestones initialized from kickoff
- **`contract-templates`**: Scope references the signed agreement
- **`proposal-generator`**: Deliverables pulled from accepted proposal
- **`client-lifecycle-agent`**: Monitors onboarding completion and triggers check-ins

## Key References

- **`references/welcome-email-template.md`**: The welcome message for Day 0
- **`references/working-with-me-guide.md`**: How-I-work document for new clients
- **`references/kickoff-agenda-template.md`**: 45-minute kickoff call structure
