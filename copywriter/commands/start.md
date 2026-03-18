---
description: Initialize the Copywriter plugin (Voice, ICP, Business Profile).
argument-hint: "No arguments required"
allowed-tools: Read, Write
model: sonnet
---

# /copywriter:start

This command runs the **Onboarding Wizard**. It systematically builds the user's "Second Brain" for copywriting.

## Workflow

1.  **Welcome**: "Welcome to Copywriter Studio. Let's set up your DNA."
2.  **Voice DNA**: Triggers `voice-dna-creator`.
    - _Input_: User pastes 3 writing samples.
    - _Output_: `data/2-Domaines/voice-dna.json`.
3.  **ICP Definition**: Triggers `icp-creator`.
    - _Input_: User answers 5 questions about their audience.
    - _Output_: `data/2-Domaines/icp.json`.
4.  **Business Profile**: Triggers `business-profile-creator`.
    - _Input_: User defines offers and language preference (`fr`/`en`).
    - _Output_: `data/2-Domaines/business-profile.json`.
5.  **Completion**: "Setup complete. You can now use `/copywriter:write`."

## Usage

```bash
/copywriter:start
```
