---
name: product-management-hygiene
description: >
  Decision hygiene for product management - prioritization, roadmap planning,
  feature scoping, effort estimation, and backlog management.
  Auto-loads when context involves product roadmap, feature prioritization,
  sprint planning, backlog grooming, RICE scoring, user story, effort
  estimation, product strategy, build vs buy, OKRs, discovery, PM review.

  Empirical: planning fallacy increases product delivery overruns by 40-80%
  (Kahneman & Lovallo, 1993). RICE/WSJF frameworks create an "illusion of
  rigor" - inputs are subjective, so outputs inherit full noise
  (Kahneman, Sibony & Sunstein, Noise, 2021). HiPPO (Highest Paid Person's
  Opinion) accounts for ~60% of de facto prioritization decisions in product
  teams without structured process (Forsgren et al., Accelerate, 2018).
bundle: domain-hygiene
triggers:
  - "product roadmap"
  - "feature prioritization"
  - "sprint planning"
  - "backlog grooming"
  - "build vs buy"
tools:
  standalone: [filesystem]
  supercharged: []
---


# Product Management - Decision Hygiene

## Why this domain is a bias minefield

Product management combines ALL ingredients of systematic poor judgment
(Kahneman, Sibony & Sunstein):

1. **Estimation under pressure** - deadlines force commitment before
   understanding, planning fallacy is the default mode
2. **Advocacy disguised as analysis** - PMs champion their features,
   RICE scores are reverse-engineered to justify decisions already made
3. **HiPPO dynamics** - roadmap discussions collapse to the highest-paid
   opinion in the room; junior PMs align rather than challenge
4. **Invisible opportunity cost** - every feature built is features not
   built; the cost of inaction on alternatives is never counted
5. **Narrative roadmaps** - roadmaps tell a story; stories cohere better
   than reality does; coherence != correctness
6. **Discovery theater** - user research is done to confirm, not to test

## Domain-specific biases (8)

Load: ${SKILL_DIR}/biases.yaml

### PM1 - RICE Laundering
Padding RICE/WSJF inputs to justify a pre-made decision.
**Question**: "What would the RICE score be if someone who DISAGREES
with building this feature filled in the inputs?"

### PM2 - HiPPO Prioritization
The highest-paid person's opinion determines the roadmap.
**Question**: "If the CPO/CEO had no opinion on this, what would the
data say the priority is?"

### PM3 - Planning Fallacy (Estimation)
Systematic underestimation of time, cost, and complexity.
**Question**: "What's the median delivery time for features of similar
scope in the last 12 months? How does this estimate compare?"

### PM4 - Discovery Theater
User research is done to validate a pre-decided solution, not to
discover real problems.
**Question**: "Did your research sessions start with the solution
or with the problem? What would have happened if users hated the idea?"

### PM5 - Sunk Cost Roadmap
Continuing a feature because it's already partially built.
**Question**: "If this feature didn't exist at all today, would you
start building it?"

### PM6 - Scope Optimism
The initial scope is always "MVP" but always grows before launch.
**Question**: "What's the actual scope after all stakeholder feedback
is incorporated? What's the minimum that delivers value if you cut 50%?"

### PM7 - Invisible Opportunity Cost
Features are evaluated in isolation, not against what else could be
built with the same resources.
**Question**: "What are the 3 best things the engineering team could
build instead? How does this feature compare?"

### PM8 - Retention Recency Bias
Loud recent feedback (Slack messages, support tickets, sales blockers)
dominates prioritization over systematic user research.
**Question**: "Is this priority driven by data or by whoever complained
loudest this week? What does the usage data say?"

## Frameworks (5)

Load: ${SKILL_DIR}/frameworks.yaml

### 1. MAP Product - Feature Scoring
6 independent dimensions:
1. **Evidence of user pain** (0-3: anecdotal; 7-10: quantified, validated at scale)
2. **Business impact** (revenue, retention, activation - causally modeled)
3. **Effort accuracy** (0-3: estimated blind; 7-10: similar feature shipped before)
4. **Strategic alignment** (0-3: tangential; 7-10: directly on the critical path)
5. **Reversibility** (0-3: permanent tech debt; 7-10: can ship/kill in one sprint)
6. **Opportunity cost** (0-3: blocks 3+ competing priorities; 7-10: net additive)

### 2. Feature Pre-mortem
"6 months post-launch. The feature flopped. What happened?"
7 product-specific failure modes.

### 3. Estimation Noise Audit
Each PM/engineer estimates independently (no anchoring). Sentinel measures
CV across estimates. CV > 40% = nobody actually knows.

### 4. Roadmap Reframes
6 techniques: churned user, competitor shipping first, cut 50%,
user who never asked for this, rebuild from first principles, kill the roadmap.

### 5. Opportunity Cost Matrix
Map all competing features by effort vs impact. Force explicit tradeoffs
before committing. No free additions.

## In-context activation

When `/sentinel` detects product management context:

**STANDARD** adds:
- MAP product dimensions (not generic)
- Domain-specific questions PM1-PM8
- Estimation anchoring check
- HiPPO detection

**FULL** adds:
- Feature pre-mortem (7 failure modes)
- Estimation noise audit (if team > 1)
- Roadmap reframes (6 perspectives)
- Reality-checker with delivery base rates
- Calibration: delivery predictions vs actual
- Opportunity cost matrix

## Templates

- Feature scorecard: ${SKILL_DIR}/templates/feature-scorecard.md
- Roadmap review: ${SKILL_DIR}/templates/roadmap-review.md
- Feature pre-mortem: ${SKILL_DIR}/templates/feature-premortem.md
- Noise audit (PM team): ${SKILL_DIR}/templates/noise-audit-pm.md
- Backlog batch scoring: ${SKILL_DIR}/templates/backlog-batch-scoring.md
- Sprint calibration: ${SKILL_DIR}/templates/sprint-calibration.md
