# Noise Audit - Investment Committee
# Sentinel M&A Pack

## Purpose

Measure the actual variance in judgment between committee members
evaluating the same target. The result is almost always uncomfortable.
That discomfort is the beginning of a better process.

Kahneman (Noise, 2021): *"The first step is a noise audit."*
This is that step.

---

## Setup

- **Target evaluated**:
- **Committee members** (roles, not names - anonymize for scoring):
  - Member A: ___
  - Member B: ___
  - Member C: ___
  - Member D: ___
  - Member E: ___
- **Facilitator** (does not score):
- **Date**:
- **Session duration**: ~90 minutes
---


## Protocol - Non-negotiable rules

**Rule 1 - No discussion before scoring**
Members score in silence. No verbal or written sharing of scores before
all sheets are submitted. This rule prevents anchoring.

**Rule 2 - Senior members score last**
The most senior person in the room submits their score last.
This prevents the most common source of seniority anchoring.

**Rule 3 - Confidence is scored separately from performance**
Members score both how good the dimension is (0-10) AND how confident
they are in their score (0-100%). Low confidence is signal, not weakness.

**Rule 4 - No averaging during discussion**
The goal of the discussion phase is to understand disagreement,
not to converge to a middle score. Forced averages hide noise,
they don't resolve it.

---

## Phase 1 - Independent scoring (25 min)

*Each member completes this section independently, in writing.*
*Do not speak. Do not show your scores.*

**Member**: ___ (A / B / C / D / E)

Score each dimension from 0-10, then rate your confidence (0-100%).

| Dimension | Score (0-10) | Confidence (0-100%) |
|---|:---:|:---:|
| D1 - Strategic fit | | |
| D2 - Market and competitive position | | |
| D3 - Financial quality | | |
| D4 - Synergy credibility | | |
| D5 - Integration feasibility | | |
| D6 - Valuation relative to value | | |
| **Total** | / 60 | |

**Overall recommendation**: [ ] Proceed  [ ] Conditional  [ ] Do not proceed

**The one thing that would change my recommendation**:
___

*Fold and submit to facilitator before any discussion.*

---

## Phase 2 - Noise measurement (10 min)

*Facilitator collects all sheets. Runs Sentinel noise measurement.*

### Data collection table (facilitator only)

| Dimension | Member A | Member B | Member C | Member D | Member E | Mean | CV% |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| D1 Strategic fit | | | | | | | |
| D2 Market position | | | | | | | |
| D3 Financial quality | | | | | | | |
| D4 Synergy credibility | | | | | | | |
| D5 Integration feasibility | | | | | | | |
| D6 Valuation | | | | | | | |
| **Total score** | | | | | | | |

### Noise calculation

Run for each dimension:
```bash
timeout 10 python3 "$CLAUDE_PLUGIN_ROOT/skills/decision-hygiene/scripts/noise.py" \
  --json '{"algorithm": "cv", "data": [scoreA, scoreB, scoreC, scoreD, scoreE]}'
```

### Noise results

| Dimension | CV% | Noise level | Flag? |
|---|:---:|:---:|:---:|
| D1 Strategic fit | | | |
| D2 Market position | | | |
| D3 Financial quality | | | |
| D4 Synergy credibility | | | |
| D5 Integration feasibility | | | |
| D6 Valuation | | | |
| **Overall (total score)** | | | |

**Noise interpretation**:
- CV < 15%: LOW - genuine agreement
- CV 15-30%: MODERATE - worth understanding
- CV 30-50%: HIGH - significant disagreement, discuss before deciding
- CV > 50%: VERY HIGH - committee is not evaluating, it is negotiating

**Most disagreed dimension**: ___ (CV: __%)
**Most agreed dimension**: ___ (CV: __%)
**Overall committee CV**: __% -> [ ] LOW  [ ] MODERATE  [ ] HIGH  [ ] VERY HIGH

---

## Phase 3 - Reveal and structured discussion (40 min)

*Facilitator reveals scores. Following structure is mandatory.*

### Step 1 - Display (5 min)

Show the table. No commentary. Let the numbers land.
*The silence after the reveal is the most valuable 30 seconds of the session.*

### Step 2 - Focus only on high-noise dimensions (20 min)

Do NOT discuss low-noise dimensions. Focus exclusively on dimensions
with CV > 30%.

For each high-noise dimension, ask:

**"What specific evidence drove your score? Not your conclusion - your evidence."**

- Member with HIGHEST score speaks first: what did you see that made you score high?
- Member with LOWEST score speaks next: what did you see that made you score low?
- Others: does either account reflect evidence you had but hadn't shared?

**Two sources of disagreement to diagnose**:

| Source | Description | Resolution |
|---|---|---|
| Information gap | One member has data others don't | Share the information |
| Interpretation gap | Same data, different weighting | Acknowledge both as valid, flag for further diligence |

**Facilitator tracks**: For each dimension - was the disagreement an information gap or an interpretation gap?

| Dimension | Source of noise | Resolution |
|---|---|---|
| | [ ] Information  [ ] Interpretation | |
| | | |

### Step 3 - Updated individual scores (10 min, in writing)

After discussion: each member OPTIONALLY updates their score in writing.
No pressure to converge. Score what you believe, not what the group believes.

| Dimension | Updated score (if changed) | Why changed |
|---|:---:|---|
| | | |

### Step 4 - Residual noise check (5 min)

Re-run noise calculation on updated scores for the high-noise dimensions.
Did disagreement decrease (information gap resolved) or persist (genuine interpretation difference)?

---

## Phase 4 - Report (facilitator completes after session)

### Noise Audit Summary

**Target**: ___
**Committee size**: ___ members
**Date**: ___

**Headline**: The committee's judgment on this target has an overall noise level of **__% CV**.

| Result | Interpretation |
|---|---|
| CV < 15% | Strong consensus - proceed with confidence |
| CV 15-30% | Moderate noise - monitor flagged dimensions |
| CV 30-50% | High noise - committee not ready to decide. Resolve flagged dimensions first. |
| CV > 50% | Decision not available. The committee is in negotiation, not evaluation. |

**Dimensions requiring additional due diligence before decision**:
| Dimension | CV% | Information gap to resolve | Owner | Deadline |
|---|:---:|---|---|---|
| | | | | |

**Recommendation status**:
[ ] Ready to decide - noise acceptable, gaps resolved
[ ] Not ready - dimensions flagged, additional DD required
[ ] Fundamental disagreement - escalate or restructure evaluation

---

## What to do with this report

**If CV < 20% overall**: Present to board with confidence. Include noise report as evidence of process quality.

**If CV 20-35%**: Complete additional DD on flagged dimensions. Re-audit before final decision.

**If CV > 35%**: Do not present to board yet. The committee doesn't agree. A board presentation would
force a premature convergence that hides the real disagreement. Resolve first.

**For the calibration coach**: Record each member's prediction alongside their score. In 24 months,
re-evaluate: who was best calibrated? This data improves future committee decisions.

---

## Note on confidentiality

Individual scores in this report are anonymous to the committee.
The facilitator retains the attribution data for calibration purposes.
Aggregate noise results are shared with all members.
