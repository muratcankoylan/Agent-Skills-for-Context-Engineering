---
name: sentinel-reframe
description: >
  Challenge the question itself before answering it. Sometimes the problem
  isn't the answer - it's the question. Uses 6 reframing techniques to
  escape framing bias.
allowed-tools: None
model: sonnet
---


<example>
user: "/sentinel-reframe How do I convince the board to approve my budget?"
assistant: |
  reframes:
    - "What if you don't need board approval? Is there a smaller version you can fund yourself?"
    - "What if the budget is right but the pitch is wrong? What does the board actually care about?"
    - "What if the board already wants to approve it but needs political cover? What would give them that?"
</example>

# /sentinel-reframe - Challenge the Question

## 6 techniques
1. **Loss  Gain**: Flip the frame (losing X vs gaining Y)
2. **Action  Inaction**: What's the cost of NOT deciding?
3. **Narrow  Broad**: Zoom in (this specific case) or out (what pattern is this?)
4. **Short  Long**: What would you decide if the timeline was 10x longer?
5. **Abstraction ladder**: Go up (why?) or down (how specifically?)
6. **Assumption inversion**: What if the opposite of your key assumption is true?

## Method
1. Identify the frame in the user's question
2. Apply 3-4 techniques that produce genuinely different questions
3. Present the reframed questions
4. Ask which one resonates - that's probably closer to the real problem

## Language
Respond in the user's language.
