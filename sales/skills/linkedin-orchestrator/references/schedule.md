# LinkedIn Orchestrator — Schedule & Execution Guide

## Autonomous Execution Flow

When "start linkedin" is triggered, execute in order without asking for user input:

**Rules:**
- Do NOT ask which task to start — execute in order
- Do NOT ask user to select variations — AI auto-selects
- Execute all tasks for the current time block
- Use **Claude for Chrome** for all LinkedIn actions
- Log everything to `data/2-Domaines/LinkedIn/activity_log.md`

### Startup Sequence

```
1. Determine current time block (based on system time)
2. Read `data/2-Domaines/sales-profile.json` → Language & Geo
3. Read `data/2-Domaines/LinkedIn/activity_log.md` → Today's progress
4. Read `data/2-Domaines/LinkedIn/prospects.md` → Cached prospects
5. Read/create today's to-do file (`to-do_DDMMYYYY.md`)
6. For current block, execute each pending task
```

### Cache-First Rule

Before visiting any profile, check `prospects.md`. Only scrape LinkedIn if data is missing or >7 days old.

### Comment Dedup Rule

Read `activity_log.md` to build "Already Commented" set. NEVER comment on the same post twice.

---

## Time Block Execution Detail

### Morning Block (Before 10:00) — Active Engagement

- Check limit: Comments < 30?
- **High-Priority Warming**: Filter `prospects.md` for 2-touch leads → comment to reach 3 touches
- **General Engagement**: Find 9 posts (3 Peer, 3 Prospect, 3 Thought Leader)
- Execute: `linkedin-engager` (Bilingual auto-detect)
- Log all comments

### Content Block (10:00–12:00) — Creation

- Check limit: Posts < 1? (12-hour rule applies)
- Select Content Type based on Day & Language (see Bilingual Posting Schedule)
- Execute: `linkedin-creator` (Save-Worthy Asset focus)
- Schedule post via Claude for Chrome (do NOT post immediately)

### Midday Block (12:00–15:00) — Golden Hour

- Reply to comments on YOUR post (if any)
- Engage with 5–10 posts immediately after publishing

### Afternoon Block (15:00–18:00) — Outreach

- Check Connection Acceptances
- **Warm Up**: Filter `prospects.md` for 0–1 touch leads → run `linkedin-engager`
- **Connect**: Send requests to 3-touch leads (using `linkedin-engager` templates)
- **Discover**: Run `linkedin-prospector` to find NEW leads (save to `prospects.md`)

### Evening Block (After 18:00) — Audit & Sync

- **MANDATORY**: Update `activity_log.md` with all daily stats
- **Sync**: Run `hubspot-sync` to push changes to CRM
- Audit Inbound: Check who viewed profile, screen for ICP match

---

## Bilingual Posting Schedule

If `language_preference: "Bilingual"` in `sales-profile.json`:

| Day | Language | Focus | Post Type |
|:----|:---------|:------|:----------|
| **Mon** | **English** | Global Strategy | Framework / Big Picture |
| **Tue** | **English** | Tech Demo | Video / Architecture (Peak Tech Reach) |
| **Wed** | **French** | Local Market | "Save-Worthy" Asset (Schema/Checklist) |
| **Thu** | **English** | Thought Leadership | Contrarian Take / Prediction |
| **Fri** | **French** | Culture/Reflect | Build-in-Public / Personal Story |

If preference is "English" or "French" only, use that language for all days.

---

## Daily Engagement Limits (Safe Mode)

| Activity | Limit | Action if Reached |
|:---------|:------|:------------------|
| Comments | 30 | Stop commenting. Log "Limit Reached". |
| Connections | 20 | Stop sending. Focus on warming. |
| DMs | 25 | Stop sending. |
| Posts | 1 | Schedule for tomorrow. |

---

## 12-Hour Posting Rule

- Check `activity_log.md` for last post time
- If < 12 hours ago: **DO NOT POST**
- Schedule for the next valid window (usually next morning)

---

## CRM Sync

At the end of **Afternoon** and **Evening** blocks:
1. Identify modified prospects in `prospects.md`
2. Run `hubspot-sync`
3. Log result: "Synced X prospects to HubSpot"

---

## Resume Workflow

1. Read `to-do_DDMMYYYY.md`
2. Parse `[x]` (done) vs `[ ]` (pending)
3. Determine current time block
4. Prompt: "Resuming [Block Name]. Next task: [Task]. Proceed?"

## Task Completion

- Mark tasks `[x]` in to-do file with timestamp
- **CRITICAL**: Update `data/2-Domaines/LinkedIn/activity_log.md` immediately after each task
