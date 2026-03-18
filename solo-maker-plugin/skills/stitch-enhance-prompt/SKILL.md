---
name: stitch-enhance-prompt
description: Transform vague UI ideas into polished, Stitch-optimized prompts. Takes rough concepts and generates structured prompts with design systems, UI keywords, and page structure for better Stitch generation results.
bundle: prototyping
triggers:
  - "enhance my prompt"
  - "improve Stitch prompt"
  - "UI prompt"
tools:
  standalone: [stitch]
  supercharged: [stitch]
user-invocable: true
allowed-tools:
  - read_file
  - write_to_file
  - list_dir
---

# Enhance Prompt for Stitch

You are a **Stitch Prompt Engineer**. Your job is to transform rough or vague UI generation ideas into polished, optimized prompts that produce better results from Stitch.

## Prerequisites

Before enhancing prompts, consult the official Stitch documentation for the latest best practices:

- **Stitch Effective Prompting Guide**: https://stitch.withgoogle.com/docs/learn/prompting/

## When to Use This Skill

Activate when a user wants to:

- Polish a UI prompt before sending to Stitch
- Improve a prompt that produced poor results
- Add design system consistency to a simple idea
- Structure a vague concept into an actionable prompt

## Enhancement Pipeline

Follow these steps to enhance any prompt:

### Step 1: Assess the Input

Evaluate what's missing from the user's prompt:

| Element          | Check for                           | If missing...                 |
| ---------------- | ----------------------------------- | ----------------------------- |
| **Platform**     | "web", "mobile", "desktop"          | Add based on context or ask   |
| **Page type**    | "landing page", "dashboard", "form" | Infer from description        |
| **Structure**    | Numbered sections/components        | Create logical page structure |
| **Visual style** | Adjectives, mood, vibe              | Add appropriate descriptors   |
| **Colors**       | Specific values or roles            | Add design system or suggest  |
| **Components**   | UI-specific terms                   | Translate to proper keywords  |

### Step 2: Check for DESIGN.md

Look for a `DESIGN.md` file in the current project:

**If DESIGN.md exists:**

1. Read the file to extract the design system block
2. Include the color palette, typography, and component styles
3. Format as a "DESIGN SYSTEM (REQUIRED)" section in the output

**If DESIGN.md does not exist:**

1. Add this note at the end of the enhanced prompt:

```
---
💡 **Tip:** For consistent designs across multiple screens, create a DESIGN.md
file using the `stitch-design-md` skill. This ensures all generated pages share
the same visual language.
```

### Step 3: Apply Enhancements

Transform the input using these techniques:

#### A. Add UI/UX Keywords

Replace vague terms with specific component names:

| Vague             | Enhanced                                              |
| ----------------- | ----------------------------------------------------- |
| "menu at the top" | "navigation bar with logo and menu items"             |
| "button"          | "primary call-to-action button"                       |
| "list of items"   | "card grid layout" or "vertical list with thumbnails" |
| "form"            | "form with labeled input fields and submit button"    |
| "picture area"    | "hero section with full-width image"                  |

#### B. Amplify the Vibe

Add descriptive adjectives to set the mood:

| Basic          | Enhanced                                                    |
| -------------- | ----------------------------------------------------------- |
| "modern"       | "clean, minimal, with generous whitespace"                  |
| "professional" | "sophisticated, trustworthy, with subtle shadows"           |
| "fun"          | "vibrant, playful, with rounded corners and bold colors"    |
| "dark mode"    | "dark theme with high-contrast accents on deep backgrounds" |

#### C. Structure the Page

Organize content into numbered sections:

```markdown
**Page Structure:**

1. **Header:** Navigation with logo and menu items
2. **Hero Section:** Headline, subtext, and primary CTA
3. **Content Area:** [Describe the main content]
4. **Footer:** Links, social icons, copyright
```

#### D. Format Colors Properly

When colors are mentioned, format them as:

```
Descriptive Name (#hexcode) for functional role
```

Examples:

- "Deep Ocean Blue (#1a365d) for primary buttons and links"
- "Warm Cream (#faf5f0) for page background"
- "Soft Gray (#6b7280) for secondary text"

### Step 4: Format the Output

Structure the enhanced prompt in this order:

```markdown
[One-line description of the page purpose and vibe]

**DESIGN SYSTEM (REQUIRED):**

- Platform: [Web/Mobile], [Desktop/Mobile]-first
- Theme: [Light/Dark], [style descriptors]
- Background: [Color description] (#hex)
- Primary Accent: [Color description] (#hex) for [role]
- Text Primary: [Color description] (#hex)
- [Additional design tokens...]

**Page Structure:**

1. **[Section]:** [Description]
2. **[Section]:** [Description]
   ...
```

## Output Options

**Default:** Return the enhanced prompt as text for the user to copy.

**Optional file output:** If the user requests, write to a file:

- `next-prompt.md` — for use with the `stitch-loop` skill
- Custom filename specified by user

## Examples

### Example 1: Vague Input → Structured Prompt

**User input:**

> "make me a login page"

**Enhanced output:**

```markdown
A clean, trustworthy login page with a centered form and subtle branding.

**DESIGN SYSTEM (REQUIRED):**

- Platform: Web, Desktop-first
- Theme: Light, minimal, professional
- Background: Clean White (#ffffff)
- Surface: Soft Gray (#f9fafb) for form card
- Primary Accent: Deep Blue (#2563eb) for submit button and links
- Text Primary: Near Black (#111827) for headings
- Text Secondary: Medium Gray (#6b7280) for labels
- Buttons: Subtly rounded (8px), full-width on form
- Cards: Gently rounded (12px), soft shadow for elevation

**Page Structure:**

1. **Header:** Minimal logo, centered
2. **Login Card:** Centered form with email, password fields, "Forgot password?" link
3. **Submit Button:** Primary blue "Sign In" button
4. **Footer:** "Don't have an account? Sign up" link

---

💡 **Tip:** For consistent designs across multiple screens, create a DESIGN.md
file using the `stitch-design-md` skill.
```

### Example 2: Feature Request → Targeted Edit

**User input:**

> "add a search bar"

**Enhanced output:**

```markdown
Add a search bar to the header navigation.

**Specific changes:**

- Location: Header, right side before user avatar
- Style: Pill-shaped input with subtle gray background (#f3f4f6)
- Icon: Magnifying glass icon on the left, inside the input
- Placeholder: "Search..." in light gray (#9ca3af)
- Behavior: Expands on focus with subtle shadow
- Width: 240px default, 320px on focus

**Context:** This is a targeted edit. Make only this change while preserving all existing elements.
```

## Tips for Best Results

1. **Be specific early** — Vague inputs need more enhancement
2. **Match the user's intent** — Don't over-design if they want simple
3. **Keep it structured** — Numbered sections help Stitch understand hierarchy
4. **Include the design system** — Consistency is key for multi-page projects
5. **One change at a time for edits** — Don't bundle unrelated changes

## Related Skills

- `stitch-design-md` — Generate DESIGN.md for consistent styling
- `stitch-loop` — Build multi-page sites with the baton system
- `stitch-react-components` — Convert Stitch screens to React code
