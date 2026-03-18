---
description: "Your Monday morning business dashboard — revenue, pipeline, content, priorities"
argument-hint: ""
allowed-tools: Read, Write, Glob
model: sonnet
---

# /solo:weekly-review

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

Your Monday morning ritual. A comprehensive business dashboard showing revenue, pipeline, content status, overdue actions, and recommended priorities for the week ahead.

## Usage

```
/solo:weekly-review
```

No arguments needed — I'll scan all your data and generate a complete business snapshot.

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                    WEEKLY BUSINESS REVIEW                         │
├──────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                        │
│  ✓ Revenue snapshot: MTD revenue, outstanding, overdue           │
│  ✓ Pipeline health: Active deals, weighted value, risks          │
│  ✓ Content status: This week's content, next week's plan         │
│  ✓ Project progress: Active projects and next actions            │
│  ✓ Overdue actions: Client follow-ups, invoices, tasks           │
│  ✓ Weekly priorities: Top 3 recommended actions                  │
├──────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                       │
│  + ~~CRM: Pull real-time deal data and activity                  │
│  + ~~accounting: Sync revenue and expense data                   │
│  + ~~project tracker: Import tasks and deadlines                 │
│  + ~~calendar: Show this week's meetings and commitments         │
│  + ~~chat: Send review summary to Slack/Discord                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Output

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WEEKLY BUSINESS REVIEW — February 17, 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 💰 REVENUE SNAPSHOT

**February Performance:**
Month-to-date (paid): €12,500
Monthly target: €15,000 — 83% achieved ✓
Outstanding invoices: €8,000 (3 invoices)
Overdue invoices: €2,000 (1 invoice) ⚠️

**Collection Metrics:**
Collection rate: 85% (target: >90%)
Avg days to payment: 22 days (target: <30)

**Trend:** ↗️ Revenue up 6.5% vs. last month

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📊 SALES PIPELINE

**Pipeline Health:**
Active deals: 5 deals worth €67,000
Weighted pipeline: €32,600 (based on stage probability)
Avg deal size: €13,400
Avg deal age: 18 days

**By Stage:**
Discovery (2): €22,000 (33%)
Proposal (1): €15,000 (22%)
Negotiation (1): €20,000 (30%)
Verbal (1): €10,000 (15%)

**Risk Flags:** 🚩 3 deals need attention

- TechStart Inc (€20K): Stale (16 days no contact)
- Beta Solutions (€12K): Past close date
- Gamma LLC (€10K): Single-threaded

**Status:** 🟢 Healthy pipeline (value = 2.2x monthly target)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📝 CONTENT STATUS

**This Week (Week 3):**
✅ Mon: LinkedIn post published (Engagement)
🔄 Wed: LinkedIn post in draft (Social Proof)
⏳ Thu: Newsletter not started
⏳ Fri: LinkedIn post idea only

**Progress:** 1/4 complete (25%) — Behind schedule ⚠️

**Next Week (Week 4):**
💡 All in "Idea" status
⚠️ Need to start drafting by Friday

**Content Mix (Last 30 days):**

- 12 posts published
- Pillars: 40% Expertise, 25% Story, 20% Opinion, 15% Other
- Channels: 80% LinkedIn, 20% Newsletter

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📦 ACTIVE PROJECTS

| Project                 | Status      | Phase     | Next Action           | Due       |
| ----------------------- | ----------- | --------- | --------------------- | --------- |
| Client Portal           | In progress | Prototype | Finish Figma mockups  | Feb 20    |
| Website Redesign (Acme) | Active      | Design    | Send design brief     | Feb 15 ⚠️ |
| Newsletter System       | Planning    | Discover  | User interviews       | Feb 18    |
| SaaS Idea Validation    | Active      | Validate  | Run landing page test | Feb 25    |

**Stalled Projects:** 1 (Personal Brand Refresh)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ⚠️ OVERDUE ACTIONS

**Urgent (3+ days overdue):**

1. Follow up on proposal (Sarah Chen / Acme Corp) — 3 days overdue
2. Send design brief (Acme Corp) — 2 days overdue
3. Payment reminder (Beta Inc / INV-2026-035) — 14 days overdue

**Due This Week:** 4. Finish Figma mockups (Client Portal) — Due Feb 20 5. User interviews (Newsletter System) — Due Feb 18 6. Send contract (Gamma LLC) — Due Feb 19

**Going Cold (14+ days no contact):** 7. TechStart Inc — 16 days since last contact

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📥 INBOX STATUS

- 0-Inbox: 3 files awaiting processing
- Last processed: 5 days ago

⚠️ Inbox needs attention (run: /solo:plan organize --inbox)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 RECOMMENDED PRIORITIES

### Priority 1: Clear Overdue Actions (2 hours)

**Impact:** High — Unblock €27K in deals + €2K overdue invoice

Actions:

1. Send payment reminder to Beta Inc
   → /solo:invoice remind INV-2026-035

2. Follow up with Sarah Chen (Acme Corp)
   → /solo:write email "Sarah Chen" --template follow-up

3. Send design brief to Acme Corp
   → Attach file from project folder

**Expected outcome:** Close Gamma LLC (€10K), re-engage TechStart (€20K)

---

### Priority 2: Complete This Week's Content (3 hours)

**Impact:** Medium — Maintain content consistency

Actions:

1. Finish Wed LinkedIn post (Social Proof)
   → /solo:write social "Revenue breakdown: How I made €15K in Feb"

2. Draft Thu newsletter
   → /solo:write newsletter "The 2-day validation sprint"

3. Outline Fri LinkedIn post
   → /solo:write social "Behind the scenes: My content process"

**Expected outcome:** Stay on track with content calendar

---

### Priority 3: Push Key Deals Forward (1 hour)

**Impact:** High — Move €30K in deals to next stage

Actions:

1. Re-engage TechStart Inc (€20K, Negotiation)
   → /solo:write email "TechStart" --template re-engagement

2. Send contract to Gamma LLC (€10K, Verbal)
   → Use template from proposals folder

**Expected outcome:** Close Gamma this week, schedule TechStart call

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📈 TRENDS & INSIGHTS

**What's Working:**
✓ Revenue trending up (6.5% MoM growth)
✓ Healthy pipeline (2.2x monthly target)
✓ Strong deal sizes (€13.4K average)

**What Needs Attention:**
⚠️ Content falling behind (25% complete this week)
⚠️ Collection rate below target (85% vs. 90%)
⚠️ 3 deals at risk (stale, past close, single-threaded)

**Recommendation:**
Block 2 hours Monday morning to clear overdue actions. This will unblock €27K in deals and get you back on track.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🚀 QUICK ACTIONS

**Clear overdue actions:**
/solo:invoice remind INV-2026-035
/solo:write email "Sarah Chen" --template follow-up
/solo:clients review "TechStart Inc"

**Complete content:**
/solo:write social "Revenue breakdown"
/solo:write newsletter "2-day validation sprint"

**Push deals:**
/solo:clients pipeline --risks
/solo:prospect outreach "TechStart Inc"

**Process inbox:**
/solo:plan organize --inbox

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Review saved to:
data/1-Projets/weekly-reviews/2026-02-17.md

Next review: Monday, February 24, 2026
```

---

## What I Analyze

### 1. Revenue Metrics

- Month-to-date revenue (paid invoices)
- Outstanding invoices (sent, awaiting payment)
- Overdue invoices (past due date)
- Collection rate and days to payment
- Trend vs. last month

**Source:** `data/1-Projets/invoices/*.md`

### 2. Sales Pipeline

- Active deals by stage
- Weighted pipeline value
- Risk flags (stale, stuck, past close date)
- Pipeline health score

**Source:** `data/1-Projets/pipeline.md`

### 3. Content Status

- This week's content progress
- Next week's content plan
- Content mix analysis (pillars, channels)
- Publishing consistency

**Source:** `data/1-Projets/content-calendar-*.md`

### 4. Active Projects

- Project status and phase
- Next actions and due dates
- Stalled or blocked projects

**Source:** `data/1-Projets/*/pipeline-status.md`

### 5. Overdue Actions

- Client follow-ups
- Invoices past due
- Project deadlines
- Clients going cold (14+ days no contact)

**Source:** All client cards, invoices, and project files

### 6. Inbox Status

- Files awaiting processing
- Last inbox review date

**Source:** `data/0-Inbox/`

---

## Agent Instructions

```python
def generate_weekly_review():
    # 1. Revenue snapshot
    invoices = load_all_invoices()
    revenue_metrics = calculate_revenue_metrics(invoices)

    # 2. Sales pipeline
    pipeline = load_pipeline()
    pipeline_health = analyze_pipeline_health(pipeline)
    risk_flags = identify_risk_flags(pipeline)

    # 3. Content status
    calendar = load_current_content_calendar()
    content_progress = analyze_content_progress(calendar)

    # 4. Active projects
    projects = scan_active_projects()
    project_status = analyze_project_status(projects)

    # 5. Overdue actions
    overdue = []

    # Client follow-ups
    clients = load_all_clients()
    for client in clients:
        if client.next_action_overdue:
            overdue.append(("client_followup", client, client.days_overdue))
        if client.days_since_contact > 14:
            overdue.append(("going_cold", client, client.days_since_contact))

    # Overdue invoices
    for invoice in invoices:
        if invoice.status == "Overdue":
            overdue.append(("invoice", invoice, invoice.days_overdue))

    # Project deadlines
    for project in projects:
        if project.next_action_overdue:
            overdue.append(("project", project, project.days_overdue))

    # Sort by urgency
    overdue.sort(key=lambda x: x[2], reverse=True)

    # 6. Inbox status
    inbox_count = count_files("data/0-Inbox/")
    last_processed = get_last_inbox_process_date()

    # 7. Generate priorities
    priorities = generate_weekly_priorities(
        revenue_metrics,
        pipeline_health,
        content_progress,
        overdue,
        risk_flags
    )

    # 8. Trends and insights
    trends = analyze_trends(revenue_metrics, pipeline_health, content_progress)

    # 9. Display review
    display_weekly_review(
        revenue_metrics,
        pipeline_health,
        content_progress,
        project_status,
        overdue,
        inbox_count,
        priorities,
        trends
    )

    # 10. Save review
    save_review(f"data/1-Projets/weekly-reviews/{today()}.md")

def generate_weekly_priorities(revenue, pipeline, content, overdue, risks):
    """
    Prioritize based on:
    1. Overdue actions (highest urgency)
    2. Revenue impact (deals at risk, overdue invoices)
    3. Content consistency (maintain publishing cadence)
    4. Project deadlines (upcoming due dates)
    """

    priorities = []

    # Priority 1: Clear overdue actions (if any urgent)
    urgent_overdue = [x for x in overdue if x[2] >= 3]  # 3+ days overdue
    if urgent_overdue:
        priorities.append({
            "title": "Clear Overdue Actions",
            "impact": "High",
            "time": estimate_time(urgent_overdue),
            "actions": generate_action_list(urgent_overdue),
            "expected_outcome": calculate_impact(urgent_overdue)
        })

    # Priority 2: Content (if behind schedule)
    if content.progress < 50:
        priorities.append({
            "title": "Complete This Week's Content",
            "impact": "Medium",
            "time": "3 hours",
            "actions": generate_content_actions(content),
            "expected_outcome": "Stay on track with content calendar"
        })

    # Priority 3: Push key deals (if risks exist)
    if risks:
        priorities.append({
            "title": "Push Key Deals Forward",
            "impact": "High",
            "time": "1 hour",
            "actions": generate_deal_actions(risks),
            "expected_outcome": calculate_deal_impact(risks)
        })

    return priorities[:3]  # Top 3 priorities
```

---

## Tips

1. **Run every Monday** — Make this your Monday morning ritual (15 minutes)
2. **Act on priorities** — The review is only useful if you execute the top 3 priorities
3. **Track trends** — Compare week-over-week to spot patterns
4. **Adjust targets** — If you're consistently hitting 120% of target, raise the target
5. **Celebrate wins** — Note what's working and do more of it

---

## Integration with Other Commands

This command pulls data from:

- `/solo:invoice status` — Revenue and payment metrics
- `/solo:clients pipeline` — Sales pipeline health
- `/solo:plan content` — Content calendar status
- `/solo:build status` — Project progress
- `/solo:clients follow-up` — Overdue actions

Use the quick actions to execute on priorities:

- `/solo:invoice remind [invoice]` — Send payment reminders
- `/solo:write email [client]` — Draft follow-ups
- `/solo:clients review [client]` — Check client status
- `/solo:plan organize --inbox` — Process inbox

---

## Skills Used

- `financial-health` — Revenue calculations
- `sales-pipeline` — Pipeline analysis
- `content-calendar-planner` — Content progress
- `client-management` — Client follow-ups
- `weekly-review` — Priority generation and insights
