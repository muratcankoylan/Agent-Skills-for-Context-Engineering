---
name: icp-creator
description: >
  Create detailed Ideal Client Profile (ICP) through guided interview or CRM analysis.
  Captures demographics, psychographics, pain points, and language patterns. Triggers
  on "create ICP", "define target audience", or "ideal client profile".
version: 1.0.0
bundle: core-identity
triggers:
  - "create ICP"
  - "define my ideal client"
  - "who is my target customer"
tools:
  standalone: ["filesystem"]
  supercharged: ["exa"]
---

# Skill: Ideal Client Profile (ICP) Creator

Creates comprehensive Ideal Client Profiles through a guided 7-phase interview or by analyzing existing customer data. Captures demographics, psychographics, pain points, goals, and language patterns for precise targeting.

## When to Use

- Defining your target audience for the first time
- Refining your positioning and messaging
- Before creating content or marketing campaigns
- Analyzing your best customers to find patterns
- Aligning team on who you're selling to

## ICP vs. Persona

| Aspect       | ICP (Ideal Client Profile)                         | Persona                                          |
| ------------ | -------------------------------------------------- | ------------------------------------------------ |
| **Focus**    | Company/client characteristics                     | Individual user characteristics                  |
| **Use Case** | Sales, marketing, positioning                      | Product design, UX, content                      |
| **Level**    | Account-level (B2B) or segment-level (B2C)         | Individual-level                                 |
| **Example**  | "Series A B2B SaaS, 20-100 employees, $2M-10M ARR" | "Sarah, 35, Freelance Designer, works from home" |

**For solopreneurs:** ICP and persona often overlap (you're selling to individuals, not companies).

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Guided 7-phase interview to define ideal client             │
│  ✓ Covers demographics, psychographics, pain points, goals     │
│  ✓ Saves icp.json to data/2-Domaines/                          │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~CRM)                                   │
│  + Analyze existing customer data from HubSpot/CRM             │
│  + Pattern detection across demographics and interactions      │
│  + Data-driven ICP draft based on your best clients            │
└─────────────────────────────────────────────────────────────────┘
```

## 7-Phase Interview Process

### Phase 1: Demographics

**Questions:**

- What's their age range?
- Where do they live? (City, region, country)
- What's their income level? (If relevant)
- Education level?

**Example Answers:**

- Age: 30-40
- Location: Major US cities (SF, NYC, Austin, Denver)
- Income: $80K-150K/year
- Education: Bachelor's degree or self-taught

### Phase 2: Professional Profile

**Questions:**

- What's their job title?
- What industry do they work in?
- Company size? (Solopreneur, 1-10, 10-50, 50-200, 200+)
- Years of experience?

**Example Answers:**

- Job title: Freelance Designer, Design Consultant
- Industry: B2B SaaS, Tech startups
- Company size: Solopreneur (just them)
- Experience: 5-10 years

### Phase 3: Psychographics

**Questions:**

- What do they value? (Freedom, security, recognition, impact, etc.)
- What are their beliefs about work/life?
- Personality traits? (Analytical, creative, risk-taker, cautious, etc.)
- Motivations? (Money, status, autonomy, mastery, etc.)

**Example Answers:**

- Values: Autonomy, work-life balance, financial security
- Beliefs: "I can build a great business without hiring"
- Personality: Self-motivated, detail-oriented, slightly introverted
- Motivations: Freedom to choose projects, financial independence

### Phase 4: Problems & Pain Points

**Questions:**

- What are their top 3 frustrations?
- What keeps them up at night?
- What problems are they actively trying to solve?
- What have they tried that didn't work?

**Example Answers:**

- Top frustrations:
  1. Time spent on admin (invoicing, proposals, follow-ups)
  2. Cash flow unpredictability (late payments)
  3. Tool overload (7+ different tools)
- Keeps them up: "Am I charging enough? Will I have enough work next month?"
- Trying to solve: Streamline business operations without hiring
- Tried: Complex CRMs (too much), spreadsheets (too manual)

### Phase 5: Goals & Desires

**Questions:**

- What are their short-term goals? (Next 6-12 months)
- What are their long-term goals? (Next 3-5 years)
- What does success look like for them?
- What are they aspiring to become?

**Example Answers:**

- Short-term: Hit $150K/year revenue, work 40 hours/week (not 50+)
- Long-term: Build a $500K-1M/year business, take 4 weeks vacation/year
- Success: Financial security + time freedom + recognized expertise
- Aspiring to: Be like Justin Welsh or Pieter Levels (successful solopreneurs)

### Phase 6: Language Patterns

**Questions:**

- What words or phrases do they use frequently?
- What questions do they ask?
- What jargon or terminology do they use?
- How do they describe their problems?

**Example Answers:**

- Frequent words: "Streamline", "automate", "all-in-one", "simple"
- Questions: "How do I scale without hiring?", "What's the best tool for X?"
- Jargon: "Productized service", "retainer clients", "MRR" (monthly recurring revenue)
- Problem description: "I'm drowning in admin work" or "Too many tools, not enough time"

### Phase 7: Content & Buying Behavior

**Questions:**

- Where do they hang out online? (Platforms, communities, forums)
- What content do they consume? (Blogs, podcasts, videos, newsletters)
- How do they make buying decisions? (Research, trials, recommendations)
- What triggers a purchase? (Pain threshold, budget availability, trust)

**Example Answers:**

- Hangouts: Reddit (r/solopreneurs), Twitter, indie hacker communities, Slack groups
- Content: YouTube tutorials, indie hacker blogs, solopreneur newsletters
- Buying: Tries free trials, reads reviews (G2, Capterra), asks for recommendations
- Purchase triggers: Pain becomes unbearable, sees ROI clearly, trusts the brand

## ICP Output Format (JSON)

```json
{
  "icp_name": "Solopreneur Designer",
  "created": "2026-02-13",
  "last_updated": "2026-02-13",
  "demographics": {
    "age_range": "30-40",
    "location": ["San Francisco", "New York", "Austin", "Denver"],
    "income": "$80K-150K/year",
    "education": "Bachelor's degree or self-taught"
  },
  "professional_profile": {
    "job_titles": ["Freelance Designer", "Design Consultant", "UX Designer"],
    "industries": ["B2B SaaS", "Tech Startups", "E-commerce"],
    "company_size": "Solopreneur",
    "years_experience": "5-10 years"
  },
  "psychographics": {
    "values": ["Autonomy", "Work-life balance", "Financial security"],
    "beliefs": [
      "I can build a great business without hiring",
      "Quality over quantity"
    ],
    "personality_traits": ["Self-motivated", "Detail-oriented", "Introverted"],
    "motivations": [
      "Freedom to choose projects",
      "Financial independence",
      "Recognized expertise"
    ]
  },
  "pain_points": [
    {
      "pain": "Time spent on admin",
      "description": "10-15 hours/week on invoicing, proposals, follow-ups instead of billable work",
      "severity": "High"
    },
    {
      "pain": "Cash flow unpredictability",
      "description": "Clients pay 15-45 days late, making financial planning difficult",
      "severity": "High"
    },
    {
      "pain": "Tool overload",
      "description": "Uses 7+ different tools, constant context switching kills productivity",
      "severity": "Medium"
    }
  ],
  "goals": {
    "short_term": [
      "Hit $150K/year revenue",
      "Work 40 hours/week (not 50+)",
      "Take 2 weeks vacation"
    ],
    "long_term": [
      "Build a $500K-1M/year business",
      "Work 30 hours/week",
      "Take 4 weeks vacation/year"
    ],
    "success_definition": "Financial security + time freedom + recognized expertise"
  },
  "language_patterns": {
    "frequent_words": [
      "Streamline",
      "Automate",
      "All-in-one",
      "Simple",
      "Efficient"
    ],
    "common_questions": [
      "How do I scale without hiring?",
      "What's the best tool for X?",
      "How much should I charge?"
    ],
    "jargon": [
      "Productized service",
      "Retainer clients",
      "MRR",
      "Value-based pricing"
    ],
    "problem_descriptions": [
      "I'm drowning in admin work",
      "Too many tools, not enough time",
      "I'm great at my craft, but bad at business"
    ]
  },
  "content_behavior": {
    "online_hangouts": [
      "Reddit (r/solopreneurs)",
      "Twitter",
      "Indie Hackers",
      "Slack communities"
    ],
    "content_consumed": [
      "YouTube tutorials",
      "Indie hacker blogs",
      "Solopreneur newsletters",
      "Podcasts"
    ],
    "buying_process": [
      "Tries free trials",
      "Reads reviews (G2, Capterra)",
      "Asks for recommendations"
    ],
    "purchase_triggers": [
      "Pain becomes unbearable",
      "Clear ROI",
      "Trust in brand"
    ]
  }
}
```

## Using the ICP

### For Content Creation

- **Voice DNA:** Use language patterns to match their vocabulary
- **Pain-focused content:** Address top pain points in blog posts, social media
- **Aspirational content:** Show how to achieve their goals

**Example:**

> "Tired of spending 10+ hours/week on admin? Here's how to streamline your solopreneur business in 30 minutes." (Uses their language: "streamline", "solopreneur")

### For Positioning

- **Target the right audience:** Focus on solopreneurs, not agencies or teams
- **Speak to their pains:** "Stop drowning in admin work"
- **Show the outcome:** "Work 40 hours/week, not 50+"

**Example Positioning:**

> "The all-in-one business tool for solopreneurs who want to focus on their craft, not admin work."

### For Product Development

- **Solve their top pains:** Invoicing, cash flow, tool overload
- **Match their goals:** Help them hit $150K/year, work less, take more vacation
- **Design for their behavior:** Free trials, simple onboarding, integrations with tools they use

### For Sales & Marketing

- **Find them:** Reddit, Twitter, indie hacker communities
- **Speak their language:** Use their jargon and problem descriptions
- **Trigger purchases:** Show clear ROI, build trust, offer free trials

## Supercharged Mode (CRM Analysis)

If you have a CRM connected (HubSpot, Pipedrive, etc.), the ICP Creator can analyze your existing customers to find patterns.

### What It Analyzes

- **Demographics:** Age, location, income (from contact properties)
- **Professional:** Job titles, industries, company sizes
- **Behavior:** Email open rates, content engagement, purchase history
- **Revenue:** Which customer segments are most profitable?

### Output

A data-driven ICP draft based on your best customers (highest revenue, longest retention, most engaged).

**Example:**

> "Your top 20% of customers are: Freelance designers, 30-40 years old, located in major US cities, earning $100K-150K/year. They engage most with content about invoicing and client management."

## Integration Points

- **`voice-dna-creator`**: ICP language patterns inform voice DNA
- **`/solo:write`**: ICP guides content creation and messaging
- **`proto-persona`**: ICP informs persona creation
- **`/solo:prospect`**: ICP helps identify and target prospects

## Workflow Logic

### Trigger

- `/solo:start` (onboarding)
- "Create ICP"
- "Define my target audience"
- "Who is my ideal client?"

### Process

**Standalone Mode:**

1. Ask user if they want guided interview or CRM analysis
2. If interview: Run 7-phase interview (one phase at a time)
3. Collect answers and synthesize into ICP JSON
4. Save to `data/2-Domaines/icp.json`
5. Show summary and confirm save

**Supercharged Mode:**

1. Connect to ~~CRM
2. Analyze contact properties and interactions
3. Find patterns in top 20% of customers
4. Generate ICP draft
5. Present to user for review and refinement
6. Save to `data/2-Domaines/icp.json`

## Key References

- **`references/interview-script.md`**: Complete 7-phase interview script
- **`references/icp-template.json`**: Blank ICP JSON template
- **`references/examples.md`**: 3 example ICPs (B2B SaaS, Service, E-commerce)

## Tips

1. **Be specific** — "Freelance designers in SF" not "creative professionals"
2. **Use their words** — Capture exact language patterns and jargon
3. **Prioritize pains** — Top 3 pains are most important
4. **Validate** — Talk to 5-10 ideal clients to confirm your ICP
5. **Update regularly** — ICP evolves as your business grows
6. **One ICP at a time** — Don't try to serve everyone. Pick your best customer type.
