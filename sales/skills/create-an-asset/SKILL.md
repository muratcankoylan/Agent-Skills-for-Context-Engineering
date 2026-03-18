---
name: create-an-asset
description: Generate tailored sales assets (landing pages, decks, one-pagers, workflow demos) from your deal context. Describe your prospect, audience, and goal — get a polished, branded asset ready to share with customers. Trigger with "create an asset", "build a demo", "make a landing page", "mock up a workflow", or "create an asset for [company]".
bundle: deal-execution
triggers:
  - "create an asset"
  - "build a demo"
  - "make a landing page for [company]"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# Create an Asset

Generate custom sales assets tailored to your prospect, audience, and goals. Supports interactive landing pages, presentation decks, executive one-pagers, and workflow/architecture demos.

## Triggers

- "Create an asset for [Company]"
- "Build a demo", "make a landing page", "mock up a workflow"
- User needs a customer-facing deliverable for a sales conversation

## Asset Formats

| Format | Best For | Output |
|--------|----------|--------|
| **Interactive landing page** | Exec alignment, intros, value prop | Multi-tab HTML with demos, metrics, calculators |
| **Deck-style** | Formal meetings, large audiences | Linear presentation-ready slides |
| **One-pager** | Leave-behinds, quick summaries | Single-scroll executive summary |
| **Workflow / Architecture demo** | Technical deep-dives, POC demos | Animated diagram with step-by-step walkthrough |

## Workflow Summary

1. **Detect context** — Identify seller company from email domain (or ask)
2. **Collect prospect context** — Company, contacts, deal stage, pain points, materials
3. **Collect audience + purpose** — Who's viewing, what they care about, desired action
4. **Select format** — Landing page, deck, one-pager, or workflow demo
5. **Research** — Prospect basics, leadership, brand colors, industry (depth based on context richness)
6. **Plan structure** — Section mapping based on format + audience + purpose
7. **Generate content** — Tailored copy using prospect language, proof points, ROI framing
8. **Apply visual design** — Prospect brand colors (dark theme), typography, animations
9. **Ask clarifying questions** — Confirm understanding before building (max 2 rounds)
10. **Build & deliver** — Self-contained HTML file, deployment options included

**Bilingual:** Checks `data/2-Domaines/sales-profile.json` for `language_preference`. Outputs in "fr" or "en" accordingly.

**Output:** Self-contained HTML file. All CSS/JS inline. No external dependencies. File naming: `[ProspectName]-[format]-[date].html`.

See `references/asset-creation-guide.md` for detailed phase instructions, YAML schemas, section templates, CSS design system, and examples.
