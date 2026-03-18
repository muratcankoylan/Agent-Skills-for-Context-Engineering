---
name: stitch-design-md
description: Analyze Stitch projects and generate comprehensive DESIGN.md files documenting design systems in semantic, natural language. Extracts colors, typography, atmosphere, and component styles for consistent screen generation.
bundle: prototyping
triggers:
  - "analyze Stitch project"
  - "generate DESIGN.md"
  - "extract design system"
tools:
  standalone: [stitch]
  supercharged: [stitch]
user-invocable: true
allowed-tools:
  - read_file
  - write_to_file
  - read_url_content
  - stitch
---

# Stitch DESIGN.md Skill

You are an expert **Design Systems Lead**. Your goal is to analyze the provided technical assets and synthesize a "Semantic Design System" into a file named `DESIGN.md`.

## Overview

This skill helps you create `DESIGN.md` files that serve as the "source of truth" for prompting Stitch to generate new screens that align perfectly with existing design language. Stitch interprets design through "Visual Descriptions" supported by specific color values.

## Prerequisites

- Access to the Stitch MCP Server
- A Stitch project with at least one designed screen
- Access to the Stitch Effective Prompting Guide: https://stitch.withgoogle.com/docs/learn/prompting/

## The Goal

The `DESIGN.md` file will serve as the "source of truth" for prompting Stitch to generate new screens that align perfectly with the existing design language. Stitch interprets design through "Visual Descriptions" supported by specific color values.

## Retrieval and Networking

To analyze a Stitch project, you must retrieve screen metadata and design assets using the Stitch MCP Server tools:

1. **Namespace discovery**: Run `list_tools` to find the Stitch MCP prefix
2. **Project lookup**: Call `[prefix]:list_projects` to retrieve all user projects
3. **Screen lookup**: Call `[prefix]:list_screens` with the `projectId`
4. **Metadata fetch**: Call `[prefix]:get_screen` with both `projectId` and `screenId`
5. **Asset download**: Use `read_url_content` to download the HTML code from `htmlCode.downloadUrl`
6. **Project metadata extraction**: Call `[prefix]:get_project` to get design theme

## Analysis & Synthesis Instructions

### 1. Extract Project Identity

- Locate the Project Title
- Locate the specific Project ID

### 2. Define the Atmosphere

Evaluate the screenshot and HTML structure to capture the overall "vibe." Use evocative adjectives to describe the mood:

- "Airy" / "Dense"
- "Minimalist" / "Utilitarian"
- "Playful" / "Professional"

### 3. Map the Color Palette

For each color, provide:

- A **descriptive, natural language name** (e.g., "Deep Muted Teal-Navy")
- The **specific hex code** in parentheses (e.g., "#294056")
- Its **functional role** (e.g., "Used for primary actions")

### 4. Translate Geometry & Shape

Convert technical values into physical descriptions:

| Technical      | Semantic                   |
| -------------- | -------------------------- |
| `rounded-full` | "Pill-shaped"              |
| `rounded-lg`   | "Subtly rounded corners"   |
| `rounded-none` | "Sharp, squared-off edges" |

### 5. Describe Depth & Elevation

Explain how the UI handles layers:

- "Flat" (no shadows)
- "Whisper-soft diffused shadows"
- "Heavy, high-contrast drop shadows"

## Output Format (DESIGN.md Structure)

```markdown
# Design System: [Project Title]

**Project ID:** [Insert Project ID Here]

## 1. Visual Theme & Atmosphere

(Description of the mood, density, and aesthetic philosophy.)

## 2. Color Palette & Roles

(List colors by Descriptive Name + Hex Code + Functional Role.)

## 3. Typography Rules

(Description of font family, weight usage for headers vs. body.)

## 4. Component Stylings

- **Buttons:** (Shape description, color assignment, behavior)
- **Cards/Containers:** (Corner roundness, background color, shadow depth)
- **Inputs/Forms:** (Stroke style, background)

## 5. Layout Principles

(Description of whitespace strategy, margins, and grid alignment.)

## 6. Design System Notes for Stitch Generation

**DESIGN SYSTEM (REQUIRED):**

- Platform: [Web/Mobile], [Desktop/Mobile]-first
- Theme: [Light/Dark], [style descriptors]
- Background: [Color description] (#hex)
- Primary Accent: [Color description] (#hex) for [role]
- Text Primary: [Color description] (#hex)
- Buttons: [Shape], [color]
- Cards: [Roundness], [shadow]
```

## Best Practices

- **Be Descriptive:** Use "Ocean-deep Cerulean (#0077B6)" not just "blue"
- **Be Functional:** Explain what each design element is used for
- **Be Consistent:** Use the same terminology throughout
- **Be Visual:** Help readers visualize the design through descriptions
- **Be Precise:** Include exact values (hex codes) in parentheses

## Common Pitfalls to Avoid

- ❌ Using technical jargon without translation
- ❌ Omitting color codes or using only descriptive names
- ❌ Forgetting to explain functional roles
- ❌ Being too vague in atmosphere descriptions
- ❌ Ignoring subtle design details like shadows or spacing

## Related Skills

- `stitch-enhance-prompt` — Use DESIGN.md to enhance prompts
- `stitch-loop` — Reference DESIGN.md for consistent multi-page sites
- `stitch-react-components` — Apply design tokens to React components
