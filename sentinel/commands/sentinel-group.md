---
name: sentinel-group
description: >
  Collective decision protocol. Generates individualized pre-meeting scoring
  sheets, structures the meeting agenda by divergence, and facilitates
  group discussion to surface unique information and prevent groupthink.
  This is NOT /sentinel run by multiple people — it is a fundamentally
  different protocol that treats group dynamics as the primary risk variable.
allowed-tools: [Read, Write, Bash]
model: sonnet
---

<example>
user: "/sentinel-group 4 partners evaluating whether to open a Berlin office"
assistant: "[Runs triage for group context -> generates Phase 1 scoring sheets for 4 participants -> structures Phase 2 meeting agenda -> activates noise-calculator to brief on expected variance -> outputs complete facilitation protocol]"
</example>

# /sentinel-group — Collective Decision Protocol

## Core premise

Group decisions have a different failure mode than individual decisions.
The enemy is not individual bias — it is **process contamination**:
information that exists in the room but never surfaces, preferences that
exist but are suppressed, disagreements that exist but are smoothed over.

The protocol does not try to make individuals less biased.
It structures the process so that group dynamics produce signal rather than noise.

## Step 1 — Triage for group context

Run standard triage, then add group-specific parameters:

```bash
if [ -z "$CLAUDE_PLUGIN_ROOT" ]; then
  CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fi
timeout 10 python3 "$CLAUDE_PLUGIN_ROOT/skills/decision-hygiene/scripts/triage.py" \
  --stakes [stakes] --complexity [complexity] --time [time] \
  --expertise [expertise] --reversibility [reversibility]
```

Additional group parameters (assess from context):
- **n_participants**: Number of decision-makers (2-4: small / 5-8: medium / 9+: large)
- **seniority_spread**: Is there a clear hierarchy? (flat / mixed / steep)
- **prior_alignment**: Has anyone already expressed a position? (none / partial / majority aligned)

## Step 2 — Select MAP dimensions

Use structure-builder logic to identify 3-5 dimensions.
For group decisions, add a mandatory dimension: **"Process legitimacy"**
(will the people who didn't get their way accept the outcome as fair?)
This dimension is always relevant in group decisions and almost always omitted.

## Step 3 — Generate Phase 1 individual scoring sheets

Activate **group-facilitator** agent to generate individualized sheets.

Each sheet contains:
- The 3-5 MAP dimensions with scoring anchors
- A "unique information" field: "What do YOU know that others may not?"
- A "strongest objection" field: "What is your best argument AGAINST the leading option?"
- Individual prediction: "What do you think will actually happen, and with what confidence?"

**Format the sheets for distribution** — plain text, copy-paste ready.
Label them Sheet A, Sheet B, etc. (not by name, to reduce anchoring to person).

## Step 4 — Brief on noise expectations

Before the meeting, provide the facilitator with:
- Expected variance range for this type of decision
- The noise interpretation thresholds (from noise-calculator)
- The paradox: "If all scores are within 1 point — that's a warning, not a success"

## Step 5 — Generate meeting facilitation guide

Structure:
1. **Opening (10 min)**: Unique information round — each person shares what only they know. No evaluation yet.
2. **Score reveal**: Show all scores simultaneously on screen. Most senior person reacts last.
3. **Highest-variance dimension first**: Spend the most time where disagreement is largest.
4. **Counter-argument phase**: One designated person argues the opposing case formally.
5. **Consensus check**: Only after all dimensions discussed. Distinguish genuine consensus from courtesy consensus.

## Step 6 — Post-meeting prediction recording

After the meeting, record:
- The group decision
- Each individual's final position (may differ from group decision)
- Each person's confidence in the outcome
- The designated review date

```bash
# Record in ledger with group metadata
timeout 10 python3 "$CLAUDE_PLUGIN_ROOT/skills/decision-hygiene/scripts/calibration.py" \
  --ledger "$CLAUDE_PLUGIN_ROOT/data/decision-ledger.json"
```

## Output structure

```
/sentinel-group output:

📋 PHASE 1 — Individual Scoring Sheets (distribute before meeting)
[Sheet A — copy-paste ready]
[Sheet B — copy-paste ready]
[...]

📊 NOISE BRIEFING — What to expect from score variance
[threshold interpretation]

🗓️ PHASE 2 — Meeting Facilitation Guide
[step-by-step agenda]

⚠️ FACILITATION WARNINGS
[seniority spread risks]
[prior alignment risks]
[courtesy bias risks]
```

## Language
Always respond in the user's language.
