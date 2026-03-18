---
name: competitive-intelligence
description: Research your competitors and build an interactive battlecard. Outputs an HTML artifact with clickable competitor cards and a comparison matrix. Trigger with "competitive intel", "research competitors", "how do we compare to [competitor]", "battlecard for [competitor]", or "what's new with [competitor]".
bundle: prospecting
triggers:
  - "competitive intel"
  - "research competitors"
  - "battlecard for [competitor]"
tools:
  standalone: [exa]
  supercharged: [exa]
version: 1.0.0
---

# Competitive Intelligence

Research your competitors extensively and generate an **interactive HTML battlecard** you can use in deals. The output is a self-contained artifact with clickable competitor tabs and an overall comparison matrix.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                  COMPETITIVE INTELLIGENCE                        │
├─────────────────────────────────────────────────────────────────┤
│  ALWAYS (works standalone via web search)                        │
│  ✓ Competitor product deep-dive: features, pricing, positioning │
│  ✓ Recent releases: what they've shipped in last 90 days        │
│  ✓ Your company releases: what you've shipped to counter        │
│  ✓ Differentiation matrix: where you win vs. where they win     │
│  ✓ Sales talk tracks: how to position against each competitor   │
│  ✓ Landmine questions: expose their weaknesses naturally        │
├─────────────────────────────────────────────────────────────────┤
│  OUTPUT: Interactive HTML Battlecard                             │
│  ✓ Comparison matrix overview                                    │
│  ✓ Clickable tabs for each competitor                           │
│  ✓ Dark theme, professional styling                             │
│  ✓ Self-contained HTML file — share or host anywhere            │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                      │
│  + CRM: Win/loss data, competitor mentions in closed deals      │
│  + Docs: Existing battlecards, competitive playbooks            │
│  + Chat: Internal intel, field reports from colleagues          │
│  + Transcripts: Competitor mentions in customer calls           │
└─────────────────────────────────────────────────────────────────┘
```

## Getting Started

**Required:**
- What company do you work for? (or I'll detect from your email)
- Who are your main competitors? (1-5 names)

**Optional:**
- Which competitor do you want to focus on first?
- Any specific deals where you're competing against them?
- Pain points you've heard from customers about competitors?

If I already have your seller context from a previous session, I'll confirm and skip the questions.

**Bilingual:** Checks `data/2-Domaines/sales-profile.json` — translates entire HTML artifact to French if `language_preference: "fr"`.

## Connectors (Optional)

| Connector | What It Adds |
|-----------|-------------|
| **~~CRM** | Win/loss history against each competitor, deal-level competitor tracking |
| **~~knowledge base** | Existing battlecards, product comparison docs, competitive playbooks |
| **~~chat** | Internal intel from the field (e.g. Slack) |
| **~~conversation intelligence** | Competitor mentions in customer calls, objections raised |

> **No connectors?** Web research works great — product pages, pricing, blogs, release notes, reviews, job postings.

See `references/research-guide.md` for the detailed research methodology, search query templates, battlecard HTML structure, and talk track templates.
