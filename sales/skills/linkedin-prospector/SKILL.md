---
name: linkedin-prospector
description: >
  Finds and pre-screens potential customers on LinkedIn using the browser.
  "Browser-First": Scrapes search results, comment sections, and "Who viewed your profile" directly from DOM.
  Filters candidates against `sales-profile.json` (ICP, Geography, Role).
  Saves qualified prospects to `data/linkedin/prospects.md`.
  Includes "Inbound Mode" for finding lurkers (viewers/followers).
bundle: prospecting
triggers:
  - "find prospects on LinkedIn"
  - "LinkedIn prospecting"
  - "scan LinkedIn for leads"
tools:
  standalone: [filesystem]
  supercharged: [linkedin]
version: 1.0.0
---

# LinkedIn Prospector (The Hunter)

Identifies high-value prospects by scanning LinkedIn pages and filtering them against your defined Ideal Customer Profile (ICP).
Designed to work with **Claude for Chrome** or an Agentic Browser.

## Configuration (Dynamic ICP)

- **Reads**: `data/2-Domaines/sales-profile.json`
- **Keys**:
  - `target_geography`: List of allowed countries (e.g., ["France", "Canada"]). **STRICT FILTER**.
  - `icp.role_keywords`: Titles to match (e.g., ["CTO", "VP Sales"]).
  - `icp.company_size`: Size range (e.g., "11-50", "51-200").
  - `icp.pain_points`: Keywords for finding problem-aware prospects.

## Triggers

- "find prospects"
- "scan feed"
- "check inbound"
- "who viewed my profile"

## Workflow Strategies

### 1. Outbound Screening (Search & Comments)

**Where to run**: LinkedIn Search Results, Comment Sections of Thought Leaders.
**Logic**:

1.  **Scrape**: Read the DOM for Name, Headline, Location.
2.  **Geo Filter**: IF Location NOT IN `target_geography` → **SKIP**.
3.  **Role Filter**: IF Headline does NOT contain `icp.role_keywords` → **SKIP**.
4.  **Pain Signal**: IF text matches `icp.pain_points` → **HIGH PRIORITY**.

### 2. Inbound Screening (Lurker Detection)

**Where to run**: `/me/profile-views/`, `/mynetwork/invitation-manager/`, Post Reactions.
**Logic**:

- **Why**: Inbound signals (views/likes) indicate intent.
- **Fast-Track**: If they viewed you + match ICP, they are "Warm" (1-2 touches).

### 3. Competitor Monitoring

**Where to run**: Competitor's Post Comments.
**Logic**: Users complaining on competitor posts are high-intent buyers.

## Browser Instructions (DOM Scraping)

**When reading a page, look for these specific elements:**

**A. Search Results / Feed:**

- Container: `.entity-result__item` or `.feed-shared-update-v2`
- Name: `.entity-result__title-text` or `.update-components-actor__name`
- Headline: `.entity-result__primary-subtitle` or `.update-components-actor__description`
- Location: `.entity-result__secondary-subtitle`
- Action: Scroll down to load more items before scraping.

**B. Profile Page:**

- Name: `.pv-text-details__left-panel h1`
- Headline: `.pv-text-details__left-panel .text-body-medium`
- Location: `.pv-text-details__left-panel .text-body-small`
- About: `#about` section text.
- Experience: `#experience` section (Current Role).

**C. Comments Section:**

- Container: `.comments-comment-item`
- Author: `.comments-post-meta__name-text`
- Text: `.comments-comment-item__main-content`
- Headline: `.comments-post-meta__headline`

## Execution Steps

1.  **Context**: Agent checks current URL to determine mode (Search vs Profile vs Inbound).
2.  **Scrape**: Extract list of candidates from DOM.
3.  **Filter (In-Memory)**: Apply `sales-profile.json` rules.
4.  **Dedup**: Check `data/2-Domaines/LinkedIn/prospects.md` (by Profile URL).
5.  **Save**: Append new matches to `prospects.md`.

## Output Format (`prospects.md`)

Append to `data/2-Domaines/LinkedIn/prospects.md`:

| Name   | Role   | Company   | Location        | Source               | Status | Notes                         |
| :----- | :----- | :-------- | :-------------- | :------------------- | :----- | :---------------------------- |
| [Name] | [Role] | [Company] | [City, Country] | [Source URL/Comment] | Lead   | High Fit; Pain: "CRM is slow" |

## Example Interaction

**User**: "Find prospects in these comments"
**Agent**:

1.  Reads `sales-profile.json` → Target: "France", Role: "CTO".
2.  Scans 15 comments.
3.  Identifies "Jean Dupont, CTO @ TechFlow, Paris". -> **MATCH**.
4.  Identifies "Alice Smith, Recruiter, London". -> **DISCARD** (Geo/Role mismatch).
5.  Saves Jean Dupont.
6.  _Output_: "Found 1 prospect: Jean Dupont (CTO). Saved to prospects.md."

## Data Privacy & Safety

- **Rate Limit**: Max 50 profile views/day (simulated).
- **Delay**: Wait 2-5 seconds between navigations if automating clicks.
- **Privacy**: Do not scrape email unless visible on public profile.
