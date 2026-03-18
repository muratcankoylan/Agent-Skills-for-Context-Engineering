# Scalable Video Schema: Master Input Parameters

This schema defines how data flows from your `business-profile.json` and `discovery-tree.md` into a production-ready Remotion video. Consistency in props allows for rapid template swapping.

---

## 1. The Core Schema (TypeScript)

Every Solo video template must implement the following `interface`:

```typescript
export interface SoloVideoProps {
  // Brand Context
  brandName: string; // e.g. "Solo OS"
  primaryColor: string; // HEX or HSL from brand-assets.json
  logoUrl?: string; // Path to local or remote asset

  // The Content
  headline: string; // The "Big Idea"
  bodyPoints: string[]; // 3-5 bullet points for the features
  screenshots: string[]; // Paths to files from figma-prototype

  // Audio & Timing
  audioUrl: string; // From voiceover-generator
  timestamps: {
    // Word-level timestamps for highlighting
    word: string;
    start: number;
    end: number;
  }[];

  // Metadata
  fps: number; // Default 30
  durationInFrames: number; // Calculated from audio length
}
```

---

## 2. Default Video Configurations

### Social Vertical (9:16)

- **Resolution**: 1080 x 1920
- **Use Case**: Instagram Reels, YouTube Shorts, TikTok.
- **Focus**: High energy, fast text, large headlines.

### Professional Landscape (16:9)

- **Resolution**: 1920 x 1080
- **Use Case**: YouTube Main, Landing Page Demos, Investor Pitches.
- **Focus**: Detail-oriented, side-by-side screenshots, lower-third titles.

---

## 3. Data Flow Architecture

1.  **Extract**: Agent identifies a high-priority solution from the `opportunity-solution-tree`.
2.  **Script**: Agent drafts a 30-second script via `voiceover-generator`.
3.  **Asset**: Agent captures screenshots via `get_image` command in `figma-prototype`.
4.  **Assemble**: Data is piped into the `parameters.md` schema.
5.  **Render**: Remotion engine consumes the schema and outputs `output.mp4`.

---

## 4. Maintenance & Validation

- **JSON Consistency**: If you update your `brandColor` in the OS settings, all future videos will automatically inherit the change through this schema.
- **Safety**: Never use remote URLs for screenshots during production renders; always download to a local `temp/` folder first to avoid network latency in the video.
