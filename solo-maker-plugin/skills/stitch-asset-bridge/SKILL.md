---
name: stitch-asset-bridge
description: >
  Automates the transfer of assets from Stitch or Figma prototypes to Remotion video
  projects. Handles screenshot detection, normalization, naming, and manifest creation.
  Triggers when "prototype-to-video" runs or on "prepare assets for video".
bundle: video-media
triggers:
  - "prepare assets for video"
  - "transfer Stitch assets"
  - "asset bridge"
tools:
  standalone: [stitch]
  supercharged: [stitch]
version: 1.0.0
---

# Skill: Stitch/Figma Asset Bridge

Critical automation component in the Prototype-to-Video pipeline. Acts as the bridge between prototype output (Stitch or Figma) and Remotion video input. Not typically invoked directly — called by `prototype-to-video` after prototype assets are generated.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Process local screenshot directories                         │
│  ✓ Normalize, rename, and resize image assets                   │
│  ✓ Generate asset-manifest.json for Remotion consumption        │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~design)                                │
│  + Export frames directly from Figma via ~~design connector     │
│  + Extract design tokens (colors, fonts, spacing) for Remotion  │
│  + Pull component names and layer metadata for scene labeling   │
└─────────────────────────────────────────────────────────────────┘
```

## Asset Detection Pipeline

### Step 1: Locate Source Assets (Multi-Source Ingest)

Scan for prototype output from **multiple sources** in priority order:

| Source                  | Location                                       | Format           | Notes                 |
| ----------------------- | ---------------------------------------------- | ---------------- | --------------------- |
| Stitch output           | `data/1-Projets/[project]/stitch-output/`      | PNG screenshots  | Primary source        |
| Figma export            | `data/1-Projets/[project]/figma-export/`       | PNG/SVG frames   | High-fidelity designs |
| Manual upload           | `data/1-Projets/[project]/screens/`            | Any image format | User-provided screens |
| **Competitor captures** | `data/1-Projets/[project]/competitor-screens/` | PNG/JPG          | Benchmarking visuals  |
| **Browser screenshots** | `data/1-Projets/[project]/browser-captures/`   | PNG              | Live site captures    |

**Multi-Source Merge**: If assets exist in multiple locations, merge them:

```python
all_assets = []

# Priority 0: Live Figma Extraction via MCP
if input.get("figma_url") and has_tool("figma_get_file"):
    figma_file_id = extract_id(input["figma_url"])
    file_data = figma_get_file(file_id=figma_file_id)

    # Extract top-level frames
    target_frames = get_top_level_frames(file_data)
    frame_ids = [frame.id for frame in target_frames]

    # Render and download images via MCP
    image_urls = figma_get_image(file_id=figma_file_id, ids=",".join(frame_ids), format="png", scale=2)
    download_images(image_urls, to="data/1-Projets/[project]/figma-export/")

    # We now have our primary assets
    all_assets.extend(glob("figma-export/*.png"))

# Priority 1: Stitch output
if exists("stitch-output/"):
    all_assets.extend(glob("stitch-output/*.png"))

# Priority 2: Figma export (manual or previously downloaded)
if exists("figma-export/") and not input.get("figma_url"):
    all_assets.extend(glob("figma-export/*.png"))

# Priority 3: Manual screens
if exists("screens/"):
    all_assets.extend(glob("screens/*"))

# Priority 4: Competitor captures
if exists("competitor-screens/"):
    competitor_assets = glob("competitor-screens/*")
    # Mark as competitor for different treatment
    for asset in competitor_assets:
        asset["type"] = "competitor"
    all_assets.extend(competitor_assets)

# Priority 5: Browser captures
if exists("browser-captures/"):
    all_assets.extend(glob("browser-captures/*.png"))

if not all_assets:
    prompt_user("No prototype screens found. Please export your prototype screens or provide a Figma URL.")
```

### Step 2: Detect and Catalog Assets

For each image file in the source directory:

1. **Identify** — Read filename, dimensions, format, file size
2. **Classify** — Determine screen type from filename or content:
   - `screen-*` → App screen
   - `component-*` → UI component
   - `icon-*` → Icon asset
   - `bg-*` → Background
3. **Order** — Detect sequence from:
   - Numeric prefix (01-, 02-, 03-)
   - Alphabetical order if no prefix
   - Storyboard order from `storyboard.md` if available

### Step 3: Normalize Assets (with Smart Cropping)

Apply these transformations:

| Property       | Rule                              | Default              |
| -------------- | --------------------------------- | -------------------- |
| **Format**     | Convert to PNG                    | PNG                  |
| **Dimensions** | Resize to target video resolution | 1920x1080            |
| **Cropping**   | Smart crop to zones of interest   | Auto-detect          |
| **Naming**     | `screen-[NN]-[slug].png`          | Sequential numbering |
| **Quality**    | Compress if >2MB per file         | 85% quality          |

**Smart Cropping Algorithm**:

```python
def smart_crop(image):
    """
    Auto-detect zones of interest for video framing.
    Prioritizes UI elements over whitespace.
    """
    # Detect content boundaries
    content_box = detect_content_box(image)  # Returns (x, y, width, height)

    # Calculate padding (10% of content size)
    padding = int(min(content_box.width, content_box.height) * 0.1)

    # Expand box with padding
    crop_box = (
        max(0, content_box.x - padding),
        max(0, content_box.y - padding),
        min(image.width, content_box.x + content_box.width + padding),
        min(image.height, content_box.y + content_box.height + padding)
    )

    # Crop and resize to target resolution
    cropped = image.crop(crop_box)
    resized = cropped.resize((1920, 1080), Image.LANCZOS)

    return resized

def detect_content_box(image):
    """
    Find the bounding box of non-whitespace content.
    """
    # Convert to grayscale
    gray = image.convert('L')

    # Threshold to find content (non-white pixels)
    threshold = 250  # Pixels darker than this are "content"
    content_pixels = [(x, y) for x in range(gray.width) for y in range(gray.height) if gray.getpixel((x, y)) < threshold]

    # Find bounding box
    if content_pixels:
        xs = [p[0] for p in content_pixels]
        ys = [p[1] for p in content_pixels]
        return BoundingBox(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    else:
        # No content detected, return full image
        return BoundingBox(0, 0, gray.width, gray.height)
```

### Step 4: Generate Manifest

Create `asset-manifest.json` in the project directory:

```json
{
  "project": "[project-name]",
  "strategy": "[standard | tiktok]",
  "generated": "[ISO timestamp]",
  "resolution": {
    "width": "[1920 | 1080 (tiktok)]",
    "height": "[1080 | 1920 (tiktok)]"
  },
  "screens": [
    {
      "id": "screen-01",
      "file": "screens/screen-01-dashboard.png",
      "label": "Dashboard Overview",
      "order": 1,
      "duration": 3,
      "transition": "fade"
    },
    {
      "id": "screen-02",
      "file": "screens/screen-02-profile.png",
      "label": "User Profile",
      "order": 2,
      "duration": 3,
      "transition": "slide-left"
    }
  ],
  "designTokens": {
    "primaryColor": "#[extracted or default]",
    "fontFamily": "[extracted or default]",
    "borderRadius": "[extracted or default]"
  }
}
```

_Note on strategy_: If the `strategy` is `tiktok`, the generator must ensure the aspect ratio is 9:16 (1080x1920) and format the manifest to accommodate Remotion's TikTok template expectations (e.g., shorter base durations, space allocated for word-by-word captions).

### Step 5: Deploy to Remotion

Copy processed assets to the Remotion project structure:

```
remotion-project/
├── public/
│   └── screens/           ← normalized PNGs go here
├── src/
│   └── asset-manifest.json ← manifest goes here
```

### Step 6: Asset Quality Report

Generate a quality report for all processed assets:

```python
quality_report = {
    "total_assets": len(all_assets),
    "processed": len(processed_assets),
    "issues": []
}

for asset in processed_assets:
    # Check dimensions
    if asset.width != 1920 or asset.height != 1080:
        quality_report["issues"].append({
            "file": asset.filename,
            "issue": "Incorrect dimensions",
            "expected": "1920x1080",
            "actual": f"{asset.width}x{asset.height}"
        })

    # Check resolution (DPI)
    if asset.dpi < 72:
        quality_report["issues"].append({
            "file": asset.filename,
            "issue": "Low resolution",
            "expected": "≥72 DPI",
            "actual": f"{asset.dpi} DPI"
        })

    # Check file size
    if asset.size_mb > 2:
        quality_report["issues"].append({
            "file": asset.filename,
            "issue": "File too large",
            "expected": "≤2MB",
            "actual": f"{asset.size_mb}MB"
        })

    # Check visual coherence (color palette consistency)
    if not matches_design_tokens(asset, design_tokens):
        quality_report["issues"].append({
            "file": asset.filename,
            "issue": "Color palette mismatch",
            "expected": f"Primary: {design_tokens['primary']}",
            "actual": f"Detected: {asset.dominant_color}"
        })

# Save report
save_json("data/1-Projets/[project]/prototype/asset-quality-report.json", quality_report)

# Print summary
if quality_report["issues"]:
    warn(f"Found {len(quality_report['issues'])} quality issues. See asset-quality-report.json for details.")
else:
    success(f"All {quality_report['total_assets']} assets passed quality checks.")
```

**Quality Report Output**:

```json
{
  "total_assets": 12,
  "processed": 12,
  "issues": [
    {
      "file": "screen-03-profile.png",
      "issue": "File too large",
      "expected": "≤2MB",
      "actual": "3.2MB"
    },
    {
      "file": "screen-07-settings.png",
      "issue": "Color palette mismatch",
      "expected": "Primary: #2563EB",
      "actual": "Detected: #FF5733"
    }
  ]
}
```

### Step 7: Cleanup

- Remove any assets in the Remotion directory not present in the new manifest
- Archive previous manifest version (rename to `asset-manifest.backup.json`)
- Report summary: "[X] screens processed, [Y] new, [Z] removed, [W] quality issues"

## Design Token Extraction

When connected to `~~design` (Figma), extract:

| Token         | Source                 | Usage in Remotion                |
| ------------- | ---------------------- | -------------------------------- |
| Colors        | Figma color styles     | Background colors, text overlays |
| Fonts         | Figma text styles      | Title/subtitle typography        |
| Spacing       | Figma auto-layout      | Animation padding/margins        |
| Border radius | Figma frame properties | Screen frame styling             |

Tokens are included in `asset-manifest.json` under `designTokens` for Remotion to consume.

## Integration

- **Upstream:** Receives assets from `figma-prototype` or `stitch-loop`
- **Downstream:** Feeds `remotion-video-generator` via `asset-manifest.json`
- **Orchestrated by:** `prototype-to-video` skill
- **Storyboard link:** Uses scene order from `storyboard` skill output if available
