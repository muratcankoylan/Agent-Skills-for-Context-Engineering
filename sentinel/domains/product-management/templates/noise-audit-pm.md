# Noise Audit - Product Management Team

## Goal

Measure judgment variability within the product team on the same prioritization
and estimation decisions. If noise is high, the roadmap depends more on WHO is
in the room than on WHAT the data says.

Kahneman (Noise, 2021): "Professional judgments are far more variable than
people assume. The noise is often greater than the bias."

---

## Protocol - NON-NEGOTIABLE RULES

1. **Each participant answers ALONE, in writing, BEFORE any discussion**
2. **Submissions collected before anyone sees others' answers**
3. **No anchoring** - do not reveal any number before all are submitted
4. **PM lead / CPO submits LAST** - prevents authority anchoring
5. **The goal is to MEASURE noise, not to reach consensus during collection**
---


## Exercise 1: Feature Prioritization (100 points)

> "Distribute 100 points across the following features based on priority
> for this quarter's primary objective: [OBJECTIVE].
> Points represent engineering time/attention, not user value.
> Work alone. Do not discuss."

**Objective**: ________________________________

| Feature | P1 | P2 | P3 | P4 | P5 | Mean | SD | CV% |
|--------|----|----|----|----|----|----|----|----|
| | | | | | | | | |
| | | | | | | | | |
| | | | | | | | | |
| | | | | | | | | |
| | | | | | | | | |
| **Total** | 100 | 100 | 100 | 100 | 100 | | | |

```bash
timeout 10 python3 "$CLAUDE_PLUGIN_ROOT/skills/decision-hygiene/scripts/noise.py" --json '{"algorithm":"cv","data":[P1, P2, P3, P4, P5]}'
```

---

## Exercise 2: MAP Scoring - One Feature (6 dimensions)

For ONE key feature in the backlog, each participant scores independently.

**Feature evaluated**: ________________________________
**Scorer role**: (each participant writes their role, not their name - to reduce authority bias)

| Dimension | P1 | P2 | P3 | P4 | P5 | Mean | CV% |
|-----------|----|----|----|----|----|----|------|
| Evidence of user pain /10 | | | | | | | |
| Business impact /10 | | | | | | | |
| Effort accuracy /10 | | | | | | | |
| Strategic alignment /10 | | | | | | | |
| Reversibility /10 | | | | | | | |
| Opportunity cost /10 | | | | | | | |
| **Weighted score /10** | | | | | | | |

---

## Exercise 3: Estimation (effort and impact)

"For each feature below, estimate independently:"

| Feature | Metric | P1 | P2 | P3 | P4 | P5 | Mean | CV% |
|---------|--------|----|----|----|----|----|----|------|
| [Feature A] | Effort (weeks) | | | | | | | |
| [Feature A] | Impact on [metric] (%) | | | | | | | |
| [Feature B] | Effort (weeks) | | | | | | | |
| [Feature B] | Impact on [metric] (%) | | | | | | | |
| Any feature | Confidence in estimate (%) | | | | | | | |

---

## Noise interpretation

### CV thresholds for product decisions

- **CV < 20%**: Good alignment. The team has a shared model. Proceed.
- **CV 20-35%**: Moderate noise. Surface assumptions before committing.
  The team has the same data but different mental models.
- **CV > 35%**: High noise. The decision depends on who you ask.
  **Do not treat the majority view as ground truth.**
- **CV > 50% on estimation**: Nobody actually knows. This is scope risk.
  Do not commit. Spike first.

### When CV > 35%, ask:
1. "What specific data is each person basing their score on?"
2. "Do you share the same definition of [noisiest dimension]?"
3. "What would you need to see to change your score by 3 points?"

### Noise pattern diagnosis

- **Level noise** (one person systematically higher/lower):
  -> Different calibration. Not different information. Discuss baseline assumptions.
- **Pattern noise** (gaps vary by feature):
  -> Disagreements on specifics. Each feature needs its own investigation.
- **Occasion noise** (redo exercise 2 weeks later, scores change >20%):
  -> Judgment is unstable. Process is not reproducible. Add structure.

---

## Results dashboard

| Exercise | Overall avg CV% | Interpretation | Action |
|---------|:--------------:|----------------|--------|
| 1. Prioritization | | | |
| 2. MAP scoring | | | |
| 3. Estimation - effort | | | |
| 3. Estimation - impact | | | |

**Noisiest dimension overall**: _________________________

**Noisiest feature overall**: _________________________

**Biggest individual outlier** (role, not name): _________________________

---

## Post-audit actions

1. **Share results with full team** (transparency is step one)
2. **Discuss the noisiest dimension** - what assumptions differ?
3. **Clarify definitions** - write shared definitions for noisiest dimensions
4. **Redo Exercise 2** with clarified definitions - CV should drop 30-50%
5. **Schedule follow-up audit** in 6 months
6. **Track estimation accuracy** - compare estimates to actuals every quarter

---

## Estimation calibration tracking

| Feature | Estimated effort | Actual effort | Ratio | Estimated impact | Actual impact | Impact ratio |
|---------|-------------:|------------:|------:|---------------:|------------:|:------------|
| | | | | | | |
| | | | | | | |
| | | | | | | |
| **Average** | | | | | | |

**If effort ratio > 1.4 consistently** -> apply 40% correction to all future estimates.
**If impact ratio < 0.6 consistently** -> apply impact discount factor. Challenge all impact claims.

---

## Audit result

**Date**: _______________
**Participants**: _______
**Overall verdict**: LOW noise / MODERATE noise / HIGH noise

**Primary actions agreed**:
1.
2.
3.

**Follow-up audit scheduled for**: _______________
