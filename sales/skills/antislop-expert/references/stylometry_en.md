# Stylometry & Burstiness — Detecting Artificial Text

## Core Principle

Stylometry measures the invariants of a writing style. A human produces text with an irregular rhythm ("bursty"), while an LLM tends to smooth out sentence length around an average.

## Burstiness (Sentence Length Variance)

### Caclulation

```
variance = Σ(sentence_length_i - mean)² / (n - 1)
```

### Interpretation

| Variance | Diagnostic                                   |
| :------- | :------------------------------------------- |
| < 10     | Strong LLM signal: rhythm too regular        |
| 10–20    | Gray zone: could be technical or edited text |
| > 20     | Natural human rhythm                         |
| > 40     | Highly varied rhythm (oral, literary)        |

### Complementary Ratios

- **Short sentences** (< 6 words): Human text typically contains 10–20%. LLMs rarely drop below 8%.
- **Long sentences** (> 30 words): Humans produce these occasionally; LLMs either avoid them or produce them at a constant frequency.
- **Normalized Standard Deviation** (CV = σ/μ): CV > 0.5 is typical of human writing, < 0.3 is suspect.

## Other Stylometric Signals

### Lexical Diversity (TTR)

Type-Token Ratio = unique words / total words. A low TTR on a short text (< 500 words) is suspect.

### Zipf Distribution

Human texts follow Zipf's law imperfectly. LLMs follow it too perfectly (distribution too smooth).

### Lexical Entropy

Measures vocabulary unpredictability. Abnormally low entropy (very predictable vocabulary) is an LLM signal.

## Limitations

No single signal is sufficient on its own. Reliable detection requires a multi-signal diagnosis combining burstiness, lexicon, structure, and typography.
