# Sales — The Revenue Operating System

> Prospecting, pipeline management, deal coaching, call prep, outreach, and negotiation — standalone or supercharged with your CRM and sales tools.

Sales is a Claude Code / Cowork plugin built for solopreneurs and small B2B teams. It combines proactive AI agents with deep skill libraries to act as a virtual Sales Manager, Deal Coach, and RevOps function in one.

**Zero setup required.** Works immediately with local files. Connect MCP integrations for live CRM sync, enrichment, and transcript analysis.

---

## What Sales Does

| Area | Commands | What you get |
|------|----------|--------------|
| **Outbound** | `/sales:prospect`, `/sales:engage` | Signal-triggered research, personalized outreach, LinkedIn campaigns |
| **Pipeline** | `/sales:pipeline`, `/sales:forecast` | Health audit, deal prioritization, weighted forecast with gap analysis |
| **Deals** | `/sales:negotiate`, `/sales:create` | Negotiation strategy, proposal builder, custom sales assets |
| **Calls** | `/sales:call-summary` | Call notes → action items, CRM update, follow-up draft |
| **Intelligence** | `/sales:win-loss` | Post-mortems, pattern analysis, competitive matrix |
| **Coaching** | `/sales:coach` | Weekly personalized coaching plan, skill gap identification |
| **LinkedIn** | `/sales:linkedin` | Content creation, prospect engagement, activity tracking |
| **Setup** | `/sales:start` | Initialize Sales DNA (ICP, Voice DNA, methodology) |

---

## Quick Start

```
/sales:start                         # Set up your Sales DNA (5 min)
/sales:prospect find Acme Corp       # Research a target account
/sales:pipeline                      # Review your pipeline health
/sales:forecast                      # Generate a weighted forecast
/sales:win-loss Acme                 # Post-mortem on a closed deal
/sales:coach                         # Get your weekly coaching plan
```

---

## 5 Things Worth Knowing

**1. Sales DNA** — Run `/sales:start` once. Sales loads your ICP, Voice DNA, selling methodology (MEDDIC, SPIN, Challenger), and competitor list. Every command, email, and script uses this profile. Your output sounds like a trained rep who knows your product — not a generic AI.

**2. 8 Autonomous Agents** — Background agents handle work you shouldn't need to manage manually: the Pipeline Guardian flags rotting deals; the Signal Trapper monitors news for outreach triggers; the Win-Loss Analyst runs post-mortems automatically; the Sales Coach surfaces skill gaps from your patterns every Friday.

**3. The Closed-Loop Intelligence System** — Every closed deal feeds the win-loss playbook. Every outreach campaign tracks response rates. Every coaching session pulls from real data. Unlike disconnected tools, Sales gets smarter the more you use it.

**4. Anti-Slop by Default** — The `antislop-expert` skill fires on all draft content. No "hope this finds you well." No "seamless synergies." Your emails sound like a human wrote them.

**5. Dual-Mode** — Every command works standalone (paste notes, upload CSV, describe your situation). Connect MCP integrations to unlock live CRM data, transcript analysis, and enrichment.

---

## Commands

| Command | Usage | What it does |
|---------|-------|-------------|
| `/sales:start` | Initialize or update your Sales DNA | Configures ICP, Voice DNA, methodology, competitors |
| `/sales:prospect` | `find [company]`, `outreach`, `sequence` | Account research, personalized emails, multi-step sequences |
| `/sales:pipeline` | `review`, `health`, `clean` | Pipeline audit, risk flags, deal prioritization |
| `/sales:forecast` | `[period]` | Weighted forecast, best/likely/worst, gap analysis |
| `/sales:negotiate` | `deal [company]`, `response [scenario]` | BATNA analysis, concession strategy, scripts |
| `/sales:call-summary` | Paste notes or transcript | Action items, follow-up email, CRM-ready summary |
| `/sales:create` | `asset [type]`, `proposal [company]` | Sales assets, SOWs, proposals, one-pagers |
| `/sales:win-loss` | `[company]` or `patterns` | Post-mortem, pattern analysis, playbook update |
| `/sales:coach` | `[focus area]` | Weekly coaching plan, skill practice routing |
| `/sales:linkedin` | `post`, `engage`, `prospect` | Content creation, comment strategy, ICP prospecting |
| `/sales:engage` | `rfp [file]`, `[scenario]` | RFP analysis (Go/No-Go), competitive response |

---

## Agents (8 Autonomous)

| Agent | Trigger | What it does |
|-------|---------|-------------|
| **Pipeline Guardian** | On demand / weekly | Audits pipeline health, staleness, CRM hygiene, forecast |
| **Signal Trapper** | On demand | Scans news, hiring signals, funding events for outreach triggers |
| **Deal Desk Advisor** | On demand | MEDDIC scoring, unblocking strategy for stalled deals |
| **Prep Master** | Before a call | Battle card: account context, attendee research, agenda, questions |
| **Roleplay Dojo** | On demand | Simulated prospect (CFO, Skeptic, Bully) with scored feedback |
| **Outbound Campaign Architect** | On demand | Multi-step sequence design and drafting across channels |
| **Win-Loss Analyst** | After deal closes | Post-mortem, root cause analysis, playbook update, ICP signal |
| **Sales Coach** | Weekly / on demand | Skill gap identification, personalized coaching plan, practice routing |

---

## 26 Specialized Skills

Sales loads the right skill automatically — no manual invocation needed:

**Prospecting & Research**
- `account-research` — Company intel, key contacts, recent news, hiring signals
- `exa-search-expert` — Deep web research engine for account and market intelligence
- `signal-trapper-agent` — Trigger event classification and outreach hooks
- `linkedin-prospector` — ICP filtering from LinkedIn search results
- `icp-creator` — Build and refine your Ideal Customer Profile

**Outreach & Messaging**
- `outbound-sequence` — Multi-step sequence design (email + LinkedIn + call)
- `email-coach` — Pre-send email scoring and rewrite (5-dimension rubric)
- `antislop-expert` — Forensic AI-slop detection on all draft content
- `voice-dna-creator` — Capture and enforce your authentic writing voice
- `linkedin-creator` — Bilingual LinkedIn post creation (social selling)
- `linkedin-engager` — Authentic comment generation with language detection

**Deal Execution**
- `call-prep` — Pre-call battle cards with attendee research and agenda
- `discovery-interview-prep` — Mom Test and JTBD interview design
- `negotiation-advisor` — BATNA, ZOPA, Voss-method scripts
- `proposal-builder` — SOW, pricing tiers, legal terms, Good/Better/Best
- `rfp-shredder` — Go/No-Go scoring, red flag detection, response drafts
- `champion-builder` — PACT champion scoring, development plan, arming toolkit
- `objection-library` — 20 objections × 3 variants × EN/FR response scripts
- `create-an-asset` — Custom sales assets (one-pagers, landing pages, demos)

**Pipeline & Intelligence**
- `client-management` — Account cards with buying committee and health tracking
- `competitive-intelligence` — Competitor research, differentiation matrix, talk tracks
- `win-loss-analyzer` — Root cause analysis, pattern detection, playbook generation
- `daily-briefing` — Prioritized daily sales briefing with pipeline alerts
- `hubspot-sync` — CRM sync orchestration (pipeline, contacts, activities)

**Operations**
- `para-organizer` — PARA file structure for deals, clients, and resources
- `qbr-builder` — Quarterly business reviews with ROI translation and expansion mapping

---

## Data Structure (PARA)

```
data/
├── 1-Projets/
│   ├── active-deals/       # [Company].md — deal card per prospect
│   │   └── [Company]/      # champion-profile.md, call-notes/, assets/
│   ├── closed-won/         # Closed deals available for pattern analysis
│   ├── closed-lost/        # Closed deals for win-loss analysis
│   ├── clients/            # Active customers — QBRs, account plans
│   ├── campaigns/          # Outreach sequences
│   └── call-notes/         # Post-call summaries
├── 2-Domaines/
│   ├── sales-profile.json  # Your role, quota, methodology, language
│   ├── voice-dna.json      # Your writing voice fingerprint
│   ├── icp.json            # Ideal Customer Profile
│   ├── win-loss-playbook.md # Living win-loss memory
│   └── competitive-intel/  # [Competitor].md per named competitor
│   └── LinkedIn/
│       ├── prospects.md    # LinkedIn prospect tracker
│       └── activity_log.md # Daily engagement log
├── 3-Ressources/           # Templates, reference materials
└── 4-Archives/
    └── win-loss/           # [Company]-postmortem.md per closed deal
```

---

## Connectors (Standalone → Supercharged)

Every command works standalone. Connect MCP integrations to unlock live data sync:

| Category | Placeholder | Default | Alternatives |
|----------|-------------|---------|-------------|
| **CRM** | `~~CRM` | HubSpot | Salesforce, Pipedrive, Close |
| **Transcripts** | `~~conversation intelligence` | Fireflies | Gong, Chorus, Otter.ai |
| **Enrichment** | `~~data enrichment` | Clay + Apollo | ZoomInfo, Clearbit, Lusha |
| **Email** | `~~email` | Microsoft 365 | Gmail |
| **Chat** | `~~chat` | Slack | Microsoft Teams |
| **Calendar** | `~~calendar` | Microsoft 365 | Google Calendar |
| **Cold Outreach** | `~~outreach` | Lemlist | Instantly, Smartlead |
| **Knowledge Base** | `~~knowledge base` | Notion | Confluence, Guru |

See [CONNECTORS.md](./CONNECTORS.md) for setup details.

---

## Settings

Create `sales/.claude/settings.local.json` to personalize:

```json
{
  "name": "Your Name",
  "title": "Account Executive",
  "company": "Your Company",
  "language_preference": "en",
  "methodology": "MEDDIC",
  "quota": {
    "annual": 1000000,
    "quarterly": 250000
  },
  "product": {
    "name": "Your Product",
    "value_props": ["Key value prop 1", "Key value prop 2"],
    "competitors": ["Competitor A", "Competitor B"]
  }
}
```

The plugin will guide you through this interactively with `/sales:start`.

---

## Companion Plugins

**[solo](../solo/README.md)** — If you're a solopreneur, Solo handles your business operations layer: invoicing, client management, and product pipeline. It shares the same Voice DNA and ICP infrastructure — run `/solo:start` first and Sales reads those files automatically.

**[copywriter](../copywriter/README.md)** — Extends your voice to content marketing: blog posts, newsletters, LinkedIn posts, and video scripts. Install both for the full content + sales loop.

---

*Designed for builders, by builders.*
