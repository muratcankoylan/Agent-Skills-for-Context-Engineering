---
name: hiring-hygiene
description: >
  Decision hygiene for recruitment and hiring. Adds domain-specific biases
  (Halo Effect, Similarity Bias, Contrast Effect) and structured interview
  templates. Auto-loads when the decision context involves candidates,
  interviews, recruitment, talent evaluation, or hiring.
bundle: domain-hygiene
triggers:
  - "hiring decision"
  - "interview bias"
  - "evaluate candidate"
  - "recruitment"
  - "talent evaluation"
tools:
  standalone: [filesystem]
  supercharged: []
---


# Hiring Decision Hygiene

## Domain-specific biases

Load additional biases from: ${SKILL_DIR}/biases.yaml

These biases are checked WITH EQUAL SEVERITY to the core 35 biases:

- **Halo Effect (H1)**: One positive trait (prestigious university, impressive
  company) influences overall perception across unrelated dimensions
- **Similarity Bias (H2)**: Favoring candidates who share traits, background,
  or hobbies with the interviewer
- **Contrast Effect (H3)**: Evaluating a candidate relative to the previous
  one rather than against absolute standards

## Frameworks

Load evaluation frameworks from: ${SKILL_DIR}/frameworks.yaml

- **Structured Interview**: Same questions, defined rubric, independent scoring
  before panel discussion. 1-5 scale per dimension.
- **Cultural Add vs Fit**: Shift from "culture fit" (similarity) to "culture add"
  (what new perspective does this person bring?)

## Default evaluation dimensions for candidates

When evaluating candidates using MAP protocol, use these independent dimensions:

1. **Skill Match** (technical/functional competence for the role)
2. **Cultural Alignment** (shared values, NOT personality similarity)
3. **Relevant Experience** (track record in comparable contexts)
4. **Growth Potential** (learning velocity, adaptability)
5. **Team Complementarity** (what's MISSING in the current team, not similarity)

## Key principle

Score each dimension INDEPENDENTLY before discussing with other interviewers.
This is the core MAP insight applied to hiring: independent evaluation prevents
the halo effect from contaminating scores across dimensions.

## Templates

- Structured interview scorecard: ${SKILL_DIR}/templates/candidate-scorecard.md
- Interview calibration guide: ${SKILL_DIR}/templates/interview-calibration.md
