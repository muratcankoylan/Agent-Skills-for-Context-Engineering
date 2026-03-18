---
description: "Generate a prototype — mockup, Figma, or demo video"
argument-hint: "[mockup | figma | video | status]"
allowed-tools: Read, Write, Glob
model: sonnet
---

# /solo-studio:build

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

Generate a working prototype from your design brief. Pick the output format that fits your goal: AI-generated mockups (standalone), interactive Figma flows (requires ~~design), or a rendered demo video (requires ~~video).

**Prerequisite**: Run `/solo:build design` first to generate `data/1-Projets/[project]/DESIGN-BRIEF.md`.

## Usage

```
/solo-studio:build mockup   # AI-generated UI screens via Stitch
/solo-studio:build figma    # Interactive Figma prototype
/solo-studio:build video    # Remotion demo video (60-120s MP4)
/solo-studio:build status   # Check prototype progress
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                    PROTOTYPE PIPELINE                             │
├──────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                        │
│  ✓ Mockup: Stitch-generated screens from DESIGN-BRIEF.md        │
│  ✓ HTML prototype: Responsive screens with design tokens         │
│  ✓ Storyboard: Scene-by-scene video narrative plan               │
│  ✓ Video config: Remotion JSON for manual rendering              │
│  ✓ Status tracking: Local markdown files in PARA structure       │
├──────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                       │
│  + ~~design (Figma/Stitch): Interactive prototypes with flows    │
│  + ~~video (Remotion): Automated MP4 rendering from storyboard   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Prototype Options

### Option A: Mockup (`/solo-studio:build mockup`)

**Best for**: Quick user testing, landing page validation, developer handoff.

**What I'll do**:

1. Read `DESIGN-BRIEF.md` and extract visual requirements
2. Read `voice-dna.json` for brand tokens (colors, typography, tone)
3. If `~~design` connected: Generate screens via Stitch or Figma API
4. Otherwise: Generate standalone HTML/CSS with design tokens
5. Create `prototype/validation-report.md` comparing screens to user stories

**Output**:
```
data/1-Projets/[project]/prototype/
├── design-tokens.json       # Colors, fonts, spacing extracted from brief
├── index.html               # (Standalone) Entry point
├── screens/                 # Individual screen files
└── validation-report.md     # Coverage vs. user stories
```

---

### Option B: Figma Prototype (`/solo-studio:build figma`)

**Best for**: Design handoff, investor demos, user testing with real interactions.

**Requires**: `~~design` (Figma MCP) connected.

**What I'll do**:

1. Read `DESIGN-BRIEF.md` for visual spec
2. Create a new Figma page for this project
3. Apply design tokens as Figma styles
4. Generate frames for each screen in the flow
5. Add clickable interactions between screens
6. Export shareable prototype link

**Output**:
```
data/1-Projets/[project]/prototype/
├── figma-link.md            # Shareable prototype URL
├── design-tokens.json       # Token reference
└── validation-report.md     # Story coverage
```

---

### Option C: Demo Video (`/solo-studio:build video`)

**Best for**: Product launches, investor pitches, user onboarding.

**Requires**: `~~video` (Remotion) for automated rendering; otherwise generates config for manual rendering.

**What I'll do**:

1. Read `DESIGN-BRIEF.md`, `PRD.md`, `voice-dna.json`
2. Select narrative variant: Product Demo (60s), Investor Pitch (90s), or Onboarding (120s)
3. Generate voiceover script using the Script Engine
4. Create storyboard mapping prototype screens to script scenes
5. Calculate timing per screen based on UI complexity
6. Generate voiceover audio (if TTS connected)
7. If `~~video` connected: Render MP4 via Remotion CLI
8. Otherwise: Generate `remotion-config.json` for manual rendering

**Output**:
```
data/1-Projets/[project]/prototype/
├── video-script.md          # Full voiceover script
├── storyboard.md            # Scene-by-scene breakdown
├── remotion-config.json     # Rendering config
└── demo-video.mp4           # (If ~~video connected) Final MP4
```

---

## /solo-studio:build status

Check prototype progress and see what's next.

**Output example**:
```
📦 PROJECT: [Your Project Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Prototype Status:
[✓] MOCKUP ────────> [►] VIDEO ────────> [ ] LAUNCH

Current: VIDEO (generating storyboard)

Completed Outputs:
  ✓ design-tokens.json
  ✓ prototype/screens/ (5 screens)
  ✓ validation-report.md (8/10 stories covered)

In Progress:
  ► video-script.md
  ○ storyboard.md (pending)

Next Steps:
  1. Review video script
  2. Approve storyboard
  3. Render video (run: npx remotion render)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Agent Instructions

### Execution Flow

1. **Detect Project Context**

   ```python
   project_name = ask("Which project? (check data/1-Projets/ for options)")
   project_path = f"data/1-Projets/{project_name}"
   design_brief = read_file(f"{project_path}/DESIGN-BRIEF.md")

   if not design_brief:
       error("DESIGN-BRIEF.md not found. Run /solo:build design first.")
   ```

2. **Execute Prototype Option**

   **For MOCKUP**:

   ```python
   invoke_skill("stitch-loop", context=[design_brief], output=f"{project_path}/prototype/")
   # OR invoke_skill("figma-prototype", ...) if ~~design connected
   invoke_skill("validation-checkpoint", context=[prototype, user_stories])
   ```

   **For FIGMA**:

   ```python
   if not has_tool("~~design"):
       warn("~~design not connected. Falling back to Stitch mockup.")
       # fallback to mockup flow
   else:
       invoke_skill("figma-prototype", context=[design_brief])
   ```

   **For VIDEO**:

   ```python
   variant = ask_choice(["Product Demo (60s)", "Investor Pitch (90s)", "Onboarding (120s)"])
   invoke_skill("storyboard", context=[design_brief, prd, problem_statement])
   invoke_skill("voiceover-generator", context=[script, voice_dna])
   invoke_skill("stitch-asset-bridge", context=[prototype_screens, storyboard])
   if has_tool("~~video"):
       invoke_skill("remotion-video-generator", context=[storyboard, assets, audio])
   else:
       generate_remotion_config(storyboard, assets)
       notify("Run 'npx remotion render' to create the video.")
   ```

---

## Integration

- **Before this command**: Run `/solo:build design` to generate `DESIGN-BRIEF.md`
- **After this command**: Review prototype → schedule user testing → update `/solo:build status`
- **Content launch**: Use `/solo:write blog` to draft a launch announcement

## Skills Used

- `stitch-loop` — AI-generated screens (standalone)
- `figma-prototype` — Interactive Figma prototype (supercharged)
- `storyboard` — Scene planning for demo videos
- `voiceover-generator` — Audio narration scripts
- `stitch-asset-bridge` — Prepare screens for Remotion
- `prototype-to-video` — Full video orchestration
- `remotion-video-generator` — Remotion code and rendering
