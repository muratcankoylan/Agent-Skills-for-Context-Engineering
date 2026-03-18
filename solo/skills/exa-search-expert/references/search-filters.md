# Search Filters Reference

Complete guide to search filters for Exa, Tavily, and other semantic search tools.

---

## Date Filters

### Last 24 Hours

**Use for:** Breaking news, real-time signals, trending topics

**Example queries:**

- "What are people saying about [product launch] today?"
- "Latest news about [company]"
- "Breaking developments in [industry]"

**Best for:** Competitive intelligence, trend detection

---

### Last Week

**Use for:** Recent developments, fresh perspectives

**Example queries:**

- "New features launched by [competitor] this week"
- "Recent discussions about [topic]"

**Best for:** Weekly research updates, monitoring competitors

---

### Last Month

**Use for:** Current trends, recent case studies

**Example queries:**

- "Best practices for [topic] published recently"
- "New tools launched in [category]"

**Best for:** Content research, market trends

---

### Last 6 Months

**Use for:** Emerging patterns, validated trends

**Example queries:**

- "Emerging trends in [industry]"
- "How [practice] has evolved recently"

**Best for:** Strategic research, identifying patterns

---

### Last Year

**Use for:** Market shifts, annual trends

**Example queries:**

- "State of [industry] in 2026"
- "How [market] changed over the past year"

**Best for:** Annual planning, market analysis

---

### Last 2 Years

**Use for:** Evergreen content, comprehensive guides

**Example queries:**

- "Complete guide to [topic]"
- "Best resources for learning [skill]"

**Best for:** Educational content, how-to guides

---

## Domain Filters

### News Sites

**Domains:** techcrunch.com, theverge.com, venturebeat.com, arstechnica.com

**Use for:** Product launches, funding announcements, industry news

**Example:** "AI product launches" + domain:techcrunch.com

---

### Industry Blogs

**Domains:** saastr.com, lennysnewsletter.com, firstround.com, a16z.com

**Use for:** Best practices, case studies, thought leadership

**Example:** "Product-market fit strategies" + domain:lennysnewsletter.com

---

### Review Sites

**Domains:** g2.com, capterra.com, producthunt.com, trustpilot.com

**Use for:** Product reviews, user sentiment, feature comparisons

**Example:** "CRM for solopreneurs" + domain:g2.com

---

### Research Firms

**Domains:** gartner.com, forrester.com, cbinsights.com

**Use for:** Market size, industry reports, trend analysis

**Example:** "SaaS market size 2026" + domain:cbinsights.com

---

### Academic

**Domains:** arxiv.org, scholar.google.com, researchgate.net

**Use for:** Research papers, academic studies, technical deep-dives

**Example:** "Machine learning for search" + domain:arxiv.org

---

### Communities

**Domains:** reddit.com, indiehackers.com, hackernews.com

**Use for:** Unfiltered opinions, pain points, workarounds

**Example:** "solopreneur invoicing pain points" + site:reddit.com

---

## Content Type Filters

### Articles

**Type:** Blog posts, news articles, opinion pieces

**Use for:** General research, trend analysis, thought leadership

**Signals:** "published", "written by", "article"

---

### Guides

**Type:** How-tos, tutorials, comprehensive guides

**Use for:** Learning, implementation, best practices

**Signals:** "complete guide", "how to", "step-by-step", "tutorial"

---

### Reviews

**Type:** Product reviews, comparisons, ratings

**Use for:** Competitive analysis, user sentiment, feature discovery

**Signals:** "review", "vs", "comparison", "pros and cons"

---

### Reports

**Type:** Research reports, whitepapers, industry analysis

**Use for:** Market sizing, trend validation, strategic planning

**Signals:** "report", "whitepaper", "study", "research"

---

### Discussions

**Type:** Reddit threads, forum posts, Q&A

**Use for:** Pain points, workarounds, unfiltered feedback

**Signals:** "discussion", "thread", "comments", "replies"

---

### Code

**Type:** GitHub repos, Stack Overflow, documentation

**Use for:** Technical research, implementation examples, API docs

**Signals:** "github.com", "stackoverflow.com", "docs"

---

## Advanced Filter Combinations

### Market Research

```
Query: "solopreneur business tools market 2026"
Date: Last 6 months
Domain: cbinsights.com, techcrunch.com, saastr.com
Type: Reports, articles
```

### Competitive Analysis

```
Query: "HubSpot vs Pipedrive for solopreneurs"
Date: Last year
Domain: g2.com, capterra.com, reddit.com
Type: Reviews, discussions
```

### Pain Point Research

```
Query: "frustrated with invoicing" OR "hate invoicing"
Date: Last 6 months
Domain: reddit.com, indiehackers.com
Type: Discussions
```

### Content Ideas

```
Query: "best practices for [topic]"
Date: Last 2 years
Domain: lennysnewsletter.com, firstround.com
Type: Guides, articles
```

### Trend Detection

```
Query: "emerging trends in [industry]"
Date: Last 3 months
Domain: techcrunch.com, a16z.com, cbinsights.com
Type: Articles, reports
```

---

## Filter Syntax by Tool

### Exa

```
search(
  query="solopreneur CRM tools",
  num_results=20,
  start_published_date="2025-08-01",
  end_published_date="2026-02-01",
  include_domains=["g2.com", "capterra.com"],
  exclude_domains=["spam-site.com"]
)
```

### Tavily

```
search(
  query="solopreneur CRM tools",
  search_depth="advanced",
  max_results=20,
  include_domains=["g2.com", "capterra.com"],
  time_range="1m"  # 1 month
)
```

### Google (via site: operator)

```
"solopreneur CRM tools" site:g2.com after:2025-08-01
```

---

## Tips

1. **Combine filters** — Date + domain + type for precise results
2. **Start broad, then narrow** — Begin with no filters, then add as needed
3. **Use exclude filters** — Remove spam, irrelevant domains
4. **Test date ranges** — Fresh data for trends, evergreen for guides
5. **Domain quality matters** — Authoritative sources > random blogs
6. **Content type affects depth** — Guides are deeper than articles
