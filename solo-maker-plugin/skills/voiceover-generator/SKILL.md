---
name: voiceover-generator
description: "Generates high-conversion scripts for product demos and ads. Includes prosody marks for TTS and tuning parameters. Triggered by 'voiceover script', 'audio narration', 'demo dialogue'."
bundle: video-media
triggers:
  - "voiceover script"
  - "audio narration"
  - "demo dialogue"
tools:
  standalone: [filesystem]
  supercharged: []
version: "2.1.0"
---

# Skill: Voiceover Generator

This skill is about "The Sound of Your Brand." It takes a technical `PRD.md` or a `DESIGN-BRIEF.md` and translates it into a narrative script that sounds human, empathetic, and persuasive when spoken aloud.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Scriptwriting Framework: Narrative Tension -> Payoff         │
│  ✓ Visual cues: Marks the script with [Frame 1], [Zoom] tags     │
│  ✓ Prosody markup: Uses (pause) and **emphasis** for TTS.       │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~audio / ElevenLabs / OpenAI)           │
│  + Audio Rendering: Auto-generate the .mp3 file using premium   │
│    voices like "Adam" or "Alloy."                               │
│  + Voice Cloning: Use a sample of the user's voice to generate   │
│    the narration for maximum brand authenticity.                │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠 Triggers

- "Draft a voiceover script for my [Project] demo"
- "I need a narration for this storyboard"
- "Write a script for a 60-second product ad"
- "How should I tune the ElevenLabs voice for this?"

---

## 📋 The Scripting Architecture

The agent writes for the _ear_, not the _eye_:

### 1. The Hook (0-10s)

_Focus_: Immediate empathy.  
_Example_: "We've all been there. You have a great idea, but the technical debt is holding you back..."

### 2. The Bridge (10-25s)

_Focus_: Transition from pain to possibility.  
_Example_: "What if you could bridge that gap without hiring a full team? Meet [Product Name]."

### 3. The Proof (25-50s)

_Focus_: Active verbs, simple steps.  
_Example_: "Simply drag your design, click 'Analyze', and watch as [Product] builds the foundation for you."

### 4. The Exit (50-60s)

_Focus_: Urgency and warmth.  
_Example_: "Stop waiting for 'Someday.' Build it today. [URL]."

---

## 🚀 Workflow

1.  **Identity Scan**: Read `voice-dna.json` for tone and `business-profile.json` for key terms.
2.  **Constraint Check**: Confirm the target length (15s, 30s, 60s, or 3-minute demo).
3.  **Drafting**: Write the first version with [SCREEN 1], [SCREEN 2] markers for the video editor.
4.  **Tuning**: Add (pacing notes) like `[Short Pause]`, `[Emphasis on 'Simply']`.
5.  **TTS Spec**: Provide a specific "Tuning Card" for engines (Stability: 0.5, Similarity: 0.75).
6.  **Output**: Save to `data/1-Projets/[Project]/prototype/script.md`.

---

## 📈 Agent Instructions

- **Write for Breath**: Use short sentences. Long compound sentences are hard for TTS (and humans) to deliver naturally.
- **Vary the Pacing**: High energy for the hook, steady for the proof, warm for the exit.
- **Output Template**:
  - The Narration Script (with timing markers).
  - The Prosody Version (for copy-pasting into ElevenLabs/OpenAI).
  - Audio Tuning Recommendations (Voice selection, settings).

---

## 📂 References

- [Voiceover Style Cheat Sheet](./references/style-guide.md)
- [How to write for TTS Engines](./references/tts-optimization.md)
- [Example Script: SaaS "Coming Soon" Ad](./examples/saas-ad.md)
