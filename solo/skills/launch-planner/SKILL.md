---
name: launch-planner
description: >
  Plans the launch of a digital product across 3 horizons: first 10 users (manual
  recruitment), 10 → 100 (channels), 100+ (what scales). Produces a day-by-day
  calendar from D-14 to D+30 and a prioritized channel grid based on the ICP.
  Triggered by "launch plan", "how to launch my product", "how to find my first
  users", "launch strategy", "0 to 100 users".
version: 1.0.0
bundle: operations
triggers:
  - "launch plan"
  - "plan my launch"
  - "product launch"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Launch Planner

There is no universal launch playbook. But there is a universal principle: the first 10 users never come from the same channels as the first 1,000. This skill plans both separately — because conflating them is the number one launch mistake.

## When to Use

- After `/solo:build design` (you have a PRD and a landing page)
- During `/solo:build launch`
- Before talking about your product publicly

---

## Horizon 1: The First 10 Users (Manual Recruitment)

**Uncomfortable truth:** The first 10 users almost always come from direct contacts or very targeted communities. Not Product Hunt. Not SEO. Not newsletters. Just you talking to humans.

**Why manual recruitment first:**
- Each early adopter is a mine of information
- Feedback from 10 engaged users is worth more than 1,000 passive signups
- You need testimonials and proof before activating broad channels

### Sources for the First 10

**Source 1: Your existing contacts**
Review your LinkedIn contacts, email, WhatsApp. Identify those who match the ICP. Write a personal message (not a broadcast).

Script:
```
"I'm building [product] for [ICP]. You match the target exactly.
I need 5 people to test before the official launch —
no commitment, just 30 minutes of your time and your honesty.
Interested?"
```

**Source 2: Targeted online communities**
Don't spam. Contribute value first, mention the product second — or post with total transparency ("I'm building X to solve Y, looking for beta testers").

Find communities via:
- Reddit: find the exact ICP subreddit (e.g., r/freelance, r/SaaS, r/nocode)
- Slack / Discord: niche communities (IndieHackers Slack, sector communities)
- Facebook Groups: still active for certain niches (freelancers, creators)
- LinkedIn: active comments under posts by domain leaders

**Source 3: Targeted cold outreach**
5 to 10 highly personalized messages to people who exactly match the ICP and have publicly expressed the pain you're solving (in LinkedIn posts, Twitter/X threads, competitor reviews).

Use `draft-outreach` to write these messages.

**Source 4: Your existing audience (if applicable)**
If you have a newsletter, social account, or community — this is your first list. Even 200 targeted subscribers can generate 10-20 beta testers.

### Horizon 1 Action Plan

```markdown
## Plan: First 10 Users

Week -2 before launch:
- [ ] List 30 potential contacts from your address book
- [ ] Filter the 10 who best match the ICP
- [ ] Write the personal message (via draft-outreach)
- [ ] Send to 10 contacts — goal: 5 positive responses

Week -1:
- [ ] Identify 3 relevant online communities
- [ ] Spend 3 days contributing (without mentioning the product)
- [ ] Post 1 beta recruitment message per community
- [ ] Goal: 3-5 additional signups

Launch Day:
- [ ] 10 active beta testers (minimum viable for feedback)
- [ ] Onboarding call with each (30 min) → notes in data/
- [ ] Collect 3 usable testimonials before D+14
```

---

## Horizon 2: From 10 to 100 Users (Channels)

At this point, you have:
- A working product (validated by the first 10)
- Early-stage social proof or testimonials
- A live landing page
- A clearer picture of who's actually using the product and why

**Now: activate 2 to 3 channels maximum.** Not 10. The classic mistake is spreading too thin.

### Channel Selection Grid

For each channel, evaluate: **ICP Fit × Effort × Time to results**

| Channel | ICP Fit | Effort | Time | Best for |
|---------|---------|--------|------|---------|
| **Communities (Reddit, Slack, Discord)** | High if well-chosen | Medium | Days | Technical niches, creators, devs |
| **LinkedIn organic** | High for B2B | Medium | Weeks | Consultants, B2B freelancers, SaaS |
| **Product Hunt** | Variable | High (1 shot) | 48h | Dev/design tools, SaaS, no-code |
| **Own newsletter** | Very high | Low | Days | Any target with existing audience |
| **Partner newsletter** | Variable | Medium | Weeks | With a good partner identified |
| **Twitter/X** | High for makers | High (long term) | Long | Builders, IndieHackers, devs |
| **YouTube/podcast** | High, long-term | Very high | Long | If existing content |
| **SEO** | High if targeted | High | Very long (6-12 mo) | Never a launch priority |
| **Targeted cold outreach** | Very high | High | Days | B2B, medium or high ticket |
| **Referral / word-of-mouth** | Maximum | Low | Weeks | Products with strong usage value |

### Recommendation by ICP

**ICP: Developers / makers / no-coders**
1. Communities (IndieHackers, Hacker News, r/SaaS)
2. Twitter/X (if already active) or build in public
3. Product Hunt (to amplify, not to start)

**ICP: Freelancers / B2B consultants**
1. LinkedIn organic (posts about the problem, not the product)
2. Sector communities (Slack/Discord groups in your field)
3. Targeted cold outreach (via draft-outreach)

**ICP: Content creators**
1. Twitter/X + TikTok (where they already are)
2. Partner newsletters (cross-promo with similar creators)
3. Creator communities (private Slack groups, creator Discord)

**ICP: SMBs / teams**
1. B2B cold outreach (volume + personalization)
2. LinkedIn (decision-makers)
3. Partners / integrators (indirect channels)

---

## Horizon 3: From 100 to 1,000+ (What Scales)

**Principle:** What works to go from 0 to 100 doesn't scale. What scales from 100 to 1,000 doesn't work at the start.

At 100 users, you have data to know:
- Which channel has the best conversion rate
- Who your real ICP is (may differ from what you imagined)
- Which message resonates best

**At 100 users, activate based on signals:**

| Signal | Action |
|--------|--------|
| Many signups via accidental SEO | Invest in content SEO |
| Spontaneous viral sharing | Build a referral mechanism |
| Strong cold outreach conversion | Structure a sales process |
| Strong retention (people keep coming back) | Invest in community around the product |
| Low retention | Fix the product before accelerating acquisition |

---

## Launch Calendar: D-14 → D+30

```markdown
# Launch Calendar: [Product Name]

## Pre-Launch (D-14 → D-1)

### D-14 to D-10: Foundations
- [ ] Landing page finalized and live
- [ ] Analytics tracking configured (Plausible, Umami, or GA4)
- [ ] Waitlist form / purchase flow working
- [ ] Welcome email written and tested
- [ ] 10 contacts identified for beta recruitment

### D-9 to D-7: Beta Recruitment
- [ ] Personal messages sent to 10 contacts
- [ ] Posts in the 2-3 targeted communities
- [ ] Goal: 5-10 beta testers recruited

### D-6 to D-4: Beta and Testimonials
- [ ] Onboarding sessions with beta testers
- [ ] Feedback notes documented in data/
- [ ] 3 testimonials collected (written or video)
- [ ] Urgent product adjustments (blocking bugs only)

### D-3 to D-1: Launch Prep
- [ ] Landing page updated with testimonials
- [ ] Launch message written (email list + social media)
- [ ] Product Hunt scheduled (if applicable)
- [ ] Partners / supporters briefed

---

## Launch Day

### Morning (8AM–12PM)
- [ ] Publish the launch post on primary social channels
- [ ] Send email to the waitlist
- [ ] Post on Product Hunt (if applicable) — recommended time: 12:01 AM PST
- [ ] Post in communities (with permission / right approach)

### Afternoon (12PM–6PM)
- [ ] Reply to all comments / messages
- [ ] Process first signups / purchases
- [ ] Monitor for errors (launches stress servers)

### Evening (6PM–10PM)
- [ ] Update launch post with first numbers
- [ ] Publicly thank early adopters (with permission)
- [ ] Personal debrief: what worked / didn't work today?

---

## Post-Launch (D+1 → D+30)

### D+1 to D+7: Consolidation
- [ ] Follow-up email to signups who haven't activated yet
- [ ] Onboarding new users (calls if < 50, automated emails if more)
- [ ] First report from launch-signal-agent
- [ ] Fix bugs and onboarding friction identified

### D+8 to D+14: Second Wave
- [ ] "One week later" post (numbers, learnings, what's next)
- [ ] Activate the second channel from the grid
- [ ] First referrals requested from satisfied early adopters

### D+15 to D+30: Cruising Altitude
- [ ] Assess: which channel has the best effort/conversion ratio?
- [ ] Double down on the winning channel
- [ ] Stop channels that aren't converting
- [ ] Prepare Horizon 3 strategy (if 100 users reached)
```

---

## Skill Output

```markdown
# Launch Plan: [Product]

## Summary
- D+30 goal: [N] active users / [N] signups / $[X] MRR
- Priority channels: [1], [2], [3]
- Horizon 1 (first 10): [specific strategy]
- Horizon 2 (10 → 100): [selected channels]

## Calendar
[Full personalized D-14 → D+30 calendar]

## Launch Messages
[Copy for each selected channel, written via draft-outreach]

## Success Metrics
- D+7: [N] beta signups with feedback
- D+14: [N] active users
- D+30: [N] paying or [N] signups depending on model
```

Save: `data/1-Projets/[project]/launch-plan-[date].md`

## Integration Points

- **`landing-page-builder`**: landing page is the hub for all campaigns
- **`draft-outreach`**: writes messages for each channel
- **`product-pricing-model`**: pricing model shapes the strategy (freemium vs. purchase)
- **`launch-signal-agent`**: monitors post-launch signals automatically

## References

- **`references/channel-fit-matrix.md`**: detailed channel selection grid for 8 product types
- **`references/launch-sequence-template.md`**: blank D-14 → D+30 calendar to fill in

---

## 🔬 Sentinel Integration (when installed)

```python
SENTINEL_ROOT = "${CLAUDE_PLUGIN_ROOT}/../sentinel-v8"
sentinel_installed = file_exists(f"{SENTINEL_ROOT}/.claude-plugin/plugin.json")
```

Skip this section entirely if `sentinel_installed` is False. Launch-planner works identically without it.

### Trigger condition
Activate **before** generating the D-14 to D+30 calendar. The pre-mortem must run before the plan is assembled, not after — once a calendar exists, the user is anchored to it.

### What to run

**Step 1 — campaign pre-mortem (strategy-marketing domain)**

Load template: `../sentinel-v8/domains/strategy-marketing/templates/campaign-premortem.md`

Populate with the launch context:
- Name: [product name] launch
- Objective: [stated traction goal, e.g. "50 paying users in 30 days"]
- Channel(s): [channels selected for Horizon 2]
- Target audience: [ICP from data/2-Domaines/icp.json]
- Timeline: D-14 to D+30

Ask the user to complete the pre-mortem failure modes independently before seeing the calendar.
Run the 4 failure mode categories from the template: Message & Audience, Channel & Distribution, Execution & Resources, Measurement.

Surface the top 3 risks and required preventive actions. These become mandatory items in the D-14 phase of the calendar.

**Step 2 — reality-checker (outside view on launch targets)**

For the stated D+30 goal (signups, users, or revenue), invoke `reality-checker`:

Reference class: "bootstrapped [product type] launched to [channel] by a solo founder"

Require estimates with confidence levels for:
- Median D+30 sign-up count for similar launches
- Conversion rate from landing page visitor to signup (typical range)
- % of launches that hit their D+30 target

If user's target is in the top 25% of reference class → flag explicitly.
Tell them where to verify (ProductHunt data, IndieHackers launch posts, SaaS benchmarks).

**Step 3 — calibration prediction record**

Before finalizing the calendar, prompt:
> "State your D+30 prediction: [N] signups / [N] users / $[N] revenue. How confident are you? (50% / 70% / 90%)"

Record in `../sentinel-v8/data/decision-ledger.json` via `calibration-coach` agent.
Set review_date to D+30 for automatic follow-up in `/sentinel-review`.

### Output format addition

Insert a **Launch Risk Brief** section before the D-14 calendar:

```
## Launch Risk Brief (Sentinel)

Pre-mortem top risks:
1. [risk] → Prevention: [action] → Watch for: [signal]
2. [risk] → Prevention: [action] → Watch for: [signal]
3. [risk] → Prevention: [action] → Watch for: [signal]

Outside view: Your [D+30 target] is in the [top X%] of comparable launches.
Base rate: [median outcome] — verify at [source].

Your prediction: [N] [metric] at [X%] confidence. Recorded for D+30 review.
```

The D-14 calendar items automatically include the preventive actions from the pre-mortem.

### Standalone output (Sentinel not installed)
Standard D-14 to D+30 calendar with channel grid and success metrics. No change.

---

## 🛡️ Sentinel Integration

```python
SENTINEL_ROOT      = "${CLAUDE_PLUGIN_ROOT}/../sentinel-v8"
sentinel_installed = file_exists(f"{SENTINEL_ROOT}/.claude-plugin/plugin.json")
```

**Trigger**: Before generating the D-14 to D+30 calendar. Run Sentinel analysis first — the calendar is only useful if the strategy behind it survives scrutiny.
**Standalone mode**: Skip this section. Proceed directly to calendar generation.

### If Sentinel installed — Strategy audit before the calendar locks

**Step 1 — Campaign pre-mortem** (strategy-marketing domain)
Load `../sentinel-v8/domains/strategy-marketing/templates/campaign-premortem.md`.

Frame it as a launch pre-mortem:
> "It's 6 months after launch day. The product failed to get traction. KPIs missed, early users churned, the momentum died. What happened?"

Generate 5–7 failure modes across these categories:
- **Audience mismatch** — reached the wrong people in Horizon 1
- **Channel bet** — the primary channel underdelivered, no fallback
- **Timing** — launched into noise (competitor launch, news cycle, holidays)
- **Conversion gap** — users came but didn't convert to paying
- **Founder bottleneck** — manual outreach didn't scale, no system for Horizon 2

For each: likelihood (HIGH/MEDIUM/LOW) + observable early warning + preventive action.

**Step 2 — reality-checker** (`../sentinel-v8/agents/reality-checker.md`)

Run outside-view check on the user's stated launch targets. Reference class:
- `"indie product launches, bootstrapped, [category], first 30 days"`

For each stated target (users, signups, revenue):
- `estimate`: what comparable launches actually achieved at D+30
- `confidence`: HIGH / MODERATE / LOW
- `verify_at`: specific sources (Product Hunt analytics, Indie Hackers launch posts, Ship Your Side Project)
- `gap`: where does the user's target sit in the distribution?

**Step 3 — Channel selection audit**

For each channel in the proposed launch mix, apply SM1 (Shiny Object Syndrome) check:
- "What is the proven ROI of this channel for a product in this category?"
- "Is this channel in the plan because of evidence, or because you've seen it work for others?"
- Flag any channel with no prior personal evidence as ASSUMPTION — not PROVEN.

**Step 4 — calibration-coach prediction record**

Before generating the calendar, record the user's D+30 prediction:

```json
{
  "id": "<uuid>",
  "date": "<today>",
  "decision": "Launch: [product name]",
  "prediction": "[X] users / [Y] signups / [Z] revenue by D+30",
  "confidence": <user-stated 0.0-1.0>,
  "review_date": "<launch date + 30 days>",
  "plugin": "solo/launch-planner",
  "pre_mortem_high_risks": ["<risk 1>", "<risk 2>"]
}
```

**Output integration** — prepend to the D-14 calendar:

```
## Pre-Launch Decision Audit (Sentinel)

### Top 3 failure modes to mitigate before D-0
1. [Highest likelihood risk] → Prevention: [action]
2. [Second risk] → Prevention: [action]
3. [Third risk] → Prevention: [action]

### Outside view on your D+30 targets
[Reality-checker summary with confidence ratings]

### Channel confidence map
- [Channel A]: EVIDENCE-BASED ✅
- [Channel B]: ASSUMPTION ⚠️ — validate before committing budget

### Prediction recorded
[Stated target] at [confidence]% — review on [date]

---
```

Then proceed to the calendar as normal.
