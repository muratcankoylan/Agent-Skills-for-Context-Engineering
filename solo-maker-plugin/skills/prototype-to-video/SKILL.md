---
name: prototype-to-video
description: "Video Narrative Engine. Orchestrates prototype-to-video conversion with intelligent scripting, narrative variants, and timing optimization. Triggers on 'make demo video', 'render prototype', 'video walkthrough', 'product demo'."
bundle: video-media
triggers:
  - "make demo video"
  - "render prototype"
  - "video walkthrough"
tools:
  standalone: [filesystem]
  supercharged: [figma]
version: "3.0.0"
---

# Skill: Prototype-to-Video Narrative Engine

This is a **High-Level Orchestrator** that transforms static prototypes into compelling video narratives. It doesn't just "make a video"—it tells a **strategic story** optimized for your audience (users, investors, or stakeholders). Coordinates 4-5 skills to produce a professional MP4 demo with voiceover, smooth transitions, and narrative intelligence.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Narrative Variants: 3 pre-built arcs (Product Demo, Investor │
│    Pitch, User Onboarding) optimized for different audiences.   │
│  ✓ Script Engine: Auto-generate voiceover from problem-statement│
│    + voice-dna.json for brand-consistent narration.             │
│  ✓ Timing Algorithms: Calculate optimal screen duration based on│
│    UI complexity and text density.                              │
│  ✓ Storyboard Generation: Strategic narrative arc with hooks.   │
│  ✓ Frame Management: Organize screenshot sequences and names.   │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~video / Remotion)                      │
│  + Automatic Rendering: Render final MP4 via Remotion CLI.      │
│  + Dynamic Overlays: Add mouse pointers, typing effects, UI     │
│    highlights, zoom animations automatically.                   │
│  + Professional Transitions: Fade, slide, zoom between scenes.  │
│  + Audio Mixing: Combine voiceover + background music.          │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠 Triggers

- "Turn my [Project] prototype into a demo video"
- "Create a video walkthrough for our MVP"
- "Generate a Remotion video from these designs"
- "I need a marketing video for my product launch"
- "Make an investor pitch video"
- "Create user onboarding video"

---

## 🎬 Narrative Variants

Choose the narrative arc based on your **audience** and **goal**:

### Variant 1: Product Demo (60 seconds)

**Audience**: Potential users, marketing campaigns, social media  
**Goal**: Show value quickly, drive signups/trials

**Structure**:

1. **Hook** (0:00-0:05) — Provocative question or bold claim
2. **Pain** (0:05-0:15) — Visualize the problem (before state)
3. **Reveal** (0:15-0:20) — "Introducing [Product Name]"
4. **Walkthrough** (0:20-0:50) — 3 core features in action
5. **Outcome** (0:50-0:60) — Success state (dashboard, "Done")
6. **CTA** (0:60) — "Get started free at [URL]"

**Tone**: Energetic, benefit-focused, fast-paced  
**Voiceover Style**: Conversational, enthusiastic

**See**: [narrative-variants.md](./references/narrative-variants.md) for full script template.

---

### Variant 2: Investor Pitch (90 seconds)

**Audience**: Investors, stakeholders, board members  
**Goal**: Demonstrate market opportunity, traction, vision

**Structure**:

1. **Problem** (0:00-0:15) — Market pain + size (TAM/SAM/SOM)
2. **Solution** (0:15-0:30) — Product overview + unique value prop
3. **Demo** (0:30-0:60) — Key features + competitive advantage
4. **Traction** (0:60-0:75) — Metrics, testimonials, early wins
5. **Vision** (0:75-0:90) — Roadmap, ask (funding, partnership)

**Tone**: Professional, data-driven, confident  
**Voiceover Style**: Authoritative, measured pace

**See**: [narrative-variants.md](./references/narrative-variants.md) for full script template.

---

### Variant 3: User Onboarding (120 seconds)

**Audience**: New users, customer success, support teams  
**Goal**: Educate users, reduce support tickets, increase activation

**Structure**:

1. **Welcome** (0:00-0:10) — "Welcome to [Product]! Here's how it works."
2. **Setup** (0:10-0:30) — Account creation, initial configuration
3. **Core Workflow** (0:30-0:90) — Step-by-step walkthrough of main use case
4. **Advanced Features** (0:90-0:110) — Optional power-user features
5. **Next Steps** (0:110-0:120) — "Try it yourself" + support resources

**Tone**: Friendly, educational, patient  
**Voiceover Style**: Calm, instructional, reassuring

**See**: [narrative-variants.md](./references/narrative-variants.md) for full script template.

---

## 🎙️ Script Engine

**Auto-generate voiceover scripts** from project context files.

### Input Sources

1. **`problem-statement.md`** — The core problem being solved
2. **`voice-dna.json`** — Brand tone and personality
3. **`PRD.md`** — Product features and benefits
4. **`user-stories.md`** — User goals and workflows
5. **`business-profile.json`** — Company name, tagline

### Script Generation Logic

```python
# Read context files
problem = read_file("data/1-Projets/[project]/problem.md")
voice = read_json("data/2-Domaines/voice-dna.json")
prd = read_file("data/1-Projets/[project]/PRD.md")

# Extract key elements
pain_point = extract_pain_point(problem)  # e.g., "Freelancers waste 10 hours/week on admin"
solution = extract_solution(prd)          # e.g., "AI-powered invoicing in 60 seconds"
tone = voice.get("tone", "professional")  # e.g., "friendly", "technical"

# Generate script based on narrative variant
if variant == "Product Demo":
    hook = generate_hook(pain_point, tone)  # "Tired of chasing late payments?"
    reveal = f"Introducing {product_name}. {solution}."
    walkthrough = generate_feature_scripts(prd, max_features=3)
    cta = f"Get started free at {website_url}"

    script = {
        "hook": hook,
        "pain": pain_point,
        "reveal": reveal,
        "walkthrough": walkthrough,
        "outcome": "Your invoices, sent and tracked automatically.",
        "cta": cta
    }
```

**Output**: `data/1-Projets/[project]/prototype/video-script.md`

---

## ⏱️ Timing Algorithms

**Calculate optimal screen duration** based on UI complexity and text density.

### Timing Rules

| Screen Type               | Base Duration | Adjustments           |
| ------------------------- | ------------- | --------------------- |
| **Simple** (1-3 elements) | 2 seconds     | +0.5s per text block  |
| **Medium** (4-7 elements) | 3 seconds     | +0.5s per text block  |
| **Complex** (8+ elements) | 4 seconds     | +1s per text block    |
| **Form/Input**            | 3 seconds     | +1s per field         |
| **Dashboard**             | 5 seconds     | +0.5s per metric card |

### Timing Calculation

```python
def calculate_screen_duration(screen):
    # Count UI elements
    element_count = count_elements(screen)

    # Count text blocks
    text_blocks = count_text_blocks(screen)

    # Base duration
    if element_count <= 3:
        base = 2.0
    elif element_count <= 7:
        base = 3.0
    else:
        base = 4.0

    # Adjust for text density
    text_adjustment = text_blocks * 0.5

    # Adjust for screen type
    if is_form(screen):
        base += 1.0
    elif is_dashboard(screen):
        base = max(base, 5.0)

    return base + text_adjustment

# Example
screen_1 = {"elements": 5, "text_blocks": 2, "type": "normal"}
duration_1 = calculate_screen_duration(screen_1)  # 3 + (2 * 0.5) = 4 seconds
```

---

## ✅ Quality Checklist

**Before rendering**, validate the video storyboard:

### Pre-Render Checklist

- [ ] **Script matches voice-dna tone** — Verify script tone aligns with brand personality
- [ ] **All screens have voiceover** — No silent screens (except intentional pauses)
- [ ] **Total duration matches target** — Product Demo ≤60s, Investor Pitch ≤90s, Onboarding ≤120s
- [ ] **Transitions are smooth** — No jarring cuts between unrelated screens
- [ ] **CTA is clear** — Final screen has obvious next step (URL, button, etc.)
- [ ] **Branding is consistent** — Logo, colors, fonts match design tokens
- [ ] **Audio levels balanced** — Voiceover audible, background music subtle (if used)
- [ ] **Timing feels natural** — No screens too fast (\u003c2s) or too slow (\u003e6s)

### Post-Render Checklist

- [ ] **Video plays without errors** — No black screens, glitches, or audio sync issues
- [ ] **Resolution is correct** — 1920x1080 (Full HD) or 1280x720 (HD)
- [ ] **File size is reasonable** — \u003c50MB for 60s video, \u003c100MB for 120s video
- [ ] **Aspect ratio matches platform** — 16:9 for YouTube, 1:1 for Instagram, 9:16 for Stories

---

## 🚀 Complete Workflow (The Orchestration Chain)

### Step 1: Requirement Check

Verify required files exist:

```python
required_files = [
    "data/1-Projets/[project]/prototype/",  # Prototype screens
    "data/1-Projets/[project]/DESIGN-BRIEF.md",
    "data/1-Projets/[project]/problem.md",
    "data/2-Domaines/voice-dna.json"
]

for file in required_files:
    if not exists(file):
        raise FileNotFoundError(f"Missing required file: {file}")
```

### Step 2: Select Narrative Variant

Ask user or auto-detect from context:

```python
variant = ask_user("Video type: [1] Product Demo (60s), [2] Investor Pitch (90s), [3] User Onboarding (120s)?")

if variant == "1":
    narrative = "Product Demo"
    target_duration = 60
elif variant == "2":
    narrative = "Investor Pitch"
    target_duration = 90
else:
    narrative = "User Onboarding"
    target_duration = 120
```

### Step 3: Generate Script

Run the **Script Engine**:

```python
script = generate_script(
    narrative=narrative,
    problem_file="data/1-Projets/[project]/problem.md",
    voice_file="data/2-Domaines/voice-dna.json",
    prd_file="data/1-Projets/[project]/PRD.md"
)

save_file("data/1-Projets/[project]/prototype/video-script.md", script)
```

### Step 4: Create Storyboard

Invoke `storyboard` skill to map screens to script:

```python
storyboard = invoke_skill("storyboard", {
    "script": script,
    "screens": list_files("data/1-Projets/[project]/prototype/screens/"),
    "narrative": narrative
})

save_file("data/1-Projets/[project]/prototype/storyboard.md", storyboard)
```

### Step 5: Calculate Timing

Apply **Timing Algorithms** to each screen:

```python
for scene in storyboard["scenes"]:
    screen = scene["screen"]
    duration = calculate_screen_duration(screen)
    scene["duration"] = duration
```

### Step 6: Generate Voiceover

Invoke `voiceover-generator` skill:

```python
audio_file = invoke_skill("voiceover-generator", {
    "script": script,
    "voice_profile": voice_dna,
    "output": "data/1-Projets/[project]/prototype/voiceover.mp3"
})
```

### Step 7: Process Assets

Invoke `stitch-asset-bridge` to prepare screens for Remotion:

```python
invoke_skill("stitch-asset-bridge", {
    "source": "data/1-Projets/[project]/prototype/screens/",
    "output": "data/1-Projets/[project]/prototype/assets/",
    "storyboard": storyboard
})
```

### Step 8: Render Video

**If Standalone**: Generate video config file for manual rendering  
**If Supercharged**: Invoke `remotion-video-generator` to render MP4

```python
if has_tool("~~video"):
    video_file = invoke_skill("remotion-video-generator", {
        "storyboard": storyboard,
        "assets": "data/1-Projets/[project]/prototype/assets/",
        "audio": audio_file,
        "output": "data/1-Projets/[project]/prototype/demo-video.mp4"
    })
else:
    # Generate config for manual rendering
    config = generate_remotion_config(storyboard, assets, audio)
    save_file("data/1-Projets/[project]/prototype/remotion-config.json", config)
    notify_user("Remotion config generated. Run `npm run render` to create video.")
```

### Step 9: Quality Check

Run the **Quality Checklist**:

```python
issues = []

# Check script tone
if not matches_tone(script, voice_dna):
    issues.append("Script tone doesn't match voice-dna")

# Check duration
total_duration = sum(scene["duration"] for scene in storyboard["scenes"])
if total_duration > target_duration * 1.1:  # Allow 10% overage
    issues.append(f"Video too long: {total_duration}s (target: {target_duration}s)")

# ... more checks

if issues:
    warn_user("Quality issues found:", issues)
```

### Step 10: Output Package

Deliver complete video package:

```
data/1-Projets/[project]/prototype/
├── demo-video.mp4           # Final rendered video
├── video-script.md          # Full voiceover script
├── storyboard.md            # Scene-by-scene breakdown
├── voiceover.mp3            # Audio track
├── assets/                  # Processed screens
└── remotion-config.json     # (If standalone) Rendering config
```

---

## 📈 Agent Instructions

### Decision Tree

```
START
  │
  ├─ Check required files (prototype/, problem.md, voice-dna.json)
  │
  ├─ Select narrative variant (Product Demo / Investor Pitch / Onboarding)
  │
  ├─ Generate script (Script Engine: problem + voice-dna + PRD)
  │
  ├─ Create storyboard (map screens to script scenes)
  │
  ├─ Calculate timing (Timing Algorithms per screen)
  │
  ├─ Generate voiceover (invoke voiceover-generator)
  │
  ├─ Process assets (invoke stitch-asset-bridge)
  │
  ├─ Check if ~~video connected?
  │   ├─ YES → Render via remotion-video-generator
  │   └─ NO  → Generate config for manual rendering
  │
  ├─ Run quality checklist
  │
  └─ Output video package + optimization tips
```

### Output Template

Every video delivery includes:

```markdown
# Video: [Project Name] — [Narrative Variant]

## Overview

- **Type**: [Product Demo / Investor Pitch / User Onboarding]
- **Duration**: [X] seconds
- **Resolution**: 1920x1080 (Full HD)
- **File Size**: [Y] MB

## Narrative Structure

1. [Scene 1]: [Description] (0:00-0:05)
2. [Scene 2]: [Description] (0:05-0:15)
   ...

## Script

[Full voiceover script]

## Assets Used

- [x] prototype screens
- [Y] transitions
- [Z] overlays (mouse pointers, highlights)

## Next Steps

1. **Review video**: [File path or link]
2. **Share**: Optimized for YouTube (16:9), LinkedIn (1:1 crop available)
3. **Iterate**: Update script in `video-script.md` and re-render
4. **Publish**: Upload to [Platform] with description template below

## Social Media Optimization

- **YouTube**: Title, description, tags
- **LinkedIn**: Teaser text, hashtags
- **Twitter**: Thread script (3-5 tweets)
```

---

## 📂 References

- **[narrative-variants.md](./references/narrative-variants.md)** — 3 complete narrative arcs with script templates
- **[demo-video-structure.md](./references/demo-video-structure.md)** — Classic demo video structure
- **[remotion-templates.md](./references/remotion-templates.md)** — Remotion scene component templates
- **[voiceover-styles.md](./references/voiceover-styles.md)** — Voiceover style guide
- **[storyboard-workbook.md](./references/storyboard-workbook.md)** — Storyboarding best practices
