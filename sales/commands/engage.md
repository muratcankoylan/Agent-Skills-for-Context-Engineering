---
description: "Engage & Warm Up Prospects"
argument-hint: "[url | topic | warm-up]"
allowed-tools: Read, Write, Glob
model: sonnet
---

# /sales:engage

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

The **Engager** is your relationship builder. It generates authentic comments to "warm up" prospects before you pitch.

It follows the **360Brew Warming Strategy**:

1.  **Touch 1 (Comment)**: Value-add or question.
2.  **Touch 2 (Reply)**: Continuing the conversation.
3.  **Touch 3 (Connect)**: Personalized request referencing the chat.

---

## Usage

```
/sales:engage url [POST_URL]    # Generate comment for specific post
/sales:engage topic "AI Sales"  # Find relevant posts to comment on
/sales:engage warm-up           # Check prospects.md for warming tasks
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                    LINKEDIN ENGAGER (WARMER)                      │
├──────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                        │
│  ✓ Comment Generation: Context-aware, value-add drafts           │
│  ✓ Strategy Selection: Insight, Debate, or Story frameworks      │
│  ✓ Anti-Slop: Automatic quality control (no "Great post!")       │
│  ✓ Warming Logic: Track touches (Comment -> Reply -> Connect)    │
├──────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                       │
│  + ~~browser: Post comments directly to LinkedIn                 │
│  + ~~CRM: Log engagement history to prospect records             │
│  + ~~feed: Auto-monitor VIP prospects for new posts              │
└──────────────────────────────────────────────────────────────────┘
```

---

## /sales:engage url [URL]

**Single Post Mode.**
Analyzes the post author, tone, and content to draft a high-quality comment.

### Output Example

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENGAGEMENT DRAFT — Strategy: "The Insight"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

POST CONTEXT
Author is complaining about long sales cycles in Enterprise.

DRAFT COMMENT
"The 'hidden' stakeholder is usually the culprit. We started mapping out the legal team's org chart during discovery, and it cut our close time by 20%. Painful upfront, but saves months on the back end."

WHY THIS WORKS

- Validates their pain (Enterprise is slow).
- Adds specific value (Mapping legal).
- No fluff ("Great post").

[Post Now via Claude] | [Regenerate with 'Question' Strategy]
```

---

## /sales:engage warm-up

**Warming Mode.**
Reads your `prospects.md` and identifies who needs attention.

### Output Example

```markdown
WARMING TASKS (Feb 13, 2026)

| Prospect   | Status | Touches | Action Needed                    |
| :--------- | :----- | :------ | :------------------------------- |
| Sarah Chen | Lead   | 1       | Comment on latest post (Touch 2) |
| Mike Ross  | Lead   | 2       | Reply to his comment (Touch 3)   |
| Acme Corp  | Cold   | 0       | Find Decision Maker              |

Executing Task 1: Sarah Chen...
-> Found post: "Our Series A funding..."
-> Drafting congratulatory (but specific) comment...
```

---

## Agent Instructions

### Comment Generation Logic

```python
def generate_comment(post_text, author_voice):
    # 1. Anti-Slop Check
    if "delve" in comment or "underscore" in comment:
        rewrite(comment, tone="Casual", strict=True)

    # 2. Strategy Selection
    if post_type == "News":
        strategy = "Insight"
    elif post_type == "Opinion":
        strategy = "Debate/Nuance"
    elif post_type == "Personal":
        strategy = "Supportive/Story"

    # 3. Voice Matching
    # Match the length and complexity of the author's post.
    # If they write short, we write short.
```

### CRM Sync

After every comment:

1.  **Log** to `data/2-Domaines/LinkedIn/activity_log.md`.
2.  **Update** `data/2-Domaines/LinkedIn/prospects.md` (Increment `touches`).

---

## Tips

1.  **Don't Pitch**: Never pitch in a comment. The goal is _visibility_, not conversion.
2.  **Read the comments**: If everyone is saying "Congrats", say something about _what_ they achieved. Stand out.
3.  **The "Golden Hour"**: Engaging within 60 mins of them posting increases visibility by 10x.

---

## Skills Used

- `linkedin-engager` — Comment generation.
- `antislop-expert` — Quality control.
- `voice-dna-creator` — Tone matching.
