---
name: website
description: Build a complete multi-page website. Home, About, Product/Services, and Contact — with consistent design and real copy throughout.
argument-hint: "[describe your business/product]"
---

# Build a Complete Website

**Load skills:** `solopreneur`, `landing-page`, `copywriting`, `frontend-design`

## What Are We Building?

<description> #$ARGUMENTS </description>

If empty: "Tell me about your business — what you do, who it's for, and what you want visitors to do."

Gather:
- Business name (or direction if unnamed)
- Type of business (SaaS, service, creator, e-commerce, etc.)
- Primary goal: sales, leads, credibility, community
- Pages needed or preferred structure
- Existing brand (colors, fonts) — or create from scratch?

---

## Website Structure

Standard solopreneur site:

```
index.html        — Home (landing page quality)
about.html        — Story, credibility, founder
[product].html    — Detailed product/service page
contact.html      — Contact/booking
```

Optional additions based on business type:
- `blog.html` — Article listing (for content businesses)
- `pricing.html` — Standalone pricing (for SaaS/services)
- `work.html` — Portfolio (for creators/agencies)
- `faq.html` — Expanded FAQ

---

## Build Process

### 1. Design System First

Create a shared design system (CSS variables) used across all pages:
- Color tokens (primary, accent, neutrals)
- Typography tokens (fonts, scale)
- Spacing scale
- Component styles (buttons, nav, footer, cards)

### 2. Build Pages in Order

1. **Home** — landing page quality, primary conversion focus
2. **About** — founder story, credibility, human connection
3. **Product/Service** — detailed explanation, features, proof
4. **Contact** — form + scheduling embed placeholder + social links

### 3. Shared Components

Same nav and footer on every page. Mobile hamburger menu. Consistent CTA button style.

### 4. Real Copy Throughout

Every page has real, specific copy. No Lorem ipsum. No "Your Company Name" placeholders (unless intentionally left for user to fill in marked with `TODO:`).

### 5. Deliver

Zip all HTML files as `[business-name]-website.zip` or deliver as separate files.

Include a `README.md` with:
- How to deploy (Netlify, GitHub Pages, Vercel instructions)
- What to customize (list of `TODO:` items)
- How to update copy
