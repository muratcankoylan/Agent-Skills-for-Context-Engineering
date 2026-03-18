---
description: "Create High-Authority Content"
argument-hint: "[post | carousel | asset]"
allowed-tools: Read, Write, Glob
model: sonnet
---

# /sales:create

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

The **Creator** builds "Save-Worthy Assets" that position you as an authority. It merges **Solo Content Intelligence** (Hooks, Formatting, Carousels) with **Sales DNA** (Pain points, Methodology).

It supports **Bilingual Generation** (English/French) based on your profile settings.

---

## Usage

```
/sales:create post "Why cold calling is dead"   # Text Post
/sales:create carousel "The 10-step Sales Playbook" # PDF Carousel
/sales:create asset "Objection Handling Cheatsheet" # Downloadable Lead Magnet
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                    LINKEDIN CREATOR                               │
├──────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                        │
│  ✓ Hook Engineering: Scroll-stopping first lines (Hook Library)  │
│  ✓ Retention Architecture: Carousel & post structuring           │
│  ✓ Voice Calibration: Writes like you, not AI                    │
│  ✓ Anti-Slop: Auto-removal of banned words (delve, tapestry)     │
├──────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                       │
│  + ~~design (Canva/Figma): Auto-generate carousel visuals        │
│  + ~~browser: Auto-schedule posts for best engagement times      │
│  + ~~knowledge: Pull case studies from your diverse docs         │
└──────────────────────────────────────────────────────────────────┘
```

---

## /sales:create carousel "[TOPIC]"

Generates a 10-slide "Retention Architecture" script.

### Output Example

```markdown
CAROUSEL SCRIPT — Topic: "The 10-Step Sales Playbook"

Slide 1 (Cover)

- Headline: "Stop Losing Deals You Should Have Won"
- Subhead: "The 10-Step Playbook used by Top 1% Reps"
- Visual: [Stark contrast, big bold text]

Slide 2 (The Stakes)

- Text: "Most reps think they lose deals at the close."
- Text: "They're wrong. You lost it at 'Hello'."
- Visual: [Iceberg graphic]

Slide 3 (The Guide)

- Text: "I audited 500+ discovery calls."
- Text: "Here is the exact pattern of the winners:"

...

Slide 10 (CTA)

- Text: "I turned this into a printable checklist."
- Text: "Repost and comment 'WINNER' to get it."
- Visual: [Photo of the printed checklist]

DESIGN INSTRUCTIONS:

- Font: Inter Tight (Bold)
- Colors: Black & Yellow (High Contrast)
- Safe Zone: Keep text centered (Mobile crop protection)
```

---

## /sales:create post "[TOPIC]"

Generates a text post optimized for Dwell Time.

### Output Example

```markdown
"I'll just send you a proposal."

This sentence loses more deals than "Your price is too high."

When you send a proposal without reviewing it live:

1. You lose control of the narrative.
2. They skip to the price page.
3. You become a commodity.

Stop emailing proposals.

Instead, book a 15-min "Pricing Review".
Walk them through the value.
Handle objections in real-time.

If they refuse the call?
They weren't going to buy anyway.

#sales #closing #meddic
```

---

## Agent Instructions

### Hook Engineering

```python
def generate_hook(topic, style="Contrarian"):
    hooks = load_library("../copywriter/skills/linkedin-post/references/hook-library.md")

    if style == "Contrarian":
        template = "Most people think {X}. The truth is {Y}."
    elif style == "Story":
        template = "I lost {Amount} doing {Mistake}. Here's how I fixed it."

    return fill_template(template, topic)
```

### Antislop Verification

Before outputting ANY content, the agent runs:

1.  **Check**: Does it contain "delve", "tapestry", "leveraging", "unlock"?
2.  **Check**: Is the first paragraph < 3 lines?
3.  **Check**: Are there emojis in every sentence? (If yes, REMOVE them).

### Bilingual Logic

If `sales-profile.json` says "French":

- Translates concepts, NOT words.
- Uses cultural equivalents (e.g., "CAC 40" instead of "Fortune 500").
- Maintains the "Punchy" formatting (French tends to be wordier; we compress it).

---

## Tips

1.  **The "Meat" Rule**: If your post doesn't teach something specific, delete it. No fluff.
2.  **Comment-to-Win**: The CTA (Call to Action) should drive comments ("Agree?", "Your thoughts?"). Comments = Reach.
3.  **Formatting**: Use "white space" liberally. Mobile users hate walls of text.

---

## Skills Used

- `linkedin-creator` — Content generation.
- `antislop-expert` — Quality assurance.
- `voice-dna-creator` — Style matching.
