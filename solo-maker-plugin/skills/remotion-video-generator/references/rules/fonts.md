# Remotion Typography System: Brand Consistency in Motion

In digital video production, typography is not just "text on a screen"; it is a set of design tokens that must remain consistent across your product demos, ad scripts, and tutorial videos.

---

## 1. Automated Font Loading Architecture

We use the `@remotion/google-fonts` package to ensure that your video renders identically across local development machines and Cloud renderers (like Lambda).

### The Implementation Pattern

```typescript
import { loadFont } from "@remotion/google-fonts/Inter";
import { loadFont as loadHeading } from "@remotion/google-fonts/Outfit";

// Load specific weights to optimize bundle size
const { fontFamily: bodyFont } = loadFont({ weights: ["400", "600"] });
const { fontFamily: headingFont } = loadHeading({ weights: ["700"] });

// Export for usage in your React components
export const THEME_FONTS = {
  body: bodyFont,
  heading: headingFont,
};
```

---

## 2. Typography Hierarchy (Responsive Video Design)

Unlike web design, video typography must be legible on small mobile screens (Reels/TikTok) and desktop monitors simultaneously.

| Element              | Size (px) |   Weight   | Line Height | Vertical Bias           |
| :------------------- | :-------: | :--------: | :---------: | :---------------------- |
| **H1 Headline**      | 110 - 140 | 700 (Bold) |     1.1     | Top-third of frame      |
| **P Body Copy**      |  56 - 72  | 400 (Reg)  |     1.4     | Middle of frame         |
| **Subtitle/Caption** |  44 - 60  | 600 (Semi) |     1.2     | Lower-third (Safe Zone) |
| **Call-to-Action**   |  48 - 64  | 700 (Bold) |     1.0     | Centered or Bottom      |

---

## 3. The "Safe Zone" Protocol (Legibility)

Never place essential text in the outer 10% of the video frame.

- **Rule**: Keep critical typography within the "Action Safe" area (inner 90%).
- **Rule**: Captions must be placed above the 200px bottom margin to avoid being covered by UI elements on TikTok/Instagram.

---

## 4. Animation Principles for Text

Text shouldn't just "appear." It should "arrive."

- **Entry**: Use `spring()` for a professional, physics-based bounce.
- **Duration**: Allow at least 2.5 seconds per sentence for readability.
- **Highlighting**: Use color-coding from `brand-assets.json` to highlight key words within a sentence (e.g., "Save **5 hours** every week").

---

## 5. Implementation Strategy

When using the `remotion-video-generator` skill:

1.  **Initialize**: The agent will auto-inject the `Inter` font by default.
2.  **Override**: If you have a custom font in your `voice-dna.json`, the agent will attempt to load it via the Google Fonts API.
3.  **Optimize**: Use the Typography Hierarchy above to ensure your demo looks professional.
