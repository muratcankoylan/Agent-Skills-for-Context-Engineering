# Visual Storytelling Library: Professional Remotion Scenes

This library defines the "Cinematic Grammar" for your product demos. Use these scene architectures to build a high-fidelity video within the `remotion-video-generator`.

---

## 1. The "Hero Reveal" Scene

_Use for Phase 3 of the Storyboard._

- **Visuals**: Logo centered, scaling from 80% to 100%. Background uses a slow-moving gradient based on `primaryColor`.
- **Animation**: `spring()` based entrance for the logo. Particles/Sparkles filtered through a `contrast(1.2)` filter.
- **Timing**: 3 seconds.

## 2. The "Side-by-Side" (Before/After)

_Use for Phase 2 of the Storyboard._

- **Visuals**: Vertical divider at 50%. Left side: "The Manual Chaos" (grayscale). Right side: "The Solo OS" (vibrant color).
- **Automation**: The divider slides from right-to-left, "erasing" the chaos and revealing the product.
- **Timing**: 5-8 seconds.

## 3. The "Feature Highlight" (The 'Pop' Scene)

_Use for Phase 4 of the Storyboard._

- **Visuals**: Full-screen screenshot of the UI. A "Focus Circle" highlights a specific button or command.
- **Animation**: The screenshot zooms in towards the focus area (1.0x -> 1.5x zoom).
- **Text**: Supporting caption slides up from the bottom (Ref: `measuring-text.md`).
- **Timing**: 10 seconds per feature.

## 4. The "Trust Banner" (Social Proof)

_Use for Phase 5 of the Storyboard._

- **Visuals**: A large quote in the center. Behind the quote, a slow-scrolling wall of client logos or successful project titles.
- **Typography**: Uses the `High Priority` styles from `fonts.md`.
- **Timing**: 6 seconds.

---

## Scene Transition Logic

- **The "Wipe"**: Used to move between different functional areas.
- **The "Fade"**: Used for emotional transitions (Problem to Reveal).
- **The "Cut"**: High-speed cuts (1-2 seconds) used for the "End-of-Video" highlight reel.

---

## Deployment Standards

- **Resolution**: 1080p (16:9) for YouTube; 1080x1920 for Social.
- **Frame Rate**: 30fps for standard; 60fps for high-fidelity animations.
- **Metadata**: Every scene must include `alt-text` in the code for accessibility and AI parsing.
