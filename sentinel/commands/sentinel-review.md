---
name: sentinel-review
description: >
  Review past predictions and measure calibration. Calculates Brier scores,
  identifies patterns, suggests improvements.
allowed-tools: [Read, Bash]
model: sonnet
---


<example>
user: "/sentinel-review"
assistant: "[Reads ledger -> calculates stats -> shows calibration patterns -> suggests one specific improvement]"
</example>

# /sentinel-review - Learn From Your Predictions

## Method
1. Read `$CLAUDE_PLUGIN_ROOT/data/decision-ledger.json`
2. Run calibration.py for Brier scores:
```bash
if [ -z "$CLAUDE_PLUGIN_ROOT" ]; then
  CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fi
timeout 15 python3 "$CLAUDE_PLUGIN_ROOT/skills/decision-hygiene/scripts/calibration.py" \
  --ledger "$CLAUDE_PLUGIN_ROOT/data/decision-ledger.json"
```
3. Identify patterns:
   - Overconfidence in which domains?
   - Timeline accuracy
   - People-dependent vs system-dependent predictions
4. One actionable recommendation

## If no predictions yet
"No predictions recorded yet. After your next /sentinel analysis,
I'll record a prediction. Come back in [timeframe] to see how it went."

## Language
Respond in the user's language.
