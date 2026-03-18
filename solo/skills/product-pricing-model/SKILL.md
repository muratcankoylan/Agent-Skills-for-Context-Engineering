---
name: product-pricing-model
description: >
  Defines the revenue model for a digital product: freemium vs. paid, one-time
  vs. subscription, tier structure, market calibration. Distinct from pricing-strategy
  which reasons in hourly service rates. Triggered by "what price for my product",
  "freemium model", "how to price my SaaS", "tier pricing", "how much to charge
  for my tool".
version: 1.0.0
bundle: revenue-ops
triggers:
  - "pricing model"
  - "revenue model"
  - "subscription pricing"
  - "price my product"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Product Pricing Model

A digital product is not a service. The marginal cost of an additional user is close to zero. Value doesn't depend on your time — it depends on what the product does for the user. These two realities change everything about pricing logic.

This skill runs after `competitive-analyzer` (which provides market price benchmarks) and before `landing-page-builder` (which communicates the pricing).

---

## The 5 Product Revenue Models

### Model 1: One-Time Payment

**Logic:** User buys once, owns forever.

**Ideal for:**
- Tools with immediate, stable value (templates, scripts, extensions)
- Markets where subscription creates friction (consumers, individual creators)
- Products without recurring infrastructure costs

**Advantages:**
- Easier conversion (no recurring commitment)
- No monthly churn to manage
- Maximum simplicity

**Pitfalls:**
- Non-recurring revenue → permanent acquisition required
- Impossible to fund product evolution without re-launching
- Frequent underpricing: "It's a one-time purchase so it should be cheap"

**Calibration:**
```
One-time price = Value delivered / [3 to 10]
Example: saves 5h/month × 12 months × hourly value $50 = $3,000/year
→ One-time price: $200–$500 (obvious ROI for the buyer)
```

**With updates:** Offer a "Lifetime deal" at a higher price including updates — standard practice on AppSumo and Gumroad.

---

### Model 2: Monthly / Annual Subscription (Classic SaaS)

**Logic:** User pays recurrently for continuous access.

**Ideal for:**
- Products with ongoing value (loses value if you stop paying)
- Data or content that evolves
- Products with infrastructure costs (servers, APIs)

**Advantages:**
- Predictable MRR → planning and investment possible
- Natural retention (switching cost)
- Can grow via expansion (upgrades, additional seats)

**Pitfalls:**
- Churn: if value isn't perceived every month, the user cancels
- Monthly favors trial / cancellation → prefer annual with discount
- Pricing too low = undervaluation + inability to fund support

**Calibration:**
```
Monthly price = [Value delivered per month] / [10 to 20]
Annual price = Monthly price × 10 (i.e., ~17% discount)

Example: saves 3h/month at $80/h = $240 value/month
→ Monthly: $12–$24/month | Annual: $120–$240/year
```

---

### Model 3: Freemium

**Logic:** Free tier for acquisition, paid tiers for monetization.

**Ideal for:**
- Products with network effects (value increases with user count)
- Markets where education is needed before conversion
- Products where the free is naturally limited (storage, usage, advanced features)

**The rule of freemium that works:**
> The free must deliver real value. The paid must be indispensable for those who actually use the product.

**Freemium that fails:**
- Free too limited → users frustrated before seeing the value
- Free too generous → nobody upgrades
- Artificial limits not tied to real usage (e.g., "max 3 projects" on a tool where everyone has 1 project)

**Types of freemium limits:**

| Limit type | Example | Recommended when |
|------------|---------|-----------------|
| **Usage** | X requests/month, X exports | Cost varies with usage |
| **Capacity** | X projects, X users, X GB | Expansion is natural |
| **Features** | Advanced analytics, integrations | Value is clearly segmented |
| **Support** | Community only vs. priority | B2B needs SLA |
| **Branding** | "Powered by X" on free | Generates viral acquisition |

---

### Model 4: Usage-Based (Pay-As-You-Go)

**Logic:** User pays proportionally to what they consume.

**Ideal for:**
- Products with variable infrastructure costs (API calls, tokens, storage)
- B2B markets where variable billing is normal
- Products whose value is directly proportional to usage

**Advantages:**
- Low barrier to entry (start without commitment)
- Perfectly aligns value and cost
- Scales automatically with customer growth

**Pitfalls:**
- Unpredictable revenue → hard to plan
- Users anxious about variable costs (bill shock)
- Complex pricing communication

**Recommended hybrid:** Fixed base + variable usage above a threshold.
```
Example: $29/month including 10,000 requests, then $0.003/additional request
```

---

### Model 5: Lifetime Deal (LTD)

**Logic:** High one-time payment = lifetime access. Used as a launch lever.

**Ideal for:**
- Launch phase: generates cash and engaged early adopters
- Markets where subscription creates too much friction
- Products in validation phase (Gumroad, AppSumo, own audience)

**Advantages:**
- Upfront cash to fund development
- Community of invested early adopters (they want it to succeed)
- Fast validation

**Pitfalls:**
- Risk of underfunding if product requires recurring costs
- Permanent support pressure without recurring revenue
- Difficulty transitioning from LTD to subscription post-launch

**Calibration rule:**
```
LTD price = Annual subscription price × 3 (minimum)
Example: $120/year → LTD at $297–$397
```

**Limit LTDs in time and volume.** Sell in waves (AppSumo does this automatically). Never offer LTDs indefinitely.

---

## Decision: Which Model to Choose

Questions to ask in order:

```
1. Does my product have variable usage costs (API, server)?
   Yes → Usage-based or Subscription with limits
   No → continue

2. Is the product value ongoing or one-time?
   Ongoing (loses value if you stop) → Subscription
   One-time (stable value once purchased) → One-time or LTD

3. Is my ICP B2B or B2C/creator?
   B2B → Subscription (monthly budget, no one-time purchases)
   B2C / solo creator → One-time or Freemium

4. Do I need to validate quickly with cash?
   Yes → LTD or one-time via Gumroad / Lemonsqueezy
   No → continue

5. Do network effects matter?
   Yes → Freemium (viral acquisition via free tier)
   No → Simple subscription
```

---

## Tier Structure

### The 3-Tier Rule (Anchoring)

Never have a single price. Always at least 3 options. Why: the choice between two options forces a binary decision (take it or leave it). The choice between three options triggers the anchoring effect: the middle tier becomes the default "right choice."

**Recommended structure:**

| Tier | Name | Goal | Psychology |
|------|------|------|-----------|
| **Tier 1** | Free / Starter / Basic | Acquisition | Shows value, generates signups |
| **Tier 2** | Pro / Growth | **The tier that must win** | The "no-brainer" — 80% of conversions here |
| **Tier 3** | Business / Team / Enterprise | High anchor | Makes Tier 2 look affordable by comparison |

**Pricing rules between tiers:**
- Tier 2 = 3 to 5× Tier 1
- Tier 3 = 3 to 5× Tier 2
- The gap must be justified by real value, not arbitrary features

### What Goes in Each Tier?

**The classic trap:** Putting the best features in the most expensive tier, frustrating mid-tier users.

**The right approach:** Tier 2 must cover the full use case of the typical individual user. Tier 3 adds organizational needs (multi-user, admin, audit, SSO, SLA) — not basic features.

```markdown
## Tier Structure Template

### [Tier 1 — Free/Starter]
- [Core feature 1]
- [Core feature 2]
- Limit: [X projects / Y exports / Z requests]
- Support: Documentation only
- Price: Free / $[X]/month

### [Tier 2 — Pro] ← The main tier
- Everything in Tier 1
- [Advanced feature 1]
- [Advanced feature 2]
- Limit: Unlimited / [high limit]
- Support: Email (24h response)
- Price: $[X]/month or $[X×10]/year

### [Tier 3 — Business/Team]
- Everything in Tier 2
- Multi-user ([N] seats included)
- Admin & permissions
- Advanced integrations / API
- Priority support (guaranteed SLA)
- Enterprise billing (purchase orders, VAT invoices)
- Price: $[X]/month or custom quote
```

---

## Final Calibration

### Market Benchmarking

Use data from `competitive-analyzer`:

```
Competitor prices: [market price table]
Target positioning: premium / parity / accessible

General rules:
- Targeting premium: 20–40% above the leader
- Targeting parity: within the median range
- Targeting accessible: 30–50% below, but with a clear value case
```

### Pricing Tests

Don't launch with a fixed final price. Test:

1. **Pricing page A/B:** Two landing pages with different prices
2. **Direct conversation:** Ask beta testers "At what price would this be a no-brainer? At what price would it feel too expensive?"
3. **Van Westendorp:** 4 questions to find the acceptable range

**Simplified Van Westendorp:**
```
Q1: At what price would you find this product too expensive to even try?
Q2: At what price would you think this product is too cheap to be reliable?
Q3: At what price would you think it's a little expensive but you'd still buy it?
Q4: At what price would you think it's a great deal?

→ Optimal price sits between Q4 and Q3.
```

---

## Save

`data/1-Projets/[project]/pricing-model-[date].md`

## Integration Points

- **`competitive-analyzer`**: provides market price benchmarks
- **`landing-page-builder`**: communicates pricing with the right arguments
- **`launch-planner`**: adapts launch strategy based on chosen model
- **`financial-health`**: integrates projected MRR into forecasts

## References

- **`references/pricing-models-product.md`**: In-depth comparison of the 5 models with real examples
- **`references/tier-design.md`**: How to build Free/Pro/Team without cannibalization
