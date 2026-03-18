# Data Flow Maps

How skills produce and consume structured data across the solo plugin. Each arrow shows which skill's output feeds into the next skill's input.

---

## Sales & Client Pipeline

The full journey from finding a prospect to getting paid.

```
                         ┌──────────────────┐
                         │  company-research │
                         │  ───────────────  │
                         │  IN: company name │
                         │  + icp.json       │
                         │  OUT: data/3-Ressources/[company].md │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  draft-outreach   │
                         │  ───────────────  │
                         │  IN: [company].md │
                         │  + voice-dna.json │
                         │  + icp.json       │
                         │  OUT: outreach message (email/LinkedIn) │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  discovery-call   │
                         │  ───────────────  │
                         │  IN: [company].md │
                         │  + outreach context│
                         │  OUT: data/1-Projets/[project]/call-summary.md │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ proposal-generator│
                         │  ───────────────  │
                         │  IN: call-summary │
                         │  + pricing-strategy│
                         │  + business-profile│
                         │  OUT: data/1-Projets/[project]/proposal.md │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │contract-templates │
                         │  ───────────────  │
                         │  IN: proposal.md  │
                         │  (scope & terms)  │
                         │  OUT: data/1-Projets/[project]/contract.md │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │client-management  │
                         │  ───────────────  │
                         │  IN: proposal +   │
                         │  contract + call  │
                         │  OUT: data/1-Projets/clients/[client].md │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ project-management│
                         │  ───────────────  │
                         │  IN: proposal     │
                         │  deliverables     │
                         │  OUT: data/1-Projets/[project]/README.md │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ invoice-generator │
                         │  ───────────────  │
                         │  IN: client card  │
                         │  + project milestones │
                         │  + pricing-strategy│
                         │  OUT: data/1-Projets/invoices/INV-YYYY-NNN.md │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ financial-health  │
                         │  ───────────────  │
                         │  IN: all invoices │
                         │  + pipeline data  │
                         │  OUT: revenue dashboard + P&L │
                         └──────────────────┘
```

### File Location Summary (Sales)

| Skill | Output File | Location |
|-------|------------|----------|
| company-research | Research findings | `data/3-Ressources/[company-name].md` |
| draft-outreach | Outreach message | Clipboard / direct send via ~~email |
| discovery-call | Call summary | `data/1-Projets/[project]/call-summary.md` |
| proposal-generator | Proposal | `data/1-Projets/[project]/proposal.md` |
| contract-templates | Contract | `data/1-Projets/[project]/contract.md` |
| client-management | Client card | `data/1-Projets/clients/[client-name].md` |
| project-management | Project tracker | `data/1-Projets/[project]/README.md` |
| invoice-generator | Invoice | `data/1-Projets/invoices/INV-YYYY-NNN.md` |
| financial-health | Dashboard | Output to screen / `data/3-Ressources/financial-dashboard.md` |
| pricing-strategy | Rate card | `data/2-Domaines/rate-card.md` |
| sales-pipeline | Pipeline | `data/1-Projets/pipeline.md` |

---

## Product Pipeline

The journey from idea to validated prototype.

```
     ┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐
     │  proto-persona   │    │  jobs-to-be-done  │    │ problem-statement │
     │  ──────────────  │    │  ──────────────── │    │  ──────────────  │
     │  OUT: persona.md │    │  OUT: jtbd.md     │    │  OUT: problem.md │
     └────────┬────────┘    └────────┬──────────┘    └────────┬────────┘
              │                      │                         │
              └──────────────────────┼─────────────────────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │   DISCOVER phase      │
                         │   ─────────────────── │
                         │   Combined output:    │
                         │   data/1-Projets/[project]/discovery-summary.md │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ validation-checkpoint  │
                         │   ─────────────────── │
                         │   IN: discovery-summary│
                         │   + pol-probe-advisor  │
                         │   OUT: data/1-Projets/[project]/validation-results.md │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │   VALIDATE phase      │
                         │   ─────────────────── │
                         │   Decision: GO →      │
                         │   ITERATE → PIVOT →   │
                         │   KILL                │
                         └───────────┬───────────┘
                                     │ (if GO)
                                     ▼
                         ┌───────────────────────┐
                         │  prd-development      │
                         │   ─────────────────── │
                         │   IN: discovery-summary│
                         │   + validation-results │
                         │   OUT: data/1-Projets/[project]/PRD.md │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │  user-stories         │
                         │   ─────────────────── │
                         │   IN: PRD.md          │
                         │   OUT: data/1-Projets/[project]/user-stories.md │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ design-brief-generator │
                         │   ─────────────────── │
                         │   IN: PRD.md          │
                         │   + user-stories.md   │
                         │   OUT: data/1-Projets/[project]/DESIGN-BRIEF.md │
                         └───────────┬───────────┘
                                     │
                            ┌────────┴────────┐
                            ▼                 ▼
               ┌──────────────────┐  ┌──────────────────┐
               │ figma-prototype  │  │   stitch-loop    │
               │  ──────────────  │  │  ──────────────  │
               │  IN: DESIGN-BRIEF│  │  IN: DESIGN-BRIEF│
               │  OUT: Figma file │  │  OUT: prototype  │
               └────────┬─────────┘  └────────┬─────────┘
                        │                      │
                        └──────────┬───────────┘
                                   ▼
                         ┌───────────────────────┐
                         │  stitch-asset-bridge   │
                         │   ─────────────────── │
                         │   IN: prototype assets │
                         │   OUT: asset-manifest.json │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ prototype-to-video    │
                         │   ─────────────────── │
                         │   IN: asset-manifest  │
                         │   + storyboard.md     │
                         │   OUT: Remotion video  │
                         └───────────────────────┘
```

### File Location Summary (Product)

| Skill | Output File | Location |
|-------|------------|----------|
| proto-persona | Persona | `data/1-Projets/[project]/persona.md` |
| jobs-to-be-done | JTBD map | `data/1-Projets/[project]/jtbd.md` |
| problem-statement | Problem brief | `data/1-Projets/[project]/problem.md` |
| validation-checkpoint | Validation results | `data/1-Projets/[project]/validation-results.md` |
| prd-development | Product Requirements | `data/1-Projets/[project]/PRD.md` |
| user-stories | User stories | `data/1-Projets/[project]/user-stories.md` |
| design-brief-generator | Design brief | `data/1-Projets/[project]/DESIGN-BRIEF.md` |
| stitch-asset-bridge | Asset manifest | `data/1-Projets/[project]/asset-manifest.json` |
| storyboard | Storyboard | `data/1-Projets/[project]/storyboard.md` |

---

## Content & Marketing Pipeline

From strategy to published content.

```
     ┌──────────────────┐    ┌──────────────────┐
     │ business-profile  │    │    icp-creator   │
     │  (pillars, voice) │    │  (pain points)   │
     └────────┬─────────┘    └────────┬─────────┘
              │                        │
              └────────────┬───────────┘
                           ▼
              ┌──────────────────────┐
              │content-calendar-planner│
              │  ────────────────────│
              │  IN: pillars + pains │
              │  OUT: data/1-Projets/content-calendar-[month].md │
              └────────────┬─────────┘
                           │
                           ▼
              ┌──────────────────────┐
              │  linkedin-post /     │
              │  newsletter-writer / │
              │  blog-post           │
              │  ────────────────────│
              │  IN: calendar topic  │
              │  + voice-dna.json    │
              │  OUT: draft content  │
              └────────────┬─────────┘
                           │
                           ▼
              ┌──────────────────────┐
              │   weekly-review      │
              │  ────────────────────│
              │  IN: calendar status │
              │  + publishing data   │
              │  OUT: content perf   │
              │  section in review   │
              └──────────────────────┘
```

---

## Identity Files (Shared Inputs)

These files are created during onboarding (`/solo:start`) and consumed by many skills:

| File | Location | Created By | Consumed By |
|------|----------|-----------|-------------|
| `business-profile.json` | `data/2-Domaines/` | business-profile-creator | content-calendar, proposal-generator, pricing-strategy |
| `voice-dna.json` | `data/2-Domaines/` | voice-dna-creator | linkedin-post, newsletter-writer, draft-outreach, blog-post |
| `icp.json` | `data/2-Domaines/` | icp-creator | company-research, draft-outreach, content-calendar, exa-search |
| `rate-card.md` | `data/2-Domaines/` | pricing-strategy | proposal-generator, invoice-generator |

---

## Pipeline Status Tracking

The `pipeline-orchestrator` maintains the overall project phase in:
`data/1-Projets/[project]/pipeline-status.md`

This file is updated as skills complete their outputs. Use the phase detection logic in `pipeline-orchestrator/SKILL.md` to determine the current phase and available transitions.
