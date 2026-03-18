---
name: voice-dna-creator
description: "Analyzes writing samples to create a comprehensive Voice DNA profile. Use when a user wants to capture their unique writing voice for AI content generation."
bundle: core-identity
triggers:
  - "create voice DNA"
  - "analyze my writing style"
  - "build my voice profile"
tools:
  standalone: ["filesystem"]
  supercharged: ["knowledge-base"]
---

# Skill: Voice DNA Creator

This skill analyzes writing samples to extract and codify a unique voice profile that the AI can use to replicate an authentic writing style.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Paste 3-5 writing samples for voice analysis                 │
│  ✓ Extracts personality, tone, language patterns, formatting    │
│  ✓ Saves voice-dna.json to data/2-Domaines/                    │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~social)                                │
│  + Auto-pull recent LinkedIn/Twitter posts for analysis         │
│  + Larger sample size = more accurate voice profile             │
│  + Track voice evolution over time                              │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

The user needs to provide writing samples:
-   **Minimum**: 3 samples (500+ words each).
-   **Ideal**: 5-10 samples of varied types (e.g., blog posts, social media, emails).

## 🛠 Agent Instructions

1.  **Mode Selection**: Ask the user if they want to provide samples manually (Standalone) or connect a social media account (Supercharged).
2.  **Sample Collection**:
    -   If Standalone, ask the user to paste their writing samples.
    -   If Supercharged, use the connected `~~social` MCP to fetch the user's recent posts.
3.  **Analysis**: Analyze the samples for the following core elements:
    -   Personality markers (energy level, relationship to the reader).
    -   Emotional range (dominant tone, intensity).
    -   Communication style (formality, sentence structure).
    -   Language patterns (signature phrases, power words).
    -   Formatting habits (emojis, lists, bold/italics).
4.  **Synthesis & Generation**: Combine the observations to create the final JSON profile.
5.  **Save Location**: Save the final JSON as `voice-dna.json` in the `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/` directory.
6.  **Validation**:
    -   Present the key findings in a summary.
    -   Provide 3 example sentences written in the generated "voice".
    -   Ask the user: "Does this capture your voice well? What would you like to adjust?"

> [!TIP]
> If you see unfamiliar placeholders like `~~social`, see `CONNECTORS.md` to learn how to connect your tools.