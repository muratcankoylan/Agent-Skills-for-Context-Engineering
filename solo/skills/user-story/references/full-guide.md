# The Master Guide to Solopreneur Agility: High-Impact User Stories

This guide defines the professional standard for documenting requirements in the Solo OS. We use a combination of Mike Cohn's User Story format and Dan North's BDD (Behavior Driven Development) Gherkin syntax.

---

## 1. The Anatomy of a High-Impact Story

A User Story is not a command; it is a **ticket for a conversation**. For a solopreneur, it is a way to "brain-dump" a feature into a format the AI agent can execute without ambiguity.

### The "Card" (Narrative)

> **As a** [Persona]  
> **I want to** [Action]  
> **So that** [Benefit]

- **The Persona**: Never use "the user." Use your `proto-personas` (e.g., "Freelancer Fiona," "Agency Alex").
- **The Action**: Use active verbs (e.g., "Schedule," "Calculate," "Validate").
- **The Benefit**: This is the most important part. If you can't find a benefit, the story is probably "Gold-plating" (useless work).

---

## 2. The INVEST Quality Protocol

Every story must pass the INVEST test before moving to the `backlog`.

| Principle       | Meaning                              | Solopreneur Strategy                                    |
| :-------------- | :----------------------------------- | :------------------------------------------------------ |
| **I**ndependent | No overlap with other stories.       | Reduces "Refactoring Hell" later.                       |
| **N**egotiable  | Discusses the "What," not the "How." | Leaves room for the AI to find the best technical path. |
| **V**aluable    | Delivers clear value to a persona.   | Prevents "Gold-plating" (building useless features).    |
| **E**stimable   | Possible to guess the effort.        | Essential for `roadmap-planning`.                       |
| **S**mall       | Can be built in 1-4 hours.           | Crucial for keeping momentum in a "Solo" environment.   |
| **T**estable    | Clear Pass/Fail criteria.            | Enables automated `verification-checkpoint` logic.      |

---

## 3. Gherkin Pattern Library (GPL)

We use the **Given / When / Then** syntax to eliminate ambiguity.

### Pattern: The Happy Path

- **Given**: The user is on the 'Home' screen and logged in.
- **When**: They click the "Quick Invoice" button.
- **Then**: A new invoice draft is created with the current date.

### Pattern: The Edge Case

- **Given**: The user has 0 clients in their database.
- **When**: They attempt to generate an invoice.
- **Then**: The system shows a "First, add a client" nudge instead of an error.

---

## 4. The SPIDR Splitting Tactics

If a story is too large (an "Epic"), use the SPIDR method to break it down:

1.  **S**pikes: Build a tiny technical proof-of-concept first (e.g., "Test Stripe API reachability").
2.  **P**aths: Split by user paths (e.g., "Login with Email" vs. "Login with Google").
3.  **I**nterface: Split by UI (e.g., "Desktop view" vs. "Mobile responsive view").
4.  **D**ata: Split by data types (e.g., "Support JPG uploads" vs. "Support PDF uploads").
5.  **R**ules: Split by business rules (e.g., "Free tier limits" vs. "Subscriber unlimited access").

---

## 5. From Story to Command

In the Solo OS, stories often map directly to AI commands.

- _Story_: As a user, I want to find high-ranking keywords for my niche.
- _Command_: `/solo:seo-research`

## 6. Common Anti-Patterns

- **The "Techno-Story"**: "As a dev, I want to update the Node version." (Use a Technical Debt task instead).
- **The "Monster Story"**: A story with 20 acceptance criteria. (Split it using SPIDR).
- **The "Vague Benefit"**: "...so that the app is better." (Be specific: "...so that I save 5 minutes on data entry per client").

---

## Next Steps

- Use the [User Story Template](./template.md) to draft your next feature.
- Cross-reference with your `opportunity-solution-tree` to ensure the story is valuable.
