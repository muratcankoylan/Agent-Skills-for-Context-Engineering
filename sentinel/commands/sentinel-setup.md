---
name: sentinel-setup
description: First-time walkthrough. Explains what Sentinel does and doesn't do.
allowed-tools: None
model: sonnet
---


<example>
user: "/sentinel-setup"
assistant: "[Explains the 3 core things Sentinel does, the limitation about LLM bias, and invites a first decision]"
</example>

# /sentinel-setup

## Say this (adapt to the user's language):

Sentinel forces you through a structured decision process. Three things it does:

1. **Breaks your decision into pieces** and scores each one independently,
   so one strong feeling doesn't contaminate everything else.
   (Kahneman's MAP protocol)

2. **Asks the questions you'd skip** - about sunk costs, hidden assumptions,
   and what happens if you're wrong.

3. **Imagines your plan has already failed** and works backward to find the
   risks you haven't considered. (Klein's pre-mortem - empirically shown to
   improve risk identification by 30%)

**What it doesn't do**: Sentinel uses a language model that has its own
biases. It's a structured thinking partner, not an infallible detector.
Your judgment remains essential.

**Try it**: describe a decision you're facing and I'll run the analysis.
Or use `/sentinel-diverge` if you're stuck and need to see more options.
