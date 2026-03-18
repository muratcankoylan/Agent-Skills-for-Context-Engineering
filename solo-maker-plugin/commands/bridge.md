---
name: bridge
description: "Bridge a Figma file directly to a Remotion video project. Extracts frames, applies design tokens, normalizes assets, and initializes the video."
argument-hint: "[figma-url] [standard | tiktok]"
---

# `bridge`

This command automates the handoff between Figma (`~~design`) and Remotion (`~~video`), completely eliminating manual asset exports.

## Requirements

The user must provide a Figma file URL.
Example: `/solo-maker:bridge https://www.figma.com/file/.../Project tiktok`

If `[standard | tiktok]` isn't provided, ask the user what format they want the video in.

## Execution Flow

### 1. Ingestion via Figma MCP

You must use the `~~design` connector (e.g., the Figma MCP server).

- **Tool**: `figma_get_file` to read the structure of the provided URL.
- **Action**: Identify all top-level frames inside the primary design page.
- **Token Extraction**: Extract color and font styles used in these frames. Save them to `data/1-Projets/[project]/prototype/design-tokens.json`.
- **Image Rendering**: Use `figma_get_image` (or equivalent tool provided by the MCP) to render the top-level frames as 2x PNGs. Save them temporarily to `data/1-Projets/[project]/figma-export/`.

### 2. Normalization via Asset Bridge

Trigger the `stitch-asset-bridge` skill.

```python
invoke_skill("stitch-asset-bridge", {
    "source": "data/1-Projets/[project]/figma-export/",
    "project": project_name,
    "strategy": requested_format  # "standard" or "tiktok"
})
```

The bridge will crop, resize, and rename the images, then generate the critical `asset-manifest.json` map.

### 3. Remotion Initialization

Initialize the video project in a new directory: `data/1-Projets/[project]/video/`

If `standard`:

```bash
npx create-video@latest data/1-Projets/[project]/video --blank
```

If `tiktok`:

```bash
npx create-video@latest data/1-Projets/[project]/video --tiktok
```

### 4. Integration

- Move the normalized assets from `stitch-asset-bridge` into `data/1-Projets/[project]/video/public/screens/`.
- Move the `asset-manifest.json` into `data/1-Projets/[project]/video/src/`.
- Provide the user with the success message below.

## Output

````markdown
# 🌉 Figma → Remotion Bridge Complete

We have successfully extracted your Figma frames and scaffolded an automated Remotion video project!

**Extracted:**

- [x] High-fidelity screens from Figma
- [Y] Brand tokens (Colors, Fonts)

**Prepared Video:**

- Format: [Standard 16:9 Demo | TikTok 9:16 Short]
- Manifest generated at `video/src/asset-manifest.json`

**Next Steps to Render:**

```bash
cd data/1-Projets/[project]/video
npm install
npm run start  # To preview the orchestration in your browser
npm run render # To export the final .mp4
```
````

```

```
