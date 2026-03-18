---
name: assets
description: Importing images, videos, audio, and fonts in Remotion
metadata:
  tags: assets, staticFile, images, fonts, public
---

# Importing Assets in Remotion

## The public folder

Place assets in the `public/` folder at the root of your project.

## Using staticFile()

You MUST use `staticFile()` to reference files in the `public/` folder:

```tsx
import { Img, staticFile } from "remotion";

export const MyComposition = () => {
  return <Img src={staticFile("logo.png")} />;
};
```

The function returns an encoded URL that works correctly when deploying in subdirectories.

## Important notes

- Remotion components (`<Img>`, `<Video>`, `<Audio>`) ensure that assets are fully loaded before rendering
- Special characters in filenames (`#`, `?`, `&`) are automatically encoded
