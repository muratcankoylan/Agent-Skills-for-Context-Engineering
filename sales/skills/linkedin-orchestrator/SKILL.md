---
name: linkedin-orchestrator
description: >
  Generate a daily LinkedIn outreach to-do list based on the 360Brew algorithm strategy.
  Adapts to `sales-profile.json` for Bilingual Schedule (EN/FR) and Target Geography.
  Four modes - (1) AUTONOMOUS with "start linkedin", (2) CREATE plan, (3) RESUME plan, (4) CHECK SCHEDULE.
  Determines current Time Block (Morning/Content/Midday/Afternoon/Evening) and executes tasks.
bundle: linkedin-social
triggers:
  - "start linkedin"
  - "create linkedin plan"
  - "resume linkedin"
tools:
  standalone: [filesystem]
  supercharged: [linkedin]
version: 1.0.0
---

# LinkedIn Orchestrator (The Manager)

Generate a structured daily outreach to-do list based on the 360Brew algorithm strategy. Integrates with all LinkedIn skills for seamless execution.

## Configuration

Reads `data/2-Domaines/sales-profile.json` for:
- `language_preference`: "English", "French", or "Bilingual"
- `target_geography`: e.g., "France", "Canada", "ASEAN"
- `selling_methodology`: e.g., "MEDDIC", "SPIN"

## Trigger

| Intent | Phrase |
|--------|--------|
| Create new plan | "plan my day", "daily linkedin plan", "linkedin to-do" |
| Resume existing | "resume linkedin", "linkedin status" |
| Autonomous run | "start linkedin", "run linkedin autonomously" |

## Time Blocks

| Block | Time | Focus |
|-------|------|-------|
| **Morning** | Before 10:00 | Warming & Commenting (9 comments) |
| **Content** | 10:00–12:00 | Creation & Scheduling (12h gap rule) |
| **Midday** | 12:00–15:00 | Golden Hour & Replies |
| **Afternoon** | 15:00–18:00 | Prospecting & Connections |
| **Evening** | After 18:00 | Audit & CRM Sync |

## Skills Integration

| Task | Skill |
|------|-------|
| Write Comments | `linkedin-engager` |
| Create Post | `linkedin-creator` |
| Find Prospects | `linkedin-prospector` |
| Sync CRM | `hubspot-sync` |

See `references/schedule.md` for the full autonomous execution flow, bilingual posting schedule, daily engagement limits, 12-hour rule, CRM sync steps, and resume workflow.
