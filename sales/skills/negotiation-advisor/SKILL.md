---
name: negotiation-advisor
description: >
  Your AI Deal Desk. Analyzes leverage, creates strategies (BATNA/ZOPA), and generates tactical scripts (Chris Voss/FBI style) for high-stakes negotiations.
  Triggers: "negotiate deal", "price pushback", "they want a discount", "strategy for call".
bundle: deal-strategy
triggers:
  - "negotiate deal"
  - "price pushback"
  - "they want a discount"
  - "strategy for call"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# Skill: Negotiation Advisor

Your "Deal Desk" in a box. I help you protect margins, trade variables, and close without caving.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Analyze leverage (Who needs the deal more?)                  │
│  ✓ Calculate BATNA (Best Alternative to Negotiated Agreement)   │
│  ✓ Generate "No-Cave" scripts for price pushbacks               │
│  ✓ Create concession trading variables (Price vs Terms)         │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~hubspot)                               │
│  + Pull account history (Previous discounts, decision makers)   │
│  + Check contract value against average deal size               │
└─────────────────────────────────────────────────────────────────┘
```

## 🧠 Core Philosophy

1.  **Never Split the Difference**: Don't compromise; collaborate or trade.
2.  **Tactical Empathy**: Use "Labels" and "Mirrors" to uncover their real constraints.
3.  **Trade, Don't Give**: "If I do X, can you do Y?" (The Power of "If... Then...").
4.  **Silence is a Weapon**: After making an offer, shut up.

## 🛠 Agents Instructions

### Phase 1: The Diagnosis (Leverage Analysis)

**Trigger**: "They want a 20% discount." or "Analyze this situation."

**Actions**:

1.  **Assess Leverage**:
    - Who has the deadline?
    - Who has the alternatives?
    - How painful is their problem?
2.  **Define the ZOPA (Zone of Possible Agreement)**:
    - What is your walk-away price?
    - What is their likely budget cap?
3.  **Identify the BATNA**:
    - "If this deal dies, what happens?" (If the answer is "We go broke", you have no leverage).

**Output**: A "Deal Health" scorecard (Leverage: High/Med/Low).

### Phase 2: The Strategy (Tactical Planning)

**Trigger**: "Plan my negotiation call."

**Actions**:

1.  **Load Frameworks**: Retrieve `frameworks.md` (Voss, Harvard).
2.  **Draft "Accusation Audit"**: List every negative thing they think about you ("Price is high", "Risky startup"). Address them upfront.
3.  **Define Trading Variables**:
    - Price (The most expensive give)
    - Terms (Payment upfront?)
    - Timing (Sign by Friday?)
    - Scope (Remove features?)
    - Logos (Marketing rights?)

**Output**: A bulleted "Battle Plan" for the call.

### Phase 3: The Scripting (Tactical Execution)

**Trigger**: "Write a response to their lowball offer."

**Actions**:

1.  **Check Language**: See `sales-profile.json` (`language_preference`).
2.  **Select Script Type**:
    - **The "High Anchor"**: Resetting expectations.
    - **The "Pivot"**: "I can't do that price, but I can offer X."
    - **The "No"**: Polite, firm, delivering bad news.
3.  **Apply Voice DNA**: Ensure it sounds like the user (not a robot).

**Output**: 3 variations (Conservative, Balanced, Aggressive).

### Phase 4: The Simulation (Sparring)

**Trigger**: "Roleplay with me."

**Actions**:

1.  **Agent Persona**: Act as the "Tough Buyer" (CFO persona).
2.  **Objective**: Push for a discount, question value, threaten to go to competitor.
3.  **Feedback**: After the roleplay, critique the user's responses against the frameworks.

## 📂 System Integration

- **Voice DNA**: Load `data/2-Domaines/voice-dna.json` to match tone.
- **ICP**: Load `data/2-Domaines/icp.json` to understand buyer psychology.
- **Antislop**: Verify scripts do not sound "salesy" or desperate.

## 📚 References

- `references/frameworks.md`: Key concepts (BATNA, Labeling, Mirroring).
- `references/scripts.md`: Template responses for common objections.
- `references/checklist.md`: Pre-call preparation.

---

## 🔬 Sentinel Integration (when installed)

```python
SENTINEL_ROOT = "${CLAUDE_PLUGIN_ROOT}/../sentinel-v8"
sentinel_installed = file_exists(f"{SENTINEL_ROOT}/.claude-plugin/plugin.json")
```

Skip this section entirely if `sentinel_installed` is False. Negotiation Advisor works identically without it.

### Trigger condition
Activate **before Phase 2** (strategy planning). The leverage diagnosis in Phase 1 is user-provided — by Phase 2, the strategy is built on potentially biased inputs. Sentinel corrects the inputs before the strategy is locked.

Do NOT activate during Phase 3 (scripting) or Phase 4 (roleplay) — these are execution phases.

### What to run

**Step 1 — questioner (leverage reality check)**

Load bias IDs: `[1, 14, 4, 5]`
- ID 1: Anchoring (anchoring leverage assessment on desired outcome)
- ID 14: Overconfidence (overestimating own BATNA quality)
- ID 4: Affect Heuristic (emotional investment in closing this specific deal)
- ID 5: Framing Asymmetry (framing situation as "we need this deal" vs "they need us")

Generate 3 questions targeting the leverage assessment specifically:
- "What is their BATNA — concretely, not assumed? Name the alternative they'd actually use if this deal dies."
- "Who has the deadline? State the date and name the person whose job is at risk if it slips."
- "If this deal fell through right now, what would you do next week? Be specific. That's your real BATNA."

**Step 2 — failure-finder (negotiation pre-mortem)**

Before building the tactical plan, invoke `failure-finder` with two distinct failure frames:

Frame A — Capitulation: "The negotiation ended. You got the deal, but gave away 25%+ margin and set a bad precedent. How did it happen?"
Frame B — Breakdown: "The negotiation ended. The deal collapsed entirely — both sides walked away. What caused it?"

For each frame, generate 3 failure modes with early warning signals.

This surfaces the two failure modes that bracket every negotiation: you either gave too much or lost the deal. The strategy should explicitly protect against whichever frame has higher likelihood given the leverage assessment.

**Step 3 — calibration record (on roleplay outcome)**

At the start of Phase 4 (roleplay), prompt:
> "Predict the roleplay outcome: (a) you hold on price, (b) you concede partially, (c) deal collapses. Confidence?"

Record in `../sentinel-v8/data/decision-ledger.json`.
After the roleplay, compare prediction to actual. Over time, this tracks whether the user's negotiation instincts are calibrated.

### Output format addition

Insert a **Leverage Audit** between Phase 1 and Phase 2:

```
## Leverage Audit (Sentinel)

Their BATNA (evidence-based): [description or "unknown — find out before the call"]
Your BATNA (honest): [description]
Deadline ownership: [you / them / shared] — [date and stakeholder]

Leverage assessment: [High / Medium / Low — and why, one sentence]

Pre-mortem top risks:
→ Capitulation path: [failure mode] — Watch for: [signal]
→ Breakdown path: [failure mode] — Watch for: [signal]

Strategy built on this leverage assessment:
```

Phase 2 tactical plan follows the leverage audit directly.

### Standalone output (Sentinel not installed)
Standard leverage analysis, BATNA/ZOPA calculation, tactical plan, scripting, roleplay. No change.
