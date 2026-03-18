---
name: competitive-analyzer
description: >
  Systematic market mapping: direct and indirect alternatives, positioning gaps,
  value matrix. Inserts into the validate phase of /solo:build. Triggered by
  "analyze the competition", "who already does this", "market map",
  "who are my competitors", "competitive analysis".
version: 1.0.0
bundle: sales-growth
triggers:
  - "competitive analysis"
  - "map competitors"
  - "analyze competition"
tools:
  standalone: ["exa"]
  supercharged: ["exa"]
---

# Skill: Competitive Analyzer

Before building, map. This skill transforms "I know competitors exist" into an actionable grid that reveals real gaps — the unresolved frustrations that existing alternatives systematically create for your ICP.

Output feeds directly into `positioning-statement` and `product-pricing-model`.

## When to Use

- After `/solo:build discover` (problem validated, now look at the market)
- Before `positioning-statement` (positioning is defined *against* alternatives, not in a vacuum)
- When someone says "but [X] already does that"

---

## Process

### Step 1: Identify Alternatives (Not "Competitors")

**Key distinction:** Founders think in terms of direct competitors. Users think in terms of alternatives — what they would do *instead* of your product, including doing nothing, using Excel, or cobbling together a manual workflow.

Four categories to map:

| Category | Description | Example |
|----------|-------------|---------|
| **Direct competitors** | Do exactly the same thing | Identifiable products |
| **Functional substitutes** | Solve the same problem differently | "We use Notion for that" |
| **Upstream alternatives** | Avoid the problem rather than solve it | "We don't have that process yet" |
| **The status quo** | Change nothing, keep hacking it together | Excel, email, sticky notes |

**Discovery method (standalone):**
1. G2/Capterra/Product Hunt reviews for the problem terms
2. Reddit: `[problem] subreddit` → see what people recommend
3. "vs" and "alternatives" pages: `[obvious solution] alternatives`
4. 1-3 star reviews of existing products — the real gold mine

**With `~~search` connected:** automated queries across all these channels.

Target: **5 to 8 alternatives** (more = analysis that loses depth).

---

### Step 2: Comparison Grid

For each alternative, score on 5 key dimensions. Dimensions vary by domain — propose the most relevant ones and confirm before filling in.

**Generic starting dimensions:**

| Dimension | What to evaluate |
|-----------|----------------|
| **Ease of adoption** | Setup time, learning curve, onboarding friction |
| **Functional depth** | Does it truly cover the full use case end-to-end |
| **Price / accessibility** | Pricing model, real cost at actual usage |
| **Integrations** | Fits into existing workflow |
| **Support / community** | Docs, support quality, active user base |

**Output format:**

```markdown
## Comparison Grid: [Domain]

| Alternative | Ease | Depth | Price | Integrations | Support | Summary |
|-------------|------|-------|-------|-------------|---------|---------|
| [Competitor A] | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 💰💰💰 | ⭐⭐ | ⭐⭐⭐ | Strong on depth, weak on adoption |
| [Competitor B] | ⭐⭐⭐⭐⭐ | ⭐⭐ | 💰 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Easy but shallow |
| Status quo (manual) | ⭐⭐⭐⭐ | ⭐ | Free | — | — | Always the most underestimated alternative |
| **[Your product]** | ? | ? | ? | ? | ? | *What you want to claim* |
```

---

### Step 3: Value Matrix

The grid says *what*, the matrix says *why it matters*. Identify the factors the industry competes on by default, and find what nobody does.

```markdown
## Value Matrix

### What everyone does (table stakes)
— No differentiation possible here
- [Factor 1]
- [Factor 2]

### What some do well (current differentiators)
— Your product must pick a side
- [Factor A] → [Competitor X] dominates
- [Factor B] → [Competitor Y] dominates

### What nobody really does (the gap)
— Positioning opportunity
- [Gap 1]: [why it matters to the ICP]
- [Gap 2]: [why it matters to the ICP]

### What you can eliminate
— What competitors offer but your ICP doesn't need
- [Unnecessary feature / complexity]
```

---

### Step 4: Frustration Analysis

The real gold mine. Not what products do — what users say when things don't work.

**Sources:**
- 1-3 star reviews on G2, Capterra, App Store
- Reddit posts "I switched from X because..."
- Competitor "vs" pages
- Negative Product Hunt comments

```markdown
## Recurring Frustrations

### [Competitor A]
- "Too complex to set up" (x[N] mentions)
- "[Feature Y] doesn't work as expected" (x[N])

### [Competitor B]
- "Pricing explodes at scale" (x[N])
- "No integration with [tool]" (x[N])

### Status quo
- "Losing time on [manual task]" (x[N])
- "Too many human errors" (x[N])

### Cross-cutting themes (unresolved by anyone)
1. [Theme 1] — present in X/Y alternatives → real opportunity
2. [Theme 2]
```

---

### Step 5: Positioning Synthesis

```markdown
## Synthesis: Where to Position

**The market competes on:** [2-3 dominant factors]

**The unaddressed gap:** [What nobody does well for the target ICP]

**Suggested positioning:**
"For [specific ICP], who are tired of [main frustration],
[product name] is the [category] that [addresses the gap],
unlike [alternatives] which [common limitation]."

**Risks:** [What could invalidate this positioning]
```

Direct brief for `positioning-statement`.

---

## Save

`data/1-Projets/[project]/competitive-analysis-[date].md`

## Integration Points

- **`/solo:build validate`**: called as the second validation step
- **`positioning-statement`**: consumes the synthesis and value matrix
- **`product-pricing-model`**: uses the competitive price grid to calibrate pricing
- **`landing-page-builder`**: frustrations become objections to address in the FAQ

## References

- **`references/feature-gap-matrix.md`**: grid template + scoring guide
- **`references/alternatives-audit.md`**: method for extracting frustrations from reviews
