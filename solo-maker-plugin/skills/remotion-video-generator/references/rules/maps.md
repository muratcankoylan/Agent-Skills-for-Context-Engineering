---
name: maps
description: Adding a map using Mapbox and animating it
metadata:
  tags: map, mapbox, geospatial, location, markers
---

# Maps in Remotion

## Prerequisites

```bash
npm i mapbox-gl @turf/turf
```

Add `REMOTION_MAPBOX_TOKEN` to your `.env` file.

## Basic Map Configuration

```tsx
import mapboxgl, { Map } from "mapbox-gl";

export const MyMap = () => {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const _map = new Map({
      container: ref.current!,
      zoom: 11,
      center: [0, 0],
      style: "mapbox://styles/mapbox/standard",
      interactive: false,
    });
  }, []);

  return <div ref={ref} style={{ width: 1920, height: 1080 }} />;
};
```

## Camera Animation

Use `map.setFreeCameraOptions()` driven by `useCurrentFrame()`.
Always leave north up by default.
