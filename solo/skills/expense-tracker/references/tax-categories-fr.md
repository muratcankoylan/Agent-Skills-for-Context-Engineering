# French Expense Deductibility Guide

> **Important:** Tax rules vary by legal structure. This guide covers the most common solopreneur situations in France. Always confirm with your accountant (expert-comptable).

---

## Structure Comparison

| Structure | Expense Deduction Method | Notes |
|-----------|-------------------------|-------|
| **Auto-entrepreneur / Micro-entrepreneur** | Flat abatement (abattement forfaitaire) — NOT actual expenses | Deducting actual expenses provides no tax benefit under this regime |
| **EIRL / EI au régime réel** | Actual expenses deductible | Must keep all receipts, file detailed accounts |
| **SASU / SAS / SARL** | Actual expenses deductible via company accounts | Need a proper accounting system |
| **Portage salarial** | Professional expenses (frais professionnels) | Reimbursed by the portage company |

**The key reality for micro-entrepreneurs:** Tracking expenses is still useful for:
1. Understanding true profitability (even if not tax-deductible)
2. Deciding whether to change legal structure (réel vs. micro)
3. Determining if upgrading to régime réel would save money

**Rule of thumb:** If your actual expenses exceed the abatement rate × revenue, régime réel saves money.
- Services (BIC): abatement = 50% → worth switching when expenses > 50% of revenue
- Liberal professions (BNC): abatement = 34% → worth switching when expenses > 34% of revenue

---

## Deductibility by Category (Régime Réel / SASU)

### ✅ Fully Deductible (100%)

**Software & Tools**
- SaaS subscriptions used professionally (Notion, Figma, GitHub, etc.)
- Licenses and one-time software purchases
- Domain names and hosting
- *CGI reference: Art. 39-1*

**Professional Services**
- Accountant / expert-comptable fees
- Lawyer (avocat) fees for business matters
- Consultants and coaches (with invoice)
- *Requires: invoice with SIRET of provider*

**Marketing**
- Advertising spend (Google Ads, LinkedIn Ads, Meta Ads)
- Freelance design or copywriting (with invoice)
- Website costs for marketing purposes
- *Requires: business purpose documented*

**Education**
- Courses, training, certifications with clear professional relevance
- Business books (keep receipt, note purpose)
- Professional conference fees + associated travel
- *Note: Personal enrichment courses may be challenged*

**Coworking / Office Rental**
- Dedicated coworking desk or private office
- Short-term meeting room rentals
- *Requires: invoice in business name*

**Banking & Finance**
- Stripe/PayPal fees on business transactions
- Professional bank account fees
- Currency conversion fees (if applicable)

**Subcontractors**
- Freelancers you hire for client delivery
- *Requires: invoice from freelancer with their SIRET*

**Insurance**
- Professional liability (RC Pro) — fully deductible
- Health supplemental (mutuelle) — partial, varies by contract type

---

### ✅ Pro-Rated Deductible

**Hardware (Computer, Phone, Tablet)**
- Deduct professional use percentage only
- If used 80% for work: deduct 80% of cost
- Document the usage ratio in writing
- Items <500€ can often be fully expensed in year of purchase
- Items >500€ should be depreciated over useful life (amortissement)
- *CGI reference: Art. 39-1-2°*

**Home Office (Travail à domicile)**
- If you work from home without a dedicated office: flat rate allowance (allocation forfaitaire) possible
- If you have a dedicated room: pro-rate by room surface / total apartment surface
- Deductible costs: rent pro-rated, electricity pro-rated, internet (if not already a separate bill)
- *Document with floor plan and lease agreement*

**Vehicle**
- Use the fiscal km allowance (barème kilométrique) — simpler than deducting actual car costs
- Keep a log: date, purpose, km driven, client/project
- *Note: Electric vehicles have favorable rates*

---

### ⚠️ Partially Deductible or Complex

**Meals & Entertainment**
- Client meals (repas d'affaires): deductible if business purpose documented (who, what discussed, what outcome)
- Solo meals while traveling for work: deductible
- Solo meals at the office: only if you live too far to go home (>15 km)
- Office drinks / team lunches: deductible if pro context
- *Rule of thumb: 75% of documented client meals are typically accepted*

**Gifts (Cadeaux d'affaires)**
- Deductible if reasonable and documented (who received it, why)
- No fixed legal cap, but excessive gifts raise audit risk
- Bottles of wine, book gifts, moderate hampers: generally fine

---

### ❌ Not Deductible

- Personal expenses mistakenly logged (groceries, personal clothing, non-work travel)
- Fines and penalties (amendes)
- Personal phone plan if not separately billed from professional usage
- Life insurance (assurance-vie) premiums

---

## Receipt Management

**What to keep:**
- Original receipt or invoice for every expense
- Email confirmations count for digital purchases
- Bank statements alone are NOT sufficient (no detail of what was purchased)

**Minimum retention:** 3 years for micro-entrepreneur; 6 years for EURL/SASU (CGI art. 1734)

**Recommended tools:**
- Scan immediately with Dext (formerly Receipt Bank), Pennylane, or a free app
- Store in `data/4-Archives/receipts-[year]/` or a linked cloud folder

---

## The Switch Decision: Micro → Régime Réel

Run this calculation annually:

```
Micro abatement rate:         [34% BNC / 50% BIC / 71% BIC commerce]
Your actual expense rate:     Total Expenses / Total Revenue × 100

If actual expenses > abatement rate → réel saves money
If actual expenses < abatement rate → stay micro
```

**Example:**
- Revenue: €60,000
- Actual expenses: €22,000 (37%)
- BNC abatement: 34% = €20,400 virtual deduction
- Actual deduction = €22,000 → régime réel saves tax on €1,600 difference
- *At 30% marginal rate: saves ~€480/year. May not be worth the accounting overhead.*

**Accounting overhead cost:** A basic expert-comptable for a sole trader runs €1,500–€3,000/year. You need to save more in taxes than you pay in accountant fees.
