---
name: calculate-metadata
description: Dynamically define duration, dimensions, and transform props for a Remotion composition.
metadata:
  tags: calculate-metadata, metadata, dynamic, duration, dimensions
---

# Using calculateMetadata

Use `calculateMetadata` to dynamically set values for your composition before it starts rendering. This is useful for adjusting duration based on a video file or fetching external data.

## Basic Usage

The function receives the current `props` and should return an object that will be merged into the composition's metadata.

```tsx
import { calculateMetadata } from "remotion";

export const myCalculateMetadata: calculateMetadata<MyProps> = async ({
  props,
}) => {
  // logic here
  return {
    durationInFrames: 300,
    props: {
      ...props,
      derivedData: "Hello",
    },
  };
};
```

## Get Video Duration

You can use `getVideoMetadata` (from `@remotion/media`) inside `calculateMetadata` to set the composition's duration based on an asset.

```tsx
import { getVideoMetadata } from "@remotion/media";
import { staticFile } from "remotion";

export const calculateMetadata = async ({ props }) => {
  const metadata = await getVideoMetadata(staticFile(props.src));
  return {
    durationInFrames: Math.floor(metadata.durationInSeconds * 30),
  };
};
```

## Fetching Data

Useful for dynamic videos based on an API or a JSON file.

```tsx
export const calculateMetadata = async () => {
  const data = await fetch("https://api.example.com/data").then((res) =>
    res.json(),
  );
  return {
    props: { data },
  };
};
```
