# Dynamic Layout Engineering: Measuring Text in Motion

Static text measurement is easy in a browser, but in Remotion (which renders frame-by-frame on the server), measuring text is a critical architectural step to prevent layout breakage, especially with dynamic user content.

---

## 1. Why Measurement Matters

If you are generating 100 variations of an ad, each with a different customer quote, you cannot manually check every layout. You need a system that:

1.  Calculates text width before the first frame is rendered.
2.  Adjusts font size or line wrapping dynamically.
3.  Positions background overlays (word-highlighting) based on text length.

---

## 2. The Implementation Pattern: Standard Measurement

### I. The "Canvas" Trick (Direct)

In your Remotion component, you can use a hidden Canvas element to get high-precision measurements.

```typescript
const measureText = (text: string, font: string) => {
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");
  if (context) {
    context.font = font;
    return context.measureText(text).width;
  }
  return text.length * 20; // Fallback
};
```

### II. The "Approximate" Formula (Performance)

If precision isn't critical (e.g., simple captions), use the "Average Character Width" formula.

- **Formula**: `width = text.length * (fontSize * 0.55)`
- **Safety Factor**: Multiply by 1.1 to ensure the background box is always slightly larger than the text.

---

## 3. Auto-Scaling Strategy (The "Shrink to Fit" Rule)

For dynamic headlines, use a React hook to scale text based on character count:

```typescript
const getFontSize = (text: string) => {
  if (text.length > 50) return "48px";
  if (text.length > 30) return "72px";
  return "110px"; // Primary size
};
```

---

## 4. Typography Layout Constraints

- **Max Characters per Line**: 35-40. Beyond this, text becomes difficult to read in a video format.
- **Line Spacing**: In video, a tighter line-height (`1.1` to `1.2`) often looks more "Premium" than standard web spacing.
- **Vertical Alignment**: For vertical video (9:16), always center-align text horizontally for maximum visual balance.

---

## 5. Integration with Skills

- **Voiceover**: The `voiceover-generator` provides timestamps. This measurement guide ensures that the text highlighting perfectly matches the audio duration.
- **Video Generator**: The `remotion-video-generator` uses these rules to calculate the `durationInFrames` based on reading speed (approx. 180 words per minute).
