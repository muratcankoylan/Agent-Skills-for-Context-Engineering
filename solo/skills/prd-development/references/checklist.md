# PRD Mastery Checklist: The Quality Guardrail

Before you move a PRD from "Draft" into "Development," it must pass this professional review audit. This ensures you aren't wasting your solo bandwidth on poorly defined features.

---

## 1. Strategic Alignment (The "Purpose" Test)

- [ ] **Value Link**: Does this feature directly solve a high-priority "Opportunity" from your `discovery-tree.md`?
- [ ] **Positioning**: Does this reinforce your `positioning-statement.md`? (Does it make you "Only"?)
- [ ] **Outcome Focus**: Is the success metric clearly defined and measurable?

---

## 2. Scope Hygiene (The "Brevity" Test)

- [ ] **Steel Thread**: Have we identified the thinnest possible path to value?
- [ ] **Out-of-Scope**: Is the "No" list clear enough to prevent scope creep during coding?
- [ ] **MVP vs. Gold-plating**: If this feature took 3x longer than expected, would it still be worth it?

---

## 3. Technical Feasibility (The "Risks" Test)

- [ ] **External API Check**: Are all 3rd party integrations (e.g., Stripe, Exa) verified?
- [ ] **Technical Debt**: Are the trade-offs explicitly mentioned in the PRD?
- [ ] **Spike Requirement**: Do we need a `technical-spike` story before we build?

---

## 4. Clarity & Executability (The "AI" Test)

- [ ] **Gherkin Scenarios**: Are the Acceptance Criteria specific enough that an AI agent could write tests from them?
- [ ] **User Flow**: Is there a clear start and end point for the user?
- [ ] **Edge Cases**: Have we defined what happens when things go wrong (e.g., no internet, empty data)?

---

## 5. Design & Polish (The "Wow" Test)

- [ ] **UI Logic**: Are the visual states (Empty, Loading, Success, Error) defined?
- [ ] **Voice DNA**: Does the copy in the feature match your `voice-dna.json`?

---

## Final Decision

- **PASS**: Proceed to `user-story-splitting`.
- **HOLD**: Redraft section [X] to fix [Y].
