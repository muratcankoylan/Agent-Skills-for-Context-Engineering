# ICP Examples

3 example ICPs across different markets (see proto-persona examples for detailed versions).

---

## Example 1: Solopreneur Designer (B2B Services)

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
    "beliefs": ["I can build a great business without hiring"],
    "personality_traits": ["Self-motivated", "Detail-oriented", "Introverted"],
    "motivations": ["Freedom to choose projects", "Financial independence"]
  },
  "pain_points": [
    {
      "pain": "Time on admin",
      "description": "10-15 hours/week on invoicing, proposals, follow-ups",
      "severity": "High"
    },
    {
      "pain": "Cash flow unpredictability",
      "description": "Clients pay 15-45 days late",
      "severity": "High"
    }
  ],
  "goals": {
    "short_term": ["Hit $150K/year revenue", "Work 40 hours/week"],
    "long_term": ["Build $500K-1M/year business"],
    "success_definition": "Financial security + time freedom"
  },
  "language_patterns": {
    "frequent_words": ["Streamline", "Automate", "All-in-one"],
    "common_questions": ["How do I scale without hiring?"],
    "jargon": ["Productized service", "MRR", "Value-based pricing"],
    "problem_descriptions": ["Drowning in admin work"]
  },
  "content_behavior": {
    "online_hangouts": ["Reddit (r/solopreneurs)", "Twitter", "Indie Hackers"],
    "content_consumed": ["YouTube tutorials", "Indie hacker blogs"],
    "buying_process": ["Free trials", "G2 reviews"],
    "purchase_triggers": ["Pain unbearable", "Clear ROI"]
  }
}
```

---

## Example 2: SaaS Product Manager

See the proto-persona examples file for the complete PM persona, which can be converted to ICP format using the same structure.

---

## Example 3: E-commerce Founder

See the proto-persona examples file for the complete e-commerce founder persona, which can be converted to ICP format using the same structure.

---

## How to Use These Examples

1. **Copy the JSON structure** — Use as a starting point
2. **Fill in your data** — Replace with your specific market
3. **Validate** — Test assumptions with real customers
4. **Update** — Refine as you learn more

---

## Converting Proto-Persona to ICP

Proto-personas and ICPs are similar. To convert:

1. **Demographics** → Same
2. **Bio** → Not included in ICP (narrative format)
3. **Goals** → Same
4. **Pain Points** → Same (add severity: High/Medium/Low)
5. **JTBD** → Not included in ICP (use in product development)
6. **Behaviors** → Maps to `content_behavior`
7. **Influences** → Not included in ICP (use for marketing)
8. **Quotes** → Not included in ICP (use in problem statements)

**Key difference:** ICP is more data-focused (JSON), proto-persona is more narrative (Markdown).
