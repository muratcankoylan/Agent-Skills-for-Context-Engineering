---
name: discovery-call
description: >
  Helps prepare for sales discovery calls and process notes afterward. Generates structured
  call summaries for downstream skills. Triggers on "prep for call with", "prepare discovery call",
  "process call notes", or "summarize my call".
version: 1.0.0
bundle: client-work
triggers:
  - "prep discovery call"
  - "discovery call for"
  - "prepare for sales call"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Discovery Call Assistant

Handles the two most critical parts of a sales discovery call: **preparation before** and **processing after**. Ensures you go into every call prepared and that no insights are lost.

## Pre-Call Preparation

### Step 1: Gather Context
- Check `data/3-Ressources/` for existing company research
- If no research exists, suggest running `company-research` first
- Load `icp.json` for fit assessment context
- Check `data/1-Projets/clients/` for any prior relationship history

### Step 2: Generate Briefing
Use `references/prep-template.md` to create a briefing that includes:
- Company snapshot (from research findings)
- Discovery questions organized by category (see rubric below)
- Objection handling scripts
- Call goals and desired outcomes

### Discovery Questions Rubric

Ask questions in this order — move from safe/broad to specific/sensitive:

#### Phase 1: Situation (2-3 min)
Understand their current state. Low-threat, easy to answer.

| Question | Purpose |
|----------|---------|
| "Can you walk me through how you currently handle [problem area]?" | Map current process |
| "What tools or systems do you use for this today?" | Identify tech landscape |
| "How big is the team working on this?" | Scope the problem |
| "How long have you been doing it this way?" | Assess inertia |

#### Phase 2: Problem (5-7 min)
Dig into pain. This is where the value lives.

| Question | Purpose |
|----------|---------|
| "What are the biggest challenges with that process?" | Surface pain |
| "What happens when [specific failure scenario]?" | Quantify downside |
| "How much time/money does this cost you per month?" | Attach a number to the pain |
| "What have you tried before to solve this?" | Understand past attempts |
| "Why didn't that work?" | Learn from failures |

#### Phase 3: Impact (3-5 min)
Connect pain to business outcomes. This justifies the budget.

| Question | Purpose |
|----------|---------|
| "What's the business impact if this isn't solved this quarter?" | Create urgency |
| "How does this affect your team / customers / revenue?" | Broaden the pain |
| "If you could solve this perfectly, what would change?" | Paint the after state |

#### Phase 4: Decision Process (3-5 min)
Understand how they buy. Only ask once rapport is built.

| Question | Purpose |
|----------|---------|
| "Who else is involved in decisions like this?" | Map stakeholders |
| "What does your evaluation process typically look like?" | Understand buying journey |
| "Is there a budget allocated for this, or would we need to build a case?" | Qualify budget |
| "What's your ideal timeline for getting this solved?" | Qualify urgency |
| "What would make you say 'no' to working together?" | Surface hidden objections |

#### Phase 5: Close (2 min)
Always end with a clear next step.

| Question | Purpose |
|----------|---------|
| "Based on what we've discussed, I think I can help with [X]. Can I send you a proposal?" | Test interest |
| "What's the best next step from your side?" | Get commitment |
| "When should we reconnect to review the proposal?" | Lock in follow-up |

### Objection Handling Framework

| Objection | Strategy | Example Response |
|-----------|----------|-----------------|
| "Too expensive" | Reframe as ROI | "If this saves you [X hours/month], the investment pays for itself in [Y weeks]." |
| "Bad timing" | Quantify delay cost | "What's the cost of waiting another quarter? [reference their pain numbers]" |
| "Using competitor" | Find the gap | "Great — what's the one thing you wish [competitor] did better?" |
| "Need to think about it" | Define next step | "Totally fair. What specific questions would help you decide? Let's schedule a follow-up for [date]." |
| "Need to check with [person]" | Offer to help | "Would it help if I put together a one-page summary for them? What would they care about most?" |

## Post-Call Processing

### Step 1: Ingest Notes
Ask the user for raw notes, transcript, or key points from the call.

### Step 2: Extract Structured Information
Parse the input to identify:
- **Pain points** — what problems did they describe?
- **Key quotes** — verbatim language that reveals priority and emotion
- **Stakeholders** — who else was mentioned? What's their role in the decision?
- **BANT** — Budget, Authority, Need, Timeline signals
- **Buying signals** — positive indicators ("we need this by Q2", "can you send pricing?")
- **Red flags** — negative indicators ("we're just exploring", "no budget this year")
- **Action items** — what each side committed to doing

### Step 3: Generate Call Summary
Save to `data/1-Projets/[project]/call-summary.md` using `references/summary-template.md`.

### Step 4: Generate Follow-Up
Invoke the `draft-outreach` skill to create a follow-up email that:
- Thanks them for their time
- Recaps the key pain points discussed
- Restates the proposed next step
- Attaches any promised materials

### Step 5: Update Client Card
If a client card exists in `data/1-Projets/clients/`, update it with:
- Last contact date
- Notes from the call
- Updated deal stage (if appropriate)
- Next action with date

## Downstream Consumers

The call summary is consumed by:
- **`proposal-generator`**: Reads pain points and scope for tailored proposals
- **`client-management`**: Updates client card with call insights
- **`pipeline-orchestrator`**: May trigger a validation or discovery activity

## Key References

- **`references/prep-template.md`**: Pre-call briefing template
- **`references/summary-template.md`**: Post-call summary template
- **`references/discovery-questions-rubric.md`**: Full question bank organized by category
