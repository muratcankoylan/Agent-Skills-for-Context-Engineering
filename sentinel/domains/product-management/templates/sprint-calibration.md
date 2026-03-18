# Sprint & Delivery Calibration - Sentinel PM

## Purpose

Track estimation predictions vs. actual outcomes over time to:
1. **Measure individual and team calibration** (do your confidence levels match your accuracy?)
2. **Apply planning fallacy corrections** based on real track record
3. **Build a reference class** for future estimates
4. **Detect systematic biases** (always optimistic? always underestimating complexity?)

Kahneman's calibration insight: "A well-calibrated person who is 70% confident
is right about 70% of the time. Most professionals are wrong 70% of the time
when they are 90% confident."

---

## Calibration ledger - Running log

Add a row each time a prediction is made. Fill actuals at review.

| Date | Feature/Initiative | Predicted ship date | Actual ship date | Ratio | Predicted impact | Actual impact | Impact ratio | PM | Confidence % |
|------|--------------------|:-------------------:|:----------------:|:-----:|:----------------:|:------------:|:------------:|----|-----------:|
| | | | | | | | | | |
| | | | | | | | | | |
| | | | | | | | | | |
| | | | | | | | | | |
| | | | | | | | | | |
| | | | | | | | | | |
| | | | | | | | | | |

**Ratio** = Actual / Predicted. Ratio > 1.0 = took longer / less impact than predicted.
---


## Calibration report (run quarterly)

### Delivery time accuracy

| Metric | Value | Interpretation |
|--------|------:|----------------|
| Mean effort ratio | | 1.0 = perfect. >1.2 = systematic underestimate |
| Median effort ratio | | |
| % features shipped on-time | | |
| Worst overrun (ratio) | | |
| Best estimate (ratio closest to 1.0) | | |

**Correction factor**: If mean ratio is 1.5 -> multiply all future estimates x 1.5

### Impact accuracy

| Metric | Value | Interpretation |
|--------|------:|----------------|
| Mean impact ratio | | 1.0 = perfect. <0.6 = systematic overestimate |
| % features meeting impact target | | |
| Highest overestimate (feature) | | |
| Most accurate impact prediction | | |

**Impact discount**: If mean impact ratio is 0.6 -> apply 0.6x to all future impact claims

---

## Confidence calibration table

After 20+ predictions, calculate how often you were right at each confidence level:

| Stated confidence | Times used | Times correct | Actual accuracy | Calibration |
|:-----------------:|:----------:|:-------------:|:---------------:|:-----------:|
| 90%+ | | | % | Over/Under/Good |
| 70-89% | | | % | Over/Under/Good |
| 50-69% | | | % | Over/Under/Good |
| < 50% | | | % | Over/Under/Good |

**Overconfidence signal**: If 90% confidence -> only right 60% of the time,
you're systematically overconfident. Reduce all stated confidence by 20%.

---

## Bias pattern detection

Answer after each quarterly calibration:

1. **Do we consistently underestimate effort?**
   - If mean ratio > 1.3: YES. Apply x1.3-1.5 correction automatically.
   - Pattern: early estimates vs. late estimates - are you worse at the start of projects?

2. **Do we consistently overestimate impact?**
   - If mean impact ratio < 0.7: YES. Challenge every impact claim by asking:
     "What would the 25th percentile outcome look like?"

3. **Who is the best calibrated PM on the team?**
   - Lowest mean |ratio - 1.0| across both dimensions
   - Use their estimation approach as the team default

4. **Which types of features are systematically underestimated?**
   - Infrastructure vs. user-facing?
   - New features vs. improvements?
   - Cross-team vs. single-team?

---

## Estimation improvement protocol

### If mean effort ratio > 1.4 (chronic underestimation):

**Root causes to investigate**:
- [ ] Best-case thinking (estimating the happy path)
- [ ] Scope not frozen before estimation
- [ ] QA, edge cases, stakeholder review not included
- [ ] External dependencies not accounted for
- [ ] "We've never done this before" not flagged as uncertainty

**Corrections to apply**:
- [ ] Switch from single-point estimates to three-point estimates (best/most-likely/worst)
- [ ] Require a comparable precedent for any estimate
- [ ] Add 40% buffer as default planning fallacy correction
- [ ] Flag any estimate without a comparable as "unknown - spike required"

### If mean impact ratio < 0.6 (chronic overestimation):

**Root causes to investigate**:
- [ ] Impact claimed by the feature advocate (not independent)
- [ ] No holdout test / A/B to measure incrementality
- [ ] Confounded with other simultaneous changes
- [ ] Wrong metric (vanity metric, not business metric)
- [ ] Short-term metric spike, no sustained impact

**Corrections to apply**:
- [ ] Require causal model (not correlation) for impact claims > 20%
- [ ] Require a holdout test for any claimed impact > $X or >Y%
- [ ] Apply impact discount factor x0.6 to all estimates until recalibrated
- [ ] Separate "usage" metric from "business outcome" metric in all scorecards

---

## Sprint retrospective calibration (short version)

Run at the end of each sprint:

**Sprint**: ___ | **Date**: ___

| Commitment | Predicted (points/days) | Actual | Ratio |
|-----------|:---------:|:------:|------:|
| Feature A | | | |
| Feature B | | | |
| Feature C | | | |
| Bug fixes | | | |
| **Sprint total** | | | |

**Sprint velocity accuracy**: ___% (target: within 20%)

**One honest answer**:
"The biggest thing we underestimated this sprint was: ________________________"

**One action for next sprint**:
"To improve estimation, we will: ________________________"

---

## Annual calibration summary

| Quarter | Mean effort ratio | Mean impact ratio | Calibration trend |
|---------|:-----------------:|:-----------------:|:-----------------:|
| Q1 | | | |
| Q2 | | | |
| Q3 | | | |
| Q4 | | | |
| **Annual** | | | |

**Best quarter** (closest to 1.0 on both):
**Worst quarter**:
**Year-over-year calibration improvement**: YES / NO / FLAT

**Calibration score** = 1 / (mean |effort ratio - 1| + mean |impact ratio - 1|)
Higher = better calibrated. Track over time.
