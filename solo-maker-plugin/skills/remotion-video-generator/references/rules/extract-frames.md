---
name: extract-frames
description: Extract frames from videos at specific timestamps using Mediabunny
metadata:
  tags: extract, frames, mediabunny, filmstrip
---

# Extracting frames from videos

Use `extractFrames()` from Mediabunny to get specific frames as canvas elements.

```tsx
import { extractFrames } from "mediabunny";

await extractFrames({
  src: "https://remotion.media/video.mp4",
  timestampsInSeconds: [0, 1, 2, 3],
  onVideoSample: (sample) => {
    const canvas = document.createElement("canvas");
    canvas.width = sample.displayWidth;
    canvas.height = sample.displayHeight;
    sample.draw(canvas.getContext("2d")!, 0, 0);
  },
});
```
