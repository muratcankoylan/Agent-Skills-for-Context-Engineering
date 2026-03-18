---
name: company-research
description: >
  Performs deep-dive research on a company or prospect. Generates structured findings
  that feed draft-outreach and proposal-generator. Triggers on "research this company",
  "tell me about [company]", or "look up [company]".
version: 1.0.0
bundle: sales-growth
triggers:
  - "research company"
  - "company intel"
  - "research [company]"
tools:
  standalone: ["exa"]
  supercharged: ["exa", "linkedin"]
---

# Skill: Company Research

Aggregates information about a target company from multiple sources and produces a structured research report that downstream skills (draft-outreach, proposal-generator, discovery-call) can consume directly.

## Research Process

### Step 1: Identify the Target
- Company name, URL, or description
- Optional focus: specific questions the user wants answered

### Step 2: Search Strategy

Run searches in this order, adapting to available tools:

| Source | Standalone Query | Supercharged Tool | What to Look For |
|--------|-----------------|-------------------|------------------|
| Company website | `site:[domain]` | ~~search | About page, team, pricing, blog |
| News & press | `"[company]" news OR announcement OR funding` | ~~search | Funding rounds, product launches, partnerships |
| Job postings | `"[company]" careers OR hiring` | ~~search | Tech stack, team growth, priorities |
| Social presence | `"[company]" linkedin OR twitter` | ~~social | Content strategy, thought leadership, engagement |
| Reviews & reputation | `"[company]" review OR comparison` | ~~search | Customer sentiment, competitive positioning |
| Firmographics | — | ~~data enrichment | Employee count, revenue, industry, location |
| People | — | ~~data enrichment | Key contacts, decision makers, titles |

### Step 3: Analyze and Structure

For each company, build a complete profile covering:

**Company Overview**
- One-liner description
- Industry and sub-industry
- Founded / HQ location
- Company size (employees, revenue if public)
- Funding stage and total raised (if startup)
- Business model (B2B, B2C, marketplace, SaaS)

**Key People**
- CEO / Founder
- Relevant decision makers (for your service)
- LinkedIn profiles if available

**Products & Services**
- What they sell
- Target market
- Pricing model (if public)
- Tech stack (from job postings, BuiltWith, Wappalyzer)

**Recent Activity (last 6 months)**
- News, press releases, blog posts
- Product launches or updates
- Hiring trends (scaling up/down? Which teams?)
- Social media activity and content themes

**Pain Signals**
- Problems they're likely facing based on their stage and industry
- Gaps in their current offering
- Competitor pressure
- Hiring for roles that suggest internal challenges (e.g., hiring a "Head of Customer Success" = churn problem)

**ICP Fit Score**
Compare against your `icp.json`. Score 1-5 on:
- Industry match
- Company size match
- Problem alignment
- Budget likelihood
- Decision-maker accessibility

### Step 4: Save Output

Save to `data/3-Ressources/[company-slug].md` using the template in `references/research-findings-template.md`.

## Downstream Consumers

This output is designed to be consumed by:
- **`draft-outreach`**: Reads pain signals and key people for personalized messaging
- **`proposal-generator`**: Reads company context and pain signals for tailored proposals
- **`discovery-call`**: Reads company snapshot for pre-call briefing
- **`client-management`**: Reads firmographics for client card creation

## Key References

- **`references/research-findings-template.md`**: Standardized output template
