---
name: weekly-review
description: >
  Generates a structured weekly review of business health, priorities, and metrics.
  Aggregates data from pipeline, invoices, and clients. Triggers on "weekly review",
  "how's my business", "week in review", or "business health check".
version: 1.0.0
bundle: operations
triggers:
  - "weekly review"
  - "week in review"
  - "monday morning"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Weekly Review

Engine behind the `/solo:weekly-review` command. Aggregates data from multiple sources and generates a comprehensive weekly business health check.

## Data Collection

### Automatic (from local files)
1. **Pipeline**: Read `data/1-Projets/pipeline.md` via `sales-pipeline` skill
2. **Revenue**: Scan `data/1-Projets/invoices/` via `financial-health` skill
3. **Clients**: Scan `data/1-Projets/clients/` via `client-management` skill
4. **Content**: Check content calendar in `data/1-Projets/` if exists

### User Input
5. **Wins**: Ask "What went well this week?"
6. **Blockers**: Ask "What's stuck or slowing you down?"

### Supercharged (from connected tools)
- `~~CRM`: Live pipeline and activity data
- `~~invoicing`: Real-time payment status
- `~~social`: Content engagement metrics
- `~~project tracker`: Task completion rates

## Review Rubric

For each section, ask these prompting questions:

### Pipeline
- Any deal untouched in 7+ days?
- Any deal past its expected close date?
- Any new leads that need qualification?
- Did any deals change stage this week?

### Revenue
- Is monthly invoicing on track vs. target?
- Any overdue payments to chase?
- Any upcoming deliverables that trigger invoicing?

### Content
- Did we hit the planned publishing cadence?
- Which post performed best (and why)?
- What's scheduled for next week?

### Blockers
- Same blocker appearing 3 weeks in a row? → structural issue, elevate to a priority
- Anything being avoided? → flag it explicitly

### Priorities
- What has the highest revenue impact?
- What has a hard deadline this week?
- What am I avoiding that I shouldn't be?

## Pattern Recognition

Track these across reviews:

| Pattern | Signal | Action |
|---------|--------|--------|
| Same blocker 3+ weeks | Structural issue | Create a project to solve it |
| Pipeline shrinking | Not enough prospecting | Schedule prospecting time |
| Revenue below target 2+ months | Pricing or volume problem | Review pricing strategy |
| Content cadence < 50% | Calendar too ambitious | Simplify or batch |
| No wins logged | Burnout risk | Take stock of progress, celebrate small things |

## Output Template

Use `references/review-template.md` format, enhanced with the metrics and pattern analysis above.

Save review to `data/3-Ressources/weekly-review-[date].md`.

## Key References

- **`references/review-template.md`**: Standard review report structure
