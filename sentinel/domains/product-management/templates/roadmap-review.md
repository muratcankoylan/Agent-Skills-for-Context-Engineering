# Roadmap Review - Structured by Sentinel

## Context
- **Company / Team**:
- **Period** (Q / H1 / annual):
- **Engineering capacity** (sprints or weeks):
- **Primary strategic objective this period**:
- **Participants**:

---

## 1. Pre-review diagnosis (before planning)

### Sentinel questions to answer BEFORE scoring anything:

- [ ] What did we ship last quarter? What was the actual impact vs. predicted?
- [ ] Which features delivered the most measurable user/business value?
- [ ] What did we build that we regret? Why did we build it?
- [ ] What percentage of last quarter's roadmap shipped on time? What was the estimate?
- [ ] What's the #1 thing users want that isn't on the roadmap?

### Baseline: delivery performance (outside view)

| Metric | Last Q | Q-2 | Q-3 | Trend |
|--------|--------|-----|-----|-------|
| Features planned | | | | |
| Features shipped | | | | |
| On-time delivery % | | | | |
| Estimation accuracy (planned vs actual time) | | | | |
| % features with measurable positive outcome | | | | |

**Planning fallacy check**: Is your estimate for this quarter's capacity
in line with your actual historical delivery rate?
---


## 2. Roadmap reframes (run BEFORE scoring)

Run at least 2 of the 6 reframes. Document findings before scoring begins.

### Reframe 1: Churned user
> "Someone just cancelled. They never asked for a single feature on the roadmap.
> What problem did they actually have?"

**Findings**:

### Reframe 2: Cut 50%
> "Engineering capacity just got cut in half. You must achieve the same
> outcomes. What do you keep?"

**Must-keep list**:

---

## 3. MAP Product - Candidate scoring

** RULE: Each PM scores ALL candidates independently before any discussion.
No sharing scores until all are submitted. PM lead scores last.**

### Candidate feature matrix

| Feature | User pain /10 | Business impact /10 | Effort accuracy /10 | Strategic alignment /10 | Reversibility /10 | Opp. cost /10 | **Weighted** | Priority |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| | | | | | | | | |
| | | | | | | | | |
| | | | | | | | | |
| | | | | | | | | |
| | | | | | | | | |

**Weights**: User pain 25% / Business impact 25% / Effort 20% / Strategy 15% / Reversibility 10% / Opp. cost 5%

---

## 4. Noise check (if team > 1 PM)

For the top 3 candidates, record each PM's weighted score independently:

| Feature | PM1 | PM2 | PM3 | PM4 | Mean | SD | CV% |
|---------|-----|-----|-----|-----|------|----|-----|
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |

**CV interpretation**:
- CV < 20%: Alignment - proceed
- CV 20-35%: Moderate noise - discuss assumptions
- CV > 35%: High noise - team doesn't agree. Don't force consensus; investigate WHY.

**Noisiest feature**: _________________________ (CV: _____%)
**Source of disagreement** (what assumption differs?):

---

## 5. Opportunity cost matrix

Before committing, plot all candidates:

```
HIGH IMPACT
    |
    |  Strategic bets  |  Quick wins     |
    |  (Break down)    |  (Ship)         |
    |------------------+-----------------|
    |  Traps           |  Fill-ins       |
    |  (Kill)          |  (If free)      |
    |
LOW IMPACT
    LOW EFFORT -------- HIGH EFFORT
```

**Items classified as Traps (kill)**:

**Items classified as Strategic bets (break down)**:

**Explicit displaced items** (for every commitment, what is delayed):

| Committed feature | Displaced item | Who agreed to this tradeoff? |
|------------------|---------------|------------------------------|
| | | |

---

## 6. Final roadmap commitment

| # | Feature | Effort (weeks) | Owner | Success metric | Review date |
|---|---------|---------------|-------|----------------|-------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

**Total committed effort**: _____ weeks (must be <= historical capacity x 0.8)

**Slack buffer**: _____ weeks (minimum 20% - for unknowns, bugs, incidents)

---

## 7. Calibrated predictions

| Prediction | Confidence % | Review date | Actual |
|-----------|-------------|-------------|--------|
| Feature 1 ships by [date] | | | |
| Feature 1 achieves [metric] = [value] | | | |
| Feature 2 ships by [date] | | | |
| Total quarterly velocity = X features | | | |

---

## 8. Pre-mortem (top 1-2 bets)

> "6 months post-launch. The bet failed. What happened?"

**Feature pre-mortemed**: _________________________

| Failure mode | Probability (%) | Early warning signal | Prevention |
|-------------|----------------|---------------------|------------|
| Built for vocal minority | | | |
| Solved a fake problem | | | |
| Scope crept past viability | | | |
| Shipped without activation loop | | | |
| Underestimated effort, overestimated quality | | | |
| Wrong success metric | | | |
| Killed by internal competition | | | |

---

## 9. Decision record

**Roadmap approved**: YES / NO / CONDITIONAL

**What would change this roadmap** (explicit tripwires):
1.
2.

**Next roadmap review date**:

**Quarterly retrospective date** (when we measure predictions vs. actuals):
