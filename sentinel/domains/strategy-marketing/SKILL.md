---
name: strategy-marketing-hygiene
description: >
  Decision hygiene for strategic planning in marketing and communication.
  Addresses biases in budget allocation, campaign planning, brand strategy,
  channel selection, go-to-market. Auto-loads when context involves marketing
  strategy, campaign, media budget, brand, communication plan, content
  strategy, go-to-market, launch, channel mix, audience targeting.

  Empirical: overconfidence bias -> 16% higher failure rates in strategic
  initiatives (Davis & Thompson, 2024). Planning fallacy and anchoring
  cause misaligned marketing strategies (Ying et al., 2025).
bundle: domain-hygiene
triggers:
  - "marketing strategy"
  - "campaign planning"
  - "go-to-market"
  - "media budget"
  - "channel mix"
tools:
  standalone: [filesystem]
  supercharged: []
---


# Marketing & Communication Strategy - Decision Hygiene

## Why this domain is a bias minefield

Marketing planning combines ALL ingredients of poor judgment (Kahneman,
Sibony & Sunstein).

1. **Creative projections** - no reliable data, judgment rules, noise is maximal
2. **Pressure to deliver** - the CMO promised ROI, the plan must confirm it (structural confirmation bias)
3. **Post-hoc measurement** - success -> campaign, failure -> market (self-serving bias)
4. **Trends** - "hot" channels capture budget vs proven ones (availability heuristic)
5. **HiPPO** - CEO/CMO "feels" the brand should go X (authority + action-oriented bias)

## Domain-specific biases (8)

Load: ${SKILL_DIR}/biases.yaml

### SM1 - Shiny Object Syndrome
New channel/tech attracts budget from proven channels.
**Question**: "Proven ROI of [existing] vs estimated ROI of [new]? Where does the estimate come from?"

### SM2 - Attribution Fallacy
Attributing success to campaign when correlation != causation.
**Question**: "Without this campaign, how many leads would have come anyway?"

### SM3 - Sunflower Bias (HiPPO)
Team aligns with leader's vision without challenge.
**Question**: "Who disagreed with this plan? If nobody - why?"

### SM4 - Narrative Fallacy (brand storytelling)
Coherent brand story becomes rigid constraint.
**Question**: "Brand identity is a choice. What would a competitor without this story do?"

### SM5 - Budget Anchoring
Last year's budget anchors this year's. "+10% digital" != strategy.
**Question**: "If you reallocated from zero, how would you split it?"

### SM6 - Survivorship Bias (benchmarks)
Studying successes without counting failures with same approach.
**Question**: "For each success case, how many tried the same with no result?"

### SM7 - Vanity Metrics Bias
Optimizing for impressive but irrelevant metrics (impressions, likes).
**Question**: "What's the correlation between this metric and revenue?"

### SM8 - Creative Sunk Cost
Continuing a campaign because time/money/energy already invested.
**Question**: "If this work didn't exist, would you launch this campaign?"

## Frameworks (5)

Load: ${SKILL_DIR}/frameworks.yaml

### 1. MAP Marketing Strategy
6 independent dimensions:
1. **Measurable business impact** (0-3: not measurable; 7-10: causally proven)
2. **True total cost** (budget + team time + opportunity cost)
3. **Proven audience alignment** (0-3: assumed; 7-10: tested)
4. **Competitive differentiation** (0-3: me-too; 7-10: unique)
5. **Executability** (skills, time, tools available?)
6. **Reversibility** (can we stop quickly if it fails?)

### 2. Campaign Pre-mortem
"6 months later. Campaign failed. What happened?"
7 marketing-specific failure modes.

### 3. Budget Noise Audit
Each team member allocates 100 points independently. Sentinel measures variance.

### 4. Marketing Reframes
6 techniques: departing customer, copying competitor, budget / 10, horizon x 5, total stop, new employee.

### 5. Zero-Based Budget Challenge
Rebuild budget from zero based on proven ROI only.

## In-context commands

When `/sentinel` detects a marketing/communication context:

**STANDARD** adds:
- MAP marketing dimensions (not generic)
- Domain-specific questions SM1-SM8
- Budget anchoring check

**FULL** adds:
- Campaign pre-mortem (7 failure modes)
- Budget noise audit (if team > 1)
- Marketing reframes (6 perspectives)
- Reality-checker with marketing base rates
- Calibration: KPI predictions vs actual

## Templates

- Strategic plan: ${SKILL_DIR}/templates/strategic-plan.md
- Campaign pre-mortem: ${SKILL_DIR}/templates/campaign-premortem.md
- Budget challenge (zero-based): ${SKILL_DIR}/templates/budget-challenge.md
- Leadership noise audit: ${SKILL_DIR}/templates/noise-audit-comex.md
- Initiative scorecard: ${SKILL_DIR}/templates/initiative-scorecard.md
- Campaign calibration: ${SKILL_DIR}/templates/campaign-calibration.md
