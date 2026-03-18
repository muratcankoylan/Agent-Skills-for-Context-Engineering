---
name: objection-library
description: >
  Comprehensive, methodology-driven objection handling system. Covers the 20 most common B2B sales objections
  with multi-framework responses (Voss, SPIN, Challenger). Generates context-specific scripts in your Voice DNA.
  Triggers: "how do I handle [objection]", "they said [objection phrase]", "I'm getting pushback on price / timing / competition".
bundle: deal-strategy
triggers:
  - "how do I handle [objection]"
  - "they said [objection]"
  - "pushback on price"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# Skill: Objection Library

The difference between a rep who caves and a rep who closes is a prepared response to the 20 objections that appear in 90% of deals.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ 20 objections mapped with multi-framework responses          │
│  ✓ Response generated in your Voice DNA                         │
│  ✓ Context adaptation: stage-aware (early vs. late deal)        │
│  ✓ EN/FR bilingual responses                                    │
│  ✓ Role-specific variant: talking to CFO vs. VP vs. Evaluator  │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~CRM)                                   │
│  + Pull account history to personalize response                 │
│  + Log objection patterns across pipeline for coaching          │
└─────────────────────────────────────────────────────────────────┘
```

## 🧠 Core Philosophy

1. **Objections are signals, not rejections**: Most objections are requests for more information or confidence.
2. **Acknowledge before you answer**: If you jump to the counter before acknowledging the concern, you're arguing, not selling.
3. **Diagnose before you prescribe**: Ask one clarifying question to understand the real objection behind the stated one.
4. **Never apologize for your price**: Discounting without resistance signals that your price was wrong to begin with.

---

## 🛠 Agent Instructions

### Phase 1: Identify and Clarify

**Trigger**: "They said [objection]. How do I respond?"

1. **Load context**:
   - What stage is the deal? (Early discovery vs. late negotiation changes the response)
   - Who raised the objection? (Champion, Economic Buyer, Technical Evaluator)
   - Load `voice-dna.json` for tone and phrase preferences

2. **Classify the objection** using the categories in `references/objection-categories-en.md` (or `fr`)

3. **Check for the "Real Objection"**: Stated objections are often proxies.
   - "Too expensive" often means "I don't believe the ROI"
   - "Not the right time" often means "This isn't a priority for leadership"
   - "We need to evaluate alternatives" often means "We're not convinced yet"

4. **Generate response** using the 3-step structure below.

---

### Phase 2: The 3-Step Response Framework (ACA)

Apply to every objection:

**A — Acknowledge**: Validate the concern. Do not dismiss or immediately counter.
> *"That's a fair concern."* / *"I hear that."* / *"That makes sense given where you are."*

**C — Clarify**: Ask one question to understand the root objection before answering.
> *"When you say it's too expensive, is the concern the total cost or the cash flow timing?"*
> *"When you say the timing isn't right, is that because of budget cycles or because there's a competing priority?"*

**A — Answer**: Now respond to the *actual* objection, not the stated one. Use the appropriate framework from `references/objection-categories-en.md`.

---

### Phase 3: Situational Variants

For each objection, generate 3 variants:

| Variant | Context | Tone |
|---------|---------|------|
| **Early Stage** | Objection during discovery/qualification | Curious, exploratory — preserve rapport |
| **Late Stage** | Objection at proposal/negotiation | Confident, specific — focus on closing |
| **Post-Loss Recovery** | They chose a competitor; door still open | Respectful, gracious, plant a seed |

---

## The 20 Core Objections (Summary Index)

See `references/objection-categories-en.md` for full response scripts.

### Price Objections
1. "It's too expensive."
2. "We don't have budget for this right now."
3. "Your competitor is cheaper."
4. "We need a discount to move forward."
5. "The ROI isn't clear enough to justify the cost."

### Timing Objections
6. "Now isn't the right time."
7. "We're in a freeze / budget is locked until next year."
8. "We want to wait and see how things develop."
9. "We have too many other priorities right now."

### Trust / Risk Objections
10. "We've never heard of you — we prefer a known vendor."
11. "We tried something like this before and it didn't work."
12. "We need to see more references / proof."
13. "We're worried about security / compliance."

### Process / Control Objections
14. "We need to evaluate other options."
15. "I need to run this by [person not in the room]."
16. "We're going to build this internally."
17. "This needs to go through procurement."

### Value / Fit Objections
18. "We're not sure we really need this."
19. "This seems complex — we don't have the resources to implement it."
20. "Our situation is different — this wasn't built for companies like us."

---

## Output Format

```markdown
## Objection: "[Exact wording they used]"

**Classification**: [Price / Timing / Trust / Process / Value]
**Likely Real Objection**: [What's behind the stated concern]

---

### Response (ACA Framework)

**Acknowledge**:
"[Empathy statement in Voice DNA tone]"

**Clarify**:
"[One question to surface the real concern]"

**Answer**:
"[Direct, confident response using relevant framework]"

---

### Variants

**If early stage**: "[Shorter, rapport-preserving version]"
**If late stage**: "[Closing-oriented version]"
**If talking to CFO**: "[Business/ROI language version]"

---

### What to Avoid
- [Specific mistake to not make with this objection]
```

---

## 📂 System Integration

- **Voice DNA**: All responses generated in user's voice — not a generic sales script
- **Negotiation Advisor**: For price objections at negotiation stage, hand off to `negotiation-advisor`
- **Roleplay Dojo**: Practice any objection response live against the `roleplay-dojo-agent`

## 📚 References

- `references/objection-categories-en.md`: All 20 objections with full scripts in English.
- `references/objection-categories-fr.md`: All 20 objections in French with cultural adaptation notes.
