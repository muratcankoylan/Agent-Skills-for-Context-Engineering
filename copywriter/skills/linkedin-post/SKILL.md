---
name: linkedin-post
description: Create high-performing LinkedIn posts that build authority and drive engagement. Optimized for "Dwell Time" and Meaningful Interactions.
model: sonnet
bundle: social-content
triggers:
  - "write a LinkedIn post"
  - "LinkedIn hook"
  - "LinkedIn carousel"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# LinkedIn Authority Architecture

This skill is designed to maximize your "Dwell Time" on LinkedIn. It uses your unique `{{voice_dna}}` to stop the scroll.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Hook Generation: 3 scroll-stopping variations.               │
│  ✓ Dwell-Time Formatting: Optimized whitespace & pacing.        │
│  ✓ Voice Match: Writes exactly like you (no "AI voice").        │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~linkedin_api / TweetHunter)            │
│  + Trend Jacking: Injects current trending news/hashtags.       │
│  + Analytics Loop: Learns from your previous top performers.    │
│  + Carousel Maker: Formats content for PDF sliders.             │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠 Triggers

- "Write a LinkedIn post about [Topic]"
- "Repurpose this blog into a social post"
- "Give me 3 hooks for this idea"
- "Fix this draft to be more viral"

## 🛠 Agent Instructions

### Before Writing

1.  **Load Context Profiles**:
    - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/voice-dna.json` to match the user's voice precisely.
    - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/icp.json` to align with the audience's pain points and jargon.
    - Read `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/business-profile.json` to ensure the post aligns with overall positioning.
2.  **Identify Post Objective**: Is the goal _Brand Awareness_, _Lead Generation_, or _Topical Authority_?
3.  **Check Source Material**: If the user wants to repurpose a blog post or transcript, search `${CLAUDE_PLUGIN_ROOT}/data/3-Resources/`.

---

## 🏛 The "LinkedIn Authority" Protocol

### 1. The Hook (First 140 Characters)

_Ref: `references/hook-library.md`_

_Goal: Stop the scroll._

- **The specific outcome**: "I spent $50k on ads. Here is what I learned."
- **The contrarian take**: "Stop doing X."
  _Rule: Never start with "In today's world..."_

### 2. Dwell-Time Engineering (The Body)

_Ref: `references/formatting-guide.md`_

- **Whitespace Rule**: No more than 2 lines per paragraph.
- **Tone**: Apply `{{voice_dna.tone}}`.
- **Anti-Slop**: Avoid words in `{{voice_dna.forbidden_words}}`.

### 3. Engagement & Conversion (The Footer)

_Ref: `references/engagement-framework.md`_

- **Meaningful CTA**: Ask a specific question.
- **The P.S. Play**: Promote `{{business.primary_cta}}` softly.

---

## 🚀 Writing Workflow

### Phase 1: Hook Generation

Generate 3 distinct hooks using the formulas in `references/hook-library.md`.

### Phase 2: Narrative Structure

Use **Hook → Story/Insight → Proof → CTA**.

### Phase 3: Algorithmic Audit

- **Length**: 1,300 - 2,000 characters.
- **Links**: "Link in comments".
- **Carousel Option**: If helpful, output a slide-by-slide breakdown using `references/carousel-blueprint.md`.

---

## 📝 Output Format

```markdown
# LinkedIn Post Draft

**Target Audience**: {{icp.job_titles}}

---

[The Hook]

[The Body - formatted with whitespace]

[The CTA]

P.S. [Soft sell for {{business.offers}}]

---

**Character Count**: [X]/3000
```
