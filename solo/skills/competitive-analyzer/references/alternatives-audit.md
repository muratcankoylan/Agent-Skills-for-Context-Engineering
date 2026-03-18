# Alternatives Audit: Extracting Frustrations from Reviews

A practical guide to turning public reviews into positioning intelligence.

---

## The Principle

Negative 1-3 star reviews are the user interviews you haven't done yet. Every frustrated review reveals:
- What the user *expected* (the real need)
- What the product *didn't deliver* (the gap to fill)
- The exact words they use (to mirror in your copy)

---

## Sources by Value

### 1. G2 and Capterra (most structured)

**URL pattern:** `g2.com/products/[product-name]/reviews`

**Filters to apply:**
- Rating: 1-3 stars only
- Section: "What do you dislike?" or "Cons"
- Sort by: Most recent (avoid reviews of old versions)

**What to look for:**
- Phrases starting with "I wish...", "The only problem is...", "It would be perfect if..."
- Words repeated across multiple independent reviews (strong signal)
- Frustrations described as workarounds: "We had to hack X to get around this"

---

### 2. Reddit (most authentic)

**Useful queries:**
```
"[product name] sucks"
"alternatives to [product name]"
"switched from [product name] to"
"[product name] vs"
"[problem] reddit"
site:reddit.com "[product name]" "problem"
```

**Subreddits by category:**
- B2B SaaS: r/SaaS, r/entrepreneur, r/smallbusiness
- Productivity: r/productivity, r/nocode, r/Notion
- Dev tools: r/webdev, r/programming, r/devtools
- Marketing: r/marketing, r/SEO, r/PPC

**Strong signal:** When someone lists reasons they switched, copy verbatim. These are your landing page bullet points.

---

### 3. Product Hunt comments (most concentrated)

**URL pattern:** `producthunt.com/posts/[product-name]`

Read comments under competitor launches — especially:
- Questions (reveal what isn't clear)
- "Would be great if..." (missing features)
- Spontaneous comparisons: "How does this compare to X?"

---

### 4. "vs" and "alternatives" pages

**Queries:**
```
"[competitor] vs [your domain]"
"[competitor] alternatives"
"best [category] tools"
```

Third-party comparison pages often list the spontaneous decision criteria users actually care about — the real selection criteria, not the ones you imagine.

---

### 5. App Store / Chrome Web Store (if applicable)

Same patterns as G2 — filter 1-3 stars, read the "cons."

---

## Collection Template

```markdown
# Alternatives Audit: [Competitor A]

**Source:** G2 / Reddit / Product Hunt
**Date:** [date]
**Volume analyzed:** [N] reviews/posts

## Direct Quotes (verbatim)
> "[Exact quote]" — [source]
> "[Exact quote]" — [source]

## Patterns Identified

| Frustration | Frequency | Exact words used |
|-------------|-----------|-----------------|
| [Problem 1] | High / Medium / Low | "[words]", "[words]" |
| [Problem 2] | | |

## What They Like (don't break this)

| Strength | Frequency |
|----------|-----------|
| [Element] | |

## Quotes Usable in Copy

For the landing page — phrases that resonate:
- "[Quote]"
- "[Quote]"
```

---

## Cross-Cutting Analysis

After auditing 3-5 alternatives, look for patterns that cut across multiple products:

**Weak signal:** One user mentions X at competitor A.
**Strong signal:** Users mention X at competitors A, B, and C — this is a structural market frustration.

**Synthesis format:**

```markdown
## Cross-Cutting Frustrations (unresolved by anyone)

### [Theme 1]
- Present at: [Competitor A] (8 mentions), [Competitor B] (5 mentions)
- Recurring phrasing: "too complex", "too long to set up", "steep learning curve"
- What they actually want: [interpretation of the underlying need]

### [Theme 2]
- Present at: ...
```

These cross-cutting themes are your positioning. Not what you want to build — what the market wants and can't find anywhere.

---

## Pitfalls to Avoid

**Don't confuse frequency with importance.** "The UI is ugly" might have 50 mentions without being a blocker. "Data can't be exported" might have 5 mentions and be critical for your ICP.

**Don't generalize from one segment.** G2 reviews about an enterprise tool don't reflect indie hacker needs. Filter by company size or profile when possible.

**Don't copy the competitor's problem — understand the need underneath it.** "Onboarding takes too long" → underlying need: see value fast. That's what you address, not "short onboarding."
