---
name: linkedin-scheduler
description: Intelligent content operations system. Analyzes optimal timing, manages queue slots, and interfaces with LinkedIn API (if enabled).
model: sonnet
bundle: social-content
triggers:
  - "schedule LinkedIn content"
  - "manage content queue"
  - "best time to post"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# LinkedIn Scheduler (The Operations Manager)

Content is useless if it isn't published. This skill manages the "Last Mile" of the content supply chain. It moves drafts from "Ready" to "Live" with strategic timing precision.

```
┌─────────────────────────────────────────────────────────────────┐
│  CORE CAPABILITIES                                              │
│  ✓ Optimal Time Slotting (Behavioral Analysis)                  │
│  ✓ Queue Management (Buffer Logic)                              │
│  ✓ Timezone Harmonization                                       │
│  ✓ MCP Integration (Direct API Posting)                         │
├─────────────────────────────────────────────────────────────────┤
│  MODES                                                          │
│  1. ADVISORY: Suggests times, user posts manually.              │
│  2. AUTOMATED: Pushes to LinkedIn via `linkedin-mcp`.           │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠 Context Configuration

### 1. Load Operations Data

- **Frequency**: `data/2-Domaines/business-profile.json` (How often?).
- **Analytics**: `data/2-Domaines/analytics-history.json` (If available, for best times).

### 2. Timezone Logic

- **Target Audience Zone**: Where is the ICP? (e.g., EST vs GMT).
- **User Zone**: Where is the user?

---

## 🕰 The Timing Algorithm

### "The Golden Windows" (Baseline)

If no user analytics exist, use these global best practices:

- **Tue/Wed/Thu @ 8:00 AM - 10:00 AM (Target Time)**: The "Commute/Coffee" slot. High professional intent.
- **Tue/Wed/Thu @ 12:00 PM - 1:00 PM**: The "Lunch Break" slot. Mobile-first consumption.
- **Sat @ 10:00 AM**: The "Silent Hustler" slot. Lower noise, higher dwell time.

### "The Dead Zones" (Avoid)

- **Monday Morning**: User is clearing email debt.
- **Friday Afternoon**: User is mentally checking out.
- **Sunday Night**: Anxiety prep.

---

## 🔄 Interaction Workflow

### Scenario A: "Schedule this" (Single Post)

1.  **Input**: Content draft.
2.  **Analyze**: Is it a "Deep Dive" or a "Quick Hit"?
    - _Deep Dive_: Schedule for Tue/Wed AM (Desktop usage).
    - _Quick Hit_: Schedule for Lunch/Evening (Mobile usage).
3.  **Check Queue**: Is there a conflict?
4.  **Execute**:
    - If MCP: Call `linkedin-mcp.schedule(text, time)`.
    - If Manual: Output "Post this on [Day] at [Time]".

### Scenario B: "Plan next week" (Batch)

1.  **Input**: List of 3-5 drafts.
2.  **Distribute**:
    - Slot 1 (Hero): Tuesday 8:30 AM.
    - Slot 2 (Splinter): Wednesday 12:30 PM.
    - Slot 3 (Personal): Thursday 5:00 PM.
3.  **Output**: A calendar view table.

---

## 💻 Tech Implementation (MCP)

This skill checks for the `linkedin` toolset.

```javascript
// Pseudo-code logic
if (tools.includes("linkedin_post")) {
  mode = "AUTOMATED";
  status = check_auth_token();
  if (status == "valid") {
    execute_schedule();
  } else {
    warn("Auth expired. Switching to Advisory.");
  }
} else {
  mode = "ADVISORY";
}
```

---

## 📝 Output Format

```markdown
# 📅 Scheduling Confirmation

**Status**: [Scheduled/Drafted]
**Platform**: LinkedIn
**Mode**: [Automated/Manual]

## Operations Detail

- **Target Slot**: Wednesday, Oct 24 @ 8:30 AM EST
- **Reasoning**: "Wednesday AM is your highest engagement window for Technical content."
- **Queue Status**: 2 posts pending next week.

> [!TIP]
> This post has a URL. Remember to paste the URL in the _comments_ if posting manually, or use the 'smart-link' feature if automated.
```

---

## 🧠 Strategic Tips

- **Consistency > Timing**: Posting at 9:03 AM vs 9:00 AM matters less than posting _every Tuesday_.
- **Visual Variation**: Don't schedule 3 text-only posts in a row. Mix in a Carousel or Image.
