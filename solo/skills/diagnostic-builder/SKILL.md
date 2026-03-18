---
name: diagnostic-builder
description: >
  Creates scored diagnostic assessments from scratch. Guides the user through
  designing dimensions, questions, scoring logic, and band recommendations — then
  saves a reusable diagnostic definition. Triggered by "create a diagnostic",
  "build an assessment", "create a scorecard", "make a quiz for my prospects",
  "build a lead qualification tool", "create a client health check".
version: 1.0.0
bundle: diagnostics
triggers:
  - "create diagnostic"
  - "build assessment"
  - "scored diagnostic"
tools:
  standalone: ["filesystem"]
  supercharged: ["tally"]
---

# Skill: Diagnostic Builder

A diagnostic is a structured set of weighted questions that produces a personalized score and recommendation for the respondent. Unlike a discovery call (which extracts free-form information), a diagnostic produces a **comparable, repeatable signal** — the same framework applied to every lead, client, or product decision.

This skill creates the diagnostic definition. `diagnostic-runner` runs it.

---

## The 5 Diagnostic Types

Before building, identify the type. Each has different integration points in Solo.

| Type | Purpose | Respondent | Connects to |
|------|---------|-----------|-------------|
| **Lead** | Qualify prospects before the first call | Prospect | `sales-pipeline`, `draft-outreach` |
| **Client** | Monitor active client health and churn risk | Active client | `client-lifecycle-agent`, client card |
| **Onboarding** | Check readiness before project kickoff | New client | `client-onboarding`, `project-management` |
| **Product** | Validate product-market fit with market signal | Community member | `/solo:build validate`, `competitive-analyzer` |
| **Self** | Assess your own business health or clarity | Solo user | `business-health-advisor`, `weekly-review` |

---

## Build Flow (6 steps, ~15 minutes)

### Step 1: Define the Purpose

Ask one question: **"What decision should this diagnostic inform?"**

The purpose must be a concrete decision, not a vague goal.

❌ "Understand my prospects better"
✅ "Decide if this prospect should get a proposal or a nurture sequence"

❌ "Check on clients"
✅ "Identify which active clients are at risk of not renewing before they go quiet"

**Example purposes by type:**

```
Lead: "Is this prospect ready for a proposal, or do they need to be educated first?"
Client: "Is this client likely to renew, or do they need proactive attention?"
Onboarding: "Is this client ready to kick off, or are there blockers to clear first?"
Product: "Is the market pain real enough to justify building this?"
Self: "Am I pricing my services for where I am, or where I was 2 years ago?"
```

### Step 2: Design Dimensions (4–6 recommended)

Dimensions are the areas being assessed. Each dimension captures a distinct aspect of the respondent's situation.

**Rules:**
- 4 dimensions minimum, 6 maximum — more fragments the score
- Each dimension must be truly independent (no overlap)
- Weights must sum to 1.0 — weight by importance to the decision, not by interest

**Starting questions to derive dimensions:**
- "What are the 4–6 things that most predict a YES answer to your purpose question?"
- "If you could only know 5 things about this person, what would they be?"

**Propose dimensions, confirm with user, then set weights together.**

Format for output:

```markdown
## Proposed Dimensions

| # | Dimension | What it measures | Weight |
|---|-----------|-----------------|--------|
| 1 | [Name] | [1 sentence] | 25% |
| 2 | [Name] | [1 sentence] | 20% |
| 3 | [Name] | [1 sentence] | 20% |
| 4 | [Name] | [1 sentence] | 20% |
| 5 | [Name] | [1 sentence] | 15% |
| **Total** | | | **100%** |

Does this structure make sense? Any dimensions to rename, merge, or reweight?
```

### Step 3: Draft Questions (2–3 per dimension)

For each dimension, draft 2–3 multiple-choice questions. Each question has 4 options scored 0–4.

**Question writing rules:**
- Written in plain language the respondent actually uses
- Neutral framing — don't telegraph the "right" answer
- Options must be mutually exclusive (respondent can only pick one)
- Score 0 = clearest negative signal | Score 4 = clearest positive signal
- Middle options (1, 3) represent partial or ambiguous signals

**Example — Dimension: Revenue Stability, for a Lead diagnostic:**

```
Q: How predictable is your monthly revenue right now?
A) I genuinely don't know what next month looks like (0)
B) I have a rough sense but it swings a lot (1)
C) I can forecast within 20–30% most months (3)
D) I have recurring contracts or retainers covering my base (4)
```

**Load `references/question-bank.md` for tested question patterns by type.**

**After drafting all questions, calculate max_points per dimension:**
`max_points = number_of_questions × 4`

### Step 4: Write Score Bands

Three bands: Low (0–35), Medium (36–65), High (66–100).

**Each band needs:**
- A short label (2–4 words, the "diagnosis headline")
- An insight paragraph (2–3 sentences — what this score reveals, honest not alarming)
- One priority action (the most important thing to do right now)
- A CTA (what you want them to do next — book a call, download something, join a waitlist)

**Write all three bands before showing any of them.** The contrast between them validates each one.

**Voice:** Load `data/2-Domaines/voice-dna.json` and write recommendations in the user's voice. The diagnostic result is a communication, not a report.

**Example — Lead diagnostic, Revenue dimension context:**

```
Low band (0–35): "Still building the foundation"
Insight: Your business is in an early or transitional phase where stability isn't yet predictable.
That's not a blocker — it's context. The work we'd do together would look different than if
you had a stable base to build from.
Priority action: Before focusing on [your service area], get one recurring revenue stream in place.
CTA: "Let's talk about sequencing → [booking link]"

Medium band (36–65): "Solid ground, ready to grow"
Insight: You have real traction and a functioning business. The gaps you're experiencing
aren't about survival — they're about optimization and scale. This is the right moment to
address [your service area] before the problems compound.
Priority action: Audit which clients and services produce the most stable revenue, then
double down before adding complexity.
CTA: "See how I'd approach this for your specific situation → [booking link]"

High band (66–100): "Strong foundation, let's build on it"
Insight: You've already done the hard work of building a stable base. The question now is
what to build on top of it. You're in a strong position to [specific outcome you enable].
Priority action: Map out what the next 12 months looks like with [your service area]
solved — the ROI math gets very clear very fast.
CTA: "Ready to get specific? → [booking link]"
```

### Step 5: Configure Routing

How should completed responses flow into Solo?

```
Routing questions to ask the user:

1. What should happen when someone completes this?
   [ ] Create / update a lead card in sales-pipeline
   [ ] Update an active client card
   [ ] Log to a product project folder
   [ ] No routing — just save the response

2. Should the score trigger a pipeline stage change?
   High score → [stage]
   Medium score → [stage]
   Low score → [no change / different nurture]

3. Should monday-morning-agent see new completions?
   [ ] Yes — include in Monday briefing
   [ ] No

4. Should client-lifecycle-agent factor the score into health monitoring?
   [ ] Yes (for client diagnostics)
   [ ] No
```

### Step 6: Save the Definition

Save to `data/2-Domaines/diagnostics/[slug].json` using the schema from `_SCHEMA.json`.

**Also output a human-readable summary:**

```markdown
# Diagnostic: [Name]
**Type:** [type] | **Purpose:** [purpose]
**Dimensions:** [N] | **Questions:** [total] | **Est. time:** [X] min

## Dimensions & Weights
| Dimension | Weight | Questions |
|-----------|--------|-----------|
| [D1] | 25% | [N] |
| [D2] | 20% | [N] |

## Score Bands
| Band | Range | Label |
|------|-------|-------|
| 🔴 Low | 0–35 | [label] |
| 🟡 Medium | 36–65 | [label] |
| 🟢 High | 66–100 | [label] |

## Routing
- Completion → [action]
- High score → [pipeline stage / action]
- monday-morning-agent: [yes/no]

## How to run
`/solo:diagnose run [slug]` → conversational mode
Tally spec: `data/2-Domaines/diagnostics/[slug]-tally-spec.md`
```

---

## Tally Publish (Step 7 — Optional, requires Tally MCP)

After saving the definition, offer to publish it as a live Tally form immediately.

**Prompt to user:**
```
✓ Diagnostic saved: data/2-Domaines/diagnostics/[slug].json

Next steps:
  A) Run it now in this session → /solo:diagnose run [slug]
  B) Publish to Tally → creates a real, shareable form URL (requires Tally MCP)
  C) Generate a Claude self-service package → /solo:diagnose share [slug] --claude

Would you like to publish this to Tally now?
```

**If yes:** Invoke `tally-integration` skill → Operation 1 (Create Form).

The `tally-integration` skill handles all MCP calls. After form creation, it returns `form_id` and `form_url`, which are written back into the diagnostic definition's `tally_export` block:

```json
"tally_export": {
  "form_title": "[Public title]",
  "form_description": "[Subtitle / intro]",
  "collect_fields": ["name", "email", "company"],
  "form_id": "abc123",
  "form_url": "https://tally.so/r/abc123",
  "published_at": "YYYY-MM-DD",
  "last_synced_at": null,
  "submission_count": 0
}
```

**If Tally MCP is not connected:** Show the setup instructions from `tally-integration/SKILL.md` ("MCP Not Connected" section), then fall back to offering the Claude self-service package.

---

## Save

Definition: `data/2-Domaines/diagnostics/[slug].json`  
Tally form URL: stored in `definition.tally_export.form_url` after publishing  
Response folder: `data/1-Projets/diagnostics/[slug]/` (auto-created on first run)

## Integration Points

- **`diagnostic-runner`**: reads the definition to run conversational sessions
- **`tally-integration`**: creates and syncs Tally forms from diagnostic definitions
- **`diagnostic-analyzer`**: reads all response files to surface patterns
- **`sales-pipeline`**: receives routed lead data from completions
- **`client-lifecycle-agent`**: receives health scores from client diagnostics
- **`draft-outreach`**: diagnostic link can be embedded in outreach sequences
- **`/solo:build validate`**: product diagnostics published to community = smoke test

## References

- **`references/dimension-library.md`**: pre-built dimension sets for 5 diagnostic types
- **`references/question-bank.md`**: tested question patterns with scoring guidance
