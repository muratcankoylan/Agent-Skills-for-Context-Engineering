---
type: decision-template
domain: product-management
name: rice-evaluation
description: RICE Scoring Framework (Reach, Impact, Confidence, Effort)
---


# RICE Evaluation Protocol

## 1. Reach

**Question**: How many users will this feature impact over a single quarter?

- [ ] Estimate: **\_** users/events per quarter.
- [ ] Source: (e.g., Analytics, Traffic Logs)

## 2. Impact

**Question**: How much will this impact the goal for each user?
(3 = Massive, 2 = High, 1 = Medium, 0.5 = Low, 0.25 = Minimal)

- [ ] Score: **\_**
- [ ] Rationale: ************************\_\_************************

## 3. Confidence

**Question**: How confident are we about our estimates? (Percentage)

- [ ] 100% (High Confidence - Data backed)
- [ ] 80% (Medium Confidence - Some data/Expert opinion)
- [ ] 50% (Low Confidence - Intuition)
- [ ] Score: **\_**%

## 4. Effort

**Question**: How many "person-months" will this take?

- [ ] Estimate: **\_** months (Engineering + Design + Product)

## Calculation

**RICE Score** = (Reach _ Impact _ Confidence) / Effort

## Sentinel Check

- **HiPPO Check**: Did you adjust "Impact" because a leader requested it?
- **Confidence Check**: Do you have data for "Reach", or is it a guess?
