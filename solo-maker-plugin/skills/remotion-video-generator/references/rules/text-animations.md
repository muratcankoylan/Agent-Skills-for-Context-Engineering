---
name: text-animations
description: Typography and text animation templates for Remotion.
metadata:
  tags: typography, text, typewriter, highlighter ken
---

## Typewriter Effect

Always use string slicing for typewriter effects. Never use per-character opacity.

```tsx
const frame = useCurrentFrame();
const text = "Hello World";
const charsShown = Math.floor(frame / 2);
const displayedText = text.slice(0, charsShown);

return <div>{displayedText}</div>;
```

## Word Highlighting

Animate a background span tag under specific words to create a highlighter effect.
