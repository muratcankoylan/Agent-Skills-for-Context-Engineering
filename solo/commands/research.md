---
description: "Research markets, competitors, prospects, and trends"
argument-hint: "[market | competitor | prospect | trends]"
allowed-tools: Read, Write, Search
model: sonnet
---

# /solo:research

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

Deep market intelligence for solopreneurs. Research markets, analyze competitors, investigate prospects, and track industry trends using web search and specialized research methodologies.

## Usage

```
/solo:research market [topic]        # Market sizing and landscape
/solo:research competitor [company]  # Competitive analysis
/solo:research prospect [company]    # Company deep-dive for sales
/solo:research trends [industry]     # Industry trends and signals
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                    RESEARCH INTELLIGENCE                          │
├──────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                        │
│  ✓ Web search: Exa-powered semantic search                       │
│  ✓ Reddit signals: Unmet needs, workarounds, jargon drift        │
│  ✓ Competitive intel: Product comparison, pricing, positioning   │
│  ✓ Company research: Org structure, tech stack, pain points      │
│  ✓ Trend analysis: Emerging patterns and opportunities           │
├──────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                       │
│  + ~~data enrichment: Clay, ZoomInfo for company data            │
│  + ~~knowledge base: Search internal research and notes          │
│  + ~~CRM: Pull existing prospect research                        │
└──────────────────────────────────────────────────────────────────┘
```

---

## /solo:research market

Understand market size, landscape, and opportunities.

### Usage

```
/solo:research market "solopreneur productivity tools"
/solo:research market "B2B SaaS for freelancers"
```

### What I'll Research

1. **Market Size (TAM/SAM/SOM)**
   - Total addressable market
   - Serviceable available market
   - Serviceable obtainable market

2. **Market Landscape**
   - Key players and market leaders
   - Emerging startups
   - Market segments

3. **Customer Pain Points**
   - Reddit discussions and complaints
   - Review site feedback
   - Forum conversations

4. **Market Trends**
   - Growing vs. declining segments
   - Technology shifts
   - Regulatory changes

### Output

```markdown
# Market Research: Solopreneur Productivity Tools

## Market Size

**TAM (Total Addressable Market):** $12B

- 59M solopreneurs globally (2024)
- Average spend: $200/year on productivity tools

**SAM (Serviceable Available Market):** $3.2B

- 16M solopreneurs in English-speaking markets
- Willing to pay for premium tools

**SOM (Serviceable Obtainable Market):** $15M

- Target: 0.5% market share in Year 1
- 75,000 users × $200 ARPU

## Market Landscape

### Leaders

- **Notion** — All-in-one workspace ($10B valuation)
- **Airtable** — Database + project management ($11B valuation)
- **Coda** — Docs + apps ($1.4B valuation)

### Emerging Players

- **Tana** — Outliner for knowledge workers (growing fast)
- **Capacities** — Object-based note-taking (early traction)

### Gaps & Opportunities

✓ Most tools are too complex for solopreneurs
✓ No tool combines CRM + invoicing + content planning
✓ Opportunity: Vertical SaaS for specific solopreneur niches

## Customer Pain Points (from Reddit)

Top complaints:

1. "Too many tools, too much context switching" (247 mentions)
2. "Notion is overkill for my simple business" (189 mentions)
3. "I need CRM + invoicing in one place" (156 mentions)
4. "Tired of duct-taping Stripe + Airtable + Notion" (134 mentions)

Unmet needs:

- Simple, opinionated tool for solopreneurs
- Built-in templates for common workflows
- Affordable ($10-20/mo, not $50+)

## Trends

📈 Growing:

- AI-powered automation
- No-code tools
- Vertical SaaS (niche-specific)

📉 Declining:

- Complex enterprise tools
- Self-hosted solutions

🔮 Emerging:

- AI agents for business tasks
- Voice-first interfaces
- Embedded finance (invoicing + payments)

## Recommendations

1. **Positioning:** "The only tool solopreneurs need" (all-in-one)
2. **Pricing:** $15-25/mo (sweet spot for this market)
3. **GTM:** Content marketing + Reddit community building
4. **Differentiation:** Opinionated workflows vs. blank canvas

Sources: 47 web pages, 12 Reddit threads, 8 review sites
```

---

## /solo:research competitor

Analyze a competitor's product, pricing, and positioning.

### Usage

```
/solo:research competitor "Notion"
/solo:research competitor "https://airtable.com"
```

### What I'll Research

1. **Product Analysis**
   - Core features
   - Unique capabilities
   - User experience

2. **Pricing Strategy**
   - Pricing tiers
   - Feature gating
   - Discounts and promotions

3. **Positioning & Messaging**
   - Value proposition
   - Target audience
   - Key differentiators

4. **Customer Sentiment**
   - Review site ratings
   - Common complaints
   - Praise points

### Output

```markdown
# Competitive Analysis: Notion

## Product Overview

**Category:** All-in-one workspace  
**Founded:** 2016  
**Valuation:** $10B (2021)  
**Users:** 30M+ (2024)

**Core Features:**

- Docs, wikis, databases
- Project management
- Collaboration tools
- AI writing assistant (2023)

**Unique Capabilities:**

- Flexible block-based editor
- Relational databases
- Template marketplace
- API + integrations

## Pricing

| Tier       | Price       | Target      | Key Features                            |
| ---------- | ----------- | ----------- | --------------------------------------- |
| Free       | $0          | Individuals | Unlimited pages, 10 guests              |
| Plus       | $10/user/mo | Small teams | Unlimited file uploads, version history |
| Business   | $18/user/mo | Companies   | Advanced permissions, SAML SSO          |
| Enterprise | Custom      | Large orgs  | Dedicated support, advanced security    |

**Pricing Strategy:**

- Freemium model (generous free tier)
- Per-user pricing (scales with team size)
- Annual discount: 20% off

## Positioning

**Value Prop:** "One workspace. Every team."

**Target Audience:**

- Primary: Knowledge workers, startups, small teams
- Secondary: Students, creators, personal use

**Key Differentiators:**

- Flexibility (blank canvas approach)
- Beautiful design
- Strong community + templates

## Customer Sentiment

**Ratings:**

- G2: 4.7/5 (4,500+ reviews)
- Capterra: 4.8/5 (1,800+ reviews)

**Top Praise:**

- "Incredibly flexible"
- "Beautiful and intuitive"
- "Great for personal knowledge management"

**Top Complaints:**

- "Too complex for simple use cases" (⭐ Opportunity)
- "Performance issues with large databases"
- "Steep learning curve for new users" (⭐ Opportunity)
- "Missing native CRM features" (⭐ Opportunity)

## Competitive Gaps

Where Notion is weak (your opportunities):

1. **Simplicity:** Too flexible = overwhelming for solopreneurs
2. **Opinionated workflows:** No built-in CRM, invoicing, or sales pipeline
3. **Onboarding:** Blank canvas is intimidating
4. **Performance:** Slow with large workspaces

## Differentiation Strategy

How to compete:

- **Positioning:** "Notion for solopreneurs" (vertical focus)
- **Product:** Opinionated templates vs. blank canvas
- **Pricing:** Simpler pricing (flat $20/mo vs. per-user)
- **Features:** Built-in CRM + invoicing (Notion requires integrations)

Sources: Notion website, G2 reviews, Reddit discussions, competitor comparison sites
```

---

## /solo:research prospect

Deep-dive research on a company before a sales call.

### Usage

```
/solo:research prospect "Acme Corp"
/solo:research prospect "https://acmecorp.com"
```

### What I'll Research

1. **Company Overview**
   - Industry, size, location
   - Funding and growth stage
   - Recent news and announcements

2. **Key People**
   - Leadership team
   - Decision makers
   - LinkedIn profiles

3. **Tech Stack**
   - Tools they use
   - Integrations
   - Technical sophistication

4. **Pain Points & Opportunities**
   - Hiring signals
   - Recent product launches
   - Challenges mentioned in press

### Output

```markdown
# Prospect Research: Acme Corp

## Company Overview

**Industry:** B2B SaaS (Marketing Automation)  
**Size:** 50-100 employees  
**Location:** San Francisco, CA  
**Founded:** 2019  
**Funding:** Series A ($12M, 2022)

**Recent News:**

- Launched new AI features (Jan 2026)
- Hiring for VP of Product (posted 2 weeks ago)
- Featured in TechCrunch (Dec 2025)

## Key People

**Decision Makers:**

- **Sarah Chen** — VP of Product (your contact)
  - LinkedIn: 500+ connections, active poster
  - Background: Ex-Google PM, Stanford MBA
  - Interests: AI, product-led growth

- **Michael Rodriguez** — CEO
  - LinkedIn: 2,000+ connections
  - Background: Serial entrepreneur (2 exits)
  - Active on Twitter, posts about scaling startups

- **Emily Patel** — Head of Engineering
  - LinkedIn: 300+ connections
  - Background: Ex-Stripe engineer
  - Tech-focused, values clean code

## Tech Stack

**Tools Detected:**

- **CRM:** HubSpot
- **Analytics:** Mixpanel, Google Analytics
- **Hosting:** AWS
- **Payments:** Stripe
- **Communication:** Slack, Zoom

**Technical Sophistication:** High

- Modern stack (React, Node.js, PostgreSQL)
- API-first architecture
- Strong engineering culture

## Pain Points & Opportunities

**Hiring Signals:**

- VP of Product role (suggests product expansion)
- 3 engineering roles (scaling team)
- Customer Success Manager (growing customer base)

**Recent Challenges:**

- TechCrunch article mentioned "scaling pains"
- Glassdoor reviews cite "rapid growth chaos"
- LinkedIn posts from CEO about "building for scale"

**Opportunities for Your Services:**

1. **Website Redesign:** Current site is outdated (last update: 2023)
2. **Product Design:** Hiring VP of Product = new features coming
3. **Design System:** Fast growth = need for consistency

## Recommended Approach

**Opening Hook:**
"I saw you're hiring a VP of Product and scaling fast. I've helped 3 Series A startups redesign their product experience during hypergrowth..."

**Pain Point to Address:**
Scaling chaos + need for design consistency

**Social Proof:**
Mention similar companies you've worked with (B2B SaaS, Series A stage)

**Next Steps:**

1. Connect with Sarah on LinkedIn
2. Reference the VP of Product hire in your outreach
3. Offer a free design audit of their current product

Sources: Company website, LinkedIn, Crunchbase, BuiltWith, Glassdoor
```

---

## /solo:research trends

Track industry trends and emerging opportunities.

### Usage

```
/solo:research trends "AI tools for solopreneurs"
/solo:research trends "B2B SaaS"
```

### Output

```markdown
# Trend Analysis: AI Tools for Solopreneurs

## Emerging Trends (Next 6-12 months)

### 1. AI Agents for Business Tasks

**Strength:** 🔥🔥🔥🔥 (Very Hot)

- **What:** AI that handles entire workflows (not just suggestions)
- **Examples:** Auto-generate invoices, draft proposals, schedule meetings
- **Market Signal:** 347% increase in "AI agent" searches (last 3 months)
- **Opportunity:** Build vertical AI agents for specific solopreneur tasks

### 2. Embedded Finance

**Strength:** 🔥🔥🔥 (Hot)

- **What:** Invoicing + payments built into productivity tools
- **Examples:** Notion + Stripe, Airtable + payments
- **Market Signal:** Stripe Embedded Checkout growing 200% YoY
- **Opportunity:** Add native invoicing to solopreneur tools

### 3. Voice-First Interfaces

**Strength:** 🔥🔥 (Warming)

- **What:** Voice commands for business tasks
- **Examples:** "Create invoice for Acme Corp", "Schedule content for next week"
- **Market Signal:** Early adopters, not mainstream yet
- **Opportunity:** Voice layer on top of existing tools

## Declining Trends

### 1. Complex No-Code Builders

**Strength:** ❄️ (Cooling)

- **Why:** Too much flexibility = decision paralysis
- **Shift:** Moving toward opinionated, vertical tools
- **Implication:** Solopreneurs want "done for you" not "build it yourself"

### 2. Self-Hosted Solutions

**Strength:** ❄️❄️ (Cold)

- **Why:** Too much maintenance overhead
- **Shift:** Cloud-first, managed services
- **Implication:** SaaS wins for solopreneurs

## Reddit Signals (Unmet Needs)

**Top Frustrations:**

1. "I need an AI that actually does the work, not just suggests" (289 upvotes)
2. "Why isn't there a Stripe for solopreneurs?" (234 upvotes)
3. "Tired of switching between 10 tools" (198 upvotes)

**Emerging Jargon:**

- "AI co-pilot" → "AI employee" (shift from assistant to autonomous)
- "No-code" → "Pre-built" (shift from flexibility to opinionated)
- "All-in-one" → "Operating system" (shift from tool to platform)

## Recommendations

**Build:**

- AI agents for specific solopreneur workflows
- Embedded invoicing + payments
- Opinionated templates (not blank canvas)

**Avoid:**

- Complex builders requiring setup
- Self-hosted solutions
- Generic productivity tools

**Watch:**

- Voice interfaces (early but promising)
- AI-generated content (getting commoditized)

Sources: Reddit, Twitter, Google Trends, Product Hunt, TechCrunch
```

---

## Agent Instructions

```python
# /solo:research market
def research_market(topic):
    # 1. Market sizing
    tam_sam_som = calculate_market_size(topic)

    # 2. Landscape research
    leaders = search_web(f"{topic} market leaders")
    startups = search_web(f"{topic} startups")

    # 3. Pain points (Reddit)
    reddit_threads = invoke_skill("reddit-research-insights", query=topic)

    # 4. Trends
    trends = search_web(f"{topic} trends 2026")

    # 5. Compile report
    return format_market_report(tam_sam_som, leaders, startups, reddit_threads, trends)

# /solo:research competitor
def research_competitor(company):
    # 1. Company overview
    overview = search_web(f"{company} about")

    # 2. Pricing
    pricing = scrape_pricing_page(company)

    # 3. Reviews
    reviews = search_web(f"{company} reviews G2 Capterra")

    # 4. Positioning
    messaging = analyze_website_copy(company)

    # 5. Gaps
    complaints = extract_top_complaints(reviews)
    opportunities = identify_gaps(complaints)

    return format_competitor_report(overview, pricing, reviews, messaging, opportunities)

# /solo:research prospect
def research_prospect(company):
    # 1. Company data
    company_data = search_web(f"{company} about funding team")

    # 2. Key people
    decision_makers = search_linkedin(f"{company} VP Product CEO")

    # 3. Tech stack
    tech_stack = invoke_skill("company-research", company=company)

    # 4. Signals
    hiring = search_web(f"{company} jobs hiring")
    news = search_web(f"{company} news announcements")

    # 5. Recommended approach
    approach = generate_outreach_strategy(company_data, decision_makers, hiring, news)

    return format_prospect_report(company_data, decision_makers, tech_stack, hiring, news, approach)
```

---

## Tips

1. **Research before outreach** — 15 minutes of research saves hours of bad pitches
2. **Use Reddit for real pain points** — Review sites are filtered, Reddit is raw
3. **Track competitor changes** — Re-research quarterly to spot shifts
4. **Save research** — Store reports in `data/3-Ressources/research/` for reference

---

## Skills Used

- `exa-search-expert` — Semantic web search
- `reddit-research-insights` — Reddit signal detection
- `company-research` — Company deep-dives
- `pestel-analysis` — Macro trend analysis
