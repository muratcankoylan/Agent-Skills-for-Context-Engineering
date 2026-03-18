---
name: design-brief-generator
description: >
  Convert PRDs and user stories into structured design briefs for prototyping. Bridges
  the gap between requirements and design. Triggers on "create design brief", "brief
  for design", or "design specifications".
version: 1.0.0
bundle: product-build
triggers:
  - "design brief"
  - "create design brief"
  - "brief for designer"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Design Brief Generator

Translates product requirements and user stories into actionable design briefs. Creates structured specifications that designers and prototyping tools can use to build interfaces.

## When to Use

- After PRD and user stories are complete
- Before starting design or prototyping
- To align designers and developers on requirements
- As input for prototyping tools (Figma, Stitch)

## Design Brief Structure

```markdown
# Design Brief: [Project Name]

**Created:** [Date]  
**Based on:** [PRD link, User stories link]  
**Designer:** [Name or "TBD"]  
**Target Completion:** [Date]

---

## Project Overview

**Problem:** [One-sentence problem statement]  
**Solution:** [One-sentence solution description]  
**Target User:** [Persona name and key characteristics]

---

## User Flows

### Primary Flow: [Flow Name]

1. [Step 1] → [Screen/State]
2. [Step 2] → [Screen/State]
3. [Step 3] → [Screen/State]

**Success Criteria:** [What defines a successful flow completion]

### Secondary Flow: [Flow Name]

[Repeat for each major user flow]

---

## Screen Inventory

| Screen     | Purpose        | Key Elements        | Priority |
| ---------- | -------------- | ------------------- | -------- |
| [Screen 1] | [What it does] | [Components needed] | P0       |
| [Screen 2] | [What it does] | [Components needed] | P1       |

---

## Interaction Patterns

### [Pattern Name]

**When:** [Trigger]  
**What:** [Interaction description]  
**Example:** [Reference or mockup]

---

## Visual Requirements

**Brand Guidelines:**

- Colors: [Primary, secondary, accent]
- Typography: [Fonts and sizes]
- Spacing: [Grid system]

**Accessibility:**

- WCAG Level: [A, AA, AAA]
- Color contrast: [Minimum ratio]
- Keyboard navigation: [Required/Not required]

**Responsive:**

- Breakpoints: [Mobile, tablet, desktop sizes]
- Priority: [Mobile-first / Desktop-first]

---

## Content Requirements

**Copy Tone:** [Professional, casual, friendly, etc.]  
**Microcopy:** [Button labels, error messages, success states]  
**Placeholder Content:** [What to use for demos]

---

## Technical Constraints

**Platform:** [Web, iOS, Android, etc.]  
**Framework:** [React, Vue, native, etc.]  
**Component Library:** [Material UI, Chakra, custom, etc.]  
**Performance:** [Load time, animation frame rate]

---

## Success Metrics

**Usability:**

- [Metric 1]: [Target]
- [Metric 2]: [Target]

**Business:**

- [Metric 1]: [Target]
- [Metric 2]: [Target]

---

## Deliverables

- [ ] User flow diagrams
- [ ] Wireframes (low-fidelity)
- [ ] Mockups (high-fidelity)
- [ ] Prototype (interactive)
- [ ] Design system documentation
- [ ] Handoff specs for developers

---

## Timeline

| Phase      | Deliverable           | Due Date |
| ---------- | --------------------- | -------- |
| Discovery  | User flows            | [Date]   |
| Wireframes | Lo-fi screens         | [Date]   |
| Design     | Hi-fi mockups         | [Date]   |
| Prototype  | Interactive prototype | [Date]   |
| Handoff    | Dev specs             | [Date]   |

---

## References

**PRD:** [Link to PRD]  
**User Stories:** [Link to user stories]  
**Research:** [Link to discovery insights, journey maps]  
**Inspiration:** [Link to competitor analysis, design references]
```

## Example Design Brief

```markdown
# Design Brief: Invoice Creation Flow

**Created:** 2026-02-13  
**Based on:** PRD: Invoice Management System, User Stories: INV-001 to INV-008  
**Designer:** TBD (will use Stitch for prototyping)  
**Target Completion:** 2026-02-20

---

## Project Overview

**Problem:** Solopreneurs spend 30-45 minutes creating invoices manually in Excel.

**Solution:** One-click invoice creation with client data pre-filled and auto-numbering.

**Target User:** Solopreneur Sarah (Freelance Designer, 32-38, manages 5-7 clients)

---

## User Flows

### Primary Flow: Create and Send Invoice

1. User clicks "New Invoice" from dashboard → Invoice creation screen
2. User selects client from dropdown (pre-fills contact info) → Invoice form
3. User adds line items (service description, hours, rate) → Line items populate
4. User reviews invoice preview → Preview modal
5. User clicks "Send Invoice" → Confirmation + email sent

**Success Criteria:** User can create and send invoice in <5 minutes (currently 30-45 minutes)

### Secondary Flow: Save Draft

1. User starts creating invoice → Invoice form
2. User clicks "Save Draft" → Draft saved
3. User returns later, clicks "Drafts" → Draft list
4. User selects draft → Resume editing

**Success Criteria:** No data loss if user navigates away

---

## Screen Inventory

| Screen          | Purpose               | Key Elements                                                 | Priority |
| --------------- | --------------------- | ------------------------------------------------------------ | -------- |
| Dashboard       | Entry point, overview | "New Invoice" button, recent invoices list, revenue summary  | P0       |
| Invoice Form    | Create/edit invoice   | Client dropdown, line items table, totals, payment terms     | P0       |
| Invoice Preview | Review before sending | Read-only invoice view, "Edit" and "Send" buttons            | P0       |
| Confirmation    | Success feedback      | "Invoice sent!" message, next actions (view, create another) | P0       |
| Draft List      | Manage drafts         | List of draft invoices, "Resume" and "Delete" actions        | P1       |

---

## Interaction Patterns

### Client Dropdown with Search

**When:** User clicks "Client" field  
**What:** Dropdown opens with search, shows recent clients first, allows adding new client inline  
**Example:** Similar to Stripe's customer selector

### Line Item Table

**When:** User adds services to invoice  
**What:** Editable table with add/remove rows, auto-calculates subtotal  
**Example:** Google Sheets-style inline editing

### Auto-Save

**When:** User pauses typing for 2 seconds  
**What:** Draft auto-saves, shows "Saved" indicator  
**Example:** Notion-style auto-save with timestamp

---

## Visual Requirements

**Brand Guidelines:**

- Colors: Primary (#2563EB blue), Secondary (#64748B gray), Success (#10B981 green)
- Typography: Inter (headings), System UI (body)
- Spacing: 8px grid system

**Accessibility:**

- WCAG Level: AA
- Color contrast: 4.5:1 minimum
- Keyboard navigation: Full support (tab through form fields)

**Responsive:**

- Breakpoints: Mobile (320px), Tablet (768px), Desktop (1024px+)
- Priority: Desktop-first (solopreneurs work on laptops)

---

## Content Requirements

**Copy Tone:** Professional but friendly (not corporate)

**Microcopy:**

- Button labels: "Send Invoice" (not "Submit"), "Save Draft" (not "Save")
- Error messages: "Oops! Client name is required." (friendly, specific)
- Success states: "Invoice sent! Sarah will receive it in 2 minutes." (reassuring)

**Placeholder Content:**

- Client: "Acme Corp"
- Line item: "Website Redesign — 40 hours × $100/hr"
- Invoice number: "INV-2026-001"

---

## Technical Constraints

**Platform:** Web (responsive)  
**Framework:** React + Tailwind CSS  
**Component Library:** Headless UI (for dropdowns, modals)  
**Performance:** Page load <1s, form interactions <100ms

---

## Success Metrics

**Usability:**

- Invoice creation time: <5 minutes (currently 30-45 minutes)
- Error rate: <5% (users complete without errors)
- Draft save rate: >80% (users save drafts before sending)

**Business:**

- Invoices sent within 24 hours of work completion: 90% (currently 60%)
- User satisfaction (NPS): 50+ (currently no baseline)

---

## Deliverables

- [x] User flow diagrams (completed)
- [ ] Wireframes (low-fidelity) — Due Feb 15
- [ ] Mockups (high-fidelity) — Due Feb 17
- [ ] Prototype (interactive via Stitch) — Due Feb 19
- [ ] Design system documentation — Due Feb 20
- [ ] Handoff specs for developers — Due Feb 20

---

## Timeline

| Phase      | Deliverable           | Due Date  |
| ---------- | --------------------- | --------- |
| Discovery  | User flows            | Feb 14 ✅ |
| Wireframes | Lo-fi screens         | Feb 15    |
| Design     | Hi-fi mockups         | Feb 17    |
| Prototype  | Interactive prototype | Feb 19    |
| Handoff    | Dev specs             | Feb 20    |

---

## References

**PRD:** `data/1-Projets/invoice-system/PRD.md`  
**User Stories:** `data/1-Projets/invoice-system/user-stories.md`  
**Research:** `data/1-Projets/invoice-system/discovery-insights.md`  
**Inspiration:** Stripe Invoicing, FreshBooks, Wave
```

## How to Generate a Design Brief

### Step 1: Ingest Requirements

- Read the PRD
- Review user stories
- Understand the problem and solution

### Step 2: Map User Flows

- Identify primary and secondary flows
- Document each step and screen transition
- Define success criteria for each flow

### Step 3: Create Screen Inventory

- List all required screens
- Define purpose and key elements for each
- Prioritize (P0 = must-have, P1 = nice-to-have)

### Step 4: Define Interaction Patterns

- Identify common interactions (dropdowns, modals, tables)
- Specify behavior and examples
- Reference similar patterns from other products

### Step 5: Specify Visual Requirements

- Brand guidelines (colors, typography, spacing)
- Accessibility requirements (WCAG level, contrast)
- Responsive design (breakpoints, priority)

### Step 6: Set Success Metrics

- Usability metrics (time, error rate, completion rate)
- Business metrics (conversion, retention, satisfaction)

### Step 7: Define Deliverables and Timeline

- List all deliverables (flows, wireframes, mockups, prototype)
- Set deadlines for each phase
- Assign owners

## Integration Points

- **`prd-development`**: PRD is the input for the design brief
- **`user-story`**: User stories inform screen inventory and flows
- **`pipeline-orchestrator`**: Triggers design brief generation after Design phase
- **`figma-prototype`**: Uses design brief as input for prototyping
- **`stitch-loop`**: Uses design brief for AI-powered prototyping

## Key References

- **`references/design-brief-template.md`**: Complete template (copy-paste ready)
- **`references/examples.md`**: 3 example design briefs (web app, mobile app, landing page)

## Tips

1. **Be specific** — "Client dropdown with search" not "select client"
2. **Include examples** — Reference similar patterns from other products
3. **Define success** — Clear metrics for usability and business goals
4. **Keep it actionable** — Designers should be able to start work immediately
5. **Link to sources** — PRD, user stories, research (for context)
6. **Update as you learn** — Design briefs evolve during the design process
