---
name: icp-creator
description: >
  Create detailed Ideal Client Profile through guided interview. Trigger with "create my ICP", "define my ideal client", "who is my target customer", or "build my audience profile".
model: sonnet
bundle: identity-core
triggers:
  - "create my ICP"
  - "define my ideal client"
  - "build my audience profile"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# ICP Creator (Ideal Client Profile)

Create a comprehensive ideal client profile that captures demographics, psychographics, problems, goals, and language patterns for precise content targeting.

## Output Format

After gathering responses, generate a JSON file following this structure and save to `data/2-Domaines/icp.json`.

```json
{
  "ideal_client_profile": {
    "version": "1.0",
    "last_updated": "YYYY-MM-DD",
    "demographics": {
      "age_range": "",
      "gender": "",
      "location": "",
      "income_level": "",
      "education": ""
    },
    "professional_profile": {
      "job_titles": [],
      "industries": [],
      "company_size": "",
      "experience_level": "",
      "decision_making_power": ""
    },
    "psychographics": {
      "values": [],
      "beliefs": [],
      "personality_traits": []
    },
    "problems_and_pain_points": {
      "primary_problems": [],
      "frustrations": [],
      "fears": [],
      "failed_solutions": []
    },
    "goals_and_desires": {
      "immediate_goals": [],
      "long_term_aspirations": [],
      "dream_outcome": ""
    },
    "language_patterns": {
      "words_they_use": [],
      "phrases_they_say": [],
      "questions_they_ask": [],
      "jargon_they_know": []
    },
    "content_consumption": {
      "platforms": [],
      "content_formats": [],
      "consumption_time": "",
      "attention_span": ""
    },
    "objections": {
      "common_objections": [],
      "trust_barriers": []
    },
    "buying_triggers": {
      "emotional_triggers": [],
      "logical_triggers": [],
      "timing_triggers": []
    }
  }
}
```
