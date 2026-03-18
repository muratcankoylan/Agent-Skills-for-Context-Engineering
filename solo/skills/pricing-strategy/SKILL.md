---
name: pricing-strategy
description: >
  Helps create a rate card, define value-based pricing, and structure tiered offers.
  Triggers on "set my prices", "rate card", "how much should I charge",
  "pricing strategy", or "create my rates".
version: 1.0.0
bundle: revenue-ops
triggers:
  - "pricing strategy"
  - "create rate card"
  - "value-based pricing"
  - "set my rates"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Pricing Strategy

Guides you through defining your pricing, from calculating a baseline rate to structuring tiered offers that maximize revenue. Output feeds directly into `proposal-generator` and `invoice-generator`.

## Process

### Step 1: Understand Your Business
Load from `data/2-Domaines/business-profile.json`:
- Services offered
- Revenue model (hourly / project / retainer / product)
- Target market

If no business profile exists, ask:
- "What services do you offer?"
- "Who are your typical clients?"
- "What's your annual income target?"

### Step 2: Calculate Baseline Rate

**Hourly rate formula:**
1. Annual income target: [X]
2. Annual business expenses: [X]
3. Total annual need = target + expenses
4. Billable hours = 52 weeks x 5 days x 8 hours x utilization rate (0.5-0.7)
5. **Minimum hourly rate = total need / billable hours**

**Day rate:** hourly x 8 x 0.85 (15% bulk discount)

### Step 3: Build Rate Card

Structure a 3-tier rate card:

| Tier | Description | Pricing Approach |
|------|-------------|-----------------|
| **Basic** | Core service, minimal scope | Cost-based (hourly x hours) |
| **Standard** | Full service, recommended | Project-based with buffer |
| **Premium** | Full service + strategy + priority | Value-based pricing |

For each service, define:
- What's included
- What's excluded
- Delivery timeline
- Price (and how it was calculated)

### Step 4: Value-Based Pricing Exercise

For high-impact engagements, guide the user through these questions:

1. "What is this problem costing the client per month?"
2. "What would solving it be worth to them?"
3. "What have they already spent trying to fix it?"
4. "What's the cost of doing nothing for 6 more months?"
5. "How does your price compare to hiring full-time?"

**Rule of thumb:** Price at 10-20% of the value you create.

### Step 5: Competitive Research

Suggest research strategies:
- Check rates on Malt, Upwork, Toptal for the user's niche
- Compare to full-time salary equivalents (rate should be 1.5-2x hourly equivalent)
- Search for industry reports on freelance rates
- Test: if closing 100% of proposals, prices are too low

### Step 6: Save Rate Card

Save to `data/2-Domaines/rate-card.md` using the rate card template from `../financial-health/references/pricing-models.md`.

## Output Connections

Rate card output is consumed by:
- **`proposal-generator`**: Pulls package prices and hourly rates for proposals
- **`invoice-generator`**: Uses rates for invoice line item calculations
- **`financial-health`**: Compares effective rate against rate card

## Key References

- **`../financial-health/references/pricing-models.md`**: Full pricing models guide with calculations, templates, and competitive research framework

---

## 🔬 Sentinel Integration (when installed)

```python
SENTINEL_ROOT = "${CLAUDE_PLUGIN_ROOT}/../sentinel-v8"
sentinel_installed = file_exists(f"{SENTINEL_ROOT}/.claude-plugin/plugin.json")
```

Skip this section entirely if `sentinel_installed` is False. Pricing-strategy works identically without it.

### Trigger condition
Activate **after Step 2** (minimum rate calculated) and **before Step 4** (value-based pricing).
The calculation is mechanical — Sentinel doesn't touch the math. It targets the inputs and the framing.

### What to run

**Step 1 — anchoring check**

Before running the formula, ask:
> "What rate were you thinking of charging before we started this?"

Record the answer. After Step 2 produces the minimum rate:
- If the final rate card ends up within 20% of the initial answer → flag: "Your result is close to your starting number. This is a classic anchoring pattern — the formula may have justified a number you'd already settled on. Check: would you reach the same conclusion if you started from the client's value instead?"

**Step 2 — sentinel-reframe (before value-based pricing)**

Before Step 4, invoke `sentinel-reframe` on the pricing question using the abstraction ladder technique:

> Current frame: "How much should I charge per hour/project?"
> Reframe up: "What problem am I solving and what is it worth to the client if it's solved?"
> Reframe down: "What is the minimum the client would accept paying for this specific outcome?"
> Inverse: "What would my best client pay if I presented this as a guaranteed outcome, not a time block?"

Present 2-3 reframes. Ask which resonates. Let the user's answer inform Step 4.

**Step 3 — reality-checker (base rate on market rates)**

After the rate card is drafted, invoke `reality-checker`:

Reference class: "[service category] freelancers / consultants in [market]"

Provide base rate estimates with confidence for:
- Median day rate for the category (source: Malt, Toptal, relevant platforms)
- Top quartile day rate (what justifies being there)
- Full-time salary equivalent (rate should be 1.5–2x hourly equivalent)

If user's rate is below median → flag: "You're pricing below market. This is a common pattern, not a signal of fair value."
If user's rate is above top quartile → require explicit articulation of why.

### Output format addition

Add a **Pricing Hygiene Check** before the final rate card:

```
## Pricing Hygiene (Sentinel)

Anchoring: [flag or clear]
Market position: Your rate is in the [bottom/mid/top] quartile for [category].
  Verify: [specific source and URL]

Reframe that shifted your thinking: "[reframe text]"
  → Applied to: [which tier in the rate card]
```

### Standalone output (Sentinel not installed)
Standard rate card with 3 tiers, value-based pricing exercise, competitive research suggestions. No change.

---

## 🛡️ Sentinel Integration

```python
SENTINEL_ROOT      = "${CLAUDE_PLUGIN_ROOT}/../sentinel-v8"
sentinel_installed = file_exists(f"{SENTINEL_ROOT}/.claude-plugin/plugin.json")
```

**Trigger**: After Step 2 (baseline rate calculated), before Step 6 (save rate card).
**Standalone mode**: Skip entirely. Save rate card as normal.

### If Sentinel installed — Three checks before the rate card saves

**Step A — Anchoring check** (runs silently before anything else)

Ask the user: "Before we look at the calculation — what rate were you expecting to land on?"
Record their answer. After the formula produces the minimum rate:
- If the final rate is within 20% of their pre-stated expectation: flag it.
  > "Your final rate is close to what you expected before the calculation. This is a classic anchor effect — the formula may have adjusted toward your prior instead of finding the true floor. Consider: if you had no prior rate in mind, would this number change?"
- If significantly different: no flag needed.

**Step B — reality-checker** (`../sentinel-v8/agents/reality-checker.md`)

After calculating the minimum hourly rate, provide the outside view:
- Reference class: `"[user's service category] freelancers, [experience level], [geography]"`
- Estimates with confidence: median rate, 75th percentile, 90th percentile
- Verify at: Malt rate reports, Toptal benchmarks, Glassdoor contractor data, Payoneer freelancer survey
- Gap analysis: "Your calculated minimum puts you at [X] percentile. At that rate, you are [above/below/at] market."

If calculated minimum is below median market rate: flag it explicitly.
> "Your minimum rate is below market median. You can charge this floor, but you likely don't have to. Consider starting from median rather than minimum."

**Step C — sentinel-reframe** (`../sentinel-v8/commands/sentinel-reframe.md`)

Before Step 4 (value-based pricing), apply the abstraction ladder technique:
- Go UP: "Instead of 'What should I charge per hour?' — what problem does this client need solved, and what is solving it worth to their business?"
- Go DOWN from the value: "If solving this problem is worth $X to the client, what fraction of that is fair to charge?"
- Inversion: "If you were the client paying this rate, at what point would the ROI feel obvious without negotiation?"

Present the reframed question alongside the value-based pricing exercise in Step 4.
