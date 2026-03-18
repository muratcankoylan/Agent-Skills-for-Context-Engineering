---
name: quote-extractor
description: Mining engine for content. Extracts "Gold Nuggets", quotes, and shareable assets from long-form inputs (transcripts, essays).
model: sonnet
bundle: research-tools
triggers:
  - "extract quotes from this transcript"
  - "find gold nuggets"
  - "mine this content"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# Quote Extractor (The Gold Miner)

You can't write everything from scratch. This skill acts as a content refinery. It takes high-volume ore (hour-long podcasts, 5k word essays) and refines it into high-value gems (Tweets, Hooks, Pull Quotes).

```
┌─────────────────────────────────────────────────────────────────┐
│  CORE CAPABILITIES                                              │
│  ✓ "Mic Drop" Sentence Identification                           │
│  ✓ Thematic Clustering (Grouping insights by topic)             │
│  ✓ Platform-Ready Formatting (Instant Tweet/LinkedIn)           │
│  ✓ Impact Scoring (Viral Probability)                           │
├─────────────────────────────────────────────────────────────────┤
│  EXTRACTION TARGETS                                             │
│  1. The "Aha" Moment (Insight)                                  │
│  2. The "Contrarian Take" (Polarity)                            │
│  3. The "Universal Truth" (Resonance)                           │
│  4. The "Data Point" (Proof)                                    │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠 Context Configuration

### 1. Load Source Context

- **Source Material**: User input (Paste) or File Read.
- **Voice**: `voice-dna.json` (Ensure extracted quotes match the persona).

### 2. Define Output Goal

- **Repurposing**: "Turn this call into 10 Tweets."
- **Testimonial Mining**: "Find where they praised the product."
- **Summary**: "Find the 3 big ideas."

---

## 🏛 The Mining Process

### Phase 1: The Scan

Read the text. Look for _friction_ and _release_.

- Where does the speaker get passionate?
- Where is the "absolute" statement? ("Always", "Never").
- Where is the specific example?

### Phase 2: The Filter (The 1-10 Scale)

Grade potential quotes:

- **1-5**: Generic. "Business is hard." (Discard).
- **6-8**: Good. "Business is hard because people lie." (Keep).
- **9-10**: Great. "Business is the art of solving problems for people who lie to you." (Gold).

### Phase 3: The Polish

Raw transcripts are messy. Polishing is required but _dangerous_.

- _Rule_: Fix grammar, but keep the rhythm.
- _Rule_: Do not change the meaning.
- _Rule_: Remove filler words ("Um", "Like", "You know").

### Phase 4: Platform Mapping

- **Short/Punchy** -> Twitter.
- **Deep/Insightful** -> LinkedIn.
- **Emotional/Story** -> Newsletter P.S.

---

## 📝 Output Format

Deliver a structured "Asset Table".

```markdown
# 💎 Content Mining Report

**Source**: [Filename/Description]
**Yield**: [X] Gold Nuggets

## 🏆 The "Top 5" (Highest Viral Potential)

### 1. The Contrarian Hook

> "Most people optimize for money. I optimize for stress. Money is infinite; cortisol kills you."

- **Impact Score**: 9.5/10
- **Best For**: Twitter Thread Hook
- **Draft**: _Most founders die rich and stressed. I chose a different path..._

### 2. The Definition

> "Product Market Fit is when the market pulls the product out of your hands faster than you can build it."

- **Impact Score**: 8/10
- **Best For**: LinkedIn Quote Card
- **Visual**: Text overlay on black background.

...

## 📂 Thematic Clusters

### On Hiring

- "Hire for slope, not intercept."
- "Fire fast, hire slow is a lie. Fire fast, hire faster."

### On Pricing

- "Charge more. It filters out the bad clients."
- "Price is a proxy for quality."

## 🚀 Execution Plan

1. Turn Quote #1 into a Twitter Thread (use `twitter-thread`).
2. Turn Quote #2 into a LinkedIn Image (Canva).
3. Use "On Pricing" cluster for next Newsletter.
```

## 🧠 Advanced Tactics

- **The "Remix"**: Take a quote and disagree with it. "I said this 2 years ago. I was wrong."
- **The "Expansion"**: "This one sentence is a whole book." Expand it using `thought-leadership`.
