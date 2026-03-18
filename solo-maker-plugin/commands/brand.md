---
name: brand
description: Define your brand identity — name, colors, typography, voice, and logo direction. Outputs a living HTML brand guide.
argument-hint: "[describe your business/product and vibe]"
---

# Build a Brand Identity

**Load skills:** `solopreneur`, `frontend-design`

## Context

<description> #$ARGUMENTS </description>

If empty: "Tell me about your business and the feeling you want your brand to create. What adjectives describe it? Who's the audience?"

Gather:
- Business name (or "help me name it")
- Industry/type
- 3 adjectives that describe the ideal brand feel
- Target audience personality
- Brands you admire (for reference, not to copy)
- Brands you explicitly DON'T want to look like

---

## Brand Identity System

### 1. Brand Positioning

Define in the guide:
- **Brand essence**: One sentence that captures what the brand stands for
- **Audience**: Who it's for (demographic + psychographic)
- **Personality**: 3-5 brand character traits with descriptions
- **Promise**: The one thing customers believe when they see the brand

### 2. Visual Identity

**Color System** (OKLCH-based):
- Primary: Main brand color with usage rules
- Accent: Complementary pop color
- Neutrals: 5-step scale (warm or cool)
- Semantic: Success, warning, error
- Show: dark mode + light mode variants

**Typography**:
- Display font: for headlines (Google Fonts, not Inter)
- Body font: for reading
- Show live type specimens at every scale

**Logo Direction** (3 concepts):
For each: name, concept description, CSS mock if feasible

**Iconography style**: Outline / filled / hand-drawn / geometric

**Photography style**: Direction for any imagery used

### 3. Voice & Tone

- 3-5 voice pillars with examples
- DO/DON'T copy examples (5 pairs)
- Sample taglines (3-5 options)
- Sample social bio (Twitter/LinkedIn/Instagram)

### 4. Usage Examples

Show the brand applied to:
- A button
- A card
- A hero section (mini)
- A form element
- A notification/badge

---

## Deliver

Output: `[brand-name]-brand-guide.html` — a beautiful, self-contained HTML brand guide.

Design the brand guide itself using the brand system being defined. It should be an example of the brand.
