---
description: "Negotiation Advisor - The Closer"
argument-hint: "[scenario | counter | roleplay]"
allowed-tools: Read, Write, Glob
model: sonnet
---

# /sales:negotiate

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

The **Negotiation Advisor** is your real-time deal closer. It helps you navigate high-stakes conversations, handle pricing pressure, and "teaching" customers to buy.

It integrates **Tactical Empathy** (Never Split the Difference) with **Commercial Teaching** (The Challenger Sale).

---

## Usage

```
/sales:negotiate "Price is too high"     # Objection Handling
/sales:negotiate script "Procurement"    # Script Generation
/sales:negotiate roleplay "CFO Battle"   # Simulation Mode
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                    NEGOTIATION ADVISOR                            │
├──────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                        │
│  ✓ Script Generation: Exact words for "Price too high" etc.      │
│  ✓ Roleplay Dojo: AI simulates the tough buyer (CFO persona)     │
│  ✓ Trade-off Engine: "If I give X, I get Y" logic                │
│  ✓ Tactical Empathy: Labeling and Mirroring guide                │
├──────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                       │
│  + ~~CRM: Pull history to customize negotiation leverage         │
│  + ~~email: Draft counter-offers directly in your draft folder   │
└──────────────────────────────────────────────────────────────────┘
```

---

## /sales:negotiate "Price is too high"

**Objection Handling.**
Generates 3 graded responses based on the deal stage and relationship.

### Output Example

```markdown
NEGOTIATION PLAYBOOK — Handling: "Price Pushback"

DIAGNOSIS
They are likely testing your confidence.
Remember: Price objections are usually "Value Objections" in disguise.

LEVEL 1: THE SOFT TOUCH (Discovery Stage)
Goal: Uncover the real blocker.

> "It sounds like you're under a lot of pressure to keep the budget down. What happens if this problem doesn't get solved this quarter?"
> (Labeling the emotion + Negative consequence question)

LEVEL 2: THE TRADE (Negotiation Stage)
Goal: Defend value.

> "We can definitely get to that number. However, we'd need to remove the [Premium Support] and the [Unlimited Users]. Is that a trade-off you're comfortable making?"
> (Forces them to choose features over price)

LEVEL 3: THE CHALLENGE (Closing Stage)
Goal: Reframe the ROI.

> "I understand. But let's look at the cost of doing nothing. You mentioned [Problem X] is costing you $10k/month. Our solution is $2k/month. Is saving $500 really worth delaying the solution?"

Select Level 1, 2, or 3 to generate the full email draft.
```

---

## /sales:negotiate roleplay "Specific Scenario"

**Simulation Mode.**
The AI acts as the toughest buyer you'll face.

### Agent Instructions (Roleplay)

```python
def start_roleplay(scenario):
    # 1. Set Persona
    print("ENTERING DOJO MODE. I am the CFO of Acme Corp.")
    print("My Personality: Skeptical, numbers-driven, hates 'fluff'.")
    print("Your Goal: Get me to agree to a follow-up meeting.")

    # 2. First Challenge
    response = ask("So, I looked at your proposal. It's 3x what we budgeted. Why should I keep reading?")

    # 3. Evaluate User Reply
    while conversation_active:
        user_reply = input()
        score = evaluate_reply(user_reply, criteria=["Empathy", "Firmness", "Clarity"])

        if score < 5:
            print(f"WEAK. You sounded defensive. Try asking: '{Voss_Question}'")
        else:
            print("GOOD. I feel heard. Proceeding...")
            react_as_cfo(user_reply)
```

---

## Tactics Library

### 1. The "Accusation Audit" (Start of Call)

Anticipate their negatives.

> "You're probably going to think this is expensive. You're going to think I'm just another salesperson trying to hit quota." -> _Disarms them instantly._

### 2. The "No-Oriented Question"

People feel safe saying "No".

> Bad: "Is this a good time to talk?" (Triggers "Yes" commitment anxiety)
> Good: "Is now a bad time to talk?" (Easy "No" -> Conversation starts)

### 3. The "Calibrated Question" (How/What)

Force them to solve your problem.

> "How am I supposed to do that?" (When they ask for a crazy discount)

---

## Agent Instructions (General)

### Deal Context Loading

```python
# Always check deal value before advising
deal_info = lookup_deal(profile.current_deal)

if deal_info.value > 100000:
    mode = "High_Stakes"
    advice = "Slow down. Build consensus. Do not rush."
else:
    mode = "Transactional"
    advice = "Create urgency. Close today."
```

### Antislop Check

- **Banned Phrases**: "Touching base", "Checking in", "Thoughts?", "Win-win".
- **Replace with**: "Any updates on X?", "Is this project still a priority?", "Does this align?"

---

## Tips

1.  **Don't Split the Difference**: Meeting in the middle is lazy and leaves money on the table. Trade value, not dollars.
2.  **Anchor High**: If you have to name a price first, anchor high (extreme anchor) to make your real price look reasonable.
3.  **Silence**: Use it. After you state your price, stop talking.

---

## Skills Used

- `negotiation-advisor` — The core tactics database.
- `roleplay-dojo` — The simulation engine.
- `financial-health` — ROI calculator for "Cost of Inaction".
