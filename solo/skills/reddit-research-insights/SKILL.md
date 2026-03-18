---
name: reddit-research-insights
description: >
  Extract deep insights from Reddit discussions - pain points, jargon, desired solutions,
  and competitor mentions. Uses Reddit as a cultural laboratory for unfiltered user
  feedback. Triggers on "research Reddit", "Reddit insights", or "listen to Reddit".
version: 1.0.0
bundle: sales-growth
triggers:
  - "reddit research"
  - "what does reddit say"
  - "reddit insights"
tools:
  standalone: ["exa"]
  supercharged: ["exa"]
---

# Skill: Reddit Research Insights

Uses Reddit as a cultural laboratory to understand raw, unfiltered user frustrations, desires, and language. Extracts pain points, desired solutions, competitor mentions, and audience-specific jargon from subreddit discussions.

## When to Use

- Market research (understanding user pain points)
- Competitive analysis (what users say about competitors)
- Content ideation (what topics resonate)
- Product validation (is this problem real?)
- Language research (how do users describe their problems?)

## Why Reddit?

### Reddit vs. Other Research Methods

| Method                          | Pros                            | Cons                                                                    |
| ------------------------------- | ------------------------------- | ----------------------------------------------------------------------- |
| **User Interviews**             | Deep, specific insights         | Time-consuming, small sample, biased (people say what you want to hear) |
| **Surveys**                     | Quantitative data, large sample | Shallow insights, low response rates                                    |
| **Review Sites (G2, Capterra)** | Product-specific feedback       | Filtered, polished, often incentivized                                  |
| **Reddit**                      | Raw, unfiltered, real problems  | Noisy, requires synthesis, not always representative                    |

**Reddit's Superpower:** People complain honestly about real problems without a sales agenda.

## Reddit Research Framework

### 1. Subreddit Selection

Find where your target audience congregates.

**For Solopreneurs:**

- r/solopreneurs (60K+ members)
- r/freelance (200K+ members)
- r/Entrepreneur (3M+ members, filter for solopreneurs)
- r/smallbusiness (1M+ members)
- Niche subreddits (r/webdev, r/design_critiques, etc.)

**For B2B SaaS:**

- r/SaaS
- r/startups
- r/ProductManagement
- r/sales

**For Specific Industries:**

- r/marketing (for marketing tools)
- r/sales (for sales tools)
- r/productivity (for productivity tools)

### 2. Search Strategy

**Keyword Patterns:**

- Pain points: "frustrated with", "hate that", "wish there was", "why is there no"
- Solutions: "looking for", "recommendations for", "best tool for"
- Competitors: "[Competitor name] vs", "alternatives to [Competitor]"
- Workarounds: "I use", "my setup", "how I solve"

**Example Searches:**

```
site:reddit.com/r/solopreneurs "invoicing" "frustrating"
site:reddit.com/r/freelance "CRM" "too complex"
site:reddit.com/r/solopreneurs "wish there was" "all-in-one"
```

### 3. Insight Categories

Extract insights into these categories:

#### A. Pain Points (Unmet Needs)

What frustrates users? What problems are they actively trying to solve?

**Signals:**

- "I hate that..."
- "Why is there no..."
- "I'm so frustrated with..."
- "This is driving me crazy..."

**Example:**

> "I hate that I have to use 5 different tools to run my business. Notion for notes, HubSpot for CRM, Stripe for invoicing, Calendly for scheduling, and Gmail for everything else. It's exhausting."

**Insight:** Tool overload is a major pain point for solopreneurs.

#### B. Desired Solutions (What They Want)

What features or products are they asking for?

**Signals:**

- "I wish there was..."
- "Looking for a tool that..."
- "Does anyone know of..."
- "I'd pay for..."

**Example:**

> "I wish there was a simple CRM that also does invoicing. I don't need all the enterprise features of HubSpot, just basic client tracking and billing."

**Insight:** Demand for an all-in-one CRM + invoicing tool for solopreneurs.

#### C. Competitor Mentions

What tools are they using? What do they like/dislike?

**Signals:**

- "[Tool name] is great for..."
- "I switched from [Tool A] to [Tool B] because..."
- "[Tool] is too expensive/complex/limited"

**Example:**

> "I switched from HubSpot to Pipedrive because HubSpot was way too complex for a solopreneur. Pipedrive is simpler but still missing invoicing."

**Insight:** HubSpot is seen as too complex, Pipedrive is simpler but incomplete.

#### D. Common Jargon & Language

How do they describe their problems? What words do they use?

**Signals:**

- Repeated phrases
- Industry-specific terms
- Metaphors and analogies

**Example:**

> "I'm drowning in admin work" (repeated 15+ times in r/solopreneurs)

**Insight:** "Drowning in admin" is a common phrase. Use it in marketing copy.

#### E. Workarounds

How are they currently solving the problem?

**Signals:**

- "I use..."
- "My setup is..."
- "I built a..."
- "I just..."

**Example:**

> "I use a Google Sheet for invoicing. It's manual but at least it's free. I've been meaning to find a better solution for months."

**Insight:** Many solopreneurs use spreadsheets for invoicing (pain point: manual, time-consuming).

## Reddit Research Template

```markdown
# Reddit Research: [Topic]

**Date:** [Date]  
**Subreddits:** [List of subreddits searched]  
**Search Keywords:** [Keywords used]  
**Threads Analyzed:** [Number]

---

## Pain Points (Unmet Needs)

### 1. [Pain Point Name]

**Frequency:** [How many times mentioned]  
**Severity:** [High/Medium/Low based on emotional language]

**Quotes:**

- "[Quote 1]" — u/username, r/subreddit
- "[Quote 2]" — u/username, r/subreddit

**Insight:** [What this tells us]

---

## Desired Solutions

### 1. [Solution Name]

**Frequency:** [How many times mentioned]  
**Willingness to Pay:** [Mentioned price points or "I'd pay for this"]

**Quotes:**

- "[Quote 1]" — u/username, r/subreddit
- "[Quote 2]" — u/username, r/subreddit

**Insight:** [What this tells us]

---

## Competitor Mentions

### [Competitor Name]

**Sentiment:** [Positive/Negative/Mixed]  
**Mentions:** [Number]

**Pros (what users like):**

- [Pro 1]
- [Pro 2]

**Cons (what users dislike):**

- [Con 1]
- [Con 2]

**Quotes:**

- "[Quote]" — u/username, r/subreddit

---

## Common Jargon & Language

**Frequent Phrases:**

- "[Phrase 1]" (mentioned X times)
- "[Phrase 2]" (mentioned X times)

**Problem Descriptions:**

- "[How they describe the problem]"

**Metaphors:**

- "[Metaphor or analogy]"

**Insight:** Use this language in marketing copy and product messaging.

---

## Workarounds

### [Workaround Name]

**Frequency:** [How many users mention this]  
**Tools Used:** [List of tools]

**Quotes:**

- "[Quote]" — u/username, r/subreddit

**Insight:** [Why they use this workaround, what's missing]

---

## Key Insights

**Top 3 Pain Points:**

1. [Pain 1] — [Impact]
2. [Pain 2] — [Impact]
3. [Pain 3] — [Impact]

**Top 3 Opportunities:**

1. [Opportunity 1] — [Why it matters]
2. [Opportunity 2] — [Why it matters]
3. [Opportunity 3] — [Why it matters]

**Competitive Gaps:**

- [Gap 1]: [Competitor] is missing [feature]
- [Gap 2]: [Competitor] is too [complex/expensive/limited]

**Language to Use:**

- [Phrase 1]
- [Phrase 2]
- [Phrase 3]

---

## Recommended Actions

1. **Product:** [What to build based on pain points]
2. **Positioning:** [How to position based on competitive gaps]
3. **Messaging:** [What language to use based on jargon research]
4. **Content:** [What topics to write about based on desired solutions]

---

## Sources

[List of Reddit threads analyzed with links]
```

## Example Reddit Research

```markdown
# Reddit Research: Solopreneur Business Tools

**Date:** 2026-02-13  
**Subreddits:** r/solopreneurs, r/freelance, r/Entrepreneur  
**Search Keywords:** "invoicing", "CRM", "all-in-one", "too many tools"  
**Threads Analyzed:** 47

---

## Pain Points (Unmet Needs)

### 1. Tool Overload

**Frequency:** 34 mentions  
**Severity:** High (strong emotional language: "exhausting", "overwhelming", "drowning")

**Quotes:**

- "I'm using 7 different tools to run my business. It's exhausting switching between them all day." — u/designer_sarah, r/solopreneurs
- "Why do I need Notion + HubSpot + Stripe + Calendly + Slack? There has to be a better way." — u/freelance_mike, r/freelance
- "I spend more time managing my tools than actually working." — u/consultant_alex, r/solopreneurs

**Insight:** Tool overload is a top frustration. Solopreneurs want an all-in-one solution.

### 2. Time-Consuming Invoicing

**Frequency:** 28 mentions  
**Severity:** High (impacts revenue: "delayed payments", "lost billable hours")

**Quotes:**

- "I spend 30-45 minutes creating each invoice in Excel. It's ridiculous." — u/designer_emma, r/freelance
- "I put off invoicing because it's such a pain. Then I get paid late." — u/dev_jordan, r/solopreneurs

**Insight:** Manual invoicing is a major time sink. Users want one-click invoice creation.

### 3. Cash Flow Unpredictability

**Frequency:** 22 mentions  
**Severity:** High (financial stress: "keeps me up at night", "can't plan")

**Quotes:**

- "I never know when clients will pay. Makes it impossible to plan expenses." — u/consultant_lisa, r/solopreneurs
- "I've had invoices go 60+ days overdue. I need better payment tracking." — u/designer_mark, r/freelance

**Insight:** Late payments cause financial stress. Users want automated payment reminders.

---

## Desired Solutions

### 1. All-in-One Business Tool

**Frequency:** 41 mentions  
**Willingness to Pay:** $20-50/mo (mentioned in 12 threads)

**Quotes:**

- "I wish there was ONE tool that did CRM + invoicing + project management. I'd pay $50/mo for that." — u/freelance_sarah, r/solopreneurs
- "Looking for an all-in-one solution. Tired of duct-taping 5 tools together." — u/designer_alex, r/freelance

**Insight:** Strong demand for an all-in-one tool. Price point: $20-50/mo.

### 2. Simple CRM (Not Enterprise)

**Frequency:** 19 mentions  
**Willingness to Pay:** $10-25/mo

**Quotes:**

- "I don't need HubSpot's enterprise features. Just basic client tracking and follow-ups." — u/consultant_mike, r/solopreneurs
- "Looking for a CRM that's actually designed for solopreneurs, not sales teams." — u/freelance_jordan, r/freelance

**Insight:** Existing CRMs are too complex. Opportunity for a simple, solopreneur-focused CRM.

---

## Competitor Mentions

### HubSpot

**Sentiment:** Mixed (powerful but too complex)  
**Mentions:** 38

**Pros:**

- Free tier is generous
- Powerful features

**Cons:**

- Too complex for solopreneurs (mentioned 24 times)
- Upsells are expensive ($45-200/mo)
- Built for teams, not individuals

**Quotes:**

- "HubSpot is overkill for a solopreneur. I use maybe 10% of the features." — u/designer_sarah, r/solopreneurs

### Notion

**Sentiment:** Positive (flexible but not built for business operations)  
**Mentions:** 31

**Pros:**

- Flexible, beautiful design
- Great for notes and project management

**Cons:**

- No native CRM or invoicing
- Requires manual setup (blank canvas problem)

**Quotes:**

- "I love Notion but it's not a CRM. I still need HubSpot + Stripe on top of it." — u/freelance_alex, r/freelance

### Stripe

**Sentiment:** Positive (best for payments, limited for invoicing)  
**Mentions:** 27

**Pros:**

- Easy payments
- Professional invoices

**Cons:**

- No client management (CRM)
- No project tracking

**Quotes:**

- "Stripe is great for payments but I still need a CRM to track clients." — u/consultant_lisa, r/solopreneurs

---

## Common Jargon & Language

**Frequent Phrases:**

- "Drowning in admin work" (mentioned 18 times)
- "Too many tools" (mentioned 34 times)
- "All-in-one solution" (mentioned 41 times)
- "Duct-taping tools together" (mentioned 12 times)

**Problem Descriptions:**

- "I'm great at my craft, but bad at the business side"
- "I spend more time on admin than actual work"
- "I just want to focus on [design/coding/consulting], not invoicing"

**Metaphors:**

- "Drowning" (admin work)
- "Juggling" (multiple tools)
- "Duct-taping" (makeshift solutions)

**Insight:** Use "drowning in admin" and "all-in-one" in marketing copy. Avoid "CRM" (too corporate), use "client tracker" instead.

---

## Workarounds

### Google Sheets for Invoicing

**Frequency:** 23 users  
**Tools Used:** Google Sheets, Excel, Airtable

**Quotes:**

- "I use a Google Sheet for invoicing. It's manual but free." — u/designer_emma, r/freelance
- "I built an Airtable base for invoicing. Works but takes forever to set up." — u/dev_jordan, r/solopreneurs

**Insight:** Many use spreadsheets (pain: manual, time-consuming). Opportunity: one-click invoicing.

### Notion + Stripe + HubSpot Stack

**Frequency:** 17 users  
**Tools Used:** Notion (notes), HubSpot (CRM), Stripe (invoicing)

**Quotes:**

- "My stack: Notion for projects, HubSpot for clients, Stripe for invoicing. It works but it's a lot." — u/consultant_mike, r/solopreneurs

**Insight:** Common stack, but users want to consolidate.

---

## Key Insights

**Top 3 Pain Points:**

1. **Tool overload** — Using 5-7 tools, constant context switching
2. **Time-consuming invoicing** — 30-45 minutes per invoice
3. **Cash flow unpredictability** — Late payments, no tracking

**Top 3 Opportunities:**

1. **All-in-one tool** — CRM + invoicing + project management in one place
2. **Simple CRM** — Built for solopreneurs, not enterprise sales teams
3. **Automated payment reminders** — Reduce late payments

**Competitive Gaps:**

- HubSpot: Too complex, built for teams
- Notion: No native CRM or invoicing
- Stripe: No client management

**Language to Use:**

- "All-in-one solution" (not "integrated platform")
- "Client tracker" (not "CRM")
- "Stop drowning in admin work" (emotional hook)
- "One tool, not seven" (clear value prop)

---

## Recommended Actions

1. **Product:** Build all-in-one tool with CRM + invoicing + project tracking
2. **Positioning:** "The only tool solopreneurs need" (vs. "best CRM")
3. **Messaging:** "Stop drowning in admin work. Manage clients, send invoices, and track projects in one place."
4. **Content:** Write about "How to escape tool overload" and "The solopreneur's tech stack"

---

## Sources

- r/solopreneurs: 28 threads
- r/freelance: 14 threads
- r/Entrepreneur: 5 threads

[Links to specific threads...]
```

## Integration Points

- **`/solo:research trends`**: Uses Reddit for trend detection
- **`exa-search-expert`**: Searches Reddit via `site:reddit.com` filter
- **`icp-creator`**: Reddit insights inform language patterns
- **`voice-dna-creator`**: Reddit language informs voice DNA

## Workflow Logic

### Trigger

- `/solo:research trends [topic]`
- "Research Reddit for [topic]"
- "What are people saying on Reddit about [topic]?"

### Process

1. **Identify subreddits** — Based on user's ICP and topic
2. **Search Reddit** — Use `~~search` tool with `site:reddit.com` filter
3. **Analyze threads** — Extract pain points, solutions, competitors, jargon, workarounds
4. **Synthesize insights** — Categorize and summarize findings
5. **Generate report** — Save to `data/3-Ressources/reddit-research-[date].md`

## Key References

- **`references/strategy.md`**: Subreddit selection guide
- **`references/analysis.md`**: Framework for analyzing Reddit discussions
- **`references/search-patterns.md`**: Keyword patterns for different research goals

## Tips

1. **Focus on pain, not praise** — Complaints are more valuable than compliments
2. **Look for patterns** — One mention is anecdotal, 10+ is a trend
3. **Capture exact language** — Use their words in your marketing
4. **Check comment threads** — Best insights are often in comments, not posts
5. **Sort by "Top" and "Controversial"** — Gets you the most passionate discussions
6. **Validate with interviews** — Reddit is a starting point, not ground truth
