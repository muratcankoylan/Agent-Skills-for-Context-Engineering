---
name: trimming
description: Trimming templates for Remotion - cutting the beginning or end of animations
metadata:
  tags: sequence, trim, clip, cut, offset
---

# Trimming in Remotion

Use `<Sequence>` with a negative `from` value to cut the beginning of an animation.

## Cutting the beginning

```tsx
import { Sequence, useVideoConfig } from "remotion";

const fps = useVideoConfig();

<Sequence from={-0.5 * fps}>
  <MyAnimation />
</Sequence>;
```

## Cutting the end

Use `durationInFrames` to unmount content after a specified duration:

```tsx
<Sequence durationInFrames={1.5 * fps}>
  <MyAnimation />
</Sequence>
```
