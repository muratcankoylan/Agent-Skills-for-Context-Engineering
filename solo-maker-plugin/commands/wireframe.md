---
name: wireframe
description: Lo-fi wireframes and user flow diagrams. Fast, structural thinking before full design. Real copy, no styling.
argument-hint: "[what to wireframe]"
---

# Build Wireframes

**Load skill:** `solopreneur`, `landing-page`

## What to Wireframe?

<description> #$ARGUMENTS </description>

If empty: "What do you want to wireframe? A landing page, onboarding flow, dashboard, checkout, or something else?"

---

## Wireframe Output Formats

### Option A — HTML Lo-fi Wireframe
Black and white, box-based layout. Real copy, no colors, minimal styling.
Uses:
- Bordered boxes for sections
- Gray rectangles for images
- Real text for headings and CTAs
- Annotations for interactions

### Option B — User Flow Diagram (HTML)
Boxes + arrows showing how users move through the product.
- Each box = a screen or decision point
- Arrows = user actions
- Diamond shapes = decisions/conditionals

### Option C — Both
Wireframe for each key screen + flow diagram connecting them.

---

## Build Process

1. Ask which format (or detect from description)
2. Identify all screens/sections needed
3. Map the user journey through them
4. Build HTML wireframe with:
   - Semantic structure
   - Real copy in every text area
   - `[IMAGE: description]` placeholders for visuals
   - `<!-- ANNOTATION: ... -->` comments for interaction notes

## Principles

- **Real copy, always** — "Get started for free" not "Button CTA"
- **Show hierarchy** — big/small text only, no color
- **Annotate decisions** — why is this section here?
- **Mobile and desktop** — side by side if they differ significantly

## Deliver

Output: `[product]-wireframe.html`
Greyscale, boxed, annotated. Looks intentionally wireframey.
