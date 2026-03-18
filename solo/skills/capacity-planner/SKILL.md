---
name: capacity-planner
description: >
  Answers "can I take this project?" by calculating available hours, current load,
  and realistic delivery timelines. Prevents overcommitment and burnout.
  Triggers on "can I take this project", "how busy am I", "do I have capacity",
  "available hours", "when can I start", or "am I overloaded".
version: 1.0.0
bundle: operations
triggers:
  - "capacity planning"
  - "can I take this project"
  - "bandwidth check"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Capacity Planner

The most dangerous word for a solopreneur is "yes." This skill quantifies your available capacity so you can make that decision with data, not optimism. It also helps you explain timelines to clients without underselling or overcommitting.

## The Solopreneur Capacity Reality

Raw available hours are not billable hours. Use this model as the default:

```
Working days per month:           ~22 days
Hours per working day:            8 hours
─────────────────────────────────────────
Raw hours/month:                  176 hours
Minus admin & overhead (20%):     -35 hours
Minus business development (15%): -26 hours
Minus breaks / energy loss (10%): -18 hours
─────────────────────────────────────────
TRUE BILLABLE HOURS/MONTH:        ~97 hours
```

**Key insight:** You have roughly 100 truly billable hours per month, not 176. Anyone who plans otherwise burns out or misses deadlines.

User's actual capacity target is loaded from `data/2-Domaines/business-profile.json` → `weekly_billable_hours` field (if set). Default: 25 hours/week.

## Current Load Calculation

### Step 1: Read Active Projects

Scan `data/1-Projets/` for all project README.md files where status ≠ "Complete" and ≠ "Archived".

For each active project, extract:
- Total estimated hours remaining (from milestones)
- Deadline (from project metadata)
- Weekly hours committed (total remaining ÷ weeks until deadline)

### Step 2: Read Pipeline Commitments

Scan `data/1-Projets/pipeline.md` for deals at "Verbal Commit" or "Negotiation" stage — these are quasi-committed and should be factored in at 70% probability.

### Step 3: Calculate Load

```
Available hours/week:            [from profile, default 25h]
Committed project hours/week:    [sum of active project commitments]
Pipeline quasi-committed (70%):  [likely pipeline × 70%]
─────────────────────────────────
Remaining available:             Available - Committed - Pipeline
```

### Step 4: Produce Load Report

```markdown
# Capacity Report — [Date]

## Available Capacity
- Weekly target: [X] hours
- Currently committed: [Y] hours
- Remaining: [Z] hours/week ([X-Y-Z])

## Load Status: [🟢 Capacity / 🟡 Near Full / 🔴 Overloaded]

## Active Projects
| Project | Client | Hours Remaining | Deadline | Weekly Burn |
|---------|--------|-----------------|----------|-------------|
| [name] | [client] | [X]h | [date] | [X]h/week |

## Near-Committed Pipeline
| Opportunity | Estimated Hours | Start | Risk |
|-------------|----------------|-------|------|
| [deal] | [X]h | [date] | 70% |

## Available Slots
- This week: [X] hours
- This month: [X] hours
- [Month+1]: [X] hours (estimate)
```

## "Can I Take This?" Decision

When user asks "can I take [project]?" — ask for:
1. Estimated total hours (if not provided, estimate from scope)
2. Desired start date
3. Hard deadline (if any)

Then produce:

```markdown
# Can You Take: [Project Name]?

## The Numbers
- Project requires: [X] hours over [Y] weeks = [Z] hours/week
- Your available: [A] hours/week
- Gap: [A - Z] hours/week ([OK / SHORTFALL of X hours])

## Verdict: [✅ Yes / ⚠️ Yes, with conditions / ❌ No]

### If Yes:
- Realistic start: [date]
- Realistic completion: [date based on actual capacity]
- Conditions: [any risks or dependencies]

### If No:
- Earliest possible start: [date]
- What would need to change: [complete [project], defer [task], reduce hours on [project]]

### The Optimistic Trap Warning:
[If calculated delivery date is later than client expects, flag this explicitly]
"Completing by [client's deadline] requires [X]h/week. You currently have [Y]h/week available.
To hit their date you'd need to: [options list]."
```

## Effective Hourly Rate Tracking

Once a project is complete, compare estimated vs actual hours:

```
Project: [Name]
Invoiced: €[X]
Estimated hours: [Y]
Actual hours: [Z]

Estimated rate: €[X/Y]/hour
Actual rate: €[X/Z]/hour

[If actual < estimated rate by >20%: flag for pricing calibration]
```

Save to `data/4-Archives/project-actuals/` for building a personal baseline.

**After 5+ completed projects**, capacity planner uses your personal baseline instead of generic estimates (e.g., "Your website projects average 1.4× your initial estimates").

## Overload Detection

Flag automatically during `weekly-review` or `monday-morning-agent` if:
- Committed hours > 110% of available hours (overloaded)
- Any project has estimated completion > deadline based on current burn rate
- 3+ active projects simultaneously (cognitive load risk regardless of hours)

**Overload script for client communication:**
> "I've reviewed my current commitments and I want to be transparent: I'm at capacity until [date]. I can start [project] on [date] and commit to [realistic deadline]. I'd rather be honest now than overpromise and underdeliver."

## Weekly Hours Log (Optional)

If user wants to track actual hours for rate calibration:

Log to `data/1-Projets/[project]/time-log.md`:
```
| Date | Task | Hours | Notes |
|------|------|-------|-------|
| [date] | [task description] | [X] | |
```

Skill reads these logs to compute actual vs. estimated hours per project.

## Integration Points

- **`project-management`**: Provides estimated hours remaining per project
- **`sales-pipeline`**: Provides pipeline commitments for near-term capacity planning
- **`weekly-review`**: Consumes capacity status for the week-ahead section
- **`monday-morning-agent`**: Reads capacity before generating the weekly plan
- **`financial-health`**: Uses actual hours to compute effective hourly rate
- **`pricing-strategy`**: Uses capacity data to set sustainable rates

## Key References

- **`references/capacity-model.md`**: Billable hours model with customization guide
- **`references/project-sizing-guide.md`**: How to estimate hours for common project types before you commit
