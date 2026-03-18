# Structural Patterns of Artificial Text

## Triad Bias (Ternary Structure)

### Signal

LLMs have a strong tendency to structure content in groups of three: "three reasons", "three key benefits", "three steps". This pattern is rare in spontaneous human writing.

### Detection

- Explicit enumeration: "firstly / secondly / thirdly".
- Announced triads: "there are three reasons why...", "here are three key steps...".
- Bullet lists of exactly 3 items (recurring).

### Remediation

- Vary the number: use 2, 4, 5, or 7 points depending on the actual content.
- Remove the number announcement if it is arbitrary.
- Merge redundant points, expand on substantive ones.

## The "Sandwich" Pattern

### Signal

Structure: Vague opening → Content → Moralizing conclusion. Typical of LLMs that "frame" every argument.

### Detection

- Opening with a platitude: "in today's world...", "in the age of AI...".
- Closing with an empty exhortation: "it is essential to...", "in conclusion...", "looking ahead...".

### Remediation

- Delete the first sentence if it contains zero information.
- Replace the moralizing conclusion with a concrete implication or next step.
- Start directly with the fact or argument.

## Symmetric Enumeration

### Signal

Lists where items have almost identical word counts (± 5 words). Humans produce items of variable length.

### Remediation

- Expand important items, condense secondary ones.
- Convert to prose if the list does not aid readability.

## The "However" Pivot (Performative Balance)

### Signal

LLMs often structure arguments with "X is true. However, Y." where the "however" introduces a weak or artificial counterpoint to appear balanced.

### Remediation

- If the counterpoint is real, keep it but back it up with evidence.
- If it is purely formal, remove this false balance structure.

## Credible Argument Structure (Reference Model)

A credible human argument follows this schema:

1.  **Thesis**: Central idea stated precisely.
2.  **Mechanism**: The "how" or "why" — explicit causality.
3.  **Evidence**: Concrete example, data, real case.
4.  **Limit**: Counter-argument, exception, validity condition.
5.  **Implication**: Practical consequence — not an abstract moral.
