# Tier Design: Building Free/Pro/Team Without Cannibalization

Practical guide for deciding what goes in each tier without frustrating users or leaving money on the table.

---

## The Classic Tier Design Trap

Most creators design their tiers starting with features ("I'll put this in free, that in pro"). The result: arbitrary tiers that don't reflect real use cases.

**The right approach: start with personas, not features.**

---

## Step 1: Identify the 3 User Personas

Before designing tiers, answer this question: who are the 3 distinct types of users who might use this product?

**Example for a content management tool:**
- **Persona A:** Solo creator who's testing, no clear budget → wants to validate before paying
- **Persona B:** Established creator who publishes regularly → clear value, willing to pay to save time
- **Persona C:** Small agency or team → needs collaboration, business billing

Tiers correspond to these personas. Each persona must find their obvious tier without having to think.

---

## Step 2: Define the Friction Points

For each persona, identify: what will block them in the tier below?

**Friction must be natural, not artificial.**

**Natural friction:** The user wants to do something the product doesn't allow in that tier because it's a genuinely advanced need.

**Artificial friction:** The product technically could do it, but the limit is imposed to force an upgrade.

Artificial friction generates frustration. Natural friction generates voluntary conversion.

**Examples of natural vs. artificial friction:**

| Limit | Natural or artificial | Why |
|-------|-----------------------|-----|
| "Max 3 projects" (if the average user has 2-3 projects) | 🔴 Artificial | The limit feels arbitrary |
| "Unlimited export" in Pro vs. "5 exports/month" in Free | 🟢 Natural | An active user exports regularly |
| "Team members" only in Pro | 🟢 Natural | A solo user doesn't need this |
| "Basic analytics" in Free vs. "Advanced analytics" in Pro | Depends | Natural if basics are truly sufficient for starting out |

---

## Step 3: Feature-by-Feature Decision Template

For each feature, answer these questions:

```
Feature: [name]

1. Who needs it?
   [ ] Persona A (testing solo)
   [ ] Persona B (established user)
   [ ] Persona C (team/agency)

2. Is it a core feature or an advanced one?
   Core = necessary to see the product's value
   Advanced = improves the experience of an already-convinced user

3. Does it generate infrastructure costs on our side if offered in free?
   Yes → Limit or reserve for paid
   No → Can go in free if it's a core feature

Decision: Free / Pro / Business
```

---

## Step 4: The Golden Rules of Tier Design

### Rule 1: Free must deliver real value

If a free tier user can't accomplish their primary goal, they leave before converting. Free is an acquisition investment, not a frustrating demo.

**Test:** Can a free tier user get a concrete result they could show someone? If not, the free tier is too limited.

### Rule 2: Pro must cover the complete use case

Pro shouldn't be "free + a few small things." Pro is the complete product for an individual user. Business/Team adds organizational needs (collaboration, admin, billing).

**Test:** Can a Pro user do everything they need without ever being blocked? If not, Pro is too limited.

### Rule 3: Only organizational needs go in Business

Multi-user management, permissions, audit trail, SSO, centralized billing, SLA support: these are structural needs, not functional ones. A solo user will never need them.

**What should NOT be exclusively in Business:** Features that solos or freelancers use alone but exist "to justify the price."

### Rule 4: The value gap must justify the price gap

If Pro costs 5× Free, the additional value must feel perceptibly 5× better.

**The "10× value" rule:** For each tier, the product should seem worth at least 10× its price. If not, pricing is too high or value isn't being communicated well enough.

---

## Concrete Example: Content Planning Tool

### Before (bad design)

| Feature | Free | Pro ($19/mo) | Business ($79/mo) |
|---------|------|-------------|-------------------|
| Editorial calendar | ✅ | ✅ | ✅ |
| Max 1 social account | ✅ | ❌ | ❌ |
| Max 3 social accounts | ❌ | ✅ | ❌ |
| Unlimited accounts | ❌ | ❌ | ✅ |
| Scheduling | ✅ | ✅ | ✅ |
| Analytics | ❌ | Basic | Advanced |
| Team | ❌ | ❌ | 5 members |

**Problem:** Pro is barely differentiated from Free. "3 accounts" vs. "1 account" is an arbitrary limit. A solo creator rarely has more than 3 accounts.

### After (good design)

**Persona A:** Solo creator just starting out
**Persona B:** Established creator with a real audience
**Persona C:** Small agency or creator with an assistant

| Feature | Free (Persona A) | Pro $19/mo (Persona B) | Agency $79/mo (Persona C) |
|---------|------|-------------|-------------------|
| Editorial calendar | ✅ | ✅ | ✅ |
| Social accounts | 3 | Unlimited | Unlimited |
| Scheduling | 10 posts/month | Unlimited | Unlimited |
| Drafts & templates | ❌ | ✅ | ✅ |
| Analytics | ❌ | ✅ Full | ✅ Full + export |
| AI (suggestions) | ❌ | ✅ | ✅ |
| Team members | 0 | 0 | 5 included |
| White-label | ❌ | ❌ | ✅ |
| Centralized billing | ❌ | ❌ | ✅ |

**Why this is better:**
- Free lets you genuinely use the tool (10 posts/month is enough to test)
- Pro is the complete product for a solo creator (analytics + AI + unlimited)
- Agency meets team and multi-client management needs

---

## Pre-Launch Checklist

```
Free tier:
[ ] A user can accomplish their primary goal without paying
[ ] The limit makes sense relative to a beginner's actual usage
[ ] The limit creates natural (not artificial) friction as usage grows

Pro tier:
[ ] Covers the full use case of an individual user
[ ] No "basic" feature is hidden behind the paywall
[ ] The move from Free to Pro is motivated by value, not frustration

Business / Team tier:
[ ] Only adds collaboration / organization features
[ ] Price is justified by measurable savings or value
[ ] A solo user will never need it

Overall:
[ ] Each tier maps clearly to an identified persona
[ ] Price gap reflects value gap
[ ] A visitor to the pricing page can find their tier in under 30 seconds
```
