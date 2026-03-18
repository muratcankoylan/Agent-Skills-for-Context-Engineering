---
name: sentinel-post
description: >
  Post-decision hygiene. Called 3-6 months after a recorded decision to
  review outcomes while correcting for the biases that contaminate
  retrospective judgment: Hindsight Bias (92), Choice-Supportive Bias (91),
  Outcome Bias (14), Self-Serving Bias (28), and Rosy Retrospection (94).
  The protocol forces evaluation of decision QUALITY separately from
  outcome QUALITY — these are not the same thing, and conflating them
  degrades future judgment.
allowed-tools: [Read, Write, Bash]
model: sonnet
---

<example>
user: "/sentinel-post review the Berlin office decision from 6 months ago"
assistant: "[Reads ledger -> restores original predictions and reasoning -> asks outcome questions -> separates decision quality from outcome quality -> updates calibration score -> extracts transferable learning]"
</example>

# /sentinel-post — Post-Decision Review Protocol

## Why retrospective bias is as dangerous as prospective bias

Four biases contaminate almost every post-decision review:

**Hindsight Bias (ID 92)**: "I knew it would go this way." People systematically
overestimate how predictable an outcome was before it occurred. This produces
false learning — you attribute predictability to a signal that was noise.

**Choice-Supportive Bias (ID 91)**: You remember your choice as better than it was.
The reasons you can recall for the decision are weighted toward the ones that
look good now. The doubts you had are forgotten.

**Outcome Bias (ID 14)**: You judge the decision by its outcome rather than by
whether it was the right decision given the information available at the time.
A good decision with a bad outcome is evaluated as a bad decision.
This is one of the most costly learning errors in organizations.

**Self-Serving Bias (ID 28)**: Successes are attributed to skill. Failures are
attributed to external factors. Neither produces accurate learning.

The /sentinel-post protocol is the structural antidote: it forces you to evaluate
the decision *as it was made*, not as it looks now.

## Language
Respond in the user's language.

## Step 1 — Retrieve original decision record

Read `$CLAUDE_PLUGIN_ROOT/data/decision-ledger.json`

Find the relevant decision by date, description, or ID.

Extract and DISPLAY to the user (before asking any questions):
- The original decision description
- The original reasoning (if recorded)
- The original prediction and confidence level
- The original MAP scores (if available)
- The review date that was set

**Critical protocol**: The user MUST see their original predictions before
they are asked to evaluate outcomes. This is not optional.
Seeing the original record counters Choice-Supportive Bias and Hindsight Bias.

If no record exists: inform the user, offer to record this decision now for
future review, and proceed with a qualitative post-mortem only.

## Step 2 — Outcome elicitation (before any evaluation)

Ask in sequence:
1. "What actually happened?" (factual, no evaluation yet)
2. "On a scale of 1-10, how would you rate the outcome?"
3. "What were the main factors that drove the outcome?"

Do NOT ask "was it a good decision?" yet. Sequence matters.
Factual outcome → rating → attribution → only then, decision quality.

## Step 3 — Separate decision quality from outcome quality

This is the core of the protocol.

Present the 2x2 framework explicitly:

```
                    GOOD OUTCOME    BAD OUTCOME
GOOD DECISION   →   Deserved win    Bad luck
BAD DECISION    →   Dumb luck       Deserved loss
```

Ask: "Given the information available at the time you made this decision
— not what you know now — was the decision process sound?"

Probe with:
- "Were the MAP dimensions the right ones?"
- "Was the pre-mortem accurate in what it identified as risks?"
- "What information, that was available at the time, was ignored or underweighted?"

The distinction matters because:
- Good decision + bad outcome → extract what went wrong externally, do NOT change the process
- Bad decision + good outcome → identify the flaw, do NOT credit luck to skill

## Step 4 — Bias audit on the retrospective itself

Before recording any learning, flag the active retrospective biases:

**Hindsight audit**: "Could you actually have predicted this outcome before it happened? What was the signal-to-noise ratio at decision time?"

**Self-serving audit**: "Are you attributing the outcome primarily to your decisions or to external factors? Apply both directions."

**Outcome bias audit**: "If the outcome had been different but you had made the same decision with the same process, how would you evaluate the decision quality?"

## Step 5 — Calibration update

```bash
if [ -z "$CLAUDE_PLUGIN_ROOT" ]; then
  CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fi
timeout 15 python3 "$CLAUDE_PLUGIN_ROOT/skills/decision-hygiene/scripts/calibration.py" \
  --ledger "$CLAUDE_PLUGIN_ROOT/data/decision-ledger.json"
```

Mark the decision as resolved in the ledger with:
- Actual outcome (success/failure/partial)
- Decision quality rating (1-5, separate from outcome)
- Key learning (one transferable insight, specific)
- Bias pattern note (which bias most distorted the original decision, in retrospect)

## Step 6 — Transferable learning extraction

The goal is not to evaluate this decision — it is to improve the next one.

Generate one specific, transferable learning statement:
- NOT: "We should have been more careful"
- YES: "Our Planning Fallacy on timeline was 2.5x off. On similar projects, add 2.5x buffer to initial estimates."

The learning must:
- Reference a specific bias or failure pattern
- Be actionable in the next decision of the same type
- Be falsifiable (testable in the future)

## Output format
```
📋 ORIGINAL RECORD (retrieved)
[original prediction, confidence, MAP scores]

📊 OUTCOME
[what happened, user's rating, attribution]

⚖️ DECISION vs OUTCOME QUALITY
[the 2x2 assessment]

🔍 RETROSPECTIVE BIAS AUDIT
[hindsight, self-serving, outcome bias flags]

📈 CALIBRATION UPDATE
[Brier score update, running pattern]

💡 TRANSFERABLE LEARNING
[one specific, actionable insight]
```
