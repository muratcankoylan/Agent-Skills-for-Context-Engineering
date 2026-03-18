---
name: newsletter-writer
description: Create intimate, high-retention email newsletters. Optimized for Open Rates, Click Rates, and "Reply" engagement. Trigger with "draft this week's newsletter", "write a welcome email", "turn this blog post into an email", or "give me subject lines".
model: sonnet
bundle: long-form-conversion
triggers:
  - "draft this weeks newsletter"
  - "write a welcome email"
  - "turn this blog into an email"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# Newsletter Writer (The Relationship Builder)

Email is the only algorithm you own. This skill treats the newsletter as a personal letter to a friend — designed to build trust, authority, and eventually, sales.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Subject Line Engineering: Optimization for Open Rates.       │
│  ✓ Personal Tone: Matches your {{voice_dna}} exactly.           │
│  ✓ Spam Check: Avoids "trigger words" that hurt deliverability. │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~email-platform)                        │
│  + Sequence Logic: Connects one-off emails to broader campaigns.│
│  + Dynamic Segmentation: Adjusts tone for "New" vs "Old" subs.  │
│  + Archive Search: References past editions to avoid repeats.   │
└─────────────────────────────────────────────────────────────────┘
```

## Triggers

- "Draft this week's newsletter about [Topic]"
- "Turn this blog post into an email"
- "Write a welcome email for new subscribers"
- "Give me 5 subject lines for..."

## Agent Instructions

### Before Writing

1. **Load Context Profiles**:
   - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/voice-dna.json` (Intimate/Casual or Professional?).
   - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/icp.json` (What are they struggling with today?).
   - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/business-profile.json` (What is the primary Offer?).
2. **Check Archive**: Search `${CLAUDE_PLUGIN_ROOT}/data/4-Archives/` to ensure no recent angle overlap.

### Define the Experience

- **From Name**: "Name from Company" (Human) vs "Company" (Brand).
- **Design Constraint**: Text-heavy (deliverability) vs Visual-heavy (brand).

## 3 Key Principles

1. **Write for One Person** — Visualize a specific reader. Write to *them*, not a "list". Use "You" not "Many of you".
2. **The You/I Ratio** — "You" > "I". Use "I" for stories/vulnerability. Use "You" for lessons/benefits.
3. **Spam Filter Discipline** — Avoid "Free", ALL CAPS, excessive `!`, and 50+ links per email.

Structure: Subject + Preview → Hook Lede → One Big Idea → CTA → P.S.

See `references/anatomy.md` for the full 5-part email anatomy, output format template, and deliverability checklist.
