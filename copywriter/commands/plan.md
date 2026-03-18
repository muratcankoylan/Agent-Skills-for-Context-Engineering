---
description: "Generate a strategic Content Calendar for the month/week."
argument-hint: "[month] [focus topic]"
allowed-tools: Read
model: sonnet
---

# /copywriter:plan

Stop posting randomly. Build a cohesive narrative strategy.

## Usage

```bash
/copywriter:plan "March" "Launch of Course"
/copywriter:plan "Next Week" "Authority Building"
```

## Workflow

1.  **Triggers** `content-calendar-planner`.
2.  **Reads** `data/2-Domaines/business-profile.json` (to align with offers).
3.  **Generates** the "Waterfall Strategy":
    - 1x Hero Asset (Blog/Newsletter).
    - 3x Social Splinters (LinkedIn/Twitter).
    - 1x Personal Story.
4.  **Outputs** a Markdown Table Grid + Task List.

---

## 🔗 Solo Integration (Ecosystem Mode)

After generating the content calendar, save to the shared path so Solo agents can read it:

```python
SOLO_ROOT = "${CLAUDE_PLUGIN_ROOT}/../solo"
solo_installed = file_exists(f"{SOLO_ROOT}/.claude-plugin/plugin.json")

# Also read 0-Inbox for content triggers from Sales (deal wins, client milestones)
if solo_installed:
    CALENDAR_PATH = f"{SOLO_ROOT}/data/2-Domaines/content-calendar.md"
    INBOX_PATH    = f"{SOLO_ROOT}/data/0-Inbox/"
    
    # Check inbox for content triggers before generating calendar
    inbox_triggers = glob(f"{INBOX_PATH}content-trigger-*.md")
    if inbox_triggers:
        note(f"Found {len(inbox_triggers)} content triggers from Sales — incorporating into calendar.")
        for trigger in inbox_triggers:
            content = read_file(trigger)
            incorporate_trigger_into_calendar(content)
            archive_file(trigger)  # Move to Archives once processed
else:
    CALENDAR_PATH = "data/2-Domaines/content-calendar.md"

save_calendar(CALENDAR_PATH)
log(f"Content calendar saved to: {CALENDAR_PATH}")
```

**Result**: Solo's `monday-morning-agent` reads the calendar every Monday morning and includes scheduled posts in the weekly brief.
