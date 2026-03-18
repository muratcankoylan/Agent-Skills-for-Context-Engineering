---
name: win-loss-analyzer
description: >
  Forensic post-mortem tool for closed deals (Won or Lost). Identifies patterns across multiple outcomes,
  surfaces root causes, and outputs an actionable playbook to replicate wins and prevent losses.
  Triggers: "analyze why we lost", "debrief on [Company]", "run a win-loss report", "why did we win the Acme deal".
bundle: coaching-quality
triggers:
  - "analyze why we lost"
  - "debrief on [Company]"
  - "run a win-loss report"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# Skill: Win-Loss Analyzer

Stop guessing why you win and lose. Build an evidence-based answer.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Single-deal post-mortem: root cause analysis in 5 minutes   │
│  ✓ Pattern detection across multiple outcomes                   │
│  ✓ Competitive analysis: where you win/lose vs. specific rivals │
│  ✓ Playbook generation: replicate wins, prevent losses          │
│  ✓ Bilingual (EN/FR): adapt language per sales-profile.json    │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~CRM)                                   │
│  + Pull closed deals automatically (no manual input)            │
│  + Statistical patterns across 50+ deals                        │
│  + Segment by ICP, deal size, geography, rep                    │
│  + Track playbook adoption over time                            │
└─────────────────────────────────────────────────────────────────┘
```

## 🧠 Core Philosophy

1. **Perception ≠ Reality**: Reps say "price" was the reason they lost. Buyers say "trust". Run this process to find the truth.
2. **Patterns beat anecdotes**: One loss tells you almost nothing. Ten losses tell you everything.
3. **Wins need autopsies too**: Knowing why you win is as important as knowing why you lose. You can't replicate luck.
4. **Competitor intel is a by-product**: Every loss to a named competitor is a competitive intelligence event.

---

## 🛠 Agent Instructions

### Phase 1: Single-Deal Post-Mortem

**Trigger**: "Debrief on the Acme deal."

**Steps**:

1. **Load Deal Context**: Read `data/1-Projets/active-deals/[Client].md` or ask user for:
   - Outcome (Won / Lost / No Decision)
   - Deal size and stage at close
   - Why we lost (internal narrative)
   - Known competitors in the deal
   - Key contacts and their roles
   - Timeline from first contact to close

2. **Apply Root Cause Framework**: See `references/root-cause-framework.md`
   - Ask the **5 Whys** on the stated reason
   - Map to one of 6 loss categories (see below)
   - Identify the **Last Recoverable Moment** — the latest point where the outcome could have changed

3. **Loss Category Diagnosis**:

   | Category | Symptoms | Telltale Signal |
   |----------|----------|-----------------|
   | **Value Gap** | "Not sure we need this" | Discovery was shallow; pain wasn't quantified |
   | **Access Gap** | "Champion couldn't get budget" | Never reached the Economic Buyer |
   | **Trust Gap** | "We went with the safer option" | No references, no credibility markers |
   | **Price Gap** | "Too expensive" | Value was not tied to specific ROI numbers |
   | **Timing Gap** | "Not the right time" | No compelling event established |
   | **Process Gap** | "Competitor had a slicker eval" | Demo/proposal was generic, not tailored |

4. **Output**: A "Deal Autopsy" document. See output format below.

---

### Phase 2: Pattern Analysis (Multi-Deal)

**Trigger**: "Show me our loss patterns this quarter."

**Steps**:

1. **Collect Data**: Load deal files from `data/1-Projets/closed-lost/` and `data/1-Projets/closed-won/`.
   - If no files, ask user to paste a CSV or describe 5+ recent outcomes.

2. **Run Pattern Detection** (see `references/pattern-detection.md`):

   ```python
   # Pattern Analysis Logic
   deals = load_deals(status=["won", "lost"])

   # Segment analysis
   loss_by_category = group_by(deals[status=="lost"], "loss_category")
   win_by_source = group_by(deals[status=="won"], "lead_source")
   competitor_win_rate = {}

   for deal in deals:
       if deal.competitor:
           if deal.competitor not in competitor_win_rate:
               competitor_win_rate[deal.competitor] = {"won": 0, "lost": 0}
           competitor_win_rate[deal.competitor][deal.status] += 1

   # ICP alignment
   icp_aligned_wins = filter(deals, icp_score > 70, status="won")
   icp_misaligned_losses = filter(deals, icp_score < 50, status="lost")

   # Deal size analysis
   avg_won_size = mean(deals[status=="won"].amount)
   avg_lost_size = mean(deals[status=="lost"].amount)
   ```

3. **Insight Generation**: Surface the top 3 actionable insights. Do not produce a list of observations — produce a list of **recommended changes**.

---

### Phase 3: Playbook Generation

**Trigger**: "Build me a playbook from our wins."

**Steps**:

1. **Extract Win DNA**:
   - Common ICP characteristics in wins
   - Lead sources with highest win rates
   - Typical deal velocity for wins
   - Objections raised and successfully handled
   - What made the champion effective

2. **Build the Anti-Loss Checklist**: A checklist of the top 5 risks to validate on every deal. Saved to `data/2-Domaines/win-loss-playbook.md`.

3. **Update ICP**: If patterns reveal a mismatch between target ICP and actual wins, flag for `icp-creator` review.

---

## 📄 Output Format

### Single Deal Autopsy

```markdown
# Deal Autopsy: [Company Name]
**Outcome**: Lost / Won
**Date Closed**: [Date]
**Deal Size**: $[X]
**Primary Competitor**: [If lost]

---

## Root Cause (Primary)

**Category**: [Value Gap / Access Gap / Trust Gap / Price Gap / Timing Gap / Process Gap]
**Root Cause Statement**: [One crisp sentence. E.g. "We never reached the CFO, so the champion couldn't defend our price internally."]

## The 5 Whys

1. Why did we lose? → [Stated reason]
2. Why did [stated reason] matter? → [Layer deeper]
3. Why did [layer 2] happen? → ...
4. Why did [layer 3] happen? → ...
5. Root cause: [What we could have controlled]

---

## Last Recoverable Moment

**When**: [Stage / Date]
**What we should have done**: [Specific action]
**Signal we missed**: [The warning sign that was visible in hindsight]

---

## Competitive Intelligence

| Dimension | Us | [Competitor] | Assessment |
|-----------|-----|--------------|------------|
| [Feature/Capability] | [Ours] | [Theirs] | [Win/Loss/Tie] |

---

## Lessons (Save to Playbook)

1. [Lesson 1 — Actionable change to make on future deals]
2. [Lesson 2]
3. [Lesson 3]
```

---

## 📂 System Integration

- **Output**: Save autopsy to `data/4-Archives/win-loss/[Client]-[date].md`
- **Playbook**: Append lessons to `data/2-Domaines/win-loss-playbook.md`
- **ICP update**: Flag `icp-creator` if patterns suggest ICP drift
- **Voice DNA**: Load `voice-dna.json` for communication style in playbook

---

## 📚 References

- `references/root-cause-framework.md`: The 5 Whys + 6 loss categories in depth.
- `references/pattern-detection.md`: How to read signal from 5+ deals.
- `references/playbook-template.md`: The standard format for the Win-Loss Playbook.
