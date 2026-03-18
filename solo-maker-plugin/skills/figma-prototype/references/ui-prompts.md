# Design Engineering: Master Prompts for Solo UI

Professional solo products need to look "Premium" from day one. Use these prompt patterns and design engineering frameworks to guide the AI when generating layouts, components, or CSS themes.

---

## 1. The "Structural Blueprint" Prompt Pattern

_Use this when generating a new page layout._

> "Generate a [Page Type, e.g. Analytics Dashboard] for a [Persona, e.g. Solopreneur].
> **Architectural Constraints**: Use a 12-column grid. Include a sticky left navigation bar (240px wide).
> **Visual Hierarchy**: The primary metric should be a large 'Card' with a sparkline chart.
> **Design Language**: Minimalist SaaS aesthetic, heavy use of whitespace, indigo-on-white color scheme. Inter typography."

---

## 2. The "Design Token" Prompt Pattern

_Use this for generating specific component libraries._

> "Create a set of UI components (Buttons, Inputs, Badges) with the following tokens:
> **Border Radius**: 12px for cards, 8px for buttons.
> **Shading**: Use a soft 'elevated' shadow (0 4px 12px rgba(0,0,0,0.05)).
> **Copy**: Use high-confidence, professional micro-copy (e.g., 'Confirm Deployment' instead of 'Submit')."

---

## 3. High-Fidelity Theming Library

| Theme Name        | Use Case              | Professional Vibe                                                       |
| :---------------- | :-------------------- | :---------------------------------------------------------------------- |
| **The Executive** | Finance & Strategy    | Dark Slate (#1e293b), Gold accents (#d4af37), serif headers.            |
| **The Creative**  | Marketing & Content   | Clean White (#ffffff), Electric Blue (#6366f1), rounded borders (24px). |
| **The Hacker**    | Technical & Dev Tools | Deep Space (#0f172a), Emerald Green (#10b981), monospaced fonts.        |

---

## 4. State Management Prompts

_Don't just prompt the 'Happy Path'. Prompt the 'Empty' and 'Error' states._

- **Empty State**: "Design the 'No Projects Found' state. Include a friendly illustration, a 'Don't worry, let's start' message, and a primary CTA button center-aligned."
- **Progressive Disclosure**: "Only show the 'Advanced Settings' toggle after the user has completed Phase 1 of the configuration."

---

## 5. Mobile-First Optimization Rules

A professional solo tool MUST be responsive.

- **Rule 1**: Buttons must be at least 44px tall (Tap target size).
- **Rule 2**: Sidebar should collapse into a "Hamburger" or "Bottom-Tab" menu on screens < 768px.
- **Rule 3**: Use `clamp()` for responsive font sizes (e.g., `font-size: clamp(1rem, 5vw, 1.5rem)`).

---

## 6. Integration with Skills

- **Figma Commands**: Use these prompts with the `figma-prototype` tool suite.
- **Voice DNA**: Ensure all generated copy matches the `voice-dna.json` personality.
