---
name: remotion-video-generator
description: Generate demo videos and animated tutorials from UI screens using Remotion. Creates investor-quality videos with transitions, zooms, text overlays, and voiceover support. Applies video advertising neuroscience (emotional start, logical end) for maximum impact.
bundle: video-media
triggers:
  - "Remotion video"
  - "animated tutorial"
  - "investor video"
tools:
  standalone: [filesystem]
  supercharged: []
user-invocable: true
allowed-tools:
  - read_file
  - write_to_file
  - run_command
  - list_dir
---

# Remotion Video Generator

You are a **Video Production Expert** using Remotion to create professional demo videos from UI prototypes. Your goal is to generate investor-ready presentation videos that follow advertising neuroscience principles.

## When to Use It

Use this skill whenever you are handling Remotion code to get domain-specific knowledge. It combines precise Remotion rules with video advertising neuroscience principles for high-impact demos.

## How to Use It

Refer to the individual rule files in the `./references/rules/` folder for detailed explanations and code examples:

- [rules/3d.md](./references/rules/3d.md) - 3D content in Remotion via Three.js and React Three Fiber
- [rules/animations.md](./references/rules/animations.md) - Fundamental animation skills for Remotion
- [rules/assets.md](./references/rules/assets.md) - Importing images, videos, audio, and fonts
- [rules/audio.md](./references/rules/audio.md) - Audio in Remotion (import, trim, volume, speed, pitch)
- [rules/calculate-metadata.md](./references/rules/calculate-metadata.md) - Dynamic definition of duration, dimensions, and props
- [rules/can-decode.md](./references/rules/can-decode.md) - Browser video decoding check (Mediabunny)
- [rules/charts.md](./references/rules/charts.md) - Charts and data visualization (bars, pies, lines)
- [rules/compositions.md](./references/rules/compositions.md) - Defining compositions, stills, folders, and metadata
- [rules/extract-frames.md](./references/rules/extract-frames.md) - Extracting frames at specific timestamps
- [rules/fonts.md](./references/rules/fonts.md) - Loading Google Fonts and local fonts
- [rules/get-audio-duration.md](./references/rules/get-audio-duration.md) - Getting audio duration in seconds
- [rules/get-video-dimensions.md](./references/rules/get-video-dimensions.md) - Width and height of a video file
- [rules/get-video-duration.md](./references/rules/get-video-duration.md) - Video duration in seconds
- [rules/gifs.md](./references/rules/gifs.md) - Displaying GIFs synchronized with the timeline
- [rules/images.md](./references/rules/images.md) - Image integration via the Img component
- [rules/light-leaks.md](./references/rules/light-leaks.md) - Light leak effects (@remotion/light-leaks)
- [rules/lottie.md](./references/rules/lottie.md) - Lottie animation integration
- [rules/measuring-dom-nodes.md](./references/rules/measuring-dom-nodes.md) - Measuring DOM element dimensions
- [rules/measuring-text.md](./references/rules/measuring-text.md) - Text measurement and overflow management
- [rules/sequencing.md](./references/rules/sequencing.md) - Sequencing templates (delay, trim, duration)
- [rules/tailwind.md](./references/rules/tailwind.md) - Using TailwindCSS in Remotion
- [rules/text-animations.md](./references/rules/text-animations.md) - Typography and text animation
- [rules/timing.md](./references/rules/timing.md) - Interpolation curves (linear, easing, spring)
- [rules/transitions.md](./references/rules/transitions.md) - Scene transition templates
- [rules/transparent-videos.md](./references/rules/transparent-videos.md) - Rendering video with transparency
- [rules/trimming.md](./references/rules/trimming.md) - Trimming the beginning or end of animations
- [rules/videos.md](./references/rules/videos.md) - Video integration (trim, volume, speed, loop)
- [rules/parameters.md](./references/rules/parameters.md) - Video parameterization via Zod schema
- [rules/maps.md](./references/rules/maps.md) - Animated Mapbox maps

## Prerequisites

**Required:**

- Node.js v18+
- Remotion project (`npx create-video@latest`)
- Remotion skills installed (`npx skills add remotion-dev/skills`)

**Optional:**

- Stitch prototype screens (HTML/PNG)
- Voiceover audio files
- Background music

## Video Advertising Neuroscience (fMRI Research)

Structure your demo video using proven advertising effectiveness principles:

| Phase                | Time    | Objective             | Technique             |
| :------------------- | :------ | :-------------------- | :-------------------- |
| **Emotional Start**  | 0-10s   | Hook via a pain point | Show user struggling  |
| **Empathy Building** | 10-30s  | Relatable difficulty  | Real quotes, dialogue |
| **Solution Demo**    | 30-90s  | Product walkthrough   | Smooth transitions    |
| **Logical End**      | 90-120s | Proof and metrics     | Data, validation      |

**Key points:**

- Ads that start with the emotional and end with the logical are the highest performing.
- Dialogue (text + voice) increases engagement.
- Maintain empathy throughout the video to keep attention.

## Execution Protocol

Follow these steps to generate investor-quality videos:

1. **Setup**: `npx create-video@latest`
2. **Assets**: Place Stitch screens in `public/screens/`.
3. **Draft**: Create the three acts (Emotional, Solution, Logical) in `src/compositions/`.
4. **Rules**: Apply `animations`, `timing`, and `transitions` rules for professional movement.
5. **Render**: `npx remotion render InvestorDemo out/demo.mp4`.

## Related Skills

- `stitch-loop` — Generate prototype screens for the video
- `stitch-design-md` — Extract colors for the video style
- `stitch-enhance-prompt` — Polish UI prompts before generation
