---
description: "Deep Market & Competitor Research. Mines Reddit, Web, and Reviews."
argument-hint: "[topic | competitor name]"
allowed-tools: WebSearch, WebFetch
model: sonnet
---

# /copywriter:research

Don't guess what to write. Find out what people are _screaming_ for.

## Usage

```bash
/copywriter:research "Email Marketing Software"
/copywriter:research "CompetitorName"
```

## Workflow

1.  **Triggers** `research-agent`.
2.  **Scans Reddit** via `reddit-research-insights` for:
    - "I hate [Competitor]"
    - "How do I [Problem]"
    - "Is there a tool for..."
3.  **Scans Web** for Pricing/Feature gaps.
4.  **Outputs** a "Market Intel Briefing":
    - 🔥 The "Hair on Fire" Pain Point.
    - 🗣️ The "Voice of Customer" (Exact phrases they use).
    - 💡 Content Angles (What to write to attract them).
