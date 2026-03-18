# Solo Maker Plugin

**The AI prototype studio for solopreneurs.** Build landing pages, pitch decks, websites, brand identities, copy packs, and full launch kits — fast.

Built on the [Compound Engineering Plugin](https://github.com/EveryInc/compound-engineering-plugin) architecture with [Impeccable Style](https://github.com/your-url) design skills baked in.

---

## What This Gives You

| Command       | What It Builds                                  |
| ------------- | ----------------------------------------------- |
| `/prototype`  | Full prototype workflow (mockups, Figma, video) |
| `/landing`    | High-converting landing page (HTML)             |
| `/pitch`      | Investor or client pitch deck (HTML)            |
| `/website`    | Complete multi-page website                     |
| `/brand`      | Brand identity guide (colors, type, voice)      |
| `/copy`       | Marketing copy pack for any surface             |
| `/bridge`     | Automate Figma to Remotion video extraction     |
| `/launch-kit` | Landing page + email sequence + social posts    |
| `/wireframe`  | Lo-fi wireframes with real copy                 |
| `/critique`   | Conversion + design critique                    |
| `/polish`     | Final quality pass (Impeccable Style)           |
| `/animate`    | Add purposeful motion (Impeccable Style)        |
| `/optimize`   | CRO optimization pass                           |

---

## Skills Included

| Skill                        | What It Does                                            |
| ---------------------------- | ------------------------------------------------------- |
| `solopreneur`                | Strategy, offer framing, prototype philosophy           |
| `copywriting`                | Headlines, CTAs, email, ad copy frameworks              |
| `landing-page`               | Conversion architecture and HTML section guidance       |
| `ux-writing`                 | Microcopy, empty states, error messages, and onboarding |
| `pitch-deck`                 | Investor + client deck structure and slide guidance     |
| `frontend-design`            | Visual design system (from Impeccable Style)            |
| `frontend-design/reference/` | Typography, color, spatial design, motion               |
| `figma-prototype`            | Interactive Figma prototypes                            |
| `stitch-*`                   | Google Stitch advanced UI/UX automation                 |
| `remotion-*`                 | Demo video generation                                   |
| `storyboard`                 | Video storyboarding                                     |
| `voiceover-generator`        | AI voiceover generation                                 |
| `prototype-to-video`         | Figma to video translation                              |

---

## Agents

| Agent                     | Role                                     |
| ------------------------- | ---------------------------------------- |
| `conversion-optimizer`    | CRO review with prioritized fixes        |
| `copy-reviewer`           | Headline + copy assessment               |
| `brand-identity-designer` | Visual identity direction                |
| `landing-page-designer`   | Design direction for landing pages       |
| `prototype-launch-agent`  | Orchestrates the full prototype workflow |

---

## Connectors

| Category | Default  | Purpose                |
| -------- | -------- | ---------------------- |
| Design   | Figma    | Interactive prototypes |
| Video    | Remotion | Demo video generation  |

See [CONNECTORS.md](./CONNECTORS.md) for setup.

---

## Quick Start

```bash
# Clone the plugin
git clone [this-repo]

# Install in Claude Code
# Copy plugins/solo-maker to your project's .claude/plugins/ directory

# Or use directly in your project
cp -r plugins/solo-maker /your-project/.claude/plugins/
```

### Your first prototype

```
/solo-maker:make I'm building a Notion template shop for freelance designers
```

That's it. Claude will ask you a few targeted questions, then build a complete landing page.

### Build specific deliverables

```
# Landing page
/solo-maker:landing Productivity app for ADHD founders

# Pitch deck
/solo-maker:pitch SaaS for restaurant inventory management, raising $500k

# Brand identity
/solo-maker:brand Online course for female solopreneurs — warm, expert, modern

# Brand identity
/solo-maker:brand Online course for female solopreneurs — warm, expert, modern

# Video Bridge (with TikTok template)
/solo-maker:bridge https://www.figma.com/file/.../Project tiktok

# Full launch kit
/solo-maker:launch-kit Newsletter about sustainable home design
```

---

## Design Philosophy

Every prototype this plugin builds:

- Commits to a **bold aesthetic direction** (no generic AI slop)
- Uses distinctive typography (no Inter/Roboto)
- Applies OKLCH color (perceptually accurate palettes)
- Is **mobile-first** and responsive
- Contains **real copy** (no Lorem ipsum)
- Is a **deployable single file** (drop it on Netlify and you're live)

---

## Architecture

```
plugins/solo-maker/
├── .claude-plugin/
│   └── plugin.json
├── CLAUDE.md                     ← AI context for every session
├── skills/
│   ├── copywriting/SKILL.md      ← Conversion copy formulas
│   ├── landing-page/SKILL.md     ← CRO + page architecture
│   ├── pitch-deck/SKILL.md       ← Deck structure + narrative
│   ├── ux-writing/               ← Microcopy and error states
│   └── frontend-design/          ← Impeccable Style (visual design)
│       ├── SKILL.md
│       └── reference/
│           ├── typography.md
│           ├── color-and-contrast.md
│           ├── spatial-design.md
│           ├── motion-design.md
│           ├── interaction-design.md
│           └── responsive-design.md
├── commands/
│   ├── prototype.md              ← Full prototype workflow
│   ├── landing.md                ← Landing page builder
│   ├── pitch.md                  ← Pitch deck builder
│   ├── website.md                ← Multi-page website
│   ├── bridge.md                 ← Figma to Remotion bridge
│   ├── brand.md                  ← Brand identity guide
│   ├── copy.md                   ← Copy pack builder
│   ├── launch-kit.md             ← Full launch kit
│   ├── wireframe.md              ← Lo-fi wireframes
│   ├── critique.md               ← Conversion critique
│   ├── polish.md                 ← (Impeccable Style)
│   ├── animate.md                ← (Impeccable Style)
│   ├── optimize.md               ← (Impeccable Style)
│   ├── style-critique.md         ← (Impeccable Style)
│   └── extract.md                ← Design system extraction
└── agents/
    ├── conversion-optimizer.md
    ├── copy-reviewer.md
    ├── brand-identity-designer.md
    ├── landing-page-designer.md
    └── prototype-launch-agent.md
```

---

## Based On

- **[Compound Engineering Plugin](https://github.com/EveryInc/compound-engineering-plugin)** by Kieran Klaassen — workflow architecture, agent patterns, command system
- **Impeccable Style Plugin** — frontend-design skill, polish/animate/optimize/critique/extract commands

---

## License

MIT
