---
name: sales-pipeline
description: >
  Manages a lightweight sales pipeline, tracks deal stages, flags risks, and generates
  weekly action plans. Triggers on "my pipeline", "deal status", "pipeline review",
  "show deals", or "pipeline health".
version: 1.0.0
bundle: sales-growth
triggers:
  - "sales pipeline"
  - "pipeline status"
  - "deal tracking"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Sales Pipeline

A file-based sales pipeline tracker that helps visualize deal flow, identify at-risk deals, and plan weekly sales activities. Primary skill for `/solo:clients pipeline`.

## Pipeline Data

Central file: `data/1-Projets/pipeline.md` — uses the template in `references/pipeline-template.md`.

## Deal Stages

| Stage | Definition | Exit Criteria | Probability |
|-------|-----------|---------------|-------------|
| **Prospect** | Identified as a potential client, no conversation yet | First meaningful interaction | 10% |
| **Discovery** | Initial conversation, exploring fit | Discovery call completed | 20% |
| **Proposal** | Proposal or SOW sent | Client confirms receipt and review | 40% |
| **Negotiation** | Discussing terms, pricing, scope | Verbal agreement or final objections | 60% |
| **Verbal Commit** | Agreed in principle, waiting on paperwork | Contract sent | 80% |
| **Closed Won** | Signed and paid (or first payment received) | -- | 100% |
| **Closed Lost** | Deal is dead | -- | 0% |

## Risk Scoring

Flag deals that show warning signs:

| Risk Signal | Threshold | Action |
|-------------|-----------|--------|
| **Stale deal** | No activity in 14+ days | Re-engage or downgrade |
| **Stuck in stage** | Same stage for 30+ days | Investigate blocker, multi-thread |
| **Past close date** | Expected close date has passed | Update date or qualify out |
| **Single-threaded** | Only one contact at the company | Identify additional stakeholders |
| **No next action** | Next Action field is empty | Define a concrete next step |
| **Ghost** | Last 2+ outreach attempts unanswered | Send breakup email or remove |

## Pipeline Health Dashboard

When showing the pipeline, generate:

```markdown
# Pipeline Health — [Date]

## Summary
- **Active deals:** [N] worth [total]
- **Weighted pipeline:** [sum of value x probability per stage]
- **Avg deal size:** [total / N]
- **Avg deal age:** [X days]

## By Stage
| Stage | Deals | Value | % of Pipeline |
|-------|-------|-------|---------------|
| Discovery | [N] | [X] | [X%] |
| Proposal | [N] | [X] | [X%] |
| Negotiation | [N] | [X] | [X%] |
| Verbal Commit | [N] | [X] | [X%] |

## Risk Flags
| Deal | Value | Risk | Days | Action |
|------|-------|------|------|--------|
| [Deal] | [X] | Stale | [X] | [Re-engage / Remove] |
| [Deal] | [X] | Stuck | [X] | [Push / Multi-thread] |

## Weekly Action Plan
1. [ ] [Highest priority deal action]
2. [ ] [Second priority action]
3. [ ] [Third priority action]
```

## Pipeline Metrics for Weekly Review

Provide these to the `weekly-review` skill:

| Metric | Healthy | Warning | Action Needed |
|--------|---------|---------|---------------|
| Active deals | 3-8 | < 3 | Increase prospecting |
| Pipeline value | > 2x monthly target | 1-2x | Need more or larger deals |
| Deal velocity | < 30 days avg | 30-60 days | Check for stuck stages |
| Win rate | > 25% | 10-25% | Improve qualification |
| Deals added/week | 1-2 new | 0 for 2+ weeks | Pipeline drying up |

## Supercharged Mode

If `~~CRM` is connected:
- Pull pipeline data from CRM instead of local file
- Provide real-time view with activity history
- Update deal stages in both local file and CRM
- Track engagement scoring from email/meeting activity

## Key References

- **`references/pipeline-template.md`**: Pipeline file structure
