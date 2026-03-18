---
name: proposal-builder
description: Generate comprehensive sales proposals based on discovery notes and meeting transcripts. Support for pricing options, testimonials, and legal terms. Trigger with "draft proposal", "create proposal for [Client]".
bundle: deal-execution
triggers:
  - "draft proposal"
  - "create proposal for [Client]"
  - "generate SOW"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# Skill: Proposal Builder

Turn discovery notes into a winning proposal.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Draft SOWs, Sales Decks, and One-Pagers                      │
│  ✓ Auto-include Legal Terms (IP, Payment, Liability)            │
│  ✓ Structure Pricing (Good/Better/Best)                         │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~google-drive)                          │
│  + Export to Google Doc or Slides                               │
│  + Pull verified testimonials from your case study database     │
└─────────────────────────────────────────────────────────────────┘
```

## 🧠 Core Philosophy

1.  **They don't care about you**: They care about their problem. Start there.
2.  **Options kill binary choices**: Always offer 3 options (Anchor, Target, Safety).
3.  **Clarity over Legalese**: Terms should be plain English (or French).

## 🛠 Agent Instructions

### Phase 1: Context Gathering

**Trigger**: "Draft proposal for [Client Name]."

**Actions**:

1.  **Read Context**:
    - `sales-profile.json` (Your services).
    - `data/1-Projets/prospects/[Client]/call-summary.md` (Their pain).
2.  **Determine Format**:
    - **SOW**: Defined project.
    - **Retainer**: Ongoing work.
    - **Pitch**: Selling the vision.

### Phase 2: The Build

**Actions**:

1.  **Executive Summary**: Restate their pain ("You are losing X because of Y").
2.  **The Solution**: Map your services to their pain.
3.  **Pricing Options**: Use `references/pricing-tables.md` to create 3 tiers.
    - _Option 1 (Basic)_: The "No Brainer".
    - _Option 2 (Standard)_: The "Target".
    - _Option 3 (Anchor)_: The "VIP/Done-For-You".
4.  **Legal Terms**: Append standard terms from `references/legal-snippets.md`.

### Phase 3: The Polish (Bilingual)

**Actions**:

1.  **Check Language**: `sales-profile.json`.
2.  **Translate**:
    - "Scope of Work" -> "Périmètre d'Intervention".
    - "Investment" -> "Budget / Investissement".
3.  **Antislop Check**: Ensure the summary isn't generated fluff.

## 📂 System Integration

- **Output**: Save to `data/1-Projets/prospects/[Client]/proposal-[Date].md`.
- **Pricing**: If `pricing-strategy` skill was used, pull the math from there.

## 📚 References

- `references/templates.md`: The structure (SOW, Pitch).
- `references/pricing-tables.md`: Visual ways to present money.
- `references/legal-snippets.md`: The fine print.
