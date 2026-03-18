# Professional User Story Template

Use this template to define high-quality development tickets. Copy and paste this into your project folder.

---

## [ID-00X] Story: [Memorable Title]

**Narrative:**

- **As a** [Persona Name]
- **I want to** [Action/Goal]
- **So that** [Primary Business/User Benefit]

---

## 1. Acceptance Criteria (Gherkin Syntax)

### Scenario 1: The Happy Path (Core Success)

- **Given** [Initial context or pre-condition]
- **And** [Additional context]
- **When** [The trigger or action]
- **Then** [Success result]
- **And** [Secondary outcome]

### Scenario 2: Error Handling / Boundary Case

- **Given** [A risky state or missing data]
- **When** [The trigger or action]
- **Then** [Graceful failure or instructive nudge]

### Scenario 3: Secondary Path (Optional)

- **Given** [Alternative context]
- **When** [The trigger or action]
- **Then** [Alternative success result]

---

## 2. Technical & Design Guardrails

- **Design/UX**: [UI link or description of the 'Vibe']
- **Security**: [Data permissions or authentication requirements]
- **Performance**: [Maximum response time or payload size]
- **Out of Scope**: [What we are NOT building to avoid scope creep]

---

## 3. Solo Strategy Check

- [ ] **INVEST Check**: Is this story Small enough to finish today?
- [ ] **Value Check**: Does this solve an Opportunity on the `discovery-tree.md`?
- [ ] **Architecture Check**: Does this impact `business-profile.json`?

---

## 4. Definition of Done (DoD)

- [ ] Code is formatted and linted.
- [ ] Gherkin scenarios verified through `verification-checkpoint`.
- [ ] UI is mobile-responsive (if applicable).
- [ ] No regression on existing commands.
