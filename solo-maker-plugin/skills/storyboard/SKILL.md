---
name: storyboard
description: Create a 6-frame visual narrative to illustrate problem and solution. Triggered by "make a storyboard", "product storytelling", "pitch my feature".
type: interactive
bundle: landing-conversion
triggers:
  - "make a storyboard"
  - "product storytelling"
  - "pitch my feature"
tools:
  standalone: [filesystem]
  supercharged: []
---

## Objective

Transform abstract product concepts into a high-impact **Narrative Storyboard**. Use this to create immediate user empathy, align stakeholders on a shared vision, and provide a structured script for the video production pipeline. This is not just a "list of screens"; it is a psychological arc designed to move the viewer from pain (Emotional Spike) to relief (Aha! Moment).

## Key Concepts

### Narrative Engineering

We don't just "show features." We engineer a story that follows the **Classic Arc**:

1. **Setting**: The status quo.
2. **Inciting Incident**: The problem appears.
3. **Ascending Action**: The pain intensifies (The "Oh Shit!" moment).
4. **Crisis/Turning Point**: Discovery of the solution.
5. **Resolution**: The "Aha!" moment.
6. **New Status Quo**: Life is better.

### The Emotional Spike

The most critical part of a storyboard. If the "pain" in Frame 2 & 3 isn't felt, the "relief" in Frame 5 won't have value.

---

## Anti-Patterns

- **The Feature Dump**: Listing features instead of telling a story about a human.
- **The Flat Story**: No tension, no crisis, no emotional resolution.
- **UI-First Thinking**: Designing screens before defining the narrative arc.
- **Generic Personas**: "A user" vs. "Sarah, an anxious freelancer with 48h to pay her rent."

---

## Workflow

### 1. Narrative Framing

Define the **Emotional Anchor**:

- **Character**: Name them, give them a specific context.
- **The Spike**: What is the exact moment everything goes wrong?

### 2. Scene Weighting

Distribute the 6 frames to ensure the "Pain" gets enough time:

- **Frames 1-3**: 50% of the narrative weight (The Struggle).
- **Frames 4-6**: 50% of the narrative weight (The Transformation).

### 3. AI Visualization Prompts

For each frame, generate a high-fidelity visual prompt for tools like Flux or Midjourney:

- **Formula**: `[Shot Type] + [Subject in Context] + [Emotional Expression] + [Lighting/Aesthetics]`
- **Example**: "Close-up of Sarah, an anxious freelancer, staring at a 'Payment Overdue' notice on her laptop at night. Cold blue screen light, stressed expression, messy desk."

---

## Integration: Video Pipeline

This skill provides the direct input for the **Remotion Video Generator**:

| Storyboard Frame    | Remotion Strategy                                    |
| ------------------- | ---------------------------------------------------- |
| Frame 1-3 (Pain)    | Slow timing, grayscale or muted colors, tense audio. |
| Frame 4 (Discovery) | Transition (fade-in), upbeat music shift.            |
| Frame 5 (Aha!)      | Zoom-in on UI, bright colors, celebratory SFX.       |

---

## Output Format

Save the output at `data/1-Projets/[project]/storyboard.md`:

```markdown
# Storyboard: [Project Name]

## Scene 1: [Title]

- **Visual**: [Description + AI Prompt]
- **Narration**: [Script]
- **Emotional State**: [e.g., Boredom / Complacency]

... (frames 2-5)

## Scene 6: [Title]

- **Visual**: [Description + AI Prompt]
- **Narration**: [Script]
- **Emotional State**: [e.g., Total Peace / Mastery]
```
