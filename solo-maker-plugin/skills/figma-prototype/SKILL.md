---
name: figma-prototype
description: "Prototype Architecture Engine. Generates interactive flows with design system intelligence, validates against user stories, and exports production-ready assets. Triggers on 'Figma', 'prototype', 'HI-FI mockup', 'interactive prototype'."
bundle: prototyping
triggers:
  - "Figma"
  - "prototype"
  - "HI-FI mockup"
  - "interactive prototype"
tools:
  standalone: [filesystem]
  supercharged: [figma]
version: "3.0.0"
---

# Skill: Figma Prototype Architecture Engine

This skill transforms a written `DESIGN-BRIEF.md` into a **visual, interactive product prototype**. It's the critical handoff between Strategy (PRD, user stories) and Execution (working prototype). Unlike basic mockup tools, this skill includes **design system intelligence**, **flow templates**, and **validation protocols**.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Interactive HTML/CSS Mockups: Clean, responsive prototypes    │
│    generated as local files. Use Tailwind/Vanilla CSS.          │
│  ✓ Design System Auto-Detection: Extract tokens from voice-dna  │
│    and brand assets (colors, typography, spacing).              │
│  ✓ Screen Flow Templates: 5 pre-built flows (SaaS, Mobile,      │
│    Landing, E-commerce, Admin) with standard screens.           │
│  ✓ Validation Checklist: Auto-verify against user stories.      │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~design / Figma)                        │
│  + Native Figma Integration: Create frames, components, and     │
│    interactions directly via Figma API.                         │
│  + Token Extraction: Pull design tokens from existing Figma     │
│    files to ensure brand consistency.                           │
│  + Component Library Sync: Use existing Figma components.       │
│  + Asset Export: Push frames to Remotion for demo videos.       │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠 Triggers

- "Create an interactive prototype for [Project]"
- "Move the design brief into Figma"
- "Build a high-fidelity mockup"
- "Generate prototype from PRD"
- "Export design tokens from this Figma URL"
- "Validate prototype against user stories"

---

## 🎨 Design System Detector

**Before generating any screens**, extract design tokens from available sources:

### Token Sources (Priority Order)

1. **`voice-dna.json`** — Brand personality informs color palette and tone
2. **`business-profile.json`** — Company name, tagline, industry context
3. **Existing brand assets** in `data/3-Ressources/brand/` (logo, style guide)
4. **Figma file** (if `~~design` connected) — Extract from existing designs
5. **Defaults** — Use professional SaaS defaults if nothing available

### Token Extraction Protocol

```python
# Read voice-dna.json
voice = read_json("data/2-Domaines/voice-dna.json")
tone = voice.get("tone")  # e.g., "professional", "playful", "technical"

# Map tone to color palette
if tone == "professional":
    primary = "#2563EB"  # Blue
    accent = "#10B981"   # Green
elif tone == "playful":
    primary = "#8B5CF6"  # Purple
    accent = "#F59E0B"   # Orange
# ... etc

# Extract typography
if "technical" in tone:
    font_family = "JetBrains Mono, monospace"
else:
    font_family = "Inter, sans-serif"

# Save to design-tokens.json
save_tokens({
    "colors": {"primary": primary, "accent": accent, ...},
    "typography": {"fontFamily": font_family, ...},
    "spacing": {"unit": "8px", ...},
    "borderRadius": "8px"
})
```

**Output**: `data/1-Projets/[project]/prototype/design-tokens.json`

---

## 📐 Screen Flow Generator

Use **pre-built flow templates** to accelerate prototyping. Each template defines:

- Required screens
- Navigation structure
- Component inventory
- Interaction patterns

### Available Templates

| Template           | Screens                                      | Best For             |
| ------------------ | -------------------------------------------- | -------------------- |
| **SaaS Dashboard** | Login, Dashboard, Settings, Profile          | B2B SaaS products    |
| **Mobile App**     | Splash, Onboarding, Home, Detail, Profile    | Consumer mobile apps |
| **Landing Page**   | Hero, Features, Pricing, CTA                 | Marketing sites      |
| **E-commerce**     | Product List, Product Detail, Cart, Checkout | Online stores        |
| **Admin Panel**    | Login, Table View, Form, Analytics           | Internal tools       |

**See**: [screen-flow-templates.md](./references/screen-flow-templates.md) for full specifications.

### Flow Selection Logic

```python
# Read PRD to detect product type
prd = read_file("data/1-Projets/[project]/PRD.md")

if "dashboard" in prd.lower() or "analytics" in prd.lower():
    template = "SaaS Dashboard"
elif "mobile" in prd.lower() or "app" in prd.lower():
    template = "Mobile App"
elif "landing" in prd.lower() or "marketing" in prd.lower():
    template = "Landing Page"
# ... etc

# Load template
flow = load_template(template)
screens = flow["screens"]  # e.g., ["login", "dashboard", "settings"]
```

---

## 📋 Prototyping Strategy

### Path A: Standalone (HTML/CSS)

**Best for**: Quick validation, "Concierge" tests, developers who want code.

**Process**:

1. Load design tokens from `design-tokens.json`
2. Select appropriate screen flow template
3. Generate HTML/CSS for each screen using tokens
4. Add basic JavaScript for navigation
5. Save to `data/1-Projets/[project]/prototype/index.html`

**Output Structure**:

```
prototype/
├── index.html          # Main entry point
├── screens/
│   ├── login.html
│   ├── dashboard.html
│   └── settings.html
├── assets/
│   ├── styles.css      # Generated from design tokens
│   └── script.js       # Basic navigation
└── design-tokens.json  # Token reference
```

---

### Path B: Supercharged (Figma Native)

**Best for**: Design handoff, professional presentations, visual refinement.

**Process**:

1. Prompt for Figma file URL and access token
2. Use `~~design` MCP to:
   - Create a new Figma page for this project
   - Apply design tokens as Figma styles
   - Generate frames for each screen in the flow
   - Add components (buttons, inputs, cards)
   - Link frames with interaction hotspots
3. Export shareable Figma prototype link
4. Save link to `data/1-Projets/[project]/prototype/figma-link.md`

**Figma API Workflow**:

```python
# Create base styles
create_color_style("Primary", primary_color)
create_text_style("Heading", font_family, 24, "bold")

# Generate frames
for screen in screens:
    frame = create_frame(screen["name"], 1440, 900)
    add_components(frame, screen["components"])

# Add interactions
link_frames("login_button", "login", "dashboard")
link_frames("settings_icon", "dashboard", "settings")
```

---

## ✅ Interactive Validation Checklist

**After prototype generation**, validate against `user-stories.md`:

### Validation Protocol

```python
# Read user stories
stories = read_file("data/1-Projets/[project]/stories.md")

# Parse acceptance criteria
criteria = extract_acceptance_criteria(stories)

# Check each criterion
validation_report = []
for criterion in criteria:
    # Example: "User can log in with email and password"
    if "log in" in criterion:
        check = "✓" if "login" in screens else "✗"
        validation_report.append(f"{check} {criterion}")
    # ... more checks

# Save report
save_report("prototype/validation-report.md", validation_report)
```

**Output**: `data/1-Projets/[project]/prototype/validation-report.md`

Example:

```markdown
# Prototype Validation Report

## Coverage: 8/10 user stories (80%)

✓ User can log in with email and password
✓ User can view dashboard with key metrics
✓ User can navigate to settings
✗ User can export data as CSV (missing export button)
✗ User can invite team members (missing invite flow)
...
```

---

## 🚀 Complete Workflow

### Step 1: Context Ingestion

Read these files in order:

1. `PRD.md` — Product scope and features
2. `DESIGN-BRIEF.md` — Visual requirements
3. `stories.md` — User stories with acceptance criteria
4. `voice-dna.json` — Brand personality
5. `business-profile.json` — Company context

### Step 2: Design System Setup

Run the **Design System Detector**:

- Extract tokens from voice-dna and brand assets
- Save to `design-tokens.json`
- If `~~design` connected, create Figma styles

### Step 3: Flow Selection

Run the **Screen Flow Generator**:

- Analyze PRD to detect product type
- Load appropriate template (SaaS, Mobile, Landing, etc.)
- Customize screens based on user stories

### Step 4: Prototype Generation

**If Standalone**:

- Generate HTML/CSS for each screen
- Apply design tokens
- Add navigation JavaScript
- Save to `prototype/` directory

**If Supercharged**:

- Create Figma file/page
- Generate frames with components
- Add interactions
- Export shareable link

### Step 5: Validation

Run the **Interactive Validation Checklist**:

- Compare prototype screens against user stories
- Generate validation report
- Flag missing features

### Step 6: Output Package

Deliver a complete prototype package:

```
data/1-Projets/[project]/prototype/
├── README.md                # Prototype overview
├── design-tokens.json       # Design system reference
├── validation-report.md     # Coverage analysis
├── figma-link.md            # (If Figma) Shareable link
├── index.html               # (If HTML) Main file
└── feedback-log.md          # Template for user testing notes
```

---

## 📈 Agent Instructions

### Decision Tree

```
START
  │
  ├─ Read PRD + DESIGN-BRIEF + stories.md
  │
  ├─ Extract design tokens (voice-dna → design-tokens.json)
  │
  ├─ Detect product type → Select flow template
  │
  ├─ Check if ~~design connected?
  │   ├─ YES → Figma Native Path
  │   └─ NO  → HTML/CSS Standalone Path
  │
  ├─ Generate screens (apply tokens + template)
  │
  ├─ Validate against user stories
  │
  └─ Output prototype package + validation report
```

### Quality Standards

- **Design Consistency**: All screens MUST use tokens from `design-tokens.json`
- **Navigation**: Every screen MUST have a way to return to home/dashboard
- **Responsiveness**: HTML prototypes MUST work on mobile (320px) and desktop (1440px)
- **Accessibility**: Use semantic HTML, ARIA labels, and sufficient color contrast
- **Validation**: MUST generate validation report comparing prototype to user stories

### Output Template

Every prototype delivery includes:

```markdown
# Prototype: [Project Name]

## Overview

- **Type**: [SaaS Dashboard / Mobile App / etc.]
- **Screens**: [Number] screens generated
- **Coverage**: [X/Y] user stories implemented ([Z]%)
- **Format**: [Figma link / HTML files]

## Design System

- **Primary Color**: [Hex]
- **Font**: [Family]
- **Spacing Unit**: [8px / 4px]

## Screen Flow

1. [Screen 1] → [Screen 2]
2. [Screen 2] → [Screen 3]
   ...

## Validation Report

✓ [Implemented features]
✗ [Missing features]

## Next Steps

1. Review prototype: [Link or file path]
2. Test with users: Use `feedback-log.md` template
3. Iterate: Update DESIGN-BRIEF and re-run
4. (Optional) Generate demo video: `/solo:build prototype video`
```

### Edge Cases

| Scenario                                | Action                                                    |
| --------------------------------------- | --------------------------------------------------------- |
| No design tokens available              | Use professional SaaS defaults (Blue primary, Inter font) |
| PRD doesn't match any template          | Use "SaaS Dashboard" as fallback, customize screens       |
| User stories conflict with design brief | Flag in validation report, ask user to clarify            |
| Figma connection fails                  | Gracefully fall back to HTML/CSS standalone               |
| Missing acceptance criteria             | Generate prototype anyway, note in validation report      |

---

## 📂 References

- **[screen-flow-templates.md](./references/screen-flow-templates.md)** — 5 complete flow templates with screen specs
- **[design-token-extractor.md](./references/design-token-extractor.md)** — Token extraction from voice-dna, Figma, and brand assets
- **[boilerplate.md](./references/boilerplate.md)** — HTML/CSS prototype starter code
- **[figma-commands.md](./references/figma-commands.md)** — Figma API command reference
- **[ui-prompts.md](./references/ui-prompts.md)** — Prompting framework for Stitch/DALL-E
