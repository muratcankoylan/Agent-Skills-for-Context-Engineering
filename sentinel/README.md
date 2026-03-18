# Sentinel v8 - Decision Hygiene Protocol

## What it does

Sentinel forces structured thinking when you're deciding under pressure.
It doesn't detect biases - it asks the questions you'd skip.

Three core mechanisms, each backed by research:

1. **MAP scoring** (Kahneman, *Noise*, 2021) - Breaks your decision into
   independent dimensions, scores each separately, distinguishes what you
   know from what you're guessing. This is choice architecture: it makes
   halo effect mechanically impossible.

2. **Pre-mortem** (Klein, 2007; Veinott et al., 2010) - Imagines your plan
   has failed and works backward. Empirically reduces overconfidence more
   than pro/cons or standard critique. Increases risk identification by ~30%.

3. **Calibration tracking** (Tetlock, *Superforecasting*, 2015) - Records
   your predictions with confidence levels, then measures how accurate you
   actually are. Without feedback, judgment doesn't improve.

## What it doesn't do

Sentinel uses a language model. LLMs exhibit cognitive biases themselves
(Echterhoff et al., EMNLP 2024; Malberg et al., 2025). This tool is a
structured thinking partner, not an infallible scanner. The value is in
the STRUCTURE it forces, not in "detecting" things.

## Architecture

- **7 agents**: questioner, structure-builder, reality-checker, failure-finder,
  noise-calculator, logic-tester, calibration-coach
- **5 commands**: /sentinel, /sentinel-diverge, /sentinel-reframe,
  /sentinel-review, /sentinel-setup
- **4 Python scripts**: triage, noise, calibration, inhibition
- **2 reference catalogs**: 35 biases, 31 fallacies
- **2 domain packs**: hiring, product management
- **6 templates**: decision record, pre-mortem, dual-frame, etc.

## Key design choice

Previous versions (v1-v7.1) centered on bias detection: scan -> label -> score.
v8 centers on choice architecture: structure -> questions -> pre-mortem.

The research says choice architecture works better than debiasing-by-information
(Fasolo et al., 2024). Asking "would you make this decision if you hadn't
already spent the money?" beats "SUNK_COST detected, severity CRITICAL."

## Usage

Describe a decision. Sentinel handles the rest.

```
/sentinel Should I accept this acquisition offer?
/sentinel-diverge I'm stuck between two options
/sentinel-reframe How do I convince the board?
/sentinel-review How are my past predictions doing?
```

## Changes from v7.1

- Bias scanner -> Questioner (questions, not diagnoses)
- Outside view -> Reality checker (honest about what it knows vs guesses)
- Structured evaluator -> Structure builder (MAP is now the CENTER)
- Removed fake interaction multipliers (x1.8, x2.0 without empirical basis)
- Inhibition check integrated into MAP (structure IS the inhibition)
- Honest limitation disclaimer built into the protocol
- 44 files -> 41 files (removed redundant agents, kept substance)
