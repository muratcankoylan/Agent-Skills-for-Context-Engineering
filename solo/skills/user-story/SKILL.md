---
name: user-story
description: >
  Breaks a build spec into a list of features with plain-English done criteria.
  Each feature becomes a card: what it does, when it's done, what's excluded from v1.
  Trigger with "list the features", "break down what to build", "what are the features for v1",
  "feature list", "acceptance criteria", or "break down my PRD".
version: 2.0.0
bundle: product-build
triggers:
  - "create user stories"
  - "break into user stories"
  - "user story for"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Feature Breakdown

Takes the scope section of your build spec (`PRD.md`) and turns each item into a feature card — a one-paragraph definition of what to build plus a checklist of plain-English done criteria.

Output: `data/1-Projets/[project]/features.md`

---

## Feature Card Format

Each feature in your v1 scope gets one card:

```markdown
## Feature: [Name]

**What it does:** [One sentence — what the user can do and what they get]

**As a** [user type], **I want to** [action] **so that** [outcome].

**Done when:**
- [ ] [Observable behavior — something you can actually check]
- [ ] [Edge case or error state handled]
- [ ] [Performance or constraint criterion if relevant]

**Not in this feature:**
- [Related thing that belongs in a different feature or v2]
```

---

## Example Feature Cards

### Example 1: Simple feature

```markdown
## Feature: Generate Invoice

**What it does:** User runs one command and gets a numbered invoice file in under 2 minutes.

**As a** freelancer, **I want to** create an invoice with a single command **so that** I can bill a client immediately after finishing a project.

**Done when:**
- [ ] Running `/solo:invoice create Client 2500` produces an invoice file
- [ ] Invoice is auto-numbered (INV-2026-001, INV-2026-002, etc.)
- [ ] Client name and address are read from the client file
- [ ] If the client file doesn't exist, a clear error message tells the user what to create

**Not in this feature:**
- PDF export (markdown works for now)
- Invoice editing after creation
- Tax calculation
```

### Example 2: Feature with a critical error state

```markdown
## Feature: Overdue Invoice Alert

**What it does:** User sees which invoices are overdue when they open the invoice dashboard.

**As a** solopreneur, **I want to** see overdue invoices flagged at a glance **so that** I don't miss chasing payments.

**Done when:**
- [ ] Invoices more than 30 days past due date appear at the top of the list
- [ ] Each overdue invoice shows how many days overdue it is
- [ ] An invoice with no due date is never marked overdue

**Not in this feature:**
- Automated payment reminder emails
- Customizable overdue threshold
- Payment integration
```

---

## Writing Good Done Criteria

**Good:** observable, specific, unambiguous
- "User sees an error message if the client file is missing"
- "Auto-incremented invoice number doesn't repeat across sessions"
- "The command completes in under 3 seconds"

**Bad:** vague, subjective, team-process language
- "Works correctly" ❌
- "Looks good" ❌
- "Unit tests pass" ❌ (internal, not user-facing)
- "Deployed to staging" ❌ (process step, not user behavior)

---

## Splitting Features That Are Too Large

If a feature takes more than 2–3 days to build, split it.

**By workflow step:**
- "User can manage invoices" → "User can create invoice" + "User can mark invoice paid" + "User can delete invoice"

**By happy path vs. error states:**
- "User can upload a file" → "User can upload a valid file" + "User sees error for wrong file type"

**By data state:**
- "User can view their pipeline" → "User can view pipeline with no deals" + "User can view pipeline with active deals"

**Rule:** Each card should be shippable on its own — removing it doesn't break the other features.

---

## How to Use

1. Open `data/1-Projets/[project]/PRD.md`
2. For each item in the "In v1" list, create one feature card
3. Each "Not in v1" item from the PRD becomes a "Not in this feature" line on the relevant card, or a note at the bottom of `features.md`
4. Save to `data/1-Projets/[project]/features.md`
5. Hand off cards to `design-brief-generator` to produce the visual spec

---

## Tips

**One feature = one user action.** If the card title contains "and", it's probably two features.

**Write done criteria before writing code.** If you can't write three clear criteria, the feature isn't defined yet.

**Exclusions are decisions, not failures.** Every "Not in this feature" line is scope protection. Write them explicitly.
