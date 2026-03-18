---
name: business-profile-creator
description: "Guided 7-phase interview to define company identity, value proposition, offerings, and brand voice. Orchestrated by /solo:start."
version: "2.1.0"
bundle: core-identity
triggers:
  - "create business profile"
  - "set up my business"
  - "define my brand"
tools:
  standalone: ["filesystem"]
  supercharged: ["knowledge-base"]
---

# Skill: Business Profile Creator

This skill acts as your "Chief Strategy Officer." It conducts a deep-dive interview to capture your business context, ensuring every piece of content Claude generates is aligned with your mission, positioning, and unique value proposition.

```
┌─────────────────────────────────────────────────────────────────┐
│  STANDALONE (always works)                                      │
│  ✓ Guided 7-phase interview to build profile from scratch       │
│  ✓ Saves business-profile.json to data/2-Domaines/             │
│  ✓ ~15-20 minutes interactive session                           │
├─────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (connect ~~knowledge base)                        │
│  + Auto-scan pitch decks, strategy docs, or websites            │
│  + Extract answers from connected documents automatically       │
│  + Generate draft profile in seconds, then refine with you      │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠 Usage & Triggers

- **Primary**: Internal skill called by `/solo:start` during onboarding.
- **Manual**: "I want to update my business profile" or "Let's refine my mission and vision."
- **Audit**: "How well-defined is my business strategy?"

---

## 📋 7-Phase Interview Framework

The agent must guide the user through these phases. Do not move to the next phase until the current one is sufficiently detailed.

### Phase 1: Identity & Origins (The "Why")

- **Mission**: What is the singular reason your business exists beyond making money?
- **Vision**: What does the world look like in 5 years if you succeed?
- **Founding Story**: Why did you start this? What gap did you see?

### Phase 2: Value Proposition (The "How")

- **Unique Method**: What is your specific "mechanism" or "blueprint" for solving the problem? (e.g., "The PARA Method", "The 10-Minute Workout").
- **Core Benefit**: What is the #1 transformation you deliver?
- **Primary Alternative**: If you didn't exist, what would they use? Why is it worse?

### Phase 3: Offerings & Revenue (The "What")

- **Core Offer**: Your premium, high-value service or product.
- **Lead Magnet**: Your "Gateway" free or low-cost offer.
- **Micro-Offers**: Productized services or smaller units of value.
- **Pricing Model**: Project-based? Retainer? Value-based?

### Phase 4: Positioning & Niche (The "Who")

- **Market Category**: What room are you in? (e.g., "AI Consulting", "Boutique E-commerce").
- **Niche Focus**: Who is your "beachhead" customer?
- **Point of View (POV)**: What do you believe that others in your industry get wrong?

### Phase 5: Brand Personality & Voice (The "Vibe")

- **Personification**: If your business were a person, who would it be?
- **Tone Matrix**: (Analytical vs. Creative, Formal vs. Casual, Provocative vs. Safe).
- **Forbidden Words**: What jargon or cliches do you NEVER use?

### Phase 6: Proof & Authority (The "Trust")

- **Key Metrics**: Successes to date (revenue, users, years, results).
- **Testimonials**: Core themes from happy clients.
- **Strategic Partners**: Who else in the ecosystem validates you?

### Phase 7: Growth & Content (The "Next")

- **Content Pillars**: The 3 topics you want to be "famous" for.
- **Primary Channel**: Where do you live? (LinkedIn, X, Newsletter, YouTube).
- **Call to Action**: What is the "next step" for every stranger you meet?

---

## 📄 Output Schema (business-profile.json)

The agent must output this format to `${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/business-profile.json`.

```json
{
  "identity": {
    "name": "",
    "mission": "",
    "vision": "",
    "elevator_pitch": ""
  },
  "strategy": {
    "value_proposition": "",
    "unique_method": "",
    "alternatives": [],
    "positioning_statement": ""
  },
  "offerings": [
    {
      "name": "",
      "type": "Core | Lead-Magnet | Productized",
      "price_point": "",
      "outcome": ""
    }
  ],
  "voice": {
    "personality": "",
    "tone": [],
    "lexicon": {
      "favored_words": [],
      "forbidden_words": []
    }
  },
  "social_proof": {
    "key_stats": [],
    "logos_or_names": []
  },
  "content": {
    "pillars": [],
    "primary_channel": "",
    "standard_cta": ""
  }
}
```

---

## 🛠 Agent Instructions (Execution Logic)

1.  **Detect Onboarding Status**: Check if `business-profile.json` exists. If yes, ask: "Update existing profile or start fresh?"
2.  **Guided Interview**:
    - Ask **one question at a time**.
    - Summarize the user's answer into a professional "Strategy" format.
    - Ask if they want to elaborate or proceed to the next phase.
3.  **Supercharged Shortcut**: If `~~knowledge base` is active, proactive scan files first. Present a "Draft Profile" based on the files and ask the user to fill the gaps via the interview.
4.  **Synthesis**: After Phase 7, generate the JSON and present a "Business Identity Card" (Markdown) as a final summary.
5.  **Persistence**: Save to `data/2-Domaines/business-profile.json`.

---

## 🔗 Integration Points

- **Connects to**: `voice-dna-creator` (Brand Voice phase), `icp-creator` (Positioning phase).
- **Feeds into**: All `/solo:write` commands, `/solo:prospect` (Positioning), and `/solo:weekly-review`.
