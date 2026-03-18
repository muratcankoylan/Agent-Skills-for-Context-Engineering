---
name: videos
description: Integrating videos in Remotion - trim, volume, speed, loop, scale
metadata:
  tags: video, media, trim, volume, speed, loop, pitch
---

# Using Videos in Remotion

## Prerequisites

```bash
npx remotion add @remotion/media
```

Use `<Video>` from `@remotion/media` to integrate videos.

```tsx
import { Video } from "@remotion/media";
import { staticFile } from "remotion";

export const MyComposition = () => {
  return <Video src={staticFile("video.mp4")} />;
};
```

## Trimming

Use `trimBefore` and `trimAfter` (values in frames).

```tsx
<Video
  src={staticFile("video.mp4")}
  trimBefore={2 * fps}
  trimAfter={10 * fps}
/>
```
