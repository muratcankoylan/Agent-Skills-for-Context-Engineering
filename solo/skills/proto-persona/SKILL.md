---
name: proto-persona
description: >
  Create hypothesis-based user personas to guide strategy before validation. Quick,
  assumption-driven profiles for early-stage product work. Trigger with "create persona", "who is my customer", "user profile", "target audience",
  "who am I building for", "describe my customer", "my target user", or "customer profile".
version: 1.0.0
bundle: product-build
triggers:
  - "create persona"
  - "proto persona"
  - "hypothesis persona"
tools:
  standalone: ["filesystem"]
  supercharged: []
---

# Skill: Proto-Persona

Creates lightweight, assumption-based user personas for early-stage product work. Unlike research-based personas, proto-personas are built from your current hypotheses and can be validated later through discovery.

## When to Use

- **Early product discovery** — Before you have research data
- **Aligning team assumptions** — Get everyone on the same page about who you're building for
- **Rapid prototyping** — Need a target user to design/test against
- **Hypothesis formation** — Crystallize assumptions before validation

## Proto-Persona vs. Research Persona

| Aspect             | Proto-Persona              | Research Persona                   |
| ------------------ | -------------------------- | ---------------------------------- |
| **Based on**       | Assumptions, hypotheses    | User research, interviews          |
| **Time to create** | 30 minutes                 | 2-4 weeks                          |
| **Confidence**     | Low (needs validation)     | High (data-backed)                 |
| **When to use**    | Early discovery            | After validation                   |
| **Purpose**        | Align team, guide research | Guide design and product decisions |

**Key Principle:** Proto-personas are **starting points**, not truth. Validate them through discovery interviews.

## Proto-Persona Template

```markdown
# [Alliterative Name] (Proto-Persona)

> **Status:** Hypothesis (Not validated)  
> **Created:** [Date]  
> **Last Updated:** [Date]

---

## Demographics

**Age:** [Range, e.g., 28-35]  
**Location:** [City/Region]  
**Job Title:** [Role]  
**Company Size:** [e.g., Solopreneur, 1-10 employees]  
**Income:** [Range, if relevant]  
**Education:** [Level]

---

## Bio (Day in the Life)

[2-3 sentences describing a typical day]

**Example:**
"Sarah wakes up at 6am, checks client emails, and spends the morning on billable work.
Afternoons are for admin tasks (invoicing, proposals, follow-ups). She works 50+ hours/week
but only bills for 30. Evenings are spent learning new skills to stay competitive."

---

## Goals & Motivations

**Professional Goals:**

- [What they're trying to achieve in their career]
- [What success looks like]

**Personal Goals:**

- [What they want in life]
- [What drives them]

**Example:**

- Build a sustainable $200K/year business without burning out
- Spend more time with family (currently working evenings/weekends)
- Be recognized as an expert in their field

---

## Pain Points & Frustrations

**Top 3 Pains:**

1. **[Pain 1]** — [Description and impact]
2. **[Pain 2]** — [Description and impact]
3. **[Pain 3]** — [Description and impact]

**Example:**

1. **Time spent on admin** — Spends 10+ hours/week on invoicing, proposals, follow-ups instead of billable work
2. **Cash flow unpredictability** — Never knows when clients will pay, makes financial planning impossible
3. **Context switching** — Juggles 5-7 tools (CRM, invoicing, project management, calendar) which kills productivity

---

## Jobs to Be Done

**When [situation], I want to [motivation], so I can [expected outcome].**

**Example:**

- When a client asks for a proposal, I want to generate it in 10 minutes (not 2 hours), so I can respond quickly and win more deals
- When an invoice is overdue, I want to send a polite reminder automatically, so I don't have to chase payments manually
- When planning my week, I want to see all client commitments in one place, so I don't miss deadlines

---

## Behaviors & Habits

**Tools They Use:**

- [List of software, platforms, tools]

**Information Sources:**

- [Where they learn, get news, find solutions]

**Decision-Making:**

- [How they evaluate and buy products]

**Example:**

- **Tools:** Notion (notes), HubSpot (CRM), Stripe (payments), Google Calendar
- **Sources:** Reddit (r/solopreneurs), Twitter, indie hacker blogs, YouTube tutorials
- **Buying:** Tries free trials, reads reviews on G2/Capterra, asks for recommendations in communities

---

## Influences & Aspirations

**Who do they follow?**

- [Influencers, thought leaders, brands]

**Who do they want to be like?**

- [Role models, aspirational figures]

**Example:**

- Follows: Pieter Levels, Arvid Kahl, Justin Welsh (solopreneur creators)
- Aspires to: Build a $1M/year one-person business like them

---

## Quotes (Hypothetical)

> "[Quote that captures their mindset or frustration]"

**Example:**

> "I'm great at my craft, but I spend more time on admin than actual work. There has to be a better way."

> "I don't need a complex CRM built for sales teams. I just need to track 10-15 clients and remember to follow up."

---

## Validation Plan

**Hypotheses to Test:**

- [ ] [Assumption 1 about this persona]
- [ ] [Assumption 2 about this persona]
- [ ] [Assumption 3 about this persona]

**How to Validate:**

- [ ] 5-10 discovery interviews with people matching this profile
- [ ] Survey 50+ people in target communities
- [ ] Analyze Reddit/forum discussions for pain point validation

**Example:**

- [ ] Hypothesis: They spend 10+ hours/week on admin tasks
- [ ] Hypothesis: They use 5+ separate tools for business operations
- [ ] Hypothesis: They're willing to pay $20-50/mo for an all-in-one solution

**Validation Method:**

- Interview 10 solopreneurs (find via r/solopreneurs, Twitter, indie hacker communities)
- Ask: "Walk me through your typical week. How much time do you spend on admin vs. billable work?"
```

## Example Proto-Persona

```markdown
# Solopreneur Sarah (Proto-Persona)

> **Status:** Hypothesis (Not validated)  
> **Created:** 2026-02-13  
> **Last Updated:** 2026-02-13

---

## Demographics

**Age:** 32-38  
**Location:** Major US cities (SF, NYC, Austin, Denver)  
**Job Title:** Freelance Designer / Design Consultant  
**Company Size:** Solopreneur (just her)  
**Income:** $80K-150K/year  
**Education:** Bachelor's in Design or self-taught

---

## Bio (Day in the Life)

Sarah runs a one-person design consultancy. She wakes up at 6am, checks client emails, and spends mornings on billable work (design, client calls). Afternoons are for admin: invoicing, proposals, follow-ups, project management. She works 50+ hours/week but only bills for 30. Evenings are spent learning new tools (Figma plugins, AI design tools) to stay competitive.

---

## Goals & Motivations

**Professional Goals:**

- Build a sustainable $200K/year business without hiring
- Work with 5-7 high-quality clients (not 20+ small projects)
- Be recognized as a go-to expert in her niche (B2B SaaS design)

**Personal Goals:**

- Spend more time with family (currently working evenings/weekends)
- Take 4 weeks of vacation per year (currently takes 1-2)
- Build financial security (6-12 months runway)

---

## Pain Points & Frustrations

**Top 3 Pains:**

1. **Time spent on admin** — 10-15 hours/week on invoicing, proposals, follow-ups, project management instead of billable design work
2. **Cash flow unpredictability** — Clients pay 15-45 days late, making it hard to plan expenses or take time off
3. **Tool overload** — Uses 7 different tools (Notion, HubSpot, Stripe, Calendly, Figma, Slack, Gmail) which requires constant context switching

---

## Jobs to Be Done

- When a client asks for a proposal, I want to generate it in 10 minutes, so I can respond quickly and win more deals
- When an invoice is overdue, I want to send a polite reminder automatically, so I don't have to chase payments
- When planning my week, I want to see all client commitments in one place, so I don't miss deadlines or double-book

---

## Behaviors & Habits

**Tools They Use:**

- Notion (notes, project management)
- HubSpot Free CRM (client tracking)
- Stripe (invoicing and payments)
- Figma (design work)
- Calendly (scheduling)
- Slack + Gmail (communication)

**Information Sources:**

- Reddit (r/solopreneurs, r/freelance)
- Twitter (follows indie hackers, design influencers)
- YouTube (productivity hacks, tool tutorials)
- Indie Hackers, Hacker News

**Decision-Making:**

- Tries free trials before buying
- Reads reviews on G2, Capterra, Product Hunt
- Asks for recommendations in Slack communities
- Price-sensitive ($20-50/mo is sweet spot, $100+ is too much)

---

## Influences & Aspirations

**Who do they follow?**

- Pieter Levels (build in public, solopreneur lifestyle)
- Justin Welsh (solopreneur playbook, productized services)
- Arvid Kahl (bootstrapping, audience building)

**Who do they want to be like?**

- Build a $500K-1M/year one-person business
- Work 30 hours/week (not 50+)
- Have systems and automation handle admin

---

## Quotes (Hypothetical)

> "I'm great at design, but I spend more time on admin than actual work. There has to be a better way."

> "I don't need a complex CRM built for sales teams. I just need to track 10-15 clients and remember to follow up."

> "Every tool I try is either too simple (doesn't do enough) or too complex (built for teams, not solopreneurs)."

---

## Validation Plan

**Hypotheses to Test:**

- [ ] They spend 10-15 hours/week on admin tasks
- [ ] They use 5-7 separate tools for business operations
- [ ] They're willing to pay $20-50/mo for an all-in-one solution
- [ ] Cash flow unpredictability is a top-3 pain point
- [ ] They prefer opinionated tools over flexible blank canvases

**How to Validate:**

- [ ] Interview 10 solopreneur designers (find via r/solopreneurs, Twitter, design communities)
- [ ] Survey 50+ solopreneurs about time spent on admin
- [ ] Analyze Reddit threads about solopreneur pain points
- [ ] Run a landing page test to gauge interest in an all-in-one tool

**Validation Questions:**

1. "Walk me through your typical week. How much time do you spend on admin vs. billable work?"
2. "What tools do you use to run your business? What frustrates you about them?"
3. "If you could wave a magic wand and fix one thing about running your business, what would it be?"
```

## Creating a Proto-Persona

### Step 1: Choose a Name

Use an alliterative name (e.g., Solopreneur Sarah, Freelancer Frank, Designer Diana)

**Why?** Makes the persona memorable and easy to reference in conversations.

### Step 2: Define Demographics

Age, location, job title, company size, income (if relevant)

**Tip:** Be specific but not too narrow. "32-38" is better than "35 exactly."

### Step 3: Write a Bio

2-3 sentences describing a typical day in their life.

**Focus on:** What they do, how they spend their time, what frustrates them.

### Step 4: Identify Goals

What are they trying to achieve professionally and personally?

**Tip:** Goals should be aspirational but realistic.

### Step 5: List Pain Points

Top 3 frustrations or problems they face.

**Format:** [Pain] — [Description and impact]

### Step 6: Define Jobs to Be Done

What are they trying to accomplish? Use the JTBD format:

"When [situation], I want to [motivation], so I can [expected outcome]."

### Step 7: Document Behaviors

What tools do they use? Where do they get information? How do they make decisions?

### Step 8: Add Influences

Who do they follow? Who do they aspire to be like?

### Step 9: Write Hypothetical Quotes

What would they say about their frustrations or needs?

### Step 10: Create Validation Plan

List hypotheses to test and how you'll validate them.

## Auto-Enrichment Protocol

**When `~~search` is connected**, automatically enrich proto-personas with real-world data:

### Enrichment Sources

| Data Point       | Source                     | Query Example                              |
| ---------------- | -------------------------- | ------------------------------------------ |
| **Demographics** | LinkedIn, Census data      | "Average age of [job title] in [location]" |
| **Pain Points**  | Reddit, forums, reviews    | "[job title] biggest frustrations"         |
| **Tools Used**   | Product Hunt, G2, Capterra | "Tools used by [job title]"                |
| **Influences**   | Twitter, LinkedIn          | "Top influencers for [job title]"          |
| **Salary Range** | Glassdoor, Payscale        | "[job title] salary in [location]"         |

### Enrichment Workflow

```python
if has_tool("~~search"):
    # Enrich demographics
    age_data = search(f"Average age of {job_title}")
    salary_data = search(f"{job_title} salary in {location}")

    # Enrich pain points
    reddit_pains = search(f"site:reddit.com {job_title} frustrations")
    forum_pains = search(f"{job_title} biggest challenges")

    # Enrich tools
    tools = search(f"Tools used by {job_title}")

    # Update persona with real data
    persona["demographics"]["age"] = age_data.get("range")
    persona["demographics"]["income"] = salary_data.get("range")
    persona["pain_points"].extend(reddit_pains.get("top_3"))
    persona["tools"].extend(tools.get("most_common"))

    # Mark enriched fields
    persona["enrichment_status"] = "Enriched with real data"
else:
    persona["enrichment_status"] = "Hypothesis only (connect ~~search to enrich)"
```

**Output**: Updated persona file with enriched data marked as `[ENRICHED]` vs `[HYPOTHESIS]`

---

## Bidirectional ICP Linking

**Proto-persona ↔ ICP Creator**: Ensure persona and ICP stay in sync.

### Persona → ICP

When creating an ICP from a proto-persona:

```python
# Extract ICP attributes from persona
icp = {
    "firmographics": {
        "company_size": persona["demographics"]["company_size"],
        "industry": persona["demographics"]["industry"]
    },
    "psychographics": {
        "goals": persona["goals"],
        "pain_points": persona["pain_points"]
    },
    "buying_behavior": {
        "decision_criteria": persona["decision_factors"],
        "budget_range": persona["demographics"]["income"]
    }
}

# Save ICP with persona reference
icp["source_persona"] = persona["name"]
save_file("data/2-Domaines/icp.json", icp)
```

### ICP → Persona

When updating an ICP, check if persona needs updating:

```python
# Read existing persona
persona = read_file(f"data/1-Projets/{project}/persona.md")

# Check for drift
if icp["firmographics"]["company_size"] != persona["demographics"]["company_size"]:
    warn("ICP and persona are out of sync. Update persona or create new one.")
```

---

## Persona Confidence Score

**Track validation progress** with a 0-100% confidence score.

### Scoring Logic

```python
# Count total hypotheses
total_hypotheses = (
    len(persona["demographics"]) +
    len(persona["goals"]) +
    len(persona["pain_points"]) +
    len(persona["behaviors"]) +
    len(persona["jtbd"])
)

# Count validated hypotheses
validated = sum(1 for h in all_hypotheses if h["status"] == "validated")

# Calculate confidence
confidence_score = (validated / total_hypotheses) * 100

# Add to persona
persona["confidence"] = {
    "score": confidence_score,
    "validated": validated,
    "total": total_hypotheses,
    "status": get_status(confidence_score)
}

def get_status(score):
    if score < 20:
        return "Low confidence — needs validation"
    elif score < 50:
        return "Medium confidence — partial validation"
    elif score < 80:
        return "High confidence — mostly validated"
    else:
        return "Very high confidence — research-backed"
```

### Confidence Display

Add to persona header:

```markdown
# [Persona Name] (Proto-Persona)

> **Status:** Hypothesis (Not validated)  
> **Confidence Score:** 35% (7/20 hypotheses validated)  
> **Confidence Status:** Medium confidence — partial validation  
> **Created:** [Date]  
> **Last Updated:** [Date]
```

### Validation Tracking

Mark each hypothesis as validated:

```markdown
## Pain Points & Frustrations

1. **Time spent on admin** [VALIDATED ✓] — Confirmed in 5/5 discovery interviews
2. **Cash flow unpredictability** [HYPOTHESIS] — Not yet tested
3. **Context switching** [VALIDATED ✓] — Confirmed via user survey (n=50)
```

---

## Integration Points

- **`/solo:build discover`**: Uses proto-personas to guide discovery research
- **`icp-creator`**: Proto-persona informs ICP definition (bidirectional sync)
- **`customer-journey-map`**: Persona is the subject of the journey map
- **`problem-statement`**: Persona's pains become problem statements
- **`~~search`**: Auto-enriches persona with real-world data when connected

## Key References

- **`references/template.md`**: Complete proto-persona template
- **`references/examples.md`**: 5 example proto-personas across different markets

## Tips

1. **Be specific** — "Freelance designer in SF" not "creative professional"
2. **Focus on behaviors** — What they do, not just who they are
3. **Include quotes** — Hypothetical quotes make personas feel real
4. **Plan validation** — Always include how you'll test your assumptions
5. **Update regularly** — As you learn, update the persona (or create new ones)
6. **Don't over-invest** — Spend 30 minutes, not 3 hours. This is a hypothesis, not truth.
