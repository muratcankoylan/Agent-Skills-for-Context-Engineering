# Carousel Architecture: Framing for High Retention

LinkedIn Carousels (PDF slides) are the most powerful format for "Dwell Time." They force the user to click 5-10 times, signaling extreme interest to the algorithm. This blueprint provides the technical architecture for carousels that don't just look good—they convert.

---

## 🏛 1. The slide-by-slide Architecture

A Grade A+ carousel should follow this "Retention Flow":

| Slide #   | Name       | Purpose                                              |
| :-------- | :--------- | :--------------------------------------------------- |
| **01**    | The Cover  | The Hook. Large text, bold contrast, high curiosity. |
| **02**    | The Stakes | The "Why." What happens if the reader ignores this?  |
| **03**    | The Guide  | The "Intro." Who you are and what the framework is.  |
| **04-07** | The Meat   | The Value. 1 point/nugget per slide. Max 30 words.   |
| **08**    | The Recap  | The "Aha!" summary of everything they just read.     |
| **09**    | The Result | The "Proof." A case study or metric.                 |
| **10**    | The CTA    | The "Ask." Clear, single direction.                  |

---

## 🧬 2. Technical Design Rules (For Non-Designers)

### The "Safe Zone" Rule:

Keep all text in the middle 60% of the slide. Avoid the edges where LinkedIn's UI overlay (arrows, slide count) will cover your content.

### The "Contrast" Law:

Use high-contrast combinations.

- **Dark Mode**: Black background + White/Yellow text.
- **Brand Mode**: Deep colored background + White text.
- **Rule**: Never use light gray on white or dark blue on black.

### The "Word Count" Cap:

Never exceed 40 words per slide. If it's more than 40 words, it should be a text post, not a carousel.

---

## 🧬 3. Carousel Templates (Frameworks)

### Template A: The "Step-by-Step Breakdown"

- **Slide 1**: How I solved [Big Pain] in [Short Time].
- **Slide 2**: The old way vs. The Solo Protocol.
- **Slide 3**: Phase 1: [Action Name].
- **Slide 4**: Phase 2: [Action Name].
- **Slide 5**: The "One Thing" people forget at this stage.
- **Slide 6**: Phase 3: [Action Name].
- **Slide 7**: Final Result Checkmark list.
- **Slide 8**: Why this works (The technical logic).
- **Slide 9**: Want the checklist?
- **Slide 10**: Comment [KEYWORD] below.

### Template B: The "Visual Teardown" (Critique)

- **Slide 1**: Analyzing [Industry Leader]'s [Asset].
- **Slide 2**: What they did right (Green signal).
- **Slide 3**: The one mistake costing them $XXXX.
- **Slide 4**: The "Before" state (Screenshot).
- **Slide 5**: The "After" state (Your redesign).
- **Slide 6-8**: The 3 principles of the fix.
- **Slide 9**: Lesson summary.
- **Slide 10**: Want a teardown of your site? Link in bio.

---

## 🧪 4. "Retention Engineering" Protocols

How to keep them swiping to Slide 10:

- **The "Cliffhanger" Slide**: End a slide with "But it wasn't enough..." or "Then I realized..." to force the swipe.
- **The "Peek-a-Boo" Design**: Have an element (like a line or an arrow) that starts on Slide 4 and ends on Slide 5. The eye naturally follows the movement.
- **The "Progress Bar"**: Include a small visual indicator at the bottom (bubbles or a line) showing the reader how far they've come.

---

## ⚒ 5. Technical PDF Optimization

- **Ratio**: Always use **1:1 (Square)** or **4:5 (Portrait)**. Never 16:9.
- **File Type**: Export as a "Standard PDF" (not for print).
- **Page Limit**: Aim for 7-12 slides. Fewer than 5 feels thin; more than 15 causes drop-off.
- **Accessibility**: Ensure your Slide 1 text is the same as your Post Hook so Google and LinkedIn can index the content for search.

---

## 🧪 6. The "Carousel-to-Text" Bridge

A carousel is nothing without a strong "Post Caption."

### The Protocol:

1.  **Headline**: Summarize the carousel.
2.  **Hook**: Use a formula from `hook-library.md`.
3.  **Instruction**: "Swipe through to see the full framework."
4.  **Recap**: 3-5 bullet points of what's inside.
5.  **CTA**: Reinforce the Slide 10 CTA.

---

## 📈 7. Performance Benchmarks

- **Swipe Through Rate (STR)**: How many people get to Slide 10? (Goal: >50%).
- **Save Rate**: Carousels are the most "Saved" format. (Goal: 1 save per 200 views).
- **Share Rate**: High value carousels get shared to "Feed." (Goal: 1 share per 500 views).

---

## 📂 Related Resources

- [The LinkedIn Hook Library](./hook-library.md)
- [LinkedIn Formatting Guide](./formatting-guide.md)
- [Stitch Asset Bridge (Figma-to-LinkedIn)](../stitch-asset-bridge/SKILL.md)

---

> [!TIP]
> Use the `/solo:build design` command if you have a Figma MCP connected. I can extract your design frames and help you structure them into this PDF architecture automatically.
