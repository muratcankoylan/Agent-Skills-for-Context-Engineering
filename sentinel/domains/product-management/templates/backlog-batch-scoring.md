# Backlog Batch Scoring - Sentinel PM

## Purpose

Score an entire backlog quickly using MAP Product dimensions to identify:
- Items with high confidence and high score -> ready to prioritize
- Items with low confidence -> need discovery before committing
- Items with high score but high noise -> need alignment session
- Items that have been in the backlog "forever" -> challenge their continued existence

**Use this template for quarterly or monthly backlog grooming.**

---

## Context

- **Product area / team**:
- **Date of scoring**:
- **Scorer(s)**:
- **Primary objective this quarter**:
- **Engineering capacity this quarter** (weeks): ___
---


## Batch scoring matrix

**Instructions**:
- Score each feature on a 1-5 scale (simplified MAP, for speed)
- Confidence = how sure are you of each score (H/M/L)
- Add a flag if the feature has been in the backlog > 6 months ()
- Score independently if multiple PMs, compare after

| # | Feature | User pain /5 | Business impact /5 | Effort /5 (inv.) | Strategy /5 | Total /20 | Avg conf. | Flag |
|---|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | | | | | | | | |
| 2 | | | | | | | | |
| 3 | | | | | | | | |
| 4 | | | | | | | | |
| 5 | | | | | | | | |
| 6 | | | | | | | | |
| 7 | | | | | | | | |
| 8 | | | | | | | | |
| 9 | | | | | | | | |
| 10 | | | | | | | | |
| 11 | | | | | | | | |
| 12 | | | | | | | | |

**Effort scoring is INVERTED**: 5 = very low effort / 1 = very high effort

---

## Scoring scale (simplified)

| Score | User pain | Business impact | Effort (inverted) | Strategy |
|------:|:----------|:----------------|:------------------|:---------|
| 5 | Quantified, widespread | Proven, large | < 1 sprint | #1 OKR |
| 4 | Clear pattern, multiple signals | Likely, modeled | 1-2 sprints | Directly aligned |
| 3 | Some signals, qualitative | Plausible, indirect | 2-4 sprints | Related |
| 2 | Anecdotal, 1-2 sources | Assumed, speculative | > 1 month | Tangential |
| 1 | Requested but unverified | No model | > 1 quarter | Unrelated |

---

## Triage quadrants

After scoring, place features into quadrants:

###  Ready to commit (Score >= 15 / 20, confidence H)
These go on the roadmap now.

| Feature | Score | Notes |
|---------|------:|-------|
| | | |

###  Investigate before committing (Score >= 12 / 20, confidence M or L)
Good hypothesis, but too uncertain. Run a spike, interview, or experiment.

| Feature | Score | What would increase confidence? |
|---------|------:|--------------------------------|
| | | |

###  Redesign (Score < 12 / 20, confidence H)
We know enough - and it's not good enough. Needs rethinking or kill.

| Feature | Score | What's the real problem? |
|---------|------:|--------------------------|
| | | |

###  Challenge existence (In backlog > 6 months, score < 12 / 20)
Why is this still here? Default action: KILL and re-examine in 6 months.

| Feature | Time in backlog | Last champion | Kill / Hold / Rethink |
|---------|:--------------:|---------------|----------------------|
| | | | |

---

## Anti-zombie protocol

Any feature that:
1. Has been in the backlog > 6 months AND
2. Has not been worked on or updated AND
3. Has no assigned PM champion

-> **Automatically moves to graveyard**. Can be resurrected with a new scorecard.

**Features moved to graveyard this cycle**:

| Feature | Date added | Date graveyard | Reason |
|---------|-----------|----------------|--------|
| | | | |

---

## Noise check (if multiple scorers)

After independent scoring, compare:

| Feature | Scorer 1 total | Scorer 2 total | Scorer 3 total | CV% | Action |
|---------|:---:|:---:|:---:|:---:|--------|
| | | | | | |
| | | | | | |

**Features with CV > 35%** -> alignment session before committing to roadmap.

---

## Outcome

**Features committed for this quarter**: ___ (max: what fits in 80% of capacity)
**Features sent to discovery**: ___
**Features sent to graveyard**: ___
**Features challenged (sponsor required)**: ___

**Total effort committed**: ___ weeks (must be <= capacity x 0.8)

**Next batch scoring date**: _______________
