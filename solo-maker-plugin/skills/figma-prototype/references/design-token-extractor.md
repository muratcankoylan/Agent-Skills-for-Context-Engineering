# Design Token Extractor

Automated extraction of design tokens from multiple sources to ensure brand consistency across all prototypes.

---

## Token Sources (Priority Order)

### 1. voice-dna.json

**Location**: `data/2-Domaines/voice-dna.json`

**Extractable Tokens**:

- **Tone** → Color palette mapping
- **Style** → Typography choices
- **Personality** → UI pattern preferences

**Extraction Logic**:

```python
voice = read_json("data/2-Domaines/voice-dna.json")

# Tone-based color mapping
tone_colors = {
    "professional": {
        "primary": "#2563EB",    # Blue
        "accent": "#10B981",     # Green
        "neutral": "#6B7280"     # Gray
    },
    "playful": {
        "primary": "#8B5CF6",    # Purple
        "accent": "#F59E0B",     # Orange
        "neutral": "#EC4899"     # Pink
    },
    "technical": {
        "primary": "#0EA5E9",    # Cyan
        "accent": "#14B8A6",     # Teal
        "neutral": "#64748B"     # Slate
    },
    "luxury": {
        "primary": "#1F2937",    # Dark Gray
        "accent": "#D97706",     # Gold
        "neutral": "#9CA3AF"     # Light Gray
    },
    "friendly": {
        "primary": "#3B82F6",    # Blue
        "accent": "#F472B6",     # Pink
        "neutral": "#A78BFA"     # Purple
    }
}

tone = voice.get("tone", "professional")
colors = tone_colors.get(tone, tone_colors["professional"])

# Style-based typography
if "technical" in voice.get("keywords", []):
    font_family = "JetBrains Mono, Consolas, monospace"
    font_weight = "400"
elif "elegant" in voice.get("keywords", []):
    font_family = "Playfair Display, Georgia, serif"
    font_weight = "300"
else:
    font_family = "Inter, -apple-system, sans-serif"
    font_weight = "400"
```

---

### 2. business-profile.json

**Location**: `data/2-Domaines/business-profile.json`

**Extractable Tokens**:

- **Company name** → Logo text
- **Tagline** → Hero subheadline
- **Industry** → Icon style preferences

**Extraction Logic**:

```python
profile = read_json("data/2-Domaines/business-profile.json")

company_name = profile.get("name", "Your Company")
tagline = profile.get("tagline", "")
industry = profile.get("industry", "general")

# Industry-based icon style
icon_styles = {
    "tech": "outline",        # Clean, minimal
    "finance": "solid",       # Professional, trustworthy
    "creative": "duotone",    # Colorful, expressive
    "healthcare": "rounded",  # Friendly, approachable
    "general": "outline"      # Default
}

icon_style = icon_styles.get(industry, "outline")
```

---

### 3. Brand Assets (data/3-Ressources/brand/)

**Location**: `data/3-Ressources/brand/`

**Extractable Tokens**:

- **Logo** → Primary brand color (from dominant color)
- **Style guide PDF** → Full design system (if available)
- **Images** → Color palette extraction

**Extraction Logic**:

```python
import os
from PIL import Image
import colorsys

brand_dir = "data/3-Ressources/brand/"

# Check for logo
logo_files = glob(f"{brand_dir}logo.*")
if logo_files:
    logo_path = logo_files[0]

    # Extract dominant color from logo
    img = Image.open(logo_path)
    colors = img.getcolors(img.size[0] * img.size[1])
    dominant_color = max(colors, key=lambda x: x[0])[1]

    # Convert to hex
    primary_color = "#{:02x}{:02x}{:02x}".format(*dominant_color[:3])
else:
    primary_color = None  # Use default from voice-dna
```

---

### 4. Figma File (if ~~design connected)

**Requires**: `~~design` MCP connector

**Extractable Tokens**:

- **Color styles** → Full color palette
- **Text styles** → Typography system
- **Effect styles** → Shadows, blurs
- **Component library** → Reusable components

**Extraction Logic**:

```python
# Requires Figma API access via ~~design MCP
figma_file_url = ask_user("Figma file URL (optional):")

if figma_file_url and has_tool("~~design"):
    file_key = extract_file_key(figma_file_url)

    # Get color styles
    color_styles = figma_api.get_local_paint_styles(file_key)
    colors = {
        style["name"]: rgb_to_hex(style["paints"][0]["color"])
        for style in color_styles
    }

    # Get text styles
    text_styles = figma_api.get_local_text_styles(file_key)
    typography = {
        style["name"]: {
            "fontFamily": style["fontFamily"],
            "fontSize": style["fontSize"],
            "fontWeight": style["fontWeight"],
            "lineHeight": style["lineHeight"]
        }
        for style in text_styles
    }
```

---

### 5. Professional Defaults

**Fallback** when no other sources available.

**Default Tokens**:

```json
{
  "colors": {
    "primary": "#2563EB",
    "accent": "#10B981",
    "neutral": "#6B7280",
    "background": "#FFFFFF",
    "surface": "#F9FAFB",
    "text": "#111827",
    "textSecondary": "#6B7280",
    "border": "#E5E7EB",
    "error": "#EF4444",
    "success": "#10B981",
    "warning": "#F59E0B"
  },
  "typography": {
    "fontFamily": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    "fontSizeBase": "16px",
    "fontWeightNormal": "400",
    "fontWeightMedium": "500",
    "fontWeightBold": "700",
    "lineHeight": "1.5",
    "headingFontFamily": "Inter, sans-serif",
    "headingFontWeight": "700"
  },
  "spacing": {
    "unit": "8px",
    "xs": "4px",
    "sm": "8px",
    "md": "16px",
    "lg": "24px",
    "xl": "32px",
    "2xl": "48px"
  },
  "borderRadius": {
    "sm": "4px",
    "md": "8px",
    "lg": "12px",
    "full": "9999px"
  },
  "shadows": {
    "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
    "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1)"
  }
}
```

---

## Complete Extraction Workflow

### Step 1: Initialize Token Object

```python
tokens = {
    "colors": {},
    "typography": {},
    "spacing": {},
    "borderRadius": {},
    "shadows": {}
}
```

### Step 2: Extract from Sources (Priority Order)

```python
# 1. Load defaults first
tokens = load_defaults()

# 2. Override with Figma (if available)
if figma_file_url and has_tool("~~design"):
    figma_tokens = extract_from_figma(figma_file_url)
    tokens = merge_tokens(tokens, figma_tokens)

# 3. Override with brand assets
if os.path.exists("data/3-Ressources/brand/"):
    brand_tokens = extract_from_brand_assets()
    tokens = merge_tokens(tokens, brand_tokens)

# 4. Override with business profile
if os.path.exists("data/2-Domaines/business-profile.json"):
    profile_tokens = extract_from_business_profile()
    tokens = merge_tokens(tokens, profile_tokens)

# 5. Override with voice DNA (highest priority for colors/typography)
if os.path.exists("data/2-Domaines/voice-dna.json"):
    voice_tokens = extract_from_voice_dna()
    tokens = merge_tokens(tokens, voice_tokens)
```

### Step 3: Validate Tokens

```python
# Ensure all required tokens exist
required_keys = {
    "colors": ["primary", "accent", "background", "text"],
    "typography": ["fontFamily", "fontSizeBase"],
    "spacing": ["unit"],
    "borderRadius": ["md"]
}

for category, keys in required_keys.items():
    for key in keys:
        if key not in tokens[category]:
            raise ValueError(f"Missing required token: {category}.{key}")
```

### Step 4: Save to design-tokens.json

```python
output_path = "data/1-Projets/[project]/prototype/design-tokens.json"
save_json(output_path, tokens)
```

---

## Token Application

### HTML/CSS Prototypes

Generate CSS variables from tokens:

```css
:root {
  /* Colors */
  --color-primary: #2563eb;
  --color-accent: #10b981;
  --color-text: #111827;

  /* Typography */
  --font-family: Inter, sans-serif;
  --font-size-base: 16px;
  --font-weight-normal: 400;

  /* Spacing */
  --spacing-unit: 8px;
  --spacing-md: 16px;

  /* Border Radius */
  --radius-md: 8px;
}

/* Apply to components */
button {
  background-color: var(--color-primary);
  font-family: var(--font-family);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
}
```

### Figma Prototypes

Create Figma styles from tokens:

```python
# Create color styles
for name, hex_value in tokens["colors"].items():
    figma_api.create_paint_style(name, hex_value)

# Create text styles
for name, props in tokens["typography"].items():
    figma_api.create_text_style(
        name,
        font_family=props["fontFamily"],
        font_size=props["fontSize"],
        font_weight=props["fontWeight"]
    )
```

---

## Example: Complete Extraction

**Input Files**:

- `voice-dna.json`: `{"tone": "professional", "keywords": ["technical", "trustworthy"]}`
- `business-profile.json`: `{"name": "DataFlow", "industry": "tech"}`
- `brand/logo.png`: Dominant color = `#1E40AF` (dark blue)

**Output** (`design-tokens.json`):

```json
{
  "colors": {
    "primary": "#1E40AF",
    "accent": "#10B981",
    "neutral": "#6B7280",
    "background": "#FFFFFF",
    "text": "#111827"
  },
  "typography": {
    "fontFamily": "JetBrains Mono, monospace",
    "fontSizeBase": "16px",
    "fontWeightNormal": "400",
    "lineHeight": "1.5"
  },
  "spacing": {
    "unit": "8px",
    "md": "16px",
    "lg": "24px"
  },
  "borderRadius": {
    "md": "8px"
  }
}
```

**Reasoning**:

- Primary color from logo (`#1E40AF`)
- Accent color from "professional" tone (`#10B981`)
- Font from "technical" keyword (`JetBrains Mono`)
- Spacing/radius from defaults
