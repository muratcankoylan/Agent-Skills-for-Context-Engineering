---
name: positioning-statement
description: "Craft authoritative positioning statements using multiple frameworks (Geoffrey Moore, April Dunford, StoryBrand). Triggered by 'positioning', 'value prop', 'USP', 'differentiation'."
version: "2.1.0"
bundle: core-identity
triggers:
  - "create positioning statement"
  - "craft my positioning"
  - "positioning for"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Positioning Statement

This skill helps you occupy a specific, valuable "category" in your customer's mind. It moves you from "just another freelancer/commodity" to "the only logical choice for [Niche]."

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ 3-Framework Generator (Moore, Dunford, StoryBrand)           │
│  ✓ Category Design logic to frame yourself as "The Only"        │
│  ✓ Emotional vs. Rational positioning analysis                  │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~search)                                │
│  + Competitor Positioning Audit: Compare your statement vs.     │
│    real-world competitors found on Google/Exa.                  │
│  + Blue Ocean Analysis: Identify gaps in current market messaging│
└─────────────────────────────────────────────────────────────────┘
```

## 🛠 Triggers

- "I need a positioning statement"
- "How do I describe what I do uniquely?"
- "Draft my elevator pitch"
- "What is my unique selling proposition (USP)?"

---

## 📋 Frameworks & Templates

The agent will offer the user 3 distinct ways to frame their business:

### 1. The Classic (Geoffrey Moore)

_Best for: B2B services and products in a defined category._

> **For** [Target Customer] **who** [Statement of the Need/Opportunity], **the** [Product Name] **is a** [Product Category] **that** [Statement of Key Benefit]. **Unlike** [Primary Competitive Alternative], **our solution** [Statement of Primary Differentiation].

### 2. The Context Shifter (April Dunford / Category Design)

_Best for: Innovative solutions that don't fit a standard category._

> **Category:** We provide [Defined Category]  
> **Value:** That helps [Specific Audience] achieve [Transformative Result]  
> **Differentiation:** By focusing uniquely on [Your Secret Sauce/Point of View]  
> **Enemy:** Preventing the struggle of [The Old Way/Status Quo]

### 3. The Narrative/Hero's Journey (StoryBrand)

_Best for: Consumer-facing brands or high-trust consulting._

> **The Problem:** [Customer] has a problem of [External/Internal/Philosophical].  
> **The Guide:** They meet [Your Brand] who has empathy and authority.  
> **The Plan:** We give them [A Simple 3-Step Process].  
> **The Success:** Resulting in [Success/Happy Ending] and avoiding [Failure/Tragedy].

---

## 🚀 Workflow

1.  **Context Pull**: Read `business-profile.json` and `icp.json` (if they exist).
2.  **Input Gap Analysis**: Ask for the "Missing Piece" (usually the "Unique Mechanism" or the "Enemy/Status Quo").
3.  **Drafting**: Provide 3 drafts (one for each framework above).
4.  **The "So What?" Test**: Challenge the drafts. If a competitor could say the same thing, it fails. Refine until "The Only" is clear.
5.  **Output**: Save to `data/2-Domaines/positioning.md`.

---

## 📈 Agent Instructions

- **Analyze first**: Don't just fill in blanks. Analyze the competitive landscape (if `~~search` is available) to ensure the differentiation isn't just "We're better/cheaper."
- **Niche Down**: If the audience is too broad ("small businesses"), push the user to specify (e.g., "Agile SaaS startups with 10-20 employees").
- **Tone Check**: Ensure the positioning reflects the business's `voice-dna`.
- **Output Template**:
  - Summary Board (ASCII)
  - The 3 Framework Versions
  - The "Elevator Pitch" (1-sentence version)
  - The "One-Word Association" (What single word do you want to own?)

---

## 📂 References

- [Positioning Examples](./references/examples.md)
- [Framework Workbook](./references/workbook.md)
- [Category Design Guide](./references/category-design.md)
