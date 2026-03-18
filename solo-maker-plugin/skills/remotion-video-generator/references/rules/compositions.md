---
name: compositions
description: Defining compositions, stills, folders, default props, and dynamic metadata.
metadata:
  tags: composition, still, folder, props, metadata
---

A `<Composition>` defines the component, width, height, frames per second (fps), and duration of a viewable video.

```tsx
import { Composition } from "remotion";
import { MyComposition } from "./MyComposition";

export const RemotionRoot = () => {
  return (
    <Composition
      id="MyComposition"
      component={MyComposition}
      durationInFrames={100}
      fps={30}
      width={1080}
      height={1080}
    />
  );
};
```

## Stills

Use `<Still>` for single-frame images.

```tsx
import { Still } from "remotion";
import { Thumbnail } from "./Thumbnail";

export const RemotionRoot = () => {
  return (
    <Still id="Thumbnail" component={Thumbnail} width={1280} height={720} />
  );
};
```
