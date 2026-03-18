---
name: project-management
description: >
  Provides lightweight project tracking for client work, including milestones,
  deliverables, and status reporting. Triggers on "track project", "project status",
  "update milestone", "project overview", or "what's overdue".
version: 1.0.0
bundle: operations
triggers:
  - "project tracking"
  - "manage project"
  - "project status"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Project Management

Lightweight, file-based project tracking for solopreneurs. Each project lives in `data/1-Projets/[project-name]/README.md` using a standardized template. Primary skill for the `/solo:plan project` command.

## Core Operations

### 1. Initialize Project

Create a new project from `references/project-template.md`:

1. Ask for: project name, client name, start date, target end date, main objective
2. Pull deliverables from the accepted proposal (via `proposal-generator`) or ask user to list them
3. Create directory: `data/1-Projets/[project-name]/`
4. Copy and fill `references/project-template.md` → `data/1-Projets/[project-name]/README.md`
5. Link the client card in `data/1-Projets/clients/[client].md` to this project

### 2. Track Milestones

Each project has 3-5 milestones with target dates and status:

| Status | Meaning | Visual |
|--------|---------|--------|
| **Not Started** | Work hasn't begun | ⬜ |
| **In Progress** | Actively working on it | 🟡 |
| **Completed** | Delivered and accepted | ✅ |
| **Overdue** | Past target date, not complete | 🔴 |
| **Blocked** | Can't proceed (reason in notes) | ⛔ |

### 3. Manage Deliverables

Deliverables use a checkbox format with assignee and due date:
```
- [ ] Deliverable description — Due: [date]
- [x] Completed deliverable — Done: [date]
```

### 4. Status Report

Generate a status summary on demand:
```
## [Project Name] — Status: [On Track / At Risk / Overdue]
- **Progress:** [X/Y] milestones complete, [A/B] deliverables done
- **Next milestone:** [Name] — due [date] ([X] days away)
- **Blockers:** [None / list]
- **Hours logged:** [X] / [Y] estimated
```

## Overdue Detection

When checking project status, flag items as overdue:

| Check | Condition | Action |
|-------|----------|--------|
| **Milestone overdue** | Target date < today AND status ≠ Completed | Mark 🔴, add to weekly review |
| **Deliverable overdue** | Due date < today AND not checked | Highlight in status report |
| **Project overdue** | End date < today AND status ≠ Terminé | Escalate: suggest client communication |
| **Stale project** | No updates in 14+ days | Flag during weekly review |

### Escalation Script

When a milestone is overdue, provide this communication template:

> Hi [Client Name],
>
> Quick update on [Project Name]. The [Milestone] milestone was originally targeted for [date]. We're currently [X days] past that due to [reason — e.g., "waiting on content from your team" / "the scope addition we discussed last week"].
>
> **Updated timeline:** I expect to complete this by [new date].
> **Impact on final delivery:** [None / Pushes final delivery to [date]].
>
> Let me know if you'd like to discuss any adjustments.

## Client Approval Workflow

For deliverables that require client sign-off:

### Step 1: Submit for Review
Mark deliverable as "Submitted" in project file. Send to client with:
> "Please review [deliverable] and let me know if it meets your expectations. I'll consider it approved if I don't hear back within [3 business days]."

### Step 2: Track Review Status

| Status | Meaning |
|--------|---------|
| **Submitted** | Sent to client, awaiting review |
| **Approved** | Client confirmed acceptance |
| **Revision Requested** | Client wants changes (track as revision round) |
| **Auto-Approved** | No response within review window |

### Step 3: Handle Revisions
- Round 1-2: Included in original scope
- Round 3+: Flag as potential scope creep → hand off to `scope-management`

### Step 4: Record Approval
Update the deliverable with approval date. This triggers:
- Milestone progress update
- Invoice eligibility (if payment is milestone-based) → feeds `invoice-generator`

## Multi-Project Dashboard

When running multiple projects, generate an overview:

```
## Active Projects — [Date]

| Project | Client | Status | Next Milestone | Due | Health |
|---------|--------|--------|---------------|-----|--------|
| [Name] | [Client] | On Track | [Milestone] | [Date] | 🟢 |
| [Name] | [Client] | At Risk | [Milestone] | [Date] | 🟡 |
| [Name] | [Client] | Overdue | [Milestone] | [Date] | 🔴 |

**Overdue items:** [count]
**Pending approvals:** [count]
**This week's deadlines:** [list]
```

## Integration

- Initialized from `proposal-generator` deliverables
- Links to `client-management` cards
- Feeds milestone data to `weekly-review`
- Overdue milestones trigger `scope-management` scripts
- Completed milestones trigger `invoice-generator` (milestone billing)
- **Supercharged:** If `~~project tracker` is connected, sync milestones and deliverables with the external tool

## Key Reference

- **`references/project-template.md`**: Standard markdown structure for new projects
