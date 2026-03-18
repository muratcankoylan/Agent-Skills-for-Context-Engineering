---
name: decision-hygiene
description: Base decision hygiene skill. Provides triage scripts, noise measurement, calibration scoring, and reference catalogs (bias, fallacy, heuristic). Used by all Sentinel agents.
bundle: core-decision
triggers:
  - "decision hygiene"
  - "noise audit"
  - "triage this decision"
  - "calibration check"
  - "bias catalog"
tools:
  standalone: [filesystem]
  supercharged: []
---

# Decision Hygiene Skill

## What this skill provides

Scripts for deterministic computation that Claude cannot do reliably:
- **triage.py** - Scores decision complexity, routes to appropriate protocol
- **noise.py** - Measures judgment variance (CV, IQR, divergence)
- **calibration.py** - Brier scores and calibration analysis
- **inhibition.py** - Heuristic appropriateness scoring (auxiliary)

## Reference catalogs
- bias-catalog.yaml - 35 cognitive biases with detection QUESTIONS
- fallacy-catalog.yaml - 31 logical fallacies with structural patterns
- heuristic-patterns.yaml - Common heuristic activations

## Usage
Scripts are called by agents (noise-calculator, calibration-coach) via Bash.
Catalogs are read by agents (questioner, logic-tester) for structured lookups.

## Important note on catalogs
The `interaction_multipliers` in bias-catalog.yaml are design parameters,
NOT empirical values. They indicate relative severity, not measured effects.
