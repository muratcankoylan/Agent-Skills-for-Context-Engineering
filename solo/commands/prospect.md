---
description: "Find prospects, craft outreach, and generate proposals"
argument-hint: "[find | outreach | proposal]"
allowed-tools: Read, Write, Search
model: sonnet
---

# /solo:prospect

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

Your sales assistant for finding prospects, crafting personalized outreach, and generating winning proposals. Turn cold leads into warm conversations.

## Usage

```
/solo:prospect find [criteria]      # Find potential clients
/solo:prospect outreach [company]   # Draft personalized outreach
/solo:prospect proposal [company]   # Generate custom proposal
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                    PROSPECTING & OUTREACH                         │
├──────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                        │
│  ✓ Prospect research: Company deep-dives with web search         │
│  ✓ Personalized outreach: Custom emails based on research        │
│  ✓ Proposal generation: Tailored proposals from templates        │
│  ✓ Follow-up sequences: Multi-touch outreach campaigns           │
├──────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                       │
│  + ~~data enrichment: Clay, ZoomInfo for contact data            │
│  + ~~email: Send outreach via your email client                  │
│  + ~~CRM: Auto-add prospects and track outreach                  │
│  + ~~LinkedIn: Research prospects and send connection requests   │
└──────────────────────────────────────────────────────────────────┘
```

---

## /solo:prospect find

Find potential clients matching your ICP.

### Usage

```
/solo:prospect find "B2B SaaS companies, Series A, 20-100 employees"
/solo:prospect find "E-commerce brands doing $1M-10M ARR"
```

### What I'll Do

1. **Parse criteria** from your description
2. **Search for companies** matching your ICP
3. **Enrich data** (size, funding, tech stack, recent news)
4. **Score fit** (1-10 based on your ICP)
5. **Suggest outreach angle** for each prospect

### Output

```markdown
# Prospect List: B2B SaaS, Series A, 20-100 employees

Found 12 companies matching your criteria:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 1. Acme Corp ⭐⭐⭐⭐⭐ (9/10 fit)

**Industry:** Marketing Automation  
**Size:** 50-100 employees  
**Funding:** Series A ($12M, 2022)  
**Location:** San Francisco, CA

**Why they're a good fit:**

- Scaling fast (3 engineering roles open)
- Recent product launch (AI features, Jan 2026)
- Outdated website (last update: 2023)
- Your sweet spot: Series A SaaS needing design refresh

**Outreach angle:**
"I saw you launched AI features and are hiring a VP of Product. Most Series A companies struggle with design consistency during hypergrowth..."

**Decision maker:**

- Sarah Chen, VP of Product (LinkedIn: 500+ connections)
- Email: sarah@acmecorp.com (verified)

**Next step:** /solo:prospect outreach "Acme Corp"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 2. Beta Solutions ⭐⭐⭐⭐ (8/10 fit)

**Industry:** HR Tech  
**Size:** 30-50 employees  
**Funding:** Series A ($8M, 2023)  
**Location:** Austin, TX

**Why they're a good fit:**

- Growing team (10 new hires in Q4 2025)
- TechCrunch feature (Dec 2025)
- Strong product, weak marketing site
- Budget: Likely $10K-20K for redesign

**Outreach angle:**
"Congrats on the TechCrunch feature! I noticed your product is getting traction, but your website doesn't reflect that growth..."

**Decision maker:**

- Michael Rodriguez, CEO (LinkedIn: 2,000+ connections)
- Email: michael@betasolutions.com (verified)

**Next step:** /solo:prospect outreach "Beta Solutions"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[10 more prospects...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUMMARY:

- 12 prospects found
- 3 high-fit (9-10/10)
- 5 good-fit (7-8/10)
- 4 medium-fit (5-6/10)

RECOMMENDED APPROACH:

1. Start with top 3 (Acme, Beta, Gamma)
2. Personalized outreach (not templates)
3. Follow up 3x before moving on

Prospect list saved to:
data/1-Projets/prospects/b2b-saas-series-a.md
```

---

## /solo:prospect outreach

Draft personalized outreach emails.

### Usage

```
/solo:prospect outreach "Acme Corp"
/solo:prospect outreach "Sarah Chen"
```

### What I'll Create

1. **Research summary** (company, decision maker, outreach angle)
2. **Email draft** (subject, body, CTA)
3. **Follow-up sequence** (3-email campaign)
4. **LinkedIn message** (alternative to email)

### Output

```markdown
# Outreach: Acme Corp (Sarah Chen)

## Research Summary

**Company:** Acme Corp (Marketing Automation SaaS)  
**Decision Maker:** Sarah Chen, VP of Product  
**Outreach Angle:** Scaling pains + design consistency

**Key Insights:**

- Launched AI features (Jan 2026)
- Hiring VP of Product (posted 2 weeks ago)
- Website outdated (last update: 2023)
- Series A stage ($12M funding)

---

## Email #1: Initial Outreach

**Subject:** Quick question about your AI launch

**Body:**

Hi Sarah,

I saw Acme just launched AI features — congrats! The TechCrunch coverage was well-deserved.

I also noticed you're hiring a VP of Product, which usually means new features and rapid iteration. In my experience working with Series A SaaS companies, that's when design consistency becomes a challenge.

I help companies like yours (Stripe, Notion, Linear) redesign their product experience during hypergrowth. Here's what I typically see:

- Product moves fast, but design system lags behind
- New features feel "bolted on" instead of integrated
- Engineering team wants clearer design specs

Does any of this resonate?

If so, I'd love to share a quick case study of how I helped [similar company] solve this during their Series A. 15-minute call?

[Your name]

P.S. If timing isn't right, no worries — I'll check back in a few months.

---

## Email #2: Follow-up (3 days later)

**Subject:** Re: Quick question about your AI launch

**Body:**

Hi Sarah,

Following up on my email from Monday. I know you're busy scaling the team, so I'll keep this short.

I put together a free design audit of Acme's current product. No strings attached — just 5-10 quick wins you could implement this week.

Want me to send it over?

[Your name]

---

## Email #3: Breakup Email (7 days later)

**Subject:** Closing the loop

**Body:**

Hi Sarah,

I haven't heard back, so I'm guessing now isn't the right time. No problem!

Before I close the loop, I'm curious: what's your biggest design challenge right now?

Even if we don't work together, I'd love to point you to some resources that might help.

[Your name]

---

## LinkedIn Message (Alternative)

Hi Sarah — saw you're hiring a VP of Product at Acme. Most Series A companies I work with struggle with design consistency during hypergrowth. I help companies like Stripe and Notion solve this. Worth a quick chat? [Link to case study]

---

## Outreach Checklist

Before sending:

- [ ] Personalize subject line (reference AI launch)
- [ ] Verify email address (sarah@acmecorp.com)
- [ ] Add case study link (similar company, Series A stage)
- [ ] Set follow-up reminder (3 days, 7 days)
- [ ] Track in CRM: /solo:clients add "Sarah Chen"

---

## Expected Response Rate

- Email #1: 10-15% reply rate
- Email #2: 5-10% reply rate
- Email #3: 15-20% reply rate (breakup emails work!)

If no response after 3 emails, move on. Add to "check back in 6 months" list.

Outreach saved to:
data/1-Projets/outreach/acme-corp-sarah-chen.md
```

---

## /solo:prospect proposal

Generate a custom proposal for a prospect.

### Usage

```
/solo:prospect proposal "Acme Corp"
```

### What I'll Create

1. **Executive summary** (problem + solution)
2. **Scope of work** (deliverables, timeline)
3. **Pricing** (based on your rate card)
4. **Case studies** (similar companies)
5. **Terms** (payment, revisions, ownership)
6. **Next steps** (how to accept)

### Output

(See `/solo:write proposal` for full example)

The proposal will be:

- **Personalized** with research from `/solo:research prospect`
- **Tailored** to their specific pain points
- **Priced** based on your rate card or custom pricing
- **Professional** with your branding and voice

**Saved to:** `data/1-Projets/proposals/acme-corp-proposal.md`

---

## Agent Instructions

```python
# /solo:prospect find
def find_prospects(criteria):
    # 1. Parse criteria
    filters = parse_criteria(criteria)

    # 2. Search for companies
    companies = search_web(f"{criteria} companies")

    # 3. Enrich data
    enriched = []
    for company in companies:
        data = invoke_skill("company-research", company=company)
        fit_score = score_fit(data, icp)
        outreach_angle = generate_outreach_angle(data, business_profile)
        enriched.append({
            "company": company,
            "data": data,
            "fit_score": fit_score,
            "outreach_angle": outreach_angle
        })

    # 4. Sort by fit score
    enriched.sort(key=lambda x: x["fit_score"], reverse=True)

    # 5. Display
    display_prospect_list(enriched)

# /solo:prospect outreach
def draft_outreach(company_name):
    # 1. Research company
    research = invoke_skill("company-research", company=company_name)

    # 2. Find decision maker
    decision_maker = find_decision_maker(research)

    # 3. Generate outreach angle
    angle = generate_outreach_angle(research, business_profile)

    # 4. Draft emails
    email_1 = invoke_skill("draft-outreach",
                          company=research,
                          decision_maker=decision_maker,
                          angle=angle,
                          voice_dna=voice_dna)

    email_2 = generate_followup(email_1, days=3)
    email_3 = generate_breakup_email(email_1, days=7)

    # 5. Display
    display_outreach_sequence(research, email_1, email_2, email_3)

# /solo:prospect proposal
def generate_proposal(company_name):
    # 1. Load client data (if exists) or research
    client = find_client_card(company_name) or invoke_skill("company-research", company=company_name)

    # 2. Generate proposal
    proposal = invoke_skill("proposal-generator",
                           client=client,
                           services=business_profile.services,
                           rate_card=business_profile.pricing)

    # 3. Save
    filename = slugify(f"{company_name}-proposal")
    save_file(f"data/1-Projets/proposals/{filename}.md", proposal)
```

---

## Tips

1. **Research before outreach** — 15 minutes of research = 10x better response rate
2. **Personalize everything** — No templates. Reference specific details.
3. **Follow up 3x** — Most deals happen on the 3rd+ touchpoint
4. **Use breakup emails** — "Closing the loop" emails get 15-20% response rates
5. **Track everything** — Add prospects to CRM immediately: `/solo:clients add`

---

## Integration with Other Commands

- **Before outreach:** Use `/solo:research prospect [company]` for deep research
- **After response:** Use `/solo:clients add [name]` to track in CRM
- **For proposals:** Use `/solo:write proposal [client]` for custom proposals
- **Track deals:** Use `/solo:clients pipeline` to monitor progress

---

## Skills Used

- `company-research` — Prospect deep-dives
- `draft-outreach` — Personalized email generation
- `proposal-generator` — Custom proposals
- `exa-search-expert` — Company discovery
