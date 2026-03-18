---
name: retrospective-hygiene
description: >
  Decision hygiene for post-mortem analysis and retrospective reviews.
  Addresses the biases that contaminate learning from past decisions:
  Hindsight Bias (92), Choice-Supportive Bias (91), Outcome Bias (14),
  Self-Serving Bias (28), and Rosy Retrospection (94). Adds domain-specific
  protocols for failure post-mortems (don't blame luck), success post-mortems
  (don't credit all skill), and ongoing project reviews (Plan Continuation
  Bias). Auto-loads when context involves: post-mortem, retrospective,
  review, what went wrong, lessons learned, debrief, after-action.

bundle: domain-hygiene
triggers:
  - "post-mortem"
  - "postmortem"
  - "retrospective"
  - "retro"
  - "what went wrong"
  - "lessons learned"
  - "debrief"
  - "after-action"
  - "review what happened"
  - "why did it fail"
  - "why did it succeed"
tools:
  standalone: [filesystem]
  supercharged: []
---

# Retrospective Decision Hygiene

## Why retrospectives are a distinct bias environment

Post-decision analysis is NOT the same as pre-decision analysis.
The biases are different, they operate in different directions,
and they require different structural interventions.

**The core asymmetry:**
- Pre-decision biases push toward bad decisions (overconfidence, anchoring)
- Post-decision biases corrupt the learning that would prevent the next bad decision

An organization that makes good retrospective analyses is more resilient than
one that makes perfect pre-decision analyses — because learning compounds.

## The four failure modes of retrospectives

### 1. Outcome contamination (Outcome Bias ID 14 + Hindsight Bias ID 92)
"The project failed → it was a bad decision."
"The project succeeded → it was a good decision."

Both inferences are logically invalid. Good decisions produce bad outcomes
(bad luck is real). Bad decisions produce good outcomes (dumb luck is real).
Conflating decision quality with outcome quality produces the wrong learning:
teams abandon good processes because of bad luck, and repeat bad processes
because of good luck.

**Structural fix**: The 2x2 framework is mandatory in all retrospectives.
Decision quality and outcome quality must be evaluated on separate axes.

### 2. Attribution reversal (Self-Serving Bias ID 28)
Successes: "We made great decisions. The team executed brilliantly."
Failures: "Market conditions were unfavorable. We couldn't have known."

Both retrospectives are written by the same people. The attribution pattern
is not based on the evidence — it is based on self-protection.

**Structural fix**: Apply the attribution audit in both directions.
For successes: "What external factors contributed that had nothing to do with us?"
For failures: "What internal decisions, made at the time, contributed to this?"

### 3. Memory reconstruction (Choice-Supportive Bias ID 91 + Rosy Retrospection ID 94)
"We always believed in this approach."
"The concern I had was minor — I didn't really worry about it."

Memory is not a recording. It is reconstructed to be consistent with
present beliefs and outcomes. Without written records from decision time,
retrospective analysis is partially fiction.

**Structural fix**: Original decision records must be read BEFORE retrospective
questions are asked. If no records exist, acknowledge this limitation explicitly
and discount retrospective conclusions accordingly.

### 4. Hindsight inevitability (Hindsight Bias ID 92)
"It was obvious this would fail."
"Anyone could have seen that the market wasn't ready."

Hindsight bias inflates the perceived predictability of past events.
The signal-to-noise ratio at decision time was much lower than it appears now.
Learning "be better at spotting the obvious" from a hindsight-contaminated
retrospective is learning nothing — because the signal wasn't obvious.

**Structural fix**: Reconstruct the information environment at decision time.
"Given only the information available on [date], what probability would you
have assigned to this outcome?" This breaks the inevitability illusion.

## Domain-specific protocols

### Failure post-mortem
Primary bias risks: Self-Serving Bias, Hindsight Bias, scapegoating
Key questions to add:
- "What was the best decision made during this project, and why didn't it save it?"
- "If the same decisions had been made with different external conditions, would it have succeeded?"
- "Which early warning signals were present but ambiguous at the time — not clear in hindsight?"
- "What structural change to the decision process would prevent this class of failure?"

**Do NOT ask**: "Who made the wrong call?" (produces scapegoating, not learning)
**DO ask**: "What information, process, or structure was missing that would have changed the decision?"

### Success post-mortem
Primary bias risks: Self-Serving Bias, Choice-Supportive Bias, attribution to skill
Key questions to add:
- "What would have had to go wrong for this to fail, and how likely was that?"
- "What decisions made during this project were actually suboptimal, even though the outcome was good?"
- "How much of the success was dependent on external conditions that may not repeat?"
- "What would a competitor need to replicate to reproduce this success?"

**Do NOT conclude**: "We have a repeatable playbook." (unless you can specify what's in it)
**DO conclude**: "The process was sound [or wasn't]. The external conditions were [favorable/unfavorable]."

### Plan continuation review (ongoing project)
Primary bias risks: Plan Continuation Bias (ID 67), Escalation of Commitment (ID 63), Sunk Cost (ID 7)
Key questions to add:
- "If we were starting this project today with no prior commitment, would we start it?"
- "What has changed since the original decision that we have not incorporated into the plan?"
- "Is momentum carrying us forward, or is genuine assessment?"
- "What is the pre-committed kill criterion, and has it been reached?"

## Default evaluation dimensions for retrospectives

When running MAP protocol on a past decision for retrospective review:

1. **Decision quality** (was the process sound given information at the time?)
2. **Outcome quality** (how did it actually turn out?)
3. **Prediction accuracy** (how well did we forecast what would happen?)
4. **Learning extracted** (have we identified the specific, transferable lesson?)
5. **Attribution accuracy** (have we correctly attributed causes to decisions vs. external factors?)

These are evaluated INDEPENDENTLY — especially 1 and 2.

## Mandatory output: The transferable learning statement

Every retrospective must end with a learning statement that meets these criteria:
- **Specific** (not "be more careful" — what specifically)
- **Transferable** (applicable to the next similar decision)
- **Falsifiable** (testable: "we will know this learning worked when...")
- **Mechanistic** (names the cognitive failure, not just the outcome failure)

Bad: "We should have done more due diligence."
Good: "Our Reality Checker relied on survivorship-biased benchmarks for SaaS growth rates.
       Next time, explicitly ask: 'What types of companies are absent from this benchmark?' before using it."

## Templates

- Post-mortem scorecard: `${SKILL_DIR}/templates/postmortem-scorecard.md`
- Attribution audit guide: `${SKILL_DIR}/templates/attribution-audit.md`
- Plan continuation review: `${SKILL_DIR}/templates/plan-continuation-review.md`
