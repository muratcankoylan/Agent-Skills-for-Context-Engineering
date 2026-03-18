---
name: measuring-dom-nodes
description: Measuring DOM element dimensions in Remotion
metadata:
  tags: measure, layout, dimensions, getBoundingClientRect, scale
---

# Measuring DOM Nodes in Remotion

Remotion applies a `scale()` transform to the container. Use `useCurrentScale()` for measurements.

```tsx
import { useCurrentScale } from "remotion";
import { useRef, useEffect, useState } from "react";

export const MyComponent = () => {
  const ref = useRef<HTMLDivElement>(null);
  const scale = useCurrentScale();
  const [dims, setDims] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    setDims({ width: rect.width / scale, height: rect.height / scale });
  }, [scale]);

  return <div ref={ref}>Content</div>;
};
```
