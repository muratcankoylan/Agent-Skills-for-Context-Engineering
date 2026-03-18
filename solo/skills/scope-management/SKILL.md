---
name: scope-management
description: >
  Helps detect scope creep, handle change requests, and set boundaries with clients.
  Triggers on "scope creep", "client wants more", "change request", "out of scope",
  or "the client is asking for extra work".
version: 1.0.0
bundle: client-work
triggers:
  - "scope creep"
  - "change request"
  - "out of scope"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Scope Management

Advisor for one of the most common solopreneur challenges: scope creep. Provides frameworks, templates, and scripts for identifying out-of-scope requests, quantifying their impact, and communicating professionally with clients.

## Scope Comparison Rubric

When a client makes a new request, run it through this decision tree:

### Step 1: Classify the Request

| Category | Definition | Example |
|----------|-----------|---------|
| **Clarification** | Refining something already in scope | "Can the logo be a slightly different shade of blue?" |
| **Enhancement** | Improving a scoped deliverable beyond spec | "Can we add animations to the homepage hero?" |
| **Addition** | Entirely new deliverable not in scope | "Can you also build us a mobile app?" |
| **Revision** | Re-doing completed work due to changed direction | "Actually, we want a completely different brand style" |

### Step 2: Check Against Original Scope

Pull the scope from one of these sources (in priority order):
1. Signed contract or SOW → `data/1-Projets/[project]/` or contract from `contract-templates`
2. Accepted proposal → from `proposal-generator` output
3. Email/message where scope was agreed

Compare by asking:
- Is this deliverable explicitly listed in the agreed scope? → **In scope**
- Is it a reasonable interpretation of a listed deliverable? → **Grey area** (clarify with client)
- Is it clearly not listed and not implied? → **Out of scope**

### Step 3: Assess Impact

For any out-of-scope or grey-area request, calculate impact using this template:

| Dimension | Current Plan | With Change | Delta |
|-----------|-------------|-------------|-------|
| **Timeline** | [End date] | [New end date] | +[X] days |
| **Budget** | [Total fee] | [New total] | +[X] EUR |
| **Resource hours** | [Hours remaining] | [New hours] | +[X] hours |
| **Risk** | [Current risk level] | [New risk level] | [Impact on quality/other deliverables] |

### Step 4: Decide and Communicate

| Impact Level | Action |
|-------------|--------|
| **Negligible** (<1 hour, no timeline impact) | Do it, note it informally |
| **Minor** (1-4 hours, no deadline risk) | Confirm with client in writing, adjust scope doc |
| **Moderate** (4-16 hours or deadline risk) | Formal change request required |
| **Major** (>16 hours or fundamental scope change) | Formal change request + contract amendment |

## Change Request Process

1. **Document** — Fill `references/change-request-template.md` with the request details, impact assessment, and cost
2. **Present** — Send to client with talking points from `references/talking-points.md`
3. **Await approval** — Do NOT start work until client signs or confirms in writing
4. **Update project** — Add the approved change to the project's `README.md` and update milestones
5. **Invoice** — Track the additional work separately for transparent invoicing

## Boundary-Setting Framework

Three methods for saying "no" professionally:

| Method | When to Use | Script Reference |
|--------|------------|-----------------|
| **Parking Lot** | Good idea, wrong time | "Great idea for Phase 2. Let's focus on delivering Phase 1 first." |
| **Resource Constraint** | Would compromise existing deliverables | "Adding this means we can't complete [X] on time. I recommend we stick to the current scope." |
| **Change Request Redirect** | Client insists, you're willing if compensated | "I'd love to do this. Let me put together a change request so you can see the impact and decide." |

## Prevention Tips

- Always reference the SOW/contract when discussing scope ("As outlined in Section 1 of our agreement...")
- Document every conversation where new requests come up
- Include an explicit "Out of Scope" section in every proposal (via `proposal-generator`)
- Include a change request clause in every contract (via `contract-templates`, Section 6)
- Bill change requests at a premium rate (1.2x–1.5x standard rate) to discourage casual additions

## Integration

- Reads scope from `proposal-generator` output or `contract-templates` SOW
- Updates `project-management` milestones when changes are approved
- Change request costs feed into `invoice-generator`
- Flags scope issues during `weekly-review`

## Key References

- **`references/change-request-template.md`**: Formal change request document
- **`references/talking-points.md`**: Scripts and phrases for scope conversations
