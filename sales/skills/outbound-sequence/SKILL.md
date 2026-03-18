---
name: outbound-sequence
description: designs and drafts a multi-step outbound sequence (Email, LinkedIn, Call). Trigger with "create sequence for [Persona]", "draft outbound campaign".
bundle: prospecting
triggers:
  - "create sequence for [Persona]"
  - "draft outbound campaign"
tools:
  standalone: [filesystem]
  supercharged: [exa]
version: 1.0.0
---

# Skill: Outbound Sequence Architect

Don't just write one email. Build a multi-channel campaign that converts.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Design 5-15 step sequences (Aggeggio, Spears, The Breakup)   │
│  ✓ Draft emails, LinkedIn messages, and call scripts            │
│  ✓ Auto-adapt tone to Voice DNA                                 │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~lemlist / ~~smartlead)                 │
│  + Export sequence directly to sending tool                     │
│  + A/B test subject lines automatically                         │
└─────────────────────────────────────────────────────────────────┘
```

## 🧠 Core Philosophy

1.  **Pattern Interrupt**: If you sound like everyone else, you're deleted.
2.  **Multi-Channel**: Email + LinkedIn + Phone = 3x conversion.
3.  **Value-First**: "Give" before you "Ask".

## 🛠 Agent Instructions

### Phase 1: Strategy Design

**Trigger**: "Create a sequence for HR Directors."

**Actions**:

1.  **Analyze Persona**: Check `icp.json`. What keeps them up at night?
2.  **Select Blueprint**: Use `references/blueprints.md`.
    - **Aggeggio**: 3-step value-heavy sequence.
    - **Spears**: Short, punchy, curiosity-driven.
    - **Omni**: Full 15-day assault.

### Phase 2: Drafting

**Actions**:

1.  **Draft Emails**: Use `references/email-templates.md`.
    - _Subject Lines_: Short (1-3 words), lowercase, boring (e.g., "hiring thoughts").
    - _Body_: Problem-Agitate-Solve structure.
2.  **Draft Social**: Use `references/social-scripts.md`.
    - _Connection Request_: Blank or context-only (no pitch).
    - _Voice Note_: Script for a 30s personalized audio.

### Phase 3: Review & Polish (Bilingual)

**Actions**:

1.  **Check Language**: `sales-profile.json`.
2.  **Antislop Scan**: Run `antislop-expert` logic on every draft.
    - _Kill List_: "Hope this finds you well", "I wanted to reach out", "Synergy".

## 📂 System Integration

- **Output**: Save as `data/1-Projets/campaigns/[CampaignName].md`.
- **References**:
  - `blueprints.md`: The architecture.
  - `email-templates.md`: The copy.

## 📚 References

- `references/blueprints.md`: The architecture.
- `references/email-templates.md`: The copy.
- `references/social-scripts.md`: The DMs.
