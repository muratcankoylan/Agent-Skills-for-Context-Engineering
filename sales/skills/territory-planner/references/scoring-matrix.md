# Territory Scoring Matrix

## ICP Fit Score (0–100)

Measures how closely an account matches your Ideal Customer Profile. Loaded from `data/2-Domaines/icp.json`.

| Dimension | Max Points | How to Score |
|-----------|-----------|--------------|
| Industry match | 25 | 25 = exact match / 15 = adjacent / 0 = no match |
| Company size (headcount) | 25 | 25 = within ICP range / 10 = 1 tier off / 0 = out of range |
| Geography | 20 | 20 = target region / 10 = adjacent / 0 = out of territory |
| Tech stack signals | 20 | 20 = uses tools that indicate need / 0 = no signals |
| Pain signal evidence | 10 | 10 = job posts, news, or content confirming pain / 0 = none |

**Total: 100 points**

---

## Potential Score (0–100)

Measures the revenue upside of the account, independent of current relationship.

| Dimension | Max Points | How to Score |
|-----------|-----------|--------------|
| Headcount proxy | 40 | 40 = 500+ / 30 = 200–499 / 20 = 50–199 / 10 = 10–49 / 0 = <10 |
| Funding / growth stage | 20 | 20 = Series B+ or high-growth / 10 = Series A / 0 = bootstrapped/stable |
| Industry budget tendency | 20 | 20 = high-spend industry (FinTech, SaaS, MedTech) / 10 = medium / 0 = low |
| Expansion signals | 20 | 20 = hiring in relevant function / 10 = recent funding / 0 = no signals |

**Total: 100 points**

---

## Recency Score (0–100)

Measures how warm the relationship currently is.

| Days Since Last Contact | Score |
|------------------------|-------|
| < 7 days | 100 |
| 7–14 days | 80 |
| 15–30 days | 60 |
| 31–60 days | 30 |
| 61–90 days | 10 |
| > 90 days or never contacted | 0 |

---

## Composite Score Formula

```
Composite Score = (ICP Fit × 0.45) + (Potential × 0.35) + (Recency × 0.20)
```

**Rationale for weights:**
- ICP Fit (45%) — the highest weight because wrong-fit accounts waste the most time regardless of effort
- Potential (35%) — revenue upside determines whether winning the account is worth the investment
- Recency (20%) — relationship warmth is a multiplier, not a fundamental qualifier

---

## Tier Thresholds

| Tier | Composite Score | Strategic Label | Weekly Touchpoints |
|------|----------------|-----------------|-------------------|
| T1 | 75–100 | Must Win | Weekly |
| T2 | 50–74 | Should Win | Bi-weekly |
| T3 | 25–49 | Could Win | Monthly |
| T4 | 0–24 | Nurture or Drop | Quarterly / drop |

---

## Overrides

Some accounts should be manually overridden regardless of score:

- **Executive relationship**: If a C-level at the account has a direct relationship with your CEO or founder → elevate to T1 regardless of score.
- **Strategic logo**: If winning the account would be a reference that unlocks a segment → elevate to T1.
- **Competitive threat**: If a competitor is actively in the account → elevate tier by 1.
- **Budget confirmed**: If buyer has confirmed budget and timeline → elevate to T1 immediately.

Document overrides explicitly in the territory plan with the reason.
