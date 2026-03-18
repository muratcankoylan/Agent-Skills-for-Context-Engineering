---
name: voice-dna-creator
description: >
  Analyze writing samples to create a comprehensive voice DNA profile. Trigger with "create my voice DNA", "analyze my writing style", "set up my voice profile", or "profile my writing".
model: sonnet
bundle: identity-core
triggers:
  - "create my voice DNA"
  - "analyze my writing style"
  - "profile my writing"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# Voice DNA Creator

Analyze writing samples to extract and codify a unique voice profile that AI can use to replicate your authentic writing style.

## Output Instructions

1. After analysis, present key findings in a summary
2. Generate the complete JSON voice profile
3. Save to `data/2-Domaines/voice-dna.json`
4. Provide 3 example sentences written in the captured voice for validation
5. Ask: "Does this capture your voice? What would you adjust?"

## JSON Structure

```json
{
  "voice_dna": {
    "version": "1.0",
    "last_updated": "YYYY-MM-DD",
    "core_essence": {
      "identity": "",
      "primary_role": "",
      "unique_angle": ""
    },
    "personality_traits": {
      "primary": [],
      "how_it_shows": {}
    },
    "emotional_palette": {
      "dominant_emotions": [],
      "emotional_range": {},
      "energy_level": ""
    },
    "communication_style": {
      "formality": "",
      "complexity": "",
      "sentence_structure": {},
      "paragraph_style": ""
    },
    "language_patterns": {
      "signature_phrases": [],
      "power_words": [],
      "words_to_avoid": [],
      "transitions": []
    },
    "never_say": {
      "phrases": [],
      "tones": [],
      "approaches": []
    },
    "formatting_preferences": {},
    "content_philosophy": {},
    "voice_examples": {
      "opening_lines": [],
      "closing_lines": [],
      "transitional_phrases": []
    }
  }
}
```

## Review Process

- Check for "AI voice" (e.g. "delve", "tapestry") in the analysis itself.
- Ensure the extracted voice is AUTHENTIC and HUMAN.
