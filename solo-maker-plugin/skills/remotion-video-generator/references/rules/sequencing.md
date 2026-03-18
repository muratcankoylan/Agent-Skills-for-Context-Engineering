---
name: sequencing
description: Sequencing templates for Remotion - delay, trim, duration limiting
metadata:
  tags: sequence, series, timing, delay, trim
---

Use `<Sequence>` to delay the appearance of an element in the timeline.

```tsx
import { Sequence } from "remotion";

const { fps } = useVideoConfig();

<Sequence from={1 * fps} durationInFrames={2 * fps} premountFor={1 * fps}>
  <Title />
</Sequence>;
```

## Series

Use `<Series>` when elements should play one after another without overlap.

```tsx
import { Series } from "remotion";

<Series>
  <Series.Sequence durationInFrames={45}>
    <Intro />
  </Series.Sequence>
  <Series.Sequence durationInFrames={60}>
    <MainContent />
  </Series.Sequence>
</Series>;
```
