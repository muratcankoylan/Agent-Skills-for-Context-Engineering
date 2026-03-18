---
name: sales-email-sequence
description: Create high-converting email sequences (Welcome, Launch, Nurture). Focuses on psychological progression and authentic selling.
model: sonnet
bundle: long-form-conversion
triggers:
  - "create email sequence"
  - "welcome sequence"
  - "launch email sequence"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# Sales Email Sequence Creator (The Closer)

We don't "blast" emails. We engineer "conversion conversations". This skill builds sequences that move `{{icp.avatar}}` from "Who are you?" to "Take my money".

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Psychological Arcs: Soap Opera, PLF, & Nurture logic.        │
│  ✓ Objection Handling: Pre-empts "Price" and "Time" concerns.   │
│  ✓ Open Loop Engineering: Keeps them reading Day 1 to Day 5.    │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~gmail / ConvertKit)                    │
│  + Dynamic Personalization: Injects specific User Data points.  │
│  + AB Test Generation: Creates Subject Line variants to test.   │
│  + Draft Injection: Pushes drafts directly to your ESP.         │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠 Triggers

- "Write a 5-day welcome sequence"
- "Create a launch sequence for [Product]"
- "Write a re-engagement email for dead leads"
- "Draft an abandoned cart recovery series"

## 🛠 Agent Instructions

### Before Writing

1.  **Load Context Profiles**:
    - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/business-profile.json` for Offer details (Price, Guarantee).
    - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/icp.json` for Pain Points and Objections.
    - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/voice-dna.json` for Email Style (Casual vs Professional).
2.  **Check Past Sequences**:
    - Search `${CLAUDE_PLUGIN_ROOT}/data/4-Archives/` to avoid repeating previous campaigns.

---

## 🏛 The Email Architecture

### Phase 1: The Trust Bridge (Email 1-2)

_Goal: Indoctrination._

- **Email 1**: Deliver the lead magnet. Set expectations.
- **Email 2**: Origin Story. "Why I started `{{business.company_name}}`."

### Phase 2: The Logic Bridge (Email 3-4)

_Goal: Shift Beliefs._

- **Email 3**: The Epiphany. "I used to think X, but realized Y."
- **Email 4**: The Hidden Enemy. "It's not your fault you failed at `{{icp.goal}}`."

### Phase 3: The Sale (Email 5+)

_Goal: Conversion._

- **Email 5**: The Offer. Direct pitch for `{{business.primary_offer}}`.
- **Email 6**: Logic + Guarantee (`{{business.guarantee}}`).
- **Email 7**: Scarcity.

---

## ✍️ Writing Guidelines

### 1. The P.S. Strategy

- _Use it to_: Restate the link to `{{business.primary_offer_url}}`.
- _Use it to_: Add a testimonial.

### 2. Mobile First

- Subject line < 40 chars.
- Preview text must support the subject.

---

## 📝 Output Format

```markdown
# Sequence Draft: [Sequence Name]

## 🏗 Sequence Overview

- **Trigger**: New Lead
- **Goal**: Sell {{business.primary_offer}}
- **Length**: 5 Days

---

## 📧 Email 1: Day 0 (Immediate)

**Subject**: [Hook addressing {{icp.pain_points}}]
**Preview**: + The one thing nobody tells you.

**Body**:
Hey [Name],

Here is the link to use:
[LINK]

But before you go...

---
```
