---
name: ma-hygiene
description: >
  Decision hygiene for M&A and due diligence - target evaluation, IC memo
  structuring, committee noise audit, and integration pre-mortem.
  Auto-loads when context involves: acquisition, merger, due diligence, target
  evaluation, investment committee, deal, valuation, synergies, LOI, term sheet,
  integration.

  Empirical: Lovallo et al. (HBR, 2007) - cognitive biases are identifiable
  at EVERY stage of the M&A process. Aschbacher & Kroon (2025) - client-advisor
  relationships generate additional biases via time pressure, standardization,
  and emotional stakes. Deal completion bias: teams with skin in the process
  systematically underestimate integration complexity by 40-60%.

bundle: domain-hygiene
triggers:
  - "acquisition"
  - "merger"
  - "due diligence"
  - "target evaluation"
  - "investment committee"
  - "IC memo"
  - "LOI"
  - "term sheet"
  - "synergies"
  - "valuation"
  - "integration"
  - "deal"
tools:
  standalone: [filesystem]
  supercharged: []
---


# M&A - Decision Hygiene

## Why this domain is the highest-stakes bias environment

M&A combines every ingredient for systematic poor judgment:

**1. Deal completion bias**
Teams working a deal develop an emotional and professional investment in
closing it. The due diligence process creates commitment escalation -
every hour spent makes the sunk cost larger and the exit more painful.
The team that should kill the deal is the team most motivated to close it.

**2. Artificial time pressure**
M&A timelines are often compressed by competitive dynamics, seller pressure,
or banker incentives. Compressed timelines kill independent evaluation:
dimensions bleed into each other, dissent gets suppressed, the deal
narrative accelerates past the questions it hasn't answered.

**3. Synergy theater**
Synergy projections are the most consistently overestimated figures in
corporate finance. McKinsey: 70% of M&A deals fail to create value.
Synergies projected during deal enthusiasm are rarely stress-tested against
the specific execution requirements of THIS integration.

**4. Committee dynamics and noise**
Investment committees produce high-noise evaluations when members hear
each other's opinions before scoring. The first speaker anchors. Seniority
distorts junior members' positions. The noise audit (Kahneman, Noise, 2021)
reveals how much judgment variance is occurring - a number that is almost
always shocking.

**5. Integration as afterthought**
Post-acquisition integration is where value is created or destroyed, yet
it receives a fraction of the analytical attention of the deal terms.
A pre-mortem on the integration - not the deal - is the highest-value
intervention available.

## Two modes

### Mode 1: Single evaluator (`/sentinel ma [decision]`)
Full MAP evaluation of a target or deal, using the 6 M&A-specific dimensions.
Runs: structure-builder -> questioner (MA1-MA8 biases) -> reality-checker
(base rates) -> failure-finder (integration pre-mortem).

### Mode 2: Committee noise audit (`/sentinel ma noise-audit`)
Multi-member evaluation protocol. Each member scores independently.
Sentinel measures noise between members. Identifies which dimensions
have the most disagreement and why.
This is the commercial flagship - the number that silences the room.

## Key principle: Integration first

Most M&A analysis focuses on the deal. Sentinel focuses on the integration.
The deal terms are visible. The integration complexity is hidden.
A pre-mortem on integration is more valuable than a pre-mortem on deal terms
because the failure modes are less obvious and more preventable.

## Templates

| Template | When to use |
|---|---|
| `ma-target-evaluation.md` | Full MAP evaluation of an acquisition target |
| `ic-memo-structured.md` | Investment committee memo with MAP scoring embedded |
| `noise-audit-committee.md` | Multi-member noise measurement for any committee |
| `integration-premortem.md` | Pre-mortem on post-acquisition integration specifically |
| `legal-dd-review.md` | Structured legal DD - risk matrix, disclosure protocol, negotiation triage |

## Mode 3: Legal counsel (`/sentinel ma legal [scope]`)

Specialized layer for M&A lawyers. Loads `lawyer-biases.yaml` (LA1-LA7)
and `lawyer-frameworks.yaml` in addition to the M&A core.

Key lens: lawyers are trained to IDENTIFY risks, not to assess their
PROBABILITY. Sentinel forces probability weighting on every legal risk -
the column in DD reports that almost never gets filled.

Auto-activates when context mentions: counsel, legal DD, SPA, reps and
warranties, disclosure letter, conditions precedent, legal opinion, closing.

## Commands

| Command | Route |
|---|---|
| `/sentinel ma [target description]` | Full single-evaluator analysis |
| `/sentinel ma noise-audit` | Committee mode - collect independent scores |
| `/sentinel ma integration [deal]` | Integration pre-mortem only |
| `/sentinel ma memo` | IC memo with MAP scoring |
| `/sentinel ma legal [DD scope]` | Legal DD with LA1-LA7 bias lens + risk matrix |
| `/sentinel ma legal negotiation` | Negotiation triage - expected value per open point |
| `/sentinel ma legal disclosure` | Disclosure letter review protocol |
