---
name: proposal-generator
description: >
  Generates professional proposals, SOWs, and sales proposals with pricing from your
  rate card. Supports 3 variants. Triggers on "write a proposal", "create SOW",
  "quote for", or "send a proposal to".
version: 1.0.0
bundle: client-work
triggers:
  - "create proposal"
  - "write proposal for"
  - "generate SOW"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Proposal Generator

Creates professional proposals by pulling discovery notes, client context, and pricing into a structured, persuasive document. Supports three proposal variants.

## Proposal Variants

| Variant | When to Use | Key Sections |
|---------|------------|--------------|
| **SOW (Scope of Work)** | Project-based engagements with defined deliverables | Problem, Solution, Scope, Timeline, Investment |
| **Sales Proposal** | Pitching new business to a prospect | Their Challenge, Your Approach, Why You, Options, Next Steps |
| **Rate Card Proposal** | Retainer or hourly arrangements | Services, Rates, Engagement Models, Terms |

## Creation Process

### Step 1: Gather Context

Check these sources (in order):
1. `data/1-Projets/[project]/call-summary.md` — discovery call notes
2. `data/3-Ressources/[company].md` — company research findings
3. `data/1-Projets/clients/[client].md` — existing client card
4. `data/2-Domaines/business-profile.json` — your positioning and services

If key context is missing, ask the user directly.

### Step 2: Select Variant

Based on context:
- If user says "proposal" or "SOW" → SOW variant
- If user says "pitch" or "sales proposal" → Sales Proposal variant
- If user says "rate card" or "retainer proposal" → Rate Card variant
- If unclear, ask: "Is this a project proposal (SOW), a sales pitch, or a retainer arrangement?"

### Step 3: Build the Proposal

**SOW Structure:**
1. **The Challenge** — restate their problem in their language (use quotes from call summary)
2. **Proposed Solution** — your approach, tailored to their specific situation
3. **Scope of Work** — deliverables (what's included) and exclusions (what's out)
4. **Timeline** — phased approach with milestones
5. **Investment** — pull pricing from `pricing-strategy` output or rate card
6. **Terms** — payment schedule, revision policy, change request process
7. **Next Steps** — clear CTA (approve, sign, schedule kickoff)

**Sales Proposal Structure:**
1. **About [Company]** — show you understand them (from research)
2. **The Opportunity** — frame their problem as an opportunity
3. **Our Approach** — how you work and what makes you different
4. **Recommended Options** — 2-3 tiered options (Good/Better/Best)
5. **Case Studies** — relevant past work (if available)
6. **Investment & Timeline** — pricing with ROI framing
7. **Next Steps** — meeting or sign

**Rate Card Proposal Structure:**
1. **Services Overview** — what you offer
2. **Engagement Models** — hourly, project, retainer
3. **Rate Card** — full pricing table
4. **How We Work Together** — process, communication, tools
5. **Terms** — minimum commitment, payment terms

### Step 4: Pricing Section

Pull pricing from these sources (in priority order):
1. `data/2-Domaines/rate-card.md` — rate card from `pricing-strategy`
2. `data/2-Domaines/business-profile.json` — revenue model info
3. Ask the user: "What's your proposed price for this?"

For tiered proposals, structure as:

| Option | What's Included | Investment |
|--------|----------------|------------|
| **Starter** | [Core scope] | [Price] |
| **Recommended** | [Full scope + extras] | [Price] |
| **Premium** | [Full scope + strategy + priority] | [Price] |

### Step 5: Terms Section

Include standard terms (reference `contract-templates` skill for full contracts):
- Payment schedule (50% upfront / 50% on delivery, or monthly)
- Revision rounds included
- Change request process and rates
- Timeline validity (proposal valid for 30 days)

### Step 6: Save and Deliver

Save to `data/1-Projets/[project]/proposal-[date].md`.
Offer to create a client card via `client-management` if one doesn't exist.

## Output Quality Checklist

Before presenting, verify:
- [ ] Problem statement uses the client's language (not your jargon)
- [ ] Scope is specific — deliverables are countable
- [ ] "Out of scope" section exists
- [ ] Timeline has real dates (not just durations)
- [ ] Pricing is clear and justified
- [ ] CTA tells them exactly what to do next

## Key References

- **`references/proposal-template.md`**: SOW template (default variant)
