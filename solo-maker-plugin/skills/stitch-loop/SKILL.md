---
name: stitch-loop
description: Autonomous frontend builder using the baton system. Generates pages with Stitch MCP, integrates into site structure, and prepares next iteration task. Enables continuous, iterative website development.
bundle: prototyping
triggers:
  - "build with Stitch"
  - "generate pages"
  - "iterate website"
tools:
  standalone: [stitch]
  supercharged: [stitch]
user-invocable: true
allowed-tools:
  - read_file
  - write_to_file
  - list_dir
  - run_command
  - stitch
---

# Stitch Build Loop

You are an **autonomous frontend builder** participating in an iterative site-building loop. Your goal is to generate a page using Stitch, integrate it into the site, and prepare instructions for the next iteration.

## Overview

The Build Loop pattern enables continuous, autonomous website development through a "baton" system. Each iteration:

1. Reads the current task from a baton file (`next-prompt.md`)
2. Generates a page using Stitch MCP tools
3. Integrates the page into the site structure
4. Writes the next task to the baton file for the next iteration

## Prerequisites

**Required:**

- Access to the Stitch MCP Server
- A Stitch project (existing or will be created)
- A `DESIGN.md` file (generate one using the `stitch-design-md` skill if needed)
- A `SITE.md` file documenting the site vision and roadmap

**Optional:**

- Chrome DevTools MCP Server — enables visual verification of generated pages

## The Baton System

The `next-prompt.md` file acts as a relay baton between iterations:

```markdown
---
page: about
---

A page describing how the app works.

**DESIGN SYSTEM (REQUIRED):**
[Copy from DESIGN.md Section 6]

**Page Structure:**

1. Header with navigation
2. Explanation of methodology
3. Footer with links
```

**Critical rules:**

- The `page` field in YAML frontmatter determines the output filename
- The prompt content must include the design system block from `DESIGN.md`
- You MUST update this file before completing your work to continue the loop

## Execution Protocol

### Step 1: Read the Baton

Parse `next-prompt.md` to extract:

- **Page name** from the `page` frontmatter field
- **Prompt content** from the markdown body

### Step 2: Consult Context Files

Before generating, read these files:

| File        | Purpose                                                               |
| ----------- | --------------------------------------------------------------------- |
| `SITE.md`   | Site vision, **Stitch Project ID**, existing pages (sitemap), roadmap |
| `DESIGN.md` | Required visual style for Stitch prompts                              |

**Important checks:**

- Section 4 (Sitemap) — Do NOT recreate pages that already exist
- Section 5 (Roadmap) — Pick tasks from here if backlog exists
- Section 6 (Creative Freedom) — Ideas for new pages if roadmap is empty

### Step 3: Generate with Stitch

Use the Stitch MCP tools to generate the page:

1. **Discover namespace**: Run `list_tools` to find the Stitch MCP prefix
2. **Get or create project**:
   - If `stitch.json` exists, use the `projectId` from it
   - Otherwise, call `[prefix]:create_project` and save the ID to `stitch.json`
3. **Generate screen**: Call `[prefix]:generate_screen_from_text` with:
   - `projectId`: The project ID
   - `prompt`: The full prompt from the baton (including design system block)
   - `deviceType`: `DESKTOP` (or as specified)
4. **Retrieve assets**: Call `[prefix]:get_screen` to get:
   - `htmlCode.downloadUrl` — Download and save as `queue/{page}.html`
   - `screenshot.downloadUrl` — Download and save as `queue/{page}.png`

### Step 4: Integrate into Site

1. Move generated HTML from `queue/{page}.html` to `site/public/{page}.html`
2. Fix any asset paths to be relative to the public folder
3. Update navigation:
   - Find existing placeholder links (e.g., `href="#"`) and wire them to the new page
   - Add the new page to the global navigation if appropriate
4. Ensure consistent headers/footers across all pages

### Step 5: Update Site Documentation

Modify `SITE.md`:

- Add the new page to Section 4 (Sitemap) with `[x]`
- Remove any idea you consumed from Section 6 (Creative Freedom)
- Update Section 5 (Roadmap) if you completed a backlog item

### Step 6: Prepare the Next Baton (Critical)

**You MUST update `next-prompt.md` before completing.** This keeps the loop alive.

1. **Decide the next page**:
   - Check `SITE.md` Section 5 (Roadmap) for pending items
   - If empty, pick from Section 6 (Creative Freedom)
   - Or invent something new that fits the site vision
2. **Write the baton** with proper YAML frontmatter

## File Structure Reference

```
project/
├── next-prompt.md      # The baton — current task
├── stitch.json         # Stitch project ID (persist this!)
├── DESIGN.md           # Visual design system (from stitch-design-md skill)
├── SITE.md             # Site vision, sitemap, roadmap
├── queue/              # Staging area for Stitch output
│   ├── {page}.html
│   └── {page}.png
└── site/public/        # Production pages
    ├── index.html
    └── {page}.html
```

## Orchestration Options

The loop can be driven by different orchestration layers:

| Method            | How it works                                           |
| ----------------- | ------------------------------------------------------ |
| **CI/CD**         | GitHub Actions triggers on `next-prompt.md` changes    |
| **Human-in-loop** | Developer reviews each iteration before continuing     |
| **Agent chains**  | One agent dispatches to another                        |
| **Manual**        | Developer runs the agent repeatedly with the same repo |

## Design System Integration

This skill works best with the `stitch-design-md` skill:

1. **First time setup**: Generate `DESIGN.md` using the `stitch-design-md` skill from an existing Stitch screen
2. **Every iteration**: Copy Section 6 ("Design System Notes for Stitch Generation") into your baton prompt
3. **Consistency**: All generated pages will share the same visual language

## Common Pitfalls

- ❌ Forgetting to update `next-prompt.md` (breaks the loop)
- ❌ Recreating a page that already exists in the sitemap
- ❌ Not including the design system block in the prompt
- ❌ Leaving placeholder links (`href="#"`) instead of wiring real navigation
- ❌ Forgetting to persist `stitch.json` after creating a new project

## Troubleshooting

| Issue                   | Solution                                                   |
| ----------------------- | ---------------------------------------------------------- |
| Stitch generation fails | Check that the prompt includes the design system block     |
| Inconsistent styles     | Ensure DESIGN.md is up-to-date and copied correctly        |
| Loop stalls             | Verify `next-prompt.md` was updated with valid frontmatter |
| Navigation broken       | Check all internal links use correct relative paths        |

## Related Skills

- `stitch-enhance-prompt` — Polish prompts before generation
- `stitch-design-md` — Generate DESIGN.md from existing screens
- `stitch-react-components` — Convert screens to React code
