# Feature Scorecard - MAP Product

## Feature
- **Name**:
- **Requestor** (who asked and when):
- **Target user segment**:
- **Requested ship date**:
- **Owner (PM)**:
- **Engineering lead**:

---

## MAP Evaluation (6 independent dimensions)

** MANDATORY: Score each dimension WITHOUT looking at other scores.
Start with the dimension you have the best evidence for.
Do NOT discuss scores with other evaluators before submitting.**
---


### 1. Evidence of user pain
> How many users have this problem? How do you know?
>
> 0-3: anecdotal (one user mentioned it)
> 4-6: pattern (multiple signals, qualitative)
> 7-10: quantified at scale (usage data / survey N>50 / validated in discovery)

**Score**: /10 - **Confidence**: %

**Evidence** (data sources, quotes, research):

**What's missing to increase confidence**:

---

### 2. Business impact
> Revenue, retention, or activation - how much, how do you know?
> Is the model causal or wishful?
>
> 0-3: assumed, no model
> 4-6: correlated (indirect proxy)
> 7-10: causally modeled (A/B proven or near-identical precedent)

**Score**: /10 - **Confidence**: %

**Impact model** (metric, expected , method):

**Assumptions** (list the assumptions this model depends on):

---

### 3. Effort accuracy
> What's the comparable feature you've built? What did it actually take?
>
> 0-3: estimated blind (no comparable, pure guess)
> 4-6: similar scope estimated (rough comparable exists)
> 7-10: near-identical feature shipped before (high confidence in estimate)

**Score**: /10 - **Confidence**: %

**Estimate**: ___ weeks / ___ sprints / ___ points

**Comparable feature**: ___________________________
**Actual time for comparable**: ___________________

**Risk factors not in estimate** (integrations, edge cases, QA, stakeholder review):

---

### 4. Strategic alignment
> Which specific OKR or strategic bet does this advance?
>
> 0-3: tangential (fits loosely, stretch rationale)
> 4-6: supports it (clearly contributes)
> 7-10: directly on the critical path of the #1 OKR this quarter

**Score**: /10 - **Confidence**: %

**Linked OKR or strategic bet**:
**How it advances it** (be specific - not just "it fits"):

---

### 5. Reversibility
> If this feature underperforms, what does it take to kill or pivot it?
>
> 0-3: permanent tech debt, hard to undo (DB schema, external contracts)
> 4-6: can be modified (significant effort to reverse)
> 7-10: can ship/kill in one sprint, no lock-in, no user migration

**Score**: /10 - **Confidence**: %

**Tech debt created**:
**Rollback plan** (if adoption is <X% after Y weeks):

---

### 6. Opportunity cost
> What 3 things WON'T be built if this is built?
>
> 0-3: blocks 3+ competing high-priority items
> 4-6: delays 1-2 items (significant tradeoff)
> 7-10: net additive (parallel track or truly low contention)

**Score**: /10 - **Confidence**: %

**Items delayed or dropped to build this**:
1.
2.
3.

---

## Aggregation

| Dimension | Score /10 | Confidence % | Weight |
|-----------|----------:|-------------:|-------:|
| Evidence of user pain | | | 25% |
| Business impact | | | 25% |
| Effort accuracy | | | 20% |
| Strategic alignment | | | 15% |
| Reversibility | | | 10% |
| Opportunity cost | | | 5% |
| **Weighted score** | | | |

## Score/Confidence pattern - diagnostic

- **High score + high confidence** -> Green light. Ship.
- **High score + low confidence** -> Potential but uncertain. Run a spike or smaller experiment first.
- **Low score + high confidence** -> Real weakness - fix it or kill it.
- **Low score + low confidence** -> Not enough information to decide. What would it take to know?

## Sentinel - Bias check

Before deciding, answer:
- [ ] **PM1 (RICE Laundering)**: Were scores assigned before or after you decided you wanted this?
- [ ] **PM2 (HiPPO)**: Did an executive express a preference before this scorecard was filled in?
- [ ] **PM3 (Planning Fallacy)**: Is the effort estimate in the bottom 25th percentile of similar features?
- [ ] **PM7 (Opportunity Cost)**: Have you named SPECIFIC items displaced by this?

---

## Decision

- [ ] **GO** - ship as scoped
- [ ] **CONDITIONAL GO** - ship after: ___________________________________
- [ ] **EXPERIMENT** - build small test to validate impact hypothesis by [date]
- [ ] **DESCOPE** - ship reduced version: ___________________________________
- [ ] **KILL** - do not build; reallocate to: ___________________________________
- [ ] **INVESTIGATE** - not enough information; next step: ___________________

**Calibrated prediction**:
"This feature will achieve [metric] = [value] by [date]."
**Confidence**: %
**Review date**: _______________

---

## Sign-off

| Role | Name | Score /10 | Confidence % | Signed |
|------|------|----------:|-------------:|--------|
| PM | | | | |
| Engineering lead | | | | |
| Design | | | | |
| Stakeholder | | | | |

*Scores entered independently before any discussion.*
