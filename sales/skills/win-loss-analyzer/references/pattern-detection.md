# Pattern Detection: Reading Signal from Multiple Deals

## Minimum Sample Sizes

| Analysis Type | Minimum Deals | Confidence Level |
|--------------|---------------|-----------------|
| Directional insight | 5 | Low — indicative only |
| Actionable pattern | 10–15 | Medium — worth acting on |
| Statistical confidence | 30+ | High — change process |

**Rule**: With fewer than 5 deals, produce a hypothesis, not a conclusion. Always label confidence level in the output.

---

## The Core Pattern Questions

For every batch analysis, answer these questions explicitly:

### 1. Where are we winning?

- **ICP Alignment**: What % of wins were perfect-ICP vs. off-ICP?
- **Lead Source**: Which sources produce the highest win rates (not the most volume)?
- **Deal Size**: At what deal size do we win most consistently?
- **Vertical/Segment**: Any vertical where we punch above average?

### 2. Where are we losing — and why?

- **Loss Category Distribution**: Which of the 6 categories dominates?
  - If >40% are "Value Gap" → Discovery process needs overhaul
  - If >40% are "Access Gap" → Need multi-threading playbook
  - If >40% are "Price Gap" → Need ROI model and value anchoring training
  - If >30% are "Process Gap" → Proposal/demo quality issue
- **Stage Where Deals Die**: Where in the funnel do most losses occur?
  - Discovery → Qualification problem (wrong deals entering)
  - Proposal → Value not landing, or champion not empowered
  - Negotiation → Pricing strategy, concession management
- **Speed to Loss**: How fast do losses close vs. wins? Slow losses waste quota.

### 3. Who is beating us and where?

For each named competitor:

| Competitor | # Times in Deal | Our Win Rate | Their Strength | Our Counter |
|-----------|----------------|--------------|----------------|-------------|
| [Name] | [#] | [%] | [What they do well] | [Our best response] |

**Competitive Win Rate Interpretation**:
- Win rate > 60% vs. a competitor: Dominant position. Maintain and document what's working.
- Win rate 40–60%: Contested. Deal-specific factors dominate. Focus on discovery quality.
- Win rate < 40%: Structural weakness. Either fix the product gap or adjust ICP to avoid them.

### 4. What is our ideal deal profile?

Build the "Perfect Win" composite from your best deals:

```
Ideal Deal Profile:
- Industry: [Most common in wins]
- Company size: [Sweet spot employees / revenue]
- Champion title: [Most effective champion role]
- Economic Buyer title: [Who signs]
- Deal size: [$X–$Y range]
- Sales cycle: [X–Y weeks]
- Lead source: [Best source]
- Trigger event: [What event preceded the win]
```

This composite becomes input to `icp-creator` for profile refinement.

---

## Red Flag Patterns (Act Immediately)

These patterns require process changes, not just coaching:

| Pattern | Threshold | Interpretation | Action |
|---------|-----------|----------------|--------|
| Loss category "Access Gap" | >35% of losses | You're consistently selling to the wrong level | Add multi-thread checkpoint to sales process |
| Average sales cycle > 2x your target | Across all deals | Qualification is too loose | Tighten entry criteria; add BANT/MEDDIC gate at Stage 2 |
| Win rate declining 3 consecutive months | Any % decline | Competitive or market shift | Run competitive intelligence sprint |
| Loss rate spiking at one specific stage | >50% of losses at same stage | Process failure at that stage | Audit all deals at that stage; run role plays |
| Wins concentrated in <2 verticals | >60% of wins | ICP too broad; opportunity to specialize | Refocus ICP; build vertical-specific assets |

---

## Output Templates

### Pattern Summary (5–15 deals)

```markdown
## Win-Loss Pattern Summary
**Period**: [Q / Month Range]
**Deals Analyzed**: [X won, Y lost, Z no decision]
**Confidence Level**: [Low / Medium / High]

### Top Insights

1. **[Most important finding]** — [Evidence + recommendation]
2. **[Second finding]** — [Evidence + recommendation]
3. **[Third finding]** — [Evidence + recommendation]

### Loss Category Distribution
- Value Gap: [X%]
- Access Gap: [X%]
- Trust Gap: [X%]
- Price Gap: [X%]
- Timing Gap: [X%]
- Process Gap: [X%]

### Competitive Summary
- Win rate vs. [Competitor A]: [X%]
- Win rate vs. [Competitor B]: [X%]

### Recommended Process Changes
1. [ ] [Specific change — who owns it, when to implement]
2. [ ] [Second change]
```
