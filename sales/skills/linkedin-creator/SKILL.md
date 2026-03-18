---
name: linkedin-creator
description: >
  Generates "Grade A" LinkedIn content by merging "Solo Authority Architecture" (Hooks, Formatting, Carousels) with "360Brew Save-Worthy Assets".
  Supports Bilingual generation (EN/FR).
  Loads context from `data/2-Domaines/sales-profile.json`, `data/2-Domaines/voice-dna.json`, and `data/2-Domaines/icp.json`.
  Enforces Mobile-First Scannability and "No-Slop" writing.
bundle: linkedin-social
triggers:
  - "create LinkedIn post"
  - "write LinkedIn content"
  - "LinkedIn carousel"
tools:
  standalone: [filesystem]
  supercharged: [linkedin]
version: 1.0.0
---

# LinkedIn Creator (The Author)

**The Ultimate Content Engine**: Combines the "Solo Authority" architecture (Dwell Time, Scroll-Stop Hooks, Carousel Flow) with the "Sales OS" strategy (Save-Worthy Assets).

## Configuration

- **Reads**: `data/2-Domaines/sales-profile.json` (Language, Geo, Methodology).
- **Reads**: `data/2-Domaines/voice-dna.json` (Tone, Stylometry).
- **Reads**: `data/2-Domaines/icp.json` (Pain points, Jargon).
- **Reads**: `data/2-Domaines/business-profile.json` (Positioning).

## Triggers

- "create post"
- "write linkedin"
- "draft authority post"
- "hooks"
- "create carousel"

## Core Philosophy: The "Save-Worthy" Asset (Sales OS)

360Brew values a **Save (5x)** more than a Like.
The goal is to create content users bookmark for future reference.

**The Utility Test**: "Can the reader use this to save 2 hours of work today?"

---

## 🏛 The Authority Architecture (Solo Intelligence)

### 1. Hook Engineering (First 140 Chars)

The first 2 lines determine 80% of the post's success.
**The Rule**: Create a narrative gap that forces a "See More" click.

**The Vault (Formulas):**

**A. The Contrarian Leader (High Authority)**

- _Formula_: "[Accepted Truth] is the reason you're failing at [Result]."
- _EN_: "Posting daily is why your reach is dying."
- _FR_: "Publier tous les jours tue votre portée."

**B. The Evidence-Based (High Credibility)**

- _Formula_: "From [Metric A] to [Metric B] in [Time]. No ads."
- _EN_: "From 0 to $10k MRR in 30 days. Here is the breakdown:"
- _FR_: "De 0 à 10k€ de MRR en 30 jours. Voici le détail :"

**C. The Value-First (High Utility)**

- _Formula_: "I found a [Tool/Method] that shaves [X hours] off my [Workflow]."
- _EN_: "The 1-page roadmap to Agentic Sales (No fluff):"
- _FR_: "La roadmap d'une page pour la Vente Agentique (Sans bla-bla) :"

### 2. Dwell-Time Formatting (Mobile-First)

- **The Rule of Two**: Never more than 2 lines per paragraph.
- **Visual Anchors**: Use specific emojis as signs, not decoration.
  - 🚀 (Result), 💡 (Insight), ✅ (Action), ⚠️ (Mistake).
- **Whitespace**: Blank line after every block.

### 3. The "No-Slop" Protocol

- **Banned Words**: "Delve", "Tapestry", "Unlock", "Game-changer", "In today's landscape".
- **Bridge Removal**: Cut "It is important to note..." -> Just state the fact.

---

## Asset Types (Content Modes)

### Mode 1: The Modular Schema (Technical Authority)

**Goal**: Share a specific structure (SQL, JSON, Workflow).
**Structure**: Hook -> Context -> **The Code Block** -> CTA (Save).

````markdown
[HOOK]
Most CRMs fail because the data structure is rigid.

[CONTEXT]
We switched to a graph-based schema.

[THE ASSET]
Here is the JSON structure:

```json
{ "node": "client", "edge": "referral" }
```
````

[CTA]
Save this for your next migration.

````

### Mode 2: The Logic Map (Process Authority)
**Goal**: Visualize a complex decision tree.
**Structure**: Hook -> The Problem -> **ASCII Flowchart** -> CTA (Save).

```markdown
[HOOK]
Automation isn't magic. It's logic.

[THE MAP]
Trigger -> Filter (Is ICP?) -> Yes -> Enrich -> No -> Discard.
````

### Mode 3: The Rapid PRD (Product Authority)

**Goal**: Share a requirements document template.
**Structure**: Hook -> The Waste -> **The Template** -> CTA (Save).

### Mode 4: The Carousel (Retention Architecture)

**Goal**: High Dwell Time (10+ clicks). Uses "Solo Retention Flow".
**Structure**: 10 Slides (PDF).

**The Retention Flow**:

1.  **Slide 01 (Cover)**: High Contrast Hook. (e.g., "Stop doing X.")
2.  **Slide 02 (Stakes)**: The "Why". (e.g., "It costs you $X/year.")
3.  **Slide 03 (Guide)**: Who you are + The Framework Intro.
4.  **Slide 04-07 (The Meat)**: 1 Nugget per slide. Max 30 words/slide.
    - _Retention Engineering_: Use "Cliffhangers" (e.g., "But here is the catch...") at simple slide bottoms.
5.  **Slide 08 (Recap)**: The "Aha!" summary.
6.  **Slide 09 (Result)**: The Proof/Case Study.
7.  **Slide 10 (CTA)**: "Want the PDF? Comment [KEYWORD]."

---

## Bilingual Workflow

1.  **Detect Language**: Check `sales-profile.json` or User Request.
2.  **Apply Logic**:
    - IF `French`: Use FR Hooks ("Le Vrai Problème"), FR formatting conventions (spaces before colons/interro).
    - IF `English`: Use EN Hooks ("The Real Problem").

## Output Format

```
✅ SELECTED VARIATION (Mode: Carousel)
Language: [EN/FR]
Hook Strategy: [Contrarian / Evidence / Value]

[THE POST CAPTION]
(Hook + "Swipe to see the full framework" + Bullets + CTA)

[THE CAROUSEL SLIDES]
Slide 1 (Cover): [Text]
Slide 2 (Stakes): [Text]
...
Slide 10 (CTA): [Text]

---
🧠 Authority Check:
- Captures Retention Flow? Yes.
- Slides < 40 words? Yes.
- Cliffhanger used? Yes (Slide 5).
```

## Quality Control (Automated via Hooks)

- **Antislop Check**: The `hook-system` automatically runs `antislop-expert` on your output.
- **Fail Criteria**: If Slop Score > 3, the output is rejected and regenerated.
- **Manual Override**: Use `/sales:antislop` to manually check any text.

## Execution

- **Drafting**: Use `linkedin-creator` to generate.
- **Publishing**: Use **Claude for Chrome** -> "Start a post" -> Upload PDF.
- **Scheduling**: **NEVER POST IMMEDIATELY**. Use the Clock icon (Tue/Thu AM).

## References

- [Hook Library (EN)](./references/hook-library.md) / [Hook Library (FR)](./references/hook-library.fr.md)
- [Formatting Guide (EN)](./references/formatting-guide.md) / [Formatting Guide (FR)](./references/formatting-guide.fr.md)
- [Carousel Blueprint (EN)](./references/carousel-blueprint.md) / [Carousel Blueprint (FR)](./references/carousel-blueprint.fr.md)
- [Engagement Framework (EN)](./references/engagement-framework.md) / [Engagement Framework (FR)](./references/engagement-framework.fr.md)
