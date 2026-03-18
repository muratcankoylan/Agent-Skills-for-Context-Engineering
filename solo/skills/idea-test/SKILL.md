---
name: idea-test
description: >
  Helps solo builders decide whether to build an idea and pick the cheapest test to confirm it.
  Part 1: Go / No-Go / Pivot decision using a quick evidence checklist.
  Part 2: Cheapest test selector — smoke test, concierge, wizard of oz, fake door, or spike.
  Trigger with "should I build this", "test my idea", "validate this idea",
  "is this worth building", "what's the cheapest test", "proof of concept", or "run a quick test".
version: 1.0.0
bundle: research-validate
triggers:
  - "test my idea"
  - "should I build"
  - "validate idea"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Idea Test

Answers two questions in one session:

1. **Should I build this?** — Quick evidence check → Go / No-Go / Pivot
2. **If yes, how do I confirm it cheapest?** — Pick the right test for the riskiest assumption

No spreadsheets, no scoring matrices. Just the minimum signal needed to decide.

---

## Part 1: Should I Build This?

Work through this checklist before committing any build time. Each question is Yes / No / Don't Know.

### Evidence Checklist

| Question | What a "Yes" looks like |
|----------|------------------------|
| **Problem is real** | You've heard at least 3 people describe it unprompted |
| **Pain is acute** | They're already doing something painful to solve it (workaround exists) |
| **You can reach them** | You know where they hang out (community, job board, Twitter, etc.) |
| **They'd pay (or use it)** | They've expressed frustration about *not having* a solution |
| **You can build v1 alone** | Core functionality is achievable in 2-4 weeks |

### Decision

| Score | Verdict | Action |
|-------|---------|--------|
| 4–5 Yes | **GO** | Pick a test (Part 2), confirm the riskiest assumption |
| 2–3 Yes | **LEARN MORE** | Run Part 2 with a cheap test before committing |
| 0–1 Yes | **STOP** | The problem or reach is unclear — return to discovery |

If you hit "Don't Know" on problem or pain, that's your signal: run a test before anything else.

---

## Part 2: Pick the Cheapest Test

The rule: **use the cheapest test that tells the hardest truth.**

Don't build a prototype to validate what a landing page can answer. Don't write a landing page to validate what a Reddit post can answer.

### The 5 Tests

| Test | What it answers | Time | Cost | Best when |
|------|----------------|------|------|-----------|
| **Smoke Test / Fake Door** | "Will people click to sign up?" | 1–3 days | Free–€50 | You want demand signal before building anything |
| **Concierge MVP** | "Will people pay / use if I do it manually?" | 3–7 days | Time only | You can fake the product with manual work |
| **Wizard of Oz** | "Will they use the workflow?" | 3–7 days | Time only | The UX matters but code doesn't yet |
| **Narrative / Video** | "Does the story land?" | 1–2 days | Free | You need stakeholder or user buy-in on a concept |
| **Spike / Feasibility** | "Can I actually build this?" | 1–2 days | Dev time | Technical risk is the biggest unknown |

### How to Choose

**Answer these two questions:**

1. What's the riskiest assumption? (What has to be true for this to work?)
2. What's the cheapest way to test just that?

**If the risk is demand** ("do enough people want this?") → Smoke Test or Concierge
**If the risk is behavior** ("will they actually go through the flow?") → Wizard of Oz
**If the risk is comprehension** ("will they get what this does?") → Narrative / Video
**If the risk is technical** ("can this be built at all?") → Spike

---

## Running the Test

For each test, define three things before starting:

```
Test: [which method]
Hypothesis: [If I do X, then Y% of people will Z]
Pass criteria: [the number that means GO — e.g., 10 signups, 3 paying users]
Timeline: [by when]
```

Save to `data/1-Projets/[project]/validation-results.md`

### After the Test

| Result | Action |
|--------|--------|
| Pass criteria met | **GO** → move to `/solo:build design` |
| Partial signal | **ITERATE** → tweak the hypothesis, run again or try a different angle |
| No signal | **PIVOT** → return to `/solo:build discover` with the new insight |
| Adjacent opportunity spotted | **PIVOT** → the test revealed a better problem |

---

## Anti-Patterns

**Don't build a prototype to validate a demand hypothesis.** A landing page is 10× faster.

**Don't confuse "they liked it" with "they'd use it."** People are polite. A signup or a payment is signal. Positive feedback in a conversation is not.

**Don't test multiple hypotheses at once.** One test, one assumption. If three things must be true, test the one you're most uncertain about first.

**Don't skip the test because you're confident.** That's confirmation bias.

---

## References

- [Test Method Catalog](./references/tests.md) — Detailed setup steps and success criteria for each test type

---

## 🔬 Sentinel Integration (when installed)

```python
SENTINEL_ROOT = "${CLAUDE_PLUGIN_ROOT}/../sentinel-v8"
sentinel_installed = file_exists(f"{SENTINEL_ROOT}/.claude-plugin/plugin.json")
```

Skip this section entirely if `sentinel_installed` is False. Idea-test works identically without it.

### Trigger condition
Activate after the Part 1 checklist produces a **GO** or **LEARN MORE** verdict.
Do NOT activate on STOP verdicts — if the idea is dead, don't add analysis overhead.

### What to run

**Step 1 — failure-finder (pre-mortem)**

Invoke the `failure-finder` agent with this specific frame:

> "It's 12 months later. You built [idea]. Nobody is paying for it (or using it, if free).
> The product exists but has no traction. What happened?"

Generate 5 failure modes. Prioritize:
- Demand was assumed, not validated ("they said they wanted it" ≠ they paid)
- Build took 3x the estimate due to a dependency or scope creep
- Distribution was never figured out (product ready, nobody knew it existed)
- A competitor shipped the same thing during the build
- The user built for themselves, not for the ICP

**Step 2 — questioner (bias check)**

Load bias IDs: `[3, 7, 14, 22]` from `../sentinel-v8/skills/decision-hygiene/references/bias-catalog.yaml`
- ID 3: Representativeness ("I have this problem so others do too")
- ID 7: Sunk Cost ("I've been thinking about this for 3 months")
- ID 14: Overconfidence ("I know I can build this in 4 weeks")
- ID 22: Planning Fallacy (build time estimate)

Generate 3 questions max. If the checklist reasoning is sound, say so instead.

### Output format addition

Append to the standard GO/LEARN MORE verdict:

```
⚠️  Pre-mortem — before you start, stress-test these:

Failure mode 1 (HIGH): [what went wrong] → [early warning signal]
Failure mode 2 (MEDIUM): [what went wrong] → [early warning signal]

Answer these first:
Q1: [questioner question]
Q2: [questioner question]

If you can answer both honestly → proceed. If not → run the cheaper test first.
```

### Standalone output (Sentinel not installed)
Standard GO / LEARN MORE / STOP verdict with anti-patterns. No change.

