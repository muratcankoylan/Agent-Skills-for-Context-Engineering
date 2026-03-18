# The Master PRD Template: Professional Product Requirements

This document is the "Golden Thread" of your feature development. It bridges the gap between high-level `product-strategy-session` outcomes and the tactical `user-story` tickets.

---

## 1. Executive Summary: The "Why"

- **Title**: [Feature Name] - V1.0
- **Objective**: What is the single most important goal of this feature?
- **Relationship to OST**: Which `Opportunity` node is this solving?
- **North Star Metric**: (e.g., "15% increase in weekly active users").

---

## 2. Target Audience & Persona context

- **Primary Persona**: (e.g., "Freelancer Fiona")
- **Pain Point Addressed**: (Ref: `discovery-interview-prep` findings)
- **User Journey Context**: Where does this feature sit in the `customer-journey-map.md`?

---

## 3. High-Level Requirements (The "What")

- **Functional Requirements**:
  1. [Requirement 1] -> [Priority: P0]
  2. [Requirement 2] -> [Priority: P1]
- **Non-Functional Requirements**:
  - **Performance**: Should load in <200ms.
  - **Security**: Data must be encrypted at rest in the `PARA` store.
  - **UI/UX**: Must follow the `stitch-design-md` design system.

---

## 4. Acceptance Criteria (Gherkin Scenarios)

_These will be directly translated into `user-story` tickets._

- **Scenario 1**: [Happy Path]
- **Scenario 2**: [Edge Case]
- **Scenario 3**: [Error State]

---

## 5. Technical Context & Constraints

- **Key Dependencies**: (e.g., "Requires exa-search-expert integration").
- **Technical Debt Trade-offs**: "We are using a manual CSV export for V1 to avoid building a full API."
- **Data Schema Changes**: Describe any new fields needed in `business-profile.json` or local storage.

---

## 6. Design & User Experience

- **Core User Flow**: A -> B -> C -> Done.
- **Figma/Mockup Link**: (Ref: `figma-prototype`)
- **Key Visual Principles**: (e.g., "Minimalist, zero-distraction").

---

## 7. Success Measurement & Analytics

- **Primary Success Signal**: [Specific Event, e.g., 'invoice_sent_successfully']
- **Secondary Signals**: [e.g., 'template_customized']
- **Analytics Tooling**: (Ref: `metrics.md` setup)

---

## 8. Out of Scope (The Guardrails)

- To maintain the **Steel Thread**, we are NOT building:
  - [Excluded Feature 1]
  - [Excluded Feature 2]

---

## 9. Next Steps

- [ ] Trigger `user-story-splitting` for all P0 requirements.
- [ ] update `roadmap-planning.md` to reflect 'Building' status.
- [ ] Run a `validation-checkpoint` with the prototype.
