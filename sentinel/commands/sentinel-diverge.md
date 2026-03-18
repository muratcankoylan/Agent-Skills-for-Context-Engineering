---
name: sentinel-diverge
description: >
  Generate diverse perspectives BEFORE evaluating. Used when the user is
  stuck in a narrow frame. 5-7 perspectives from different stakeholders,
  timeframes, or value systems. Then optionally feeds into /sentinel.
allowed-tools: None
model: sonnet
---


<example>
user: "/sentinel-diverge Should we open a Paris office?"
assistant: "[Generates perspectives: CFO view, remote employees, Paris clients, 5-year future self, competitor watching, new hire in Paris, regulatory lens]"
</example>

# /sentinel-diverge - Expand Before You Evaluate

## When to use
- "I only see two options"
- "What am I missing?"
- The decision feels binary when it shouldn't be

## Method
1. Generate 5-7 perspectives from DIFFERENT viewpoints
2. Each perspective must offer a genuinely different framing
3. Map conflicts between perspectives
4. Ask: "Which of these perspectives haven't you considered?"
5. Offer to run /sentinel on the expanded option set

## Perspective types
- Different stakeholders (CEO, junior dev, customer, investor)
- Different timeframes (next week vs next year vs 5 years)
- Different values (growth, stability, team happiness, customer impact)
- Inverse framing (what if you did the opposite?)

## Language
Respond in the user's language.
