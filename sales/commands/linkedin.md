---
description: "Launch the LinkedIn Orchestrator - Manage your daily sales routine"
argument-hint: "[autonomous | plan | resume | status]"
allowed-tools: Read, Write, Glob
model: sonnet
---

# /sales:linkedin

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

The **LinkedIn Orchestrator** is your daily sales manager. It organizes your day into high-impact time blocks (Warming, Content, Outreach, Admin) based on the **360Brew Strategy**.

It adapts to your **Sales Profile** (Bilingual/English/French) and manages your **Daily Limits** (Safe Mode) to protect your account.

---

## Usage

```
/sales:linkedin              # Interactive mode (Plan -> Execute)
/sales:linkedin autonomous   # Auto-run based on time of day
/sales:linkedin resume       # Resume today's plan
/sales:linkedin status       # Check limits and progress
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                    LINKEDIN ORCHESTRATOR                          │
├──────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                        │
│  ✓ Time Blocking: 360Brew routine (Warming, Content, Outreach)   │
│  ✓ Safe Mode: Daily limit tracking to avoid restrictions         │
│  ✓ Content Drafting: AI-generated comments and posts             │
│  ✓ Bilingual Schedule: Auto-switch EN/FR based on day            │
├──────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                       │
│  + ~~browser: Automate reading and posting (via Chrome)          │
│  + ~~CRM: Log all activities and new connections                 │
│  + ~~calendar: Schedule time blocks in your outlook/gcal         │
└──────────────────────────────────────────────────────────────────┘
```

---

## /sales:linkedin autonomous

**The "One-Click" Mode.**

When you run this at 09:00 AM, the Orchestrator works through the **Morning Block**:

1.  **Reads** `sales-profile.json` (Language: English today).
2.  **Checks** `activity_log.md` (Comments sent: 0).
3.  **Identifies** 3 Peers, 3 Prospects, 3 Thought Leaders to engage with.
4.  **Executes** `linkedin-engager` for each.
5.  **Logs** results.

### Output Example

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LINKEDIN ORCHESTRATOR — Morning Block (English Day)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GOAL: 9 Comments (Warming) | 0/30 Daily Limit Used

1. [x] Engage Peer: @AlexHormozi (Strategy: Contrarian)
       -> Analyzed post: "Volume negates luck"
       -> Drafted comment: "Volume is the floor, but feedback loops..."
       -> Status: POSTED (via Claude for Chrome)

2. [ ] Engage Prospect: @SarahChen (Touch 2/3)
       -> Found recent post about "Hiring engineers"
       -> Strategy: Value-Add (Share resource)
       -> Action: Drafting...

3. [ ] Engage Thought Leader: @JustinWelsh
       ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Paused at Step 2. Waiting for browser confirmation...
```

---

## /sales:linkedin status

Check your daily "Safe Mode" limits and progress.

### Output Example

```markdown
DAILY STATS (Feb 13, 2026)

| Metric      | Count | Limit | Status |
| :---------- | :---- | :---- | :----- |
| Comments    | 12    | 30    | OK     |
| Connections | 5     | 20    | OK     |
| Posts       | 1     | 1     | MAX    |
| DMs         | 3     | 25    | OK     |

WARMING PIPELINE

- 2 Prospects moved to "Warm" (2 touches)
- 1 Prospect moved to "Hot" (3 touches - Ready to Connect)
```

---

## Agent Instructions

### Execution Steps

```python
# 1. Load Context
profile = read_json("data/2-Domaines/sales-profile.json")
activity_log = read_file("data/2-Domaines/LinkedIn/activity_log.md")
current_hour = get_current_time().hour

# 2. Determine Time Block
if current_hour < 10:
    block = "MORNING"
    skill_focus = "linkedin-engager"
elif 10 <= current_hour < 12:
    block = "CONTENT"
    skill_focus = "linkedin-creator"
elif 12 <= current_hour < 15:
    block = "MIDDAY"
    skill_focus = "linkedin-engager"
elif 15 <= current_hour < 18:
    block = "AFTERNOON"
    skill_focus = "linkedin-prospector"
else:
    block = "EVENING"
    skill_focus = "hubspot-sync"

# 3. Safe Mode Check
daily_comments = count_today_comments(activity_log)
if daily_comments >= 30:
    print("Daily Comment Limit Reached. Switching to Passive Mode.")
    skill_focus = "learning"

# 4. Bilingual Logic
day_of_week = get_day_of_week()
if profile.language == "Bilingual":
    target_lang = "French" if day_of_week in ["Wednesday", "Friday"] else "English"
    print(f"Today is a {target_lang} Content Day.")

# 5. Execute Block
print(f"Starting {block} Block...")
invoke_skill(skill_focus, language=target_lang)
```

---

## Integration Tips

1.  **Always keep prospects.md updated**: The Orchestrator relies on this file to know who to warm up next.
2.  **Respect the limits**: If the Orchestrator says "Stop", STOP.
3.  **Use "Resume"**: If you get interrupted, `/sales:linkedin resume` picks up exactly where you left off.

---

## Skills Used

- `linkedin-orchestrator` — The master logic.
- `linkedin-engager` — Commenting & Warming.
- `linkedin-creator` — Posting.
- `linkedin-prospector` — Finding leads.
- `hubspot-sync` — CRM data entry.
