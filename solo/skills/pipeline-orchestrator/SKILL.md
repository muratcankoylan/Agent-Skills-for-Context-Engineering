---
name: pipeline-orchestrator
description: >
  Master skill that maps and manages the complete Discover, Validate, Design, and Prototype
  product development flow. Triggers on "start product pipeline", "what's next for this project",
  "pipeline status", or "move to next phase".
version: 1.0.0
bundle: product-build
triggers:
  - "product pipeline"
  - "orchestrate build"
  - "map product steps"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Pipeline Orchestrator

This skill acts as the master controller for the `/solo:build` command. It manages the entire product development lifecycle from initial discovery to functional prototype, tracking state, invoking sub-skills, and routing data between phases.

## State Machine

The pipeline has 4 phases with defined transitions:

```
    ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
    │ DISCOVER  │────▶│ VALIDATE │────▶│  DESIGN  │────▶│PROTOTYPE │
    └──────────┘     └──────────┘     └──────────┘     └──────────┘
         │                │                                   │
         │           pivot│                                   │
         │◀───────────────┘                                   │
         │                                                    │
         └──────────────────── restart ◀──────────────────────┘
```

### Phase Detection

Read `data/1-Projets/[project]/pipeline-status.md` to detect current phase:
- If file doesn't exist → project not started → begin at DISCOVER
- If last completed phase = Discover → current phase = VALIDATE
- If last completed phase = Validate and result = "go" → current phase = DESIGN
- If last completed phase = Validate and result = "pivot" → current phase = DISCOVER (restart)
- If last completed phase = Design → current phase = PROTOTYPE
- If all phases complete → project done → show summary

### Transition Rules

A phase can only transition to the next when its exit criteria are met:

| Phase | Exit Criteria | Output Files Required |
|-------|--------------|----------------------|
| DISCOVER | Problem statement defined, persona created | `persona.md`, `problem.md` |
| VALIDATE | Go/no-go decision recorded | `validation-results.md` |
| DESIGN | PRD complete, design brief generated | `PRD.md`, `DESIGN-BRIEF.md` |
| PROTOTYPE | Prototype artifact exists | mockup file or Figma link |

### Skip Logic

Users may skip phases. Allow skipping when:
- **Skip Discover**: User says "I already know my users and problem" → ask them to provide a brief problem statement, save it as `problem.md`, mark Discover as "Skipped"
- **Skip Validate**: User says "I've already validated this" → ask for evidence (customer quotes, survey data, pilot results), save as `validation-results.md` with status "Externally Validated"
- **Jump to Prototype**: User says "I just need a mockup" → create a minimal design brief from their description, mark upstream phases as "Skipped"

Never allow skipping without capturing the minimum context needed for downstream phases.

### Restart Logic

Restart the pipeline when:
- Validation result is "pivot" → return to Discover with the pivot reason documented
- User explicitly says "start over" or "rethink this"
- Prototype user testing reveals fundamental problem misunderstanding → return to Discover

On restart, archive current phase outputs to `data/4-Archives/[project]/attempt-N/` and reset `pipeline-status.md`.

## Skill Invocation per Phase

### DISCOVER
Invoke these skills in order:
1. `proto-persona` → outputs `persona.md`
2. `jobs-to-be-done` → outputs `jtbd.md`
3. `customer-journey-map` → outputs `journey.md`
4. `problem-statement` → outputs `problem.md` (synthesizes from above)

Optional (suggest but don't require):
- `tam-sam-som-calculator` → market sizing
- `opportunity-solution-tree` → solution mapping

### VALIDATE
1. `validation-checkpoint` → determines go/no-go/pivot
2. `pol-probe-advisor` → selects the cheapest test for the hardest truth

### DESIGN
1. `prd-development` → outputs `PRD.md`
2. `user-story` → outputs `stories.md`
3. `design-brief-generator` → outputs `DESIGN-BRIEF.md`

Optional:
- `roadmap-planning` → timeline and milestones
- `epic-breakdown-advisor` → epic decomposition

### PROTOTYPE
1. `figma-prototype` or `stitch-loop` → visual prototype
2. `prototype-to-video` → demo video (optional)
3. `stitch-asset-bridge` → asset handoff for Remotion (optional)

## Data Flow

Each phase reads the previous phase's outputs:
- VALIDATE reads: `persona.md`, `problem.md`, `journey.md`
- DESIGN reads: `problem.md`, `validation-results.md`
- PROTOTYPE reads: `PRD.md`, `DESIGN-BRIEF.md`, `stories.md`

See `references/data-flow.md` for the full output→input map across all skills.

## Pipeline Status File Format

Maintain at `data/1-Projets/[project]/pipeline-status.md`. Use the template in `references/pipeline-status-template.md`.

## Key References

- **`references/pipeline-map.md`**: Definitive map of skills per phase
- **`references/pipeline-status-template.md`**: Template for tracking pipeline state

## Worked Example

> **Project X — "Client Portal"**
> - Jan 15: Started Discover. Ran proto-persona (freelance designers), JTBD ("hire a way to share project updates without email"), journey map (identified 3 pain points in feedback loop).
> - Jan 18: Completed problem statement: "Freelance designers waste 3 hours/week chasing client feedback via email threads that get lost."
> - Jan 19: Started Validate. pol-probe-advisor recommended a "Narrative Probe" — write a fake landing page and measure interest.
> - Jan 22: 47 signups from 200 visitors (23.5% conversion). Validation: GO.
> - Jan 23: Started Design. PRD written, 12 user stories generated, design brief completed.
> - Jan 28: Prototype built in Figma via Stitch. Demo video generated. Ready for user testing.
