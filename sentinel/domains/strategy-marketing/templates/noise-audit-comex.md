# Noise Audit - Leadership Team

## Goal
Measure judgment variability within the team on the same strategic decisions.
If noise is high, your decisions depend more on WHO is in the room than on
WHAT is decided.

---

## Protocol

### NON-NEGOTIABLE RULES
1. Each participant answers ALONE, WITHOUT discussing
2. Responses collected BEFORE any discussion
3. Nobody sees others' responses until pooling
4. Leader/CMO submits LAST (avoids sunflower bias)
---


## Exercise 1: Budget Allocation (100 points)

"Distribute 100 points across the following channels/initiatives based on
importance for the primary business objective."

| Channel | P1 | P2 | P3 | P4 | P5 | Mean | SD | CV% |
|---------|----|----|----|----|----|-----------:|-----------:|----:|
| | | | | | | | | |
| | | | | | | | | |
| | | | | | | | | |
| **Total** | 100 | 100 | 100 | 100 | 100 | | | |

```bash
timeout 10 python3 "$CLAUDE_PLUGIN_ROOT/skills/decision-hygiene/scripts/noise.py" --json '{"algorithm":"cv","data":[P1, P2, P3, ...]}'
```

---

## Exercise 2: Initiative MAP Scoring (6 dimensions)

For ONE key initiative, each participant scores independently.

**Initiative evaluated**: ________________________________

| Dimension | P1 | P2 | P3 | P4 | P5 | Mean | CV% |
|-----------|----|----|----|----|----|----|----:|
| Business impact | | | | | | | |
| Total cost | | | | | | | |
| Audience alignment | | | | | | | |
| Differentiation | | | | | | | |
| Executability | | | | | | | |
| Reversibility | | | | | | | |

---

## Exercise 3: KPI Prediction

"What result do you expect from [initiative X] in 6 months?"

| Metric | P1 | P2 | P3 | P4 | P5 | Mean | CV% |
|--------|----|----|----|----|----|----|----:|
| Leads generated | | | | | | | |
| Pipeline $ | | | | | | | |
| Expected CAC | | | | | | | |
| Time to result (weeks) | | | | | | | |

---

## Noise Interpretation

- **CV < 15%**: Reasonable agreement. Team is aligned.
- **CV 15-30%**: Moderate noise. Discuss assumptions.
- **CV > 30%**: High noise. Decision depends on who's in the room. Structure judgment first.

### When CV > 30%, ask:
1. "What information is each person basing their score on?"
2. "Do you have the same definition of [dimension]?"
3. "Do you have access to the same data?"

---

## Post-audit actions

1. **Share results** (transparency = first step)
2. **Discuss biggest gaps** (> 20 points)
3. **Clarify definitions** for noisiest dimensions
4. **Redo exercise** with clarified definitions
5. **Measure improvement** (CV should drop 30-50%)
6. **Schedule follow-up** in 6 months

---

## Result

**Overall average CV**: ___% -> ___________
**Noisiest dimensions**:
1.
2.
**Main noise source**:
**Actions decided**:
