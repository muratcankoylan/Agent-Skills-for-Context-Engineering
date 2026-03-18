# Connectors

## How tool references work

This plugin uses `~~category` as a placeholder for whatever tool you connect in that category (e.g., `~~CRM`). This allows the plugin to be tool-agnostic, describing workflows in terms of general categories rather than specific products. You can connect your preferred tools from the options below.

## Connectors for this plugin

| Category | Placeholder | Included servers | Other options |
|----------|-------------|-----------------|---------------|
| Calendar | `~~calendar` | Microsoft 365 | Google Calendar |
| Chat | `~~chat` | Slack | Microsoft Teams, Discord |
| CRM | `~~CRM` | HubSpot | Pipedrive, Close, Copper |
| Data enrichment | `~~data enrichment` | Clay | Apollo, Clearbit |
| Email | `~~email` | Microsoft 365 | Gmail |
| Invoicing | `~~invoicing` | Stripe | Wave, QuickBooks, FreshBooks |
| Knowledge base | `~~knowledge base` | Notion | Obsidian, Confluence |
| Search | `~~search` | Exa | Tavily, Google |
| Social | `~~social` | LinkedIn MCP | Twitter/X |
| Meeting transcription | `~~transcription` | Fireflies | Otter.ai, Grain |
| Project tracker | `~~project tracker` | Notion | Linear, Asana, Trello |
| Storage | `~~storage` | Filesystem | Google Drive, Dropbox |
| Forms | `~~forms` | Tally | Typeform, Fillout |

## Companion Plugins

| Plugin | Handles | Install |
|--------|---------|---------|
| **copywriter** | Blog posts, newsletters, LinkedIn posts, content calendar, anti-slop auditing | `knowledge-work-plugins/copywriter` |
| **solo-studio** | Figma prototypes, Remotion videos, Stitch mockups | `knowledge-work-plugins/solo-studio` |

Solo creates your **Voice DNA** (`data/2-Domaines/voice-dna.json`) and **ICP** (`data/2-Domaines/icp.json`). Both companion plugins read these files automatically — no reconfiguration needed.