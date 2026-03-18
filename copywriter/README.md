# Copywriter — The Copywriting Studio

> Blog posts, newsletters, LinkedIn, sales copy — all in your Voice DNA.

Copywriter is a Claude Code plugin for solopreneurs and creators. It handles every content format from a single set of profile files. Pair with **solo** for business operations and Voice DNA generation.

**Zero setup required.** Works immediately with local Markdown files. Connect MCP integrations for CMS publishing, scheduling, and analytics.

---

## What Copywriter Does

| Area | Commands | What you get |
|------|----------|--------------|
| **Write** | `/copywriter:write` | Blog, newsletter, LinkedIn, script, sales copy — all in your voice |
| **Audit** | `/copywriter:audit` | Anti-slop forensic check on any text |
| **Plan** | `/copywriter:plan` | Monthly content calendar with Cascade repurposing strategy |
| **Research** | `/copywriter:research` | Reddit + web mining for content angles and competitor gaps |
| **Setup** | `/copywriter:start` | Onboard Voice DNA, ICP, and business profile |

---

## Quick Start

```
/copywriter:start              # Set up your Voice DNA, ICP, and business profile (3 min)
/copywriter:write blog "topic" # Write an SEO blog post in your voice
/copywriter:plan "March"       # Build your content calendar
/copywriter:audit "my draft"   # Check any text for AI slop
```

---

## 5 Things Worth Knowing

**1. Voice DNA** — Run `/copywriter:start` once. Copywriter profiles your writing style and uses it for every piece of content. Your output sounds like you, not an AI.

**2. Cascade Repurposing** — One Hero asset (blog or newsletter) automatically becomes social splinters (LinkedIn, Twitter) and short-form signals. Write once, publish everywhere.

**3. Anti-Slop by Default** — The `antislop-expert` skill fires automatically after every piece of content. It scores your draft for AI-ness and offers a humanized rewrite.

**4. Dual-Mode** — Every command works standalone (no API keys). Connect `~~CMS`, `~~search`, or `~~social` MCP integrations to unlock live publishing and analytics.

**5. Solo Integration** — Install **solo** first and run `/solo:start`. Copywriter reads `voice-dna.json`, `icp.json`, and `business-profile.json` automatically — no reconfiguration needed.

---

## Agents

| Agent | Trigger | What it does |
|-------|---------|--------------|
| **blog-agent** | `/copywriter:write blog` | SEO research → title → draft → antislop check |
| **social-agent** | `/copywriter:write social` | LinkedIn story post + Twitter thread |
| **newsletter-agent** | `/copywriter:write newsletter` | Email draft with subject, preview, P.S. |
| **script-agent** | `/copywriter:write script` | YouTube/TikTok script with visual cues |
| **sales-copy-agent** | `/copywriter:write sales` | Multi-email conversion sequence |
| **research-agent** | `/copywriter:research` | Reddit + web market intelligence |
| **onboarding-agent** | `/copywriter:start` | Guided setup for Voice DNA, ICP, business profile |

---

## 20 Skills

Copywriter loads the right skill automatically — no manual invocation needed:

- **Voice & identity**: `voice-dna-creator`, `icp-creator`, `business-profile-creator`, `social-media-bio-generator`
- **Long-form**: `seo-blog-writer` (also handles how-to guides and thought leadership essays)
- **Social**: `linkedin-post`, `twitter-thread`, `linkedin-analytics`, `linkedin-scheduler`
- **Email**: `newsletter-writer`, `sales-email-sequence`
- **Video**: `video-script-generator`
- **Planning**: `content-calendar-planner`, `title-brain`, `quote-extractor`
- **Research**: `exa-search-expert`, `reddit-research-insights`
- **Publishing**: `wordpress-publisher`, `landing-page-copy`
- **Quality**: `antislop-expert`

---

## Command Reference

| Command | Usage | Core skill |
|---------|-------|------------|
| `/copywriter:start` | Onboard Voice DNA, ICP, business profile | `voice-dna-creator`, `icp-creator`, `business-profile-creator` |
| `/copywriter:write blog [topic]` | SEO blog post | `seo-blog-writer` |
| `/copywriter:write social [topic]` | LinkedIn + Twitter | `linkedin-post`, `twitter-thread` |
| `/copywriter:write newsletter [topic]` | Email draft | `newsletter-writer` |
| `/copywriter:write script [topic]` | Video script | `video-script-generator` |
| `/copywriter:write sales [topic]` | Sales email sequence | `sales-email-sequence` |
| `/copywriter:audit [text or path]` | Anti-slop audit | `antislop-expert` |
| `/copywriter:plan [month] [focus]` | Content calendar | `content-calendar-planner` |
| `/copywriter:research [topic]` | Market intelligence | `exa-search-expert`, `reddit-research-insights` |

---

## Connectors (Standalone → Supercharged)

Every command works standalone. Connect MCP integrations to unlock publishing and analytics:

| Category | Placeholder | Default | Alternatives |
|----------|-------------|---------|--------------|
| **CMS** | `~~CMS` | WordPress MCP | Ghost, Webflow, Notion |
| **Search** | `~~search` | WebSearch (built-in) | Exa, Tavily |
| **Social** | `~~social` | LinkedIn MCP | Buffer, Twitter/X API |
| **Email** | `~~email-platform` | (manual export) | Beehiiv, Mailchimp, ConvertKit |

See [CONNECTORS.md](./CONNECTORS.md) for setup details.

---

## Data Structure

```
data/
├── 1-Projects/       # Active drafts and content in progress
├── 2-Areas/          # Persistent profiles
│   ├── voice-dna.json          # Your writing style fingerprint
│   ├── icp.json                # Your ideal client profile
│   └── business-profile.json  # Your offers and identity
├── 3-Resources/      # Templates and reference materials
└── 4-Archives/       # Published content (used to avoid angle repeats)
```

---

## Companion Plugins

**[solo](../solo/README.md)** is the business operations layer: client management, invoicing, pipeline, product discovery, and Voice DNA generation. Solo creates the profile files; copywriter uses them to publish.

**[solo-studio](../solo-studio/README.md)** adds the prototyping phase: Figma mockups, Remotion demo videos, and Stitch wireframes. Install all three for the complete build → write → prototype → launch pipeline.

---

*Designed for builders, by builders.*
