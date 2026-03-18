---
name: landing-page-builder
description: >
  Generates the complete copy for a conversion landing page for an early-stage
  product: headline, subheadline, social proof, features, pricing, CTA.
  Focused on product copywriting, not technical design. Triggered by "write my
  landing page", "sales page", "homepage copy", "launch page", "copy for my site".
version: 1.0.0
bundle: sales-growth
triggers:
  - "create landing page"
  - "write landing page"
  - "build landing page"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Landing Page Builder

The landing page is often the first concrete artifact of a product. It forces you to answer the hardest question: why you, why now, for whom exactly.

This skill produces copy — not design. Copy comes before design. A great message with bad design converts. A bad message with great design does not.

## When to Use

- **Validate phase:** A landing page with a signup form = demand test without building the product
- **Launch phase:** The real launch page for first users
- Anytime the message needs to be reframed

## What This Skill Produces

Complete copy for the following sections, in order:

1. Above the fold (hero)
2. The problem (agitation)
3. The solution + how it works
4. Features / benefits
5. Social proof
6. Pricing
7. FAQ
8. Final CTA

---

## Required Inputs

Before generating, collect:

```
- Product: [name]
- ICP: [who exactly — as specific as possible]
- Problem solved: [in one sentence]
- Primary benefit: [concrete result the user gets]
- Differentiators vs. alternatives: [what you do that nobody else does]
- Social proof available: [testimonials, numbers, notable users — even early-stage]
- Page goal: [waitlist / direct purchase / demo / closed beta]
- Pricing model: [free / freemium / one-time / subscription]
```

If `competitive-analyzer` has already run → load `data/1-Projets/[project]/competitive-analysis-[date].md` for frustrations (to transform into objections addressed in the FAQ).

---

## Section 1: Above the Fold (Hero)

The only section everyone sees. It must answer in 5 seconds: "What is this, who is it for, what do I get?"

### Headline

**Golden rule:** The headline speaks to the user's outcome, not the product's features.

❌ "The most powerful content management platform"
✅ "Publish 3× faster without ever missing a deadline"

**Tested formulas:**

| Formula | Structure | Example |
|---------|-----------|---------|
| **Outcome** | Verb + outcome + context | "Launch your product in 2 weeks, not 6 months" |
| **Problem → Solution** | [Known problem] → [Direct solution] | "Stop chasing spreadsheets. Know if your business is healthy in 5 minutes a week." |
| **For [ICP]** | For [who], [outcome] | "For B2B freelancers who hate chasing late payments: automated follow-ups" |
| **The [category] that [differentiator]** | Direct positioning | "The only planning tool that thinks like a creator, not an agency" |
| **Number + outcome** | Concrete figure + benefit | "127 hours recovered per year. That's what [product] does for you." |

**Generate 5 headline options, present the 3 best with explanation.**

### Subheadline

1 to 2 sentences. Role: clarify the headline, name the ICP, specify the mechanism.

**Structure:** "[Product] helps [specific ICP] [outcome] through [mechanism]. [Proof or secondary differentiator]."

**Example:**
> Noté helps B2B freelancers get paid on time through automated, personalized follow-ups. Without ever sounding like a debt collection robot.

### Primary CTA

Single button. Value-oriented text, not a generic action.

❌ "Sign up" / "Get started" / "Try it"
✅ "Get my time back" / "Try free — no credit card" / "Join the waitlist"

**For a waitlist:** Minimal email form + promise of what will be received.
**For direct purchase:** CTA with price shown if possible ("Start for $19/month").
**For a demo:** Calendly embed or short qualification form.

### Proof Point (optional but powerful)

One line below the CTA: number, minimal social proof, or risk reduction.

Examples:
- "Already used by 340 freelancers"
- "14-day free trial — cancel in 2 clicks"
- "Recommended by [known name in the niche]"

---

## Section 2: The Problem

Before presenting the solution, name the problem in a way that makes the ICP feel understood. This section creates the emotional context that makes the solution desirable.

**Agitation structure:**
1. Name the situation (neutral)
2. Agitate the frustration (emotional)
3. Consequences (what it costs)

**Example:**

> You spend 2 hours a week chasing clients to get paid.
>
> That's not work — it's mental energy wasted on tasks you hate. And the longer you wait, the less likely you are to get paid.
>
> On average, freelancers lose 12% of their annual income to late or unpaid invoices. That's not an abstract statistic — it's a month of work that disappears.

**Length:** 3 to 5 sentences. Don't over-agitate (it becomes depressing rather than motivating).

---

## Section 3: The Solution + How It Works

Two distinct parts:

**The solution:** 1 paragraph presenting the product as the direct answer to the problem described.

**How it works:** 3 steps maximum. Creators always underestimate how complex their product can seem from the outside. 3 simple steps reduce perceived friction.

**3-step format:**
```
Step 1: [Action verb] — [Short description]
Step 2: [Action verb] — [Short description]
Step 3: [Final result]
```

Example:
```
1. Connect your invoicing tool — 2 minutes, no CSV needed
2. Set your follow-up rules — your style, your timing
3. Get paid — automatically, without thinking about it
```

---

## Section 4: Features / Benefits

**Rule:** Features = what the product does. Benefits = what the user gets. Always communicate both.

❌ "Automated follow-up system"
✅ "Automated follow-ups — you stop having to think about it, clients pay faster"

**Recommended format (3 to 6 items):**

```
🔔 [Feature name]
[Benefit in one sentence — starts with "You..." or "Your..."]
[Optional detail — how it works concretely]
```

**Order:** From most differentiating benefit to most expected (table stakes last).

---

## Section 5: Social Proof

### With testimonials (ideal)

Short format (20-40 words) + photo + name + title.

> "Since using [product], my payment delays went from 45 days to 12. I recovered $3,200 last quarter."
> — Marie L., Independent HR Consultant

**To collect before launch:** Have 5-10 people test it and ask for a testimonial about the result they got (not about the product in general).

### Without testimonials (early-stage)

Alternatives:
- Usage numbers ("340 users in beta")
- Logos of who's using it (even if it's freelancers with first name + industry)
- Press or community mention ("Featured on r/freelance")
- "Built by [founder credibility]"

---

## Section 6: Pricing

Three principles:
1. Show the price clearly — ambiguity kills conversion
2. Justify each tier by its target persona
3. Visually highlight the recommended tier

**Copy structure for each tier:**
```
[Tier name]
$[Price] / [period]
[Who it's for: one sentence]
---
✓ [Feature / benefit 1]
✓ [Feature / benefit 2]
✓ [Feature / benefit 3]
[CTA]
```

**To reassure:** Below the pricing table, add a risk-reduction line.
"All plans include a 14-day trial. No credit card required to start."

---

## Section 7: FAQ

**Role:** Address the objections that block conversion without the visitor having to contact anyone.

**Sources for objections:**
- `competitive-analyzer` → recurring market frustrations
- Conversations with early-stage users
- Hesitations observed during demos

**Standard questions to include:**

| Objection | FAQ Question |
|-----------|-------------|
| Trust | "Is my data safe?" |
| Complexity | "Do I need technical skills?" |
| Commitment | "Can I cancel at any time?" |
| Alternatives | "How is this different from [main competitor]?" |
| Timing | "I'm not ready yet — when should I start?" |
| Results | "How long before I see results?" |

**Format:** Question in H3, direct answer of 2-4 sentences.

---

## Section 8: Final CTA

Repeat the primary CTA with one last reason to act.

**Structure:**
```
[Summary headline — reframe the primary benefit]
[Subheadline — risk reduction]
[CTA button]
[Proof point]
```

Example:
```
Stop chasing your payments.
14-day free trial — no credit card.
[Start now]
340 freelancers are already using it.
```

---

## Copy Validation

Before publishing, test with this filter:

**The 5-second test:** Show the hero (above the fold) to someone who doesn't know your product. Ask these 3 questions after 5 seconds:
1. "What does this product do?"
2. "Who is it for?"
3. "What do you get out of using it?"

If answers are vague or wrong → the headline or subheadline needs work.

**The "so what" test:** For every feature sentence, ask "so what?" until you reach the concrete benefit. If you can't answer, the sentence isn't benefit-oriented enough.

---

## Save

`data/1-Projets/[project]/landing-page-copy-[date].md`

## Integration Points

- **`competitive-analyzer`**: frustrations → FAQ objections, differentiators → headline
- **`product-pricing-model`**: tier structure → pricing section
- **`positioning-statement`**: positioning → headline and subheadline
- **`voice-dna-creator`**: copy tone and style → coherence with creator's voice
- **`launch-planner`**: landing page is the hub for all launch campaigns

## References

- **`references/landing-page-frameworks.md`**: PAS, AIDA, Before/After/Bridge — 3 frameworks with full examples
- **`references/headline-formulas.md`**: 25 headline formulas with SaaS/tool/creator examples
