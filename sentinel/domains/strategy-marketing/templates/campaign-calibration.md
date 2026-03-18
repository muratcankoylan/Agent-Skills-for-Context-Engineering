# Campaign Calibration - Prediction Tracker

## Goal
Track your marketing performance predictions to improve calibration over
time. Tetlock (2015): without feedback, judgment doesn't improve.

---

## Active predictions

| # | Date | Campaign / Initiative | Prediction | Confidence | Review date | Result | Brier |
|---|------|----------------------|------------|------------|-------------|--------|-------|
| 1 | | | | % | | | |
| 2 | | | | % | | | |
| 3 | | | | % | | | |
| 4 | | | | % | | | |
| 5 | | | | % | | | |
---


## Resolved predictions

| # | Prediction | Confidence | Result | Gap | Brier |
|---|------------|------------|--------|-----|-------|
| | | | | | |

**Average Brier score**: ___ (0 = perfect, 0.25 = chance, 0.5 = useless)

---

## Patterns identified

### By domain
| Prediction type | N | Avg Brier | Tendency |
|----------------|---|-----------|----------|
| Timelines / deadlines | | | Optimistic / Realistic / Pessimistic |
| Quantitative KPIs (leads, revenue) | | | |
| Audience adoption / engagement | | | |
| Budget / costs | | | |

### Calibration curve
| Stated confidence | Actual hit rate | Gap |
|-------------------|-----------------|-----|
| 90%+ | | |
| 70-89% | | |
| 50-69% | | |
| <50% | | |

**Good calibration**: 80% confidence -> happens ~80% of the time.
**Overconfidence**: 80% stated -> 50% actual.
**Underconfidence**: 50% stated -> 80% actual.

---

## Sentinel recommendation

Based on your patterns:

**Your main bias**:
**Recommended adjustment**:
**Example**: "When you predict at 80% confidence, treat it as
___% until your calibration improves."

---

## Compute

```bash
timeout 15 python3 "$CLAUDE_PLUGIN_ROOT/skills/decision-hygiene/scripts/calibration.py" --ledger "$CLAUDE_PLUGIN_ROOT/data/decision-ledger.json"
```
