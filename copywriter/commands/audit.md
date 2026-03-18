---
description: "Run a Forensic Authenticity Audit on any text. Detects AI Slop and Corporate Jargon."
argument-hint: "[paste text or file path]"
allowed-tools: Read
model: haiku
---

# /copywriter:audit

The "Red Pen" for your content. Use this to sanitize AI-generated text or polish your own drafts.

## Usage

```bash
/copywriter:audit "Here is some text I wrote..."
/copywriter:audit data/1-Projets/drafts/my-post.md
```

## Workflow

1.  **Reads** the input text.
2.  **Loads** `data/2-Domaines/voice-dna.json` (to compare against your baseline).
3.  **Triggers** the `antislop-expert` skill.
4.  **Outputs** the "Slop Report":
    - 🚨 Slop Score (0-100)
    - 💀 Hall of Shame (List of worst words used)
    - ✨ Assessing "Humanity" (Texture check)
5.  **Offers** a Rewrite (Version A: Polish / Version B: Radical Humanization).
