---
name: lottie
description: Integrating Lottie animations in Remotion.
metadata:
  category: Animation
---

# Using Lottie Animations in Remotion

## Prerequisites

```bash
npx remotion add @remotion/lottie
```

## Displaying a Lottie File

```tsx
import { Lottie, LottieAnimationData } from "@remotion/lottie";

export const MyAnimation = () => {
  const [animationData, setAnimationData] =
    useState<LottieAnimationData | null>(null);

  useEffect(() => {
    fetch("https://assets4.lottiefiles.com/packages/lf20_zyquagfl.json")
      .then((data) => data.json())
      .then((json) => setAnimationData(json));
  }, []);

  if (!animationData) return null;

  return (
    <Lottie animationData={animationData} style={{ width: 400, height: 400 }} />
  );
};
```
