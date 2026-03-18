---
description: "Find & Screen Prospects - The Hunter"
argument-hint: "[keywords | url | inbound]"
allowed-tools: Read, Write, Glob
model: sonnet
---

# /sales:prospect

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

The **Prospector** identifies high-value potential customers. It runs in two modes:

1.  **Outbound**: Scans search results, comments, and groups.
2.  **Inbound**: Scans "Who viewed your profile" and post likes.

It filters candidates against your `icp.json` (Ideal Customer Profile) and saves qualified leads to your local database.

---

## Usage

```
/sales:prospect "SaaS CTO in Paris"   # Quick Search
/sales:prospect inbound               # Check who viewed your profile
/sales:prospect url [LINKEDIN_URL]    # Analyze a specific list/post
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                    LINKEDIN PROSPECTOR                            │
├──────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                        │
│  ✓ Filtering Logic: Match candidates against ICP & Geography     │
│  ✓ Search Construction: Boolean search string generation         │
│  ✓ Markdown Database: Local storage of qualified leads           │
│  ✓ Fit Scoring: High/Med/Low ranking based on role match         │
├──────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                       │
│  + ~~browser: Auto-scan search results and profile views         │
│  + ~~CRM: Push qualified leads to HubSpot/Salesforce             │
│  + ~~email: Find verified email addresses (via enrichment)       │
└──────────────────────────────────────────────────────────────────┘
```

---

## /sales:prospect "SaaS CTO"

**Outbound Search Mode.**
Scrapes the current page (or searches) for candidates.

### Output Example

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROSPECTOR REPORT — Search: "SaaS CTO"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scanned: 15 profiles
Qualified: 3 prospects

| Name        | Role   | Company  | Fit Score | Why?                              |
| :---------- | :----- | :------- | :-------- | :-------------------------------- |
| Jean Dupont | CTO    | TechFlow | HIGH      | Matches Role + Geo (Paris)        |
| Sarah Smith | VP Eng | DataCorp | MED       | Role match, Geo mismatch (London) |
| Alex Martin | Dev    | StartupX | LOW       | Junior role                       |

ACTIONS:

1. Saved Jean Dupont to prospects.md
2. Saved Sarah Smith to prospects.md (Watchlist)
3. Discarded Alex Martin

Suggested Next Step:
/sales:engage "Jean Dupont" (Start Warming)
```

---

## /sales:prospect inbound

**Lurker Detection Mode.**
Scans `/me/profile-views/` to find people checking you out.

### Agent Instructions (Inbound)

```python
# 1. Navigate to Profile Views
browser.goto("linkedin.com/me/profile-views/")

# 2. Scrape List
viewers = scrape_dom(".viewer-card")

# 3. Filter matches
for viewer in viewers:
    if match_icp(viewer, profile.icp):
        print(f"HOT LEAD: {viewer.name} viewed your profile.")
        # Check if already in prospects.md
        if not exists_in_db(viewer):
            save_prospect(viewer, source="Inbound View")
            suggest_action(f"Connect with {viewer.name}")
```

---

## Agent Instructions (General)

### Filtering Logic

```python
def is_qualified(candidate):
    # 1. Geography (Strict)
    if candidate.location not in profile.target_geography:
        return False, "Wrong Location"

    # 2. Role (Keyword Match)
    if not any(role in candidate.headline for role in profile.icp.roles):
        return False, "Wrong Role"

    return True, "Qualified"
```

### Data Privacy

- **Rate Limit**: Max 50 profile views/day (simulated).
- **Delays**: Wait 2-5 seconds between scrapes.
- **No Email Scraping**: Unless publicly visible on the profile.

---

## Tips

1.  **Look for "Open" signals**: Search for "Hiring Sales" or "Looking for CRM". These prospects are Problem-Aware.
2.  **Competitor Poaching**: Go to a competitor's post. Run `/sales:prospect url [POST_URL]`. Scrape the dissatisfied commenters.
3.  **Inbound is Key**: A profile view is a 5x stronger signal than a cold search result. Always prioritize inbound.

---

## Skills Used

- `linkedin-prospector` — DOM scraping & ICP matching.
- `icp-creator` — Definition of the target profile.
