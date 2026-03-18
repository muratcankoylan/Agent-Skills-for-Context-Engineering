---
name: video-script-generator
description: Create retention-focused video scripts for YouTube, TikTok, and Reels. Optimized for "Watch Time" and Algorithm Hooks.
model: sonnet
bundle: social-content
triggers:
  - "write a video script"
  - "YouTube script"
  - "TikTok script"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# Video Script Generator (The Director)

Video is not about words; it is about _visual retention_. This skill writes scripts that account for what the user _sees_, not just what the host _says_.

```
┌─────────────────────────────────────────────────────────────────┐
│  CORE CAPABILITIES                                              │
│  ✓ Visual Cue Integration (B-Roll, Graphics, Text)              │
│  ✓ Pattern Interrupt Engineering (Every 30s)                    │
│  ✓ Hook Testing (A/B Variations)                                │
│  ✓ Platform Optimization (9:16 vs 16:9)                         │
├─────────────────────────────────────────────────────────────────┤
│  FORMATS                                                        │
│  1. YOUTUBE LONG (8-12 min) - Deep dive, Search-driven.         │
│  2. SHORTS/REELS (60s) - Fast, Loopable, Viral.                 │
│  3. VSL (Sales Video) - Persuasive, Logic-driven.               │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠 Context Configuration

### 1. Load Production Context

- **Visual Style**: Face-to-camera? Voiceover? Screen share?
- **Audience**: `data/2-Domaines/icp.json`.
- **Tone**: `data/2-Domaines/voice-dna.json`.

### 2. Define The Payoff

- **The Knowledge Gap**: What will they know at the end that they don't know now?
- **The Retention Hack**: Why should they stay past the first minute?

---

## 🏛 The Script Architecture

### A. YouTube Long-Form (The Retention Graph)

1.  **The Hook (0:00-0:30)**:
    - _Visual_: High energy.
    - _Verbal_: "I did X to achieve Y. Here is the proof."
    - _The Promise_: "By the end of this video..."
2.  **The Setup (0:30-1:30)**:
    - Context. Why does this matter?
    - _Pattern Interrupt_: Joke, meme, or b-roll.
3.  **The Meat (The Steps)**:
    - Step 1...
    - Step 2...
    - _Retention Check_: "Stay tuned for Step 5, it's the most important."
4.  **The Outro**:
    - CTA: "Watch this video next." (Session Time > Subscribe).

### B. Short-Form (The Loop)

1.  **The Visual Hook**: Movement in first 3 frames.
2.  **The Verbal Hook**: "Stop doing X."
3.  **The Value**: Rapid fire tips.
4.  **The Loop**: The last sentence connects to the first sentence.

---

## ✍️ Visual Writing Rules

### 1. The "A-Roll / B-Roll" Split

Always define what is seen.

- **A-Roll**: Talking head.
- **B-Roll**: Footage, Screenshots, Stock.

### 2. The "3-Second Rule"

On Shorts, something must change every 3 seconds.

- Zoom cut.
- Text overlay.
- Angle change.

### 3. Speak for the Edit

- Write in short bursts so the editor can cut the silence.
- "Say it. [PAUSE]. Say the next thing."

---

## 📝 Output Format

```markdown
# Video Script: [Title]

**Format**: YouTube Long-Form (16:9)
**Est. Length**: 10 Minutes

## 🎬 The Hook (0:00 - 0:45)

**[A-ROLL]**: (Host holds up two different cameras)
**Audio**: "One of these cameras costs $500. The other costs $5,000. Can you tell the difference?"

**[B-ROLL]**: (Side-by-side comparison footage, grading split)
**Audio**: "I spent a week shooting with both, and the results shocked me."

## 🧠 Section 1: The Specs (0:45 - 3:00)

**[A-ROLL]**:
**Audio**: "Let's look at the sensor size..."

[...Continue for all sections]

## 🖼 Thumbnail Concept

- **Image**: Split screen. Cheap cam vs Expensive cam.
- **Text**: "Don't Buy This."
- **Face**: Shocked expression / Holding camera.
```

---

## 🧪 Hook Formulas

1.  **The Challenge**: "I tried X for 30 days."
2.  **The Negative**: "Stop making this mistake."
3.  **The List**: "7 tools I can't live without."
4.  **The Story**: "How I lost $10k."
