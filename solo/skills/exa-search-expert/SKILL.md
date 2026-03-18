---
name: exa-search-expert
description: >
  Advanced semantic search for market research, competitor analysis, and content discovery.
  Uses neural search with Exa/Tavily for better-than-Google results. Triggers on "research",
  "search for", "find companies", or "market intelligence".
version: 1.0.0
bundle: sales-growth
triggers:
  - "deep search"
  - "semantic search"
  - "research with Exa"
tools:
  standalone: ["exa"]
  supercharged: ["exa"]
---

# Skill: Advanced Search Expert (Exa/Tavily)

Performs semantic, neural-powered search for market research, competitor analysis, company discovery, and content intelligence. Goes beyond keyword matching to understand intent and context.

## When to Use

- Market research and competitive analysis
- Finding companies matching specific criteria
- Discovering content on niche topics
- Technical research (code, documentation)
- Trend analysis and signal detection

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Neural search with ~~search connector (Exa, Tavily, etc.)   │
│  ✓ Semantic understanding (intent, not just keywords)          │
│  ✓ Explore → Expand → Extract research workflow                │
│  ✓ Content filtering (date, domain, type)                      │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when ~~search supports advanced features)       │
│  + Deep research agents (full-topic synthesis)                 │
│  + "Find similar" content discovery                            │
│  + Full-text extraction and crawling                           │
│  + Auto-highlight key passages                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Search Workflow: Explore → Expand → Extract

### 1. Explore (Broad Discovery)

Start with a broad, semantic search to understand the landscape.

**Example Query:**

```
"What are the most innovative AI-powered tools that help sales teams
improve outbound prospecting?"
```

**Not:** "AI sales tools" (too generic, keyword-based)

**Output:** 10-20 relevant results with snippets and URLs

### 2. Expand (Related Content)

Use "find similar" to discover related content and broaden research.

**Example:**

```
Find similar to: [URL of best result from Explore phase]
```

**Output:** 10-20 related articles, tools, or companies

### 3. Extract (Deep Dive)

For high-value URLs, extract full content for detailed analysis.

**Example:**

```
Extract full text from: [URL]
```

**Output:** Complete article text, structured data, key passages highlighted

## Neural Search Best Practices

### ✅ Good Queries (Semantic, Intent-Based)

**Market Research:**

- "What are the biggest pain points for solopreneurs managing client relationships?"
- "How are B2B SaaS companies using AI to improve customer onboarding?"

**Competitor Analysis:**

- "What features do the top project management tools for freelancers offer?"
- "How do successful solopreneur productivity tools differentiate themselves?"

**Company Discovery:**

- "Which Series A SaaS companies are hiring aggressively in product and design?"
- "What e-commerce brands doing $1M-10M ARR are using Shopify Plus?"

**Trend Analysis:**

- "What are the emerging trends in AI-powered content creation for 2026?"
- "How is the solopreneur market evolving based on recent funding and launches?"

### ❌ Bad Queries (Keyword-Based, Vague)

- "AI tools" (too broad)
- "best CRM" (no context)
- "productivity hacks" (generic)
- "startup funding" (what about it?)

### Query Formulation Framework

| Element        | Purpose                     | Example                                  |
| -------------- | --------------------------- | ---------------------------------------- |
| **Context**    | Who/what is this for?       | "For solopreneurs..."                    |
| **Action**     | What are they trying to do? | "...managing client relationships..."    |
| **Constraint** | Any specific requirements?  | "...without complex CRM software"        |
| **Outcome**    | What's the goal?            | "...to save time and increase retention" |

**Full Query:**
"What are the best tools for solopreneurs managing client relationships without complex CRM software, focused on saving time and increasing retention?"

## Search Types

### 1. Market Research

**Goal:** Understand market size, trends, and opportunities

**Query Pattern:**

```
"What is the current state of [market] in [year]? Include market size,
key players, emerging trends, and growth opportunities."
```

**Example:**

```
"What is the current state of the solopreneur productivity tools market
in 2026? Include market size, key players, emerging trends, and growth
opportunities."
```

**Filters:**

- Date: Last 12 months (for fresh data)
- Domain: Industry publications, research firms
- Type: Articles, reports, case studies

### 2. Competitor Analysis

**Goal:** Identify competitors and analyze their positioning

**Query Pattern:**

```
"What are the top [category] tools for [audience]? Compare features,
pricing, and customer reviews."
```

**Example:**

```
"What are the top CRM tools for solopreneurs and freelancers? Compare
features, pricing, and customer reviews."
```

**Filters:**

- Date: Last 6 months
- Domain: Review sites (G2, Capterra), product blogs
- Type: Comparisons, reviews, case studies

### 3. Company Discovery

**Goal:** Find companies matching specific criteria

**Query Pattern:**

```
"Which [type] companies [criteria] are [signal]?"
```

**Example:**

```
"Which Series A B2B SaaS companies with 20-100 employees are hiring
for product and design roles?"
```

**Filters:**

- Date: Last 3 months (for fresh signals)
- Domain: Job boards, company blogs, news sites
- Type: Job postings, announcements, press releases

### 4. Content Discovery

**Goal:** Find high-quality content on a specific topic

**Query Pattern:**

```
"What are the best [content type] about [topic] for [audience]?"
```

**Example:**

```
"What are the best in-depth guides about value-based pricing for
solopreneurs and consultants?"
```

**Filters:**

- Date: Last 24 months (evergreen content)
- Domain: Authority sites, expert blogs
- Type: Guides, tutorials, case studies

### 5. Trend Analysis

**Goal:** Identify emerging patterns and opportunities

**Query Pattern:**

```
"What are the emerging trends in [industry/topic] based on recent
[signals]?"
```

**Example:**

```
"What are the emerging trends in AI-powered productivity tools based
on recent product launches and funding announcements?"
```

**Filters:**

- Date: Last 6 months
- Domain: Tech news, industry blogs, funding databases
- Type: News, announcements, analysis

## Advanced Features

### Find Similar

Discover related content based on a seed URL.

**Use Case:** You found a great article and want more like it.

**Example:**

```
Find similar to: https://example.com/great-article
```

**Output:** 10-20 semantically similar articles

### Deep Research Agent

Launch an autonomous research agent for comprehensive topic synthesis.

**Use Case:** You need a complete report on a complex topic.

**Example:**

```
Deep research: "Complete analysis of the solopreneur CRM market including
market size, key players, customer pain points, pricing models, and
emerging opportunities"
```

**Output:** Multi-page research report with citations

### Content Extraction

Extract full text from URLs for detailed analysis.

**Use Case:** You found a valuable article behind a paywall or want clean text.

**Example:**

```
Extract content from: https://example.com/article
```

**Output:** Clean, structured text with key passages highlighted

## Search Filters

### Date Filters

- **Last 24 hours:** Breaking news, real-time signals
- **Last week:** Recent developments
- **Last month:** Current trends
- **Last 6 months:** Emerging patterns
- **Last year:** Market shifts
- **Last 2 years:** Evergreen content

### Domain Filters

- **News sites:** TechCrunch, VentureBeat, The Verge
- **Industry blogs:** SaaStr, Lenny's Newsletter, First Round Review
- **Review sites:** G2, Capterra, Product Hunt
- **Research firms:** Gartner, Forrester, CB Insights
- **Academic:** ArXiv, Google Scholar, research papers

### Content Type Filters

- **Articles:** Blog posts, news articles
- **Guides:** How-tos, tutorials, comprehensive guides
- **Reviews:** Product reviews, comparisons
- **Reports:** Research reports, whitepapers
- **Discussions:** Reddit, forums, Q&A sites
- **Code:** GitHub, Stack Overflow, documentation

## Integration Points

- **`/solo:research`**: Primary command using this skill
- **`company-research`**: Uses search for company intelligence
- **`reddit-research-insights`**: Combines with Reddit for cultural signals
- **`content-calendar-planner`**: Discovers content ideas

## Example Outputs

### Market Research Example

**Query:**

```
"What are the biggest pain points for solopreneurs managing finances
and invoicing in 2026?"
```

**Results:**

```
1. "The Hidden Cost of Manual Invoicing for Freelancers" (Jan 2026)
   Source: Freelancer's Union Blog
   Key insight: 40% of solopreneurs spend 5+ hours/month on invoicing

2. "Why Solopreneurs Are Ditching QuickBooks" (Dec 2025)
   Source: SaaStr
   Key insight: Complexity and cost driving shift to simpler tools

3. "The State of Solopreneur Finances 2026" (Nov 2025)
   Source: FreshBooks Research
   Key insight: 60% struggle with cash flow forecasting

[15 more results...]

Summary:
- Top pain: Time spent on manual invoicing (40% spend 5+ hours/month)
- Emerging need: Simple, affordable invoicing + payments in one tool
- Market gap: No tool combines invoicing, expenses, and cash flow forecasting
- Opportunity: Build vertical SaaS for solopreneur finance management
```

### Competitor Analysis Example

**Query:**

```
"What are the top CRM tools for solopreneurs? Compare features, pricing,
and customer sentiment."
```

**Results:**

```
Top 5 CRM Tools for Solopreneurs:

1. HubSpot (Free CRM)
   - Features: Contact management, email tracking, basic pipeline
   - Pricing: Free (upsells to $45/mo for advanced features)
   - Sentiment: "Great free tier, but upsells are expensive" (G2: 4.4/5)

2. Pipedrive
   - Features: Visual pipeline, email integration, automation
   - Pricing: $14/user/mo
   - Sentiment: "Simple and effective, but lacks invoicing" (G2: 4.2/5)

3. Streak (Gmail CRM)
   - Features: Lives in Gmail, email tracking, pipeline
   - Pricing: Free (Pro: $49/user/mo)
   - Sentiment: "Perfect for Gmail users, limited outside Gmail" (G2: 4.5/5)

[2 more competitors...]

Gaps & Opportunities:
- No tool combines CRM + invoicing + proposals
- Most are too complex for solopreneurs (built for teams)
- Pricing is per-user (doesn't make sense for solopreneurs)
```

## Key References

- **`references/prompting-best-practices.md`**: Query formulation guide
- **`references/search-filters.md`**: Complete filter reference
- **`references/use-cases.md`**: 50+ example queries by use case

## Tips

1. **Be specific** — "AI tools for solopreneur content creation" not "AI tools"
2. **Use full sentences** — Neural search understands intent, not just keywords
3. **Add context** — Who, what, why, and constraints
4. **Filter by date** — Fresh data for trends, evergreen for guides
5. **Iterate** — Start broad (Explore), then narrow (Expand), then deep-dive (Extract)
6. **Combine with Reddit** — Use `reddit-research-insights` for unfiltered user pain points
