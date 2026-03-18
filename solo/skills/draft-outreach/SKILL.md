---
name: draft-outreach
description: >
  Draft personalized cold and warm outreach messages for email and social media.
  Uses voice DNA and prospect research for high-response-rate messages. Triggers
  on "write outreach", "cold email", "draft message", or "LinkedIn outreach".
version: 1.0.0
bundle: sales-growth
triggers:
  - "draft outreach"
  - "cold email"
  - "write outreach for"
  - "prospect message"
tools:
  standalone: ["filesystem"]
  supercharged: ["exa"]
---

# Skill: Draft Outreach

Creates personalized outreach messages that get responses. Combines your unique voice, prospect research, and proven outreach frameworks to generate emails, LinkedIn messages, and follow-up sequences.

## When to Use

- Cold outreach to prospects
- Warm introductions via mutual connections
- Follow-up sequences (2nd, 3rd touch)
- LinkedIn connection requests and DMs
- Breakup emails (final follow-up)

## Core Responsibilities

### 1. Personalization

- Loads `voice-dna.json` to match your writing style
- Uses `icp.json` to tailor messaging to target audience
- Incorporates prospect-specific research (company news, pain points, tech stack)

### 2. Channel-Specific Formatting

- **Email:** Subject line + 150-200 word body
- **LinkedIn DM:** 100-150 words (shorter, more casual)
- **LinkedIn Connection Request:** 200 characters max
- **Twitter/X DM:** 280 characters max

### 3. Research Integration

- Works with `company-research` skill for prospect context
- References recent news, hiring signals, product launches
- Identifies outreach angles (pain points, opportunities)

## Outreach Framework

### The AIDA Structure

Every outreach message follows this pattern:

| Element       | Purpose                           | Example                                                                          |
| ------------- | --------------------------------- | -------------------------------------------------------------------------------- |
| **A**ttention | Hook with specific detail         | "I saw you just launched AI features..."                                         |
| **I**nterest  | Show you understand their problem | "Most Series A companies struggle with design consistency during hypergrowth..." |
| **D**esire    | Demonstrate value you can provide | "I helped Stripe solve this by..."                                               |
| **A**ction    | Clear, low-friction CTA           | "Worth a 15-minute call?"                                                        |

### Personalization Levels

| Level                      | Effort | Response Rate | When to Use                        |
| -------------------------- | ------ | ------------- | ---------------------------------- |
| **Template**               | 30 sec | 1-3%          | Mass outreach (not recommended)    |
| **Light personalization**  | 2 min  | 5-10%         | Company name + industry            |
| **Medium personalization** | 5 min  | 15-25%        | Company + recent news + pain point |
| **Deep personalization**   | 15 min | 30-50%        | Full research + custom angle       |

**Recommendation:** Always use medium or deep personalization. Templates don't work.

## Email Outreach Template

### Cold Email (First Touch)

```markdown
Subject: [Specific detail about their company]

Hi [First name],

[ATTENTION: Specific observation about their company]
I saw [Company] just [recent event/news/hiring]. Congrats on [specific achievement]!

[INTEREST: Show you understand their problem]
I also noticed [pain point signal]. In my experience working with [similar companies],
that's usually when [specific challenge] becomes a bottleneck.

[DESIRE: Demonstrate value]
I help companies like [similar company 1] and [similar company 2] solve this.
Here's a quick example: [1-sentence case study with metric].

[ACTION: Low-friction CTA]
Worth a quick chat? I put together a [specific deliverable] that might be helpful.
15 minutes?

[Your name]

P.S. If timing isn't right, no worries — I'll check back in a few months.
```

**Length:** 150-200 words  
**Tone:** Professional but conversational  
**CTA:** Specific and low-commitment

### Follow-Up Email #2 (3-5 days later)

```markdown
Subject: Re: [Original subject]

Hi [First name],

Following up on my email from [day]. I know you're busy, so I'll keep this short.

I put together a [specific deliverable] for [Company]. No strings attached —
just [3-5 quick wins] you could implement this week.

Want me to send it over?

[Your name]
```

**Length:** 50-75 words  
**Tone:** Helpful, not pushy  
**CTA:** Even lower friction (just say yes/no)

### Follow-Up Email #3 (7-10 days later) — Breakup Email

```markdown
Subject: Closing the loop

Hi [First name],

I haven't heard back, so I'm guessing now isn't the right time. No problem!

Before I close the loop, I'm curious: what's your biggest [pain point area]
challenge right now?

Even if we don't work together, I'd love to point you to some resources that
might help.

[Your name]
```

**Length:** 50-75 words  
**Tone:** Gracious, genuinely helpful  
**Why it works:** Breakup emails get 15-20% response rates (people feel guilty ignoring them)

## LinkedIn Outreach

### Connection Request (200 characters max)

```
Hi [Name] — saw you're [specific detail]. I help [similar companies] with [problem].
Worth connecting? [Link to case study]
```

**Tips:**

- Be specific (not "I saw your profile")
- Offer value upfront
- Include a link (case study, article, tool)

### LinkedIn DM (After Connection Accepted)

```markdown
Hi [Name],

Thanks for connecting!

I saw [Company] is [specific observation]. Most [similar companies] I work with
struggle with [pain point] at this stage.

I helped [similar company] solve this by [1-sentence solution + metric].

Worth a quick chat? I can share the exact approach.

[Your name]
```

**Length:** 100-150 words  
**Tone:** Casual but professional  
**CTA:** Specific value offer

## Outreach Best Practices

### Do's ✅

1. **Research first** — Spend 10-15 minutes researching before writing
2. **Be specific** — Reference actual details (news, hiring, product launches)
3. **Lead with value** — What's in it for them?
4. **Keep it short** — 150-200 words max for email
5. **One clear CTA** — Don't give multiple options
6. **Follow up 3x** — Most deals happen on the 3rd+ touchpoint
7. **Use breakup emails** — They work surprisingly well

### Don'ts ❌

1. **Don't use templates** — Personalize every message
2. **Don't pitch immediately** — Build rapport first
3. **Don't be vague** — "I help companies grow" means nothing
4. **Don't apologize** — "Sorry to bother you" is weak
5. **Don't ask for too much** — "Can I pick your brain?" is too vague
6. **Don't follow up daily** — Give them 3-5 days between touches
7. **Don't lie or exaggerate** — Authenticity wins

## Subject Line Formulas

### For Cold Emails

**Pattern 1: Specific Observation**

- "Quick question about [recent news]"
- "Saw you're hiring a [role]"
- "Congrats on [achievement]"

**Pattern 2: Mutual Connection**

- "[Mutual connection] suggested I reach out"
- "Following up from [event]"

**Pattern 3: Value Offer**

- "Free [deliverable] for [Company]"
- "[Specific insight] for your [project]"

**Avoid:**

- ❌ "Quick question" (too vague)
- ❌ "Collaboration opportunity" (spammy)
- ❌ "I can help you" (self-serving)

## Response Rate Benchmarks

| Outreach Type                  | Expected Response Rate |
| ------------------------------ | ---------------------- |
| Cold email (template)          | 1-3%                   |
| Cold email (personalized)      | 15-25%                 |
| Warm intro (mutual connection) | 40-60%                 |
| LinkedIn connection request    | 30-40%                 |
| LinkedIn DM (after connection) | 20-30%                 |
| Follow-up #2                   | 5-10%                  |
| Follow-up #3 (breakup)         | 15-20%                 |

**If your response rate is <10%:** Your personalization isn't strong enough or your ICP is wrong.

## Integration Points

- **`company-research`**: Provides prospect context for personalization
- **`voice-dna-creator`**: Ensures outreach matches your writing style
- **`icp-creator`**: Tailors messaging to target audience
- **`/solo:prospect outreach`**: Primary command that uses this skill

## Workflow Logic

### Trigger

- `/solo:prospect outreach [company/person]`
- "Draft a cold email to [Person] at [Company]"
- "Write LinkedIn message for [Person]"

### Process

1. **Identify target**
   - Parse company name and/or person name
   - Determine channel (email, LinkedIn, Twitter)

2. **Gather research**
   - Invoke `company-research` skill
   - Extract: recent news, hiring signals, pain points, tech stack
   - Identify outreach angle

3. **Load context**
   - Read `voice-dna.json` from `data/2-Domaines/`
   - Read `icp.json` from `data/2-Domaines/`
   - Understand user's writing style and target audience

4. **Select template**
   - Based on channel and outreach type (cold vs. warm)
   - Load from `references/` directory

5. **Generate draft**
   - Populate template with research
   - Match voice DNA style
   - Tailor to ICP pain points
   - Apply AIDA framework

6. **Present for review**
   - Show draft to user
   - Suggest edits if needed
   - Provide send checklist

## Example Output

### Input

```
/solo:prospect outreach "Acme Corp"
```

### Output

```markdown
# Outreach Draft: Acme Corp (Sarah Chen, VP of Product)

## Research Summary

- Company: Acme Corp (Marketing Automation SaaS)
- Recent news: Launched AI features (Jan 2026)
- Hiring signal: VP of Product role posted 2 weeks ago
- Pain point: Scaling design during hypergrowth (Series A stage)
- Outreach angle: Design consistency during rapid product iteration

---

## Email Draft

**Subject:** Quick question about your AI launch

**Body:**

Hi Sarah,

I saw Acme just launched AI features — congrats! The TechCrunch coverage was well-deserved.

I also noticed you're hiring a VP of Product, which usually means new features and rapid iteration. In my experience working with Series A SaaS companies, that's when design consistency becomes a challenge.

I help companies like Stripe and Notion redesign their product experience during hypergrowth. Here's a quick example: I helped [similar company] reduce design debt by 60% while shipping 2x faster.

Worth a 15-minute call? I put together a free design audit of Acme's current product that might be helpful.

[Your name]

P.S. If timing isn't right, no worries — I'll check back in a few months.

---

## LinkedIn DM Alternative

Hi Sarah — saw you're hiring a VP of Product at Acme. Most Series A companies I work with struggle with design consistency during hypergrowth. I help companies like Stripe and Notion solve this. Worth a quick chat? [Link to case study]

---

## Send Checklist

- [ ] Verify email address (sarah@acmecorp.com)
- [ ] Personalize subject line (reference AI launch)
- [ ] Add case study link
- [ ] Set follow-up reminder (3 days)
- [ ] Track in CRM: /solo:clients add "Sarah Chen"

---

## Expected Response Rate

- Email: 20-30% (deep personalization + relevant angle)
- LinkedIn DM: 25-35% (if connection accepted)

## Follow-Up Plan

- Day 3: Send follow-up #2 (offer design audit)
- Day 7: Send breakup email
- If no response after 3 touches, move to "check back in 6 months" list
```

## Key References

- **`references/email-template.md`**: Cold email template with AIDA structure
- **`references/linkedin-dm-template.md`**: LinkedIn DM template
- **`references/follow-up-sequence.md`**: 3-email follow-up templates
- **`references/subject-lines.md`**: 50+ proven subject line formulas

## Tips

1. **Research is 80% of the work** — Spend more time researching than writing
2. **Be human** — Write like you're talking to a friend, not a prospect
3. **One idea per email** — Don't try to say everything in one message
4. **Test subject lines** — A/B test to find what works for your audience
5. **Track everything** — Measure response rates and iterate
