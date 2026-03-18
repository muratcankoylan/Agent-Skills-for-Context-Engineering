Refactoring Complete — v2.2.0
What was fixed (P1)
Bug Fix
discovery-interview-prep entirely in French — invisible to English users Fully translated SKILL.md and full-guide.md to English
discovery-process referenced two deleted skills Replaced dead references with self-contained descriptions
README promised "idea to prototype" (prototype is in solo-studio) Build section now says discover → validate → design, with a callout to solo-studio
/solo:check-connections missing from command table Added
What was consolidated (P2)
discovery-interview-prep + discovery-process merged into user-discovery — one skill, one clear trigger, 5 reference files. discovery-call kept separate (it's distinctly sales-oriented).

What was removed (P3)
Skill Why
context-engineering-advisor Claude tutorial — not a business workflow
memory-management Internal architecture docs — user-facing noise
eol-message Product sunset messaging — too niche
What was rewritten (P4)
solo/README.md is now proper marketplace copy: 5 differentiators up front, agent table, full skill inventory, quick-start block.

Version bump (P5)
2.1.0 → 2.2.0 with a full CHANGELOG.md tracing back to the 2.1.0 refactoring.

Skill count: 43 → 40 (every remaining skill has a clear user-facing job).

7 changes, 37 final skills (down from 40):

Change What
Create idea-test — merges "should I build this?" + "cheapest test?" into one skill
Rewrite prd-development — 10-section PRD → 5-section solo build spec (30 min)
Rewrite user-story — INVEST/Gherkin/story points → plain-English feature cards
Edit triggers customer-journey-map, proto-persona — add builder-friendly phrases
Edit build.md — update Skills Used + Phase 2 to reference idea-test
Delete lean-ux-canvas, jobs-to-be-done — covered elsewhere
Delete validation-checkpoint, pol-probe-advisor — merged into idea-test
Every remaining PM skill answers one builder question — no frameworks for their own sake.

Claude’s Plan
Plan: Refactor Solo PM Skills → MVP Production Focus
Context
The remaining PM skills in Solo were designed for product managers on product teams. They use enterprise frameworks (INVEST, Gherkin, OKRs, guardrail metrics, story points) and assume team collaboration ("align stakeholders", "collaborate with design and engineering"). A solopreneur building an MVP doesn't need PM methodology — they need to make fast build/no-build decisions and produce a spec they can code or hand to a freelancer in 30 minutes.

Guiding principle: Every PM skill should answer a question a solo builder naturally asks, not implement a PM framework.

Diagnosis
prd-development — Enterprise PRD, not a solo build spec:

Description says "guides product managers" and "aligns stakeholders" (wrong audience)
10-section structure, 8-phase workflow (~8h total) — overkill
Includes OKRs, guardrail metrics, strategic context, open questions, dependencies
Common pitfalls: "collaborate with design and engineering" (assumes a team)
user-story — Scrum ticket format, not a feature checklist:

INVEST principles table (Agile team methodology)
Fibonacci story points (1, 2, 3, 5, 8, 13) — Scrum ceremony
"Deployed to staging" in Definition of Done (assumes QA/DevOps team)
References deleted roadmap-planning skill
pol-probe-advisor — Good logic, opaque name:

"pol-probe-advisor" means nothing to a solopreneur
Functionality (cheapest test selector) is valuable — just needs to be discoverable
validation-checkpoint — Works as a gate, redundant with pol-probe-advisor:

Decision gate: Go / No-Go / Pivot
Pol-probe-advisor then tells you how to test
These two are the same user intent: "Should I build this and if so how?"
lean-ux-canvas — Workshop artifact, not an action:

Full canvas exercise that duplicates what the pipeline already captures
No unique value when persona + problem statement + validation are separate skills
jobs-to-be-done — Covered by user-discovery:

After the previous refactoring, user-discovery already contains JTBD methodology
Standalone JTBD session adds overhead without unique output
Changes

1. Rewrite prd-development → solo build spec
   Keep the skill name (it's referenced in the build command), completely replace content.

New structure (5 sections, ~30 min):

What: One paragraph — what are we building, what it does
Who: Reference persona.md — the one person this is for
Why: Reference problem.md — the specific pain being solved
Scope (v1 only): Bulleted feature list, ruthlessly minimal
Done when: 3–5 plain-English criteria; no metric tables
Remove: OKRs, strategic context, stakeholder language, open questions section, dependencies section, guardrail metrics, "Epic hypothesis" references, 8-phase workflow, the "Common Pitfalls" about team collaboration.

New description: "Turns your problem statement and persona into a one-page build spec. Defines what to build, who it's for, and exactly when it's done."

New triggers: "write a build spec", "what should I build", "define the MVP", "write my spec", "scope the first version".

2. Rewrite user-story → feature checklist
   Keep the skill name (referenced in build command), completely replace content.

New format — a simple feature card:

## Feature: [Name]

**What it does:** [one sentence]

**Done when:**

- [ ] [plain English criterion]
- [ ] [plain English criterion]

**Not in v1:**

- [explicit exclusion]
  Remove: INVEST table, Fibonacci story points, Gherkin Given/When/Then, Definition of Done for teams, "Deployed to staging", "E2E test", references to roadmap-planning.

Keep: The user perspective format ("As a user, I want X so that Y"), the story splitting techniques (they're genuinely useful for solo builders keeping scope small), plain-English acceptance criteria examples.

New description: "Breaks a build spec into a list of features with plain-English done criteria. Keeps v1 scope tight by making exclusions explicit."

New triggers: "list the features", "break down what to build", "what are the features for v1", "feature list", "acceptance criteria".

3. Merge validation-checkpoint + pol-probe-advisor → idea-test
   Create new skill solo/skills/idea-test/SKILL.md that combines:

Part 1 (from validation-checkpoint): Go / No-Go / Pivot decision with evidence checklist
Part 2 (from pol-probe-advisor): Cheapest test selector (Proof of Life, Wizard of Oz, Concierge, Fake Door, Smoke Test)
Single user intent: "Is this worth building? And if yes, what's the cheapest way to confirm it?"

New triggers: "should I build this", "test my idea", "validate this idea", "is this worth building", "what's the cheapest test", "proof of concept", "run a quick test".

Delete both source skill directories after creating idea-test.

4. Remove lean-ux-canvas
   Delete solo/skills/lean-ux-canvas/ — the discovery → validate → design pipeline already captures its logic.

5. Remove jobs-to-be-done
   Delete solo/skills/jobs-to-be-done/ — the user-discovery skill already contains JTBD methodology.

6. Update customer-journey-map triggers
   Add builder-friendly trigger phrases to SKILL.md frontmatter description:

Add: "map the pain points", "what problems does my user face", "user problems in order", "where do users get stuck"
Keep existing UX triggers for discoverability 7. Update proto-persona triggers
Add natural-language trigger phrases:

Add: "who am I building for", "describe my customer", "my target user", "customer profile"
Keep existing triggers 8. Update solo/commands/build.md
Remove from "Skills Used" section: lean-ux-canvas, jobs-to-be-done.
Add idea-test in place of validation-checkpoint and pol-probe-advisor.
Phase 2 (VALIDATE) description: reference idea-test instead of two separate skills.

Files to Create
File Content
solo/skills/idea-test/SKILL.md Combined validation decision + test selector
solo/skills/idea-test/references/tests.md Test method catalog with time/cost/evidence ratings
Files to Rewrite (full content replacement)
File Change
solo/skills/prd-development/SKILL.md Replace with 5-section solo build spec
solo/skills/user-story/SKILL.md Replace with feature card format
Files to Edit (description/triggers only)
File Change
solo/skills/customer-journey-map/SKILL.md Add 4 builder-friendly trigger phrases to frontmatter
solo/skills/proto-persona/SKILL.md Add 4 natural-language trigger phrases to frontmatter
solo/commands/build.md Update Skills Used; update Phase 2 reference
Files to Delete (git rm + rm -rf)
Path Reason
solo/skills/lean-ux-canvas/ Covered by pipeline flow
solo/skills/jobs-to-be-done/ Covered by user-discovery
solo/skills/validation-checkpoint/ Merged into idea-test
solo/skills/pol-probe-advisor/ Merged into idea-test
Skill Count Impact
State Count
Before this refactoring 40 skills
After: +1 idea-test +1
After: −4 (lean-ux-canvas, jobs-to-be-done, validation-checkpoint, pol-probe-advisor) −4
After 37 skills
Every remaining PM skill answers one builder question:

"Who am I building for?" → proto-persona
"What do they struggle with?" → customer-journey-map, problem-statement
"How do I learn from them?" → user-discovery, discovery-call
"Should I build this?" → idea-test
"What exactly am I building?" → prd-development
"What are the features?" → user-story
"What should it look like?" → design-brief-generator
Verification
Run /solo:build discover → should invoke proto-persona, customer-journey-map, problem-statement (not jobs-to-be-done)
Run /solo:build validate → should invoke idea-test (not two separate skills)
Run /solo:build design → should invoke prd-development (new 5-section spec), user-story (new feature cards), design-brief-generator
Check no commands reference deleted skills: lean-ux-canvas, validation-checkpoint, pol-probe-advisor, jobs-to-be-done
Check idea-test triggers fire on "should I build this", "test my idea"
Check prd-development triggers fire on "write a build spec", "define the MVP"

Plan: Refactor Solo PM Skills → MVP Production Focus
Context
The remaining PM skills in Solo were designed for product managers on product teams. They use enterprise frameworks (INVEST, Gherkin, OKRs, guardrail metrics, story points) and assume team collaboration ("align stakeholders", "collaborate with design and engineering"). A solopreneur building an MVP doesn't need PM methodology — they need to make fast build/no-build decisions and produce a spec they can code or hand to a freelancer in 30 minutes.

Guiding principle: Every PM skill should answer a question a solo builder naturally asks, not implement a PM framework.

Diagnosis
prd-development — Enterprise PRD, not a solo build spec:

Description says "guides product managers" and "aligns stakeholders" (wrong audience)
10-section structure, 8-phase workflow (~8h total) — overkill
Includes OKRs, guardrail metrics, strategic context, open questions, dependencies
Common pitfalls: "collaborate with design and engineering" (assumes a team)
user-story — Scrum ticket format, not a feature checklist:

INVEST principles table (Agile team methodology)
Fibonacci story points (1, 2, 3, 5, 8, 13) — Scrum ceremony
"Deployed to staging" in Definition of Done (assumes QA/DevOps team)
References deleted roadmap-planning skill
pol-probe-advisor — Good logic, opaque name:

"pol-probe-advisor" means nothing to a solopreneur
Functionality (cheapest test selector) is valuable — just needs to be discoverable
validation-checkpoint — Works as a gate, redundant with pol-probe-advisor:

Decision gate: Go / No-Go / Pivot
Pol-probe-advisor then tells you how to test
These two are the same user intent: "Should I build this and if so how?"
lean-ux-canvas — Workshop artifact, not an action:

Full canvas exercise that duplicates what the pipeline already captures
No unique value when persona + problem statement + validation are separate skills
jobs-to-be-done — Covered by user-discovery:

After the previous refactoring, user-discovery already contains JTBD methodology
Standalone JTBD session adds overhead without unique output
Changes

1. Rewrite prd-development → solo build spec
   Keep the skill name (it's referenced in the build command), completely replace content.

New structure (5 sections, ~30 min):

What: One paragraph — what are we building, what it does
Who: Reference persona.md — the one person this is for
Why: Reference problem.md — the specific pain being solved
Scope (v1 only): Bulleted feature list, ruthlessly minimal
Done when: 3–5 plain-English criteria; no metric tables
Remove: OKRs, strategic context, stakeholder language, open questions section, dependencies section, guardrail metrics, "Epic hypothesis" references, 8-phase workflow, the "Common Pitfalls" about team collaboration.

New description: "Turns your problem statement and persona into a one-page build spec. Defines what to build, who it's for, and exactly when it's done."

New triggers: "write a build spec", "what should I build", "define the MVP", "write my spec", "scope the first version".

2. Rewrite user-story → feature checklist
   Keep the skill name (referenced in build command), completely replace content.

New format — a simple feature card:

## Feature: [Name]

**What it does:** [one sentence]

**Done when:**

- [ ] [plain English criterion]
- [ ] [plain English criterion]

**Not in v1:**

- [explicit exclusion]
  Remove: INVEST table, Fibonacci story points, Gherkin Given/When/Then, Definition of Done for teams, "Deployed to staging", "E2E test", references to roadmap-planning.

Keep: The user perspective format ("As a user, I want X so that Y"), the story splitting techniques (they're genuinely useful for solo builders keeping scope small), plain-English acceptance criteria examples.

New description: "Breaks a build spec into a list of features with plain-English done criteria. Keeps v1 scope tight by making exclusions explicit."

New triggers: "list the features", "break down what to build", "what are the features for v1", "feature list", "acceptance criteria".

3. Merge validation-checkpoint + pol-probe-advisor → idea-test
   Create new skill solo/skills/idea-test/SKILL.md that combines:

Part 1 (from validation-checkpoint): Go / No-Go / Pivot decision with evidence checklist
Part 2 (from pol-probe-advisor): Cheapest test selector (Proof of Life, Wizard of Oz, Concierge, Fake Door, Smoke Test)
Single user intent: "Is this worth building? And if yes, what's the cheapest way to confirm it?"

New triggers: "should I build this", "test my idea", "validate this idea", "is this worth building", "what's the cheapest test", "proof of concept", "run a quick test".

Delete both source skill directories after creating idea-test.

4. Remove lean-ux-canvas
   Delete solo/skills/lean-ux-canvas/ — the discovery → validate → design pipeline already captures its logic.

5. Remove jobs-to-be-done
   Delete solo/skills/jobs-to-be-done/ — the user-discovery skill already contains JTBD methodology.

6. Update customer-journey-map triggers
   Add builder-friendly trigger phrases to SKILL.md frontmatter description:

Add: "map the pain points", "what problems does my user face", "user problems in order", "where do users get stuck"
Keep existing UX triggers for discoverability 7. Update proto-persona triggers
Add natural-language trigger phrases:

Add: "who am I building for", "describe my customer", "my target user", "customer profile"
Keep existing triggers 8. Update solo/commands/build.md
Remove from "Skills Used" section: lean-ux-canvas, jobs-to-be-done.
Add idea-test in place of validation-checkpoint and pol-probe-advisor.
Phase 2 (VALIDATE) description: reference idea-test instead of two separate skills.

Files to Create
File Content
solo/skills/idea-test/SKILL.md Combined validation decision + test selector
solo/skills/idea-test/references/tests.md Test method catalog with time/cost/evidence ratings
Files to Rewrite (full content replacement)
File Change
solo/skills/prd-development/SKILL.md Replace with 5-section solo build spec
solo/skills/user-story/SKILL.md Replace with feature card format
Files to Edit (description/triggers only)
File Change
solo/skills/customer-journey-map/SKILL.md Add 4 builder-friendly trigger phrases to frontmatter
solo/skills/proto-persona/SKILL.md Add 4 natural-language trigger phrases to frontmatter
solo/commands/build.md Update Skills Used; update Phase 2 reference
Files to Delete (git rm + rm -rf)
Path Reason
solo/skills/lean-ux-canvas/ Covered by pipeline flow
solo/skills/jobs-to-be-done/ Covered by user-discovery
solo/skills/validation-checkpoint/ Merged into idea-test
solo/skills/pol-probe-advisor/ Merged into idea-test
Skill Count Impact
State Count
Before this refactoring 40 skills
After: +1 idea-test +1
After: −4 (lean-ux-canvas, jobs-to-be-done, validation-checkpoint, pol-probe-advisor) −4
After 37 skills
Every remaining PM skill answers one builder question:

"Who am I building for?" → proto-persona
"What do they struggle with?" → customer-journey-map, problem-statement
"How do I learn from them?" → user-discovery, discovery-call
"Should I build this?" → idea-test
"What exactly am I building?" → prd-development
"What are the features?" → user-story
"What should it look like?" → design-brief-generator
Verification
Run /solo:build discover → should invoke proto-persona, customer-journey-map, problem-statement (not jobs-to-be-done)
Run /solo:build validate → should invoke idea-test (not two separate skills)
Run /solo:build design → should invoke prd-development (new 5-section spec), user-story (new feature cards), design-brief-generator
Check no commands reference deleted skills: lean-ux-canvas, validation-checkpoint, pol-probe-advisor, jobs-to-be-done
Check idea-test triggers fire on "should I build this", "test my idea"
Check prd-development triggers fire on "write a build spec", "define the MVP"
