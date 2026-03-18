---
description: "Initialize Sales OS - Configure your Sales DNA"
argument-hint: "[reset|update]"
allowed-tools: Read, Write, Glob
model: sonnet
---

# /sales:start

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

Welcome. This command configures the AI to act as your dedicated sales partner.

## Usage

```
/sales:start
/sales:start --update icp        # Update specific config
/sales:start --scan deck.pdf     # Auto-configure from file
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                    SALES OS INITIALIZATION                        │
├──────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                        │
│  ✓ Sales DNA: Define methodology (MEDDIC, SPIN, etc.)            │
│  ✓ ICP Definition: Target buyer, geography, and pain points      │
│  ✓ PARA Setup: Organized folder structure for deals & data       │
│  ✓ Bilingual Mode: English/French configuration                  │
├──────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                       │
│  + ~~knowledge (Scan): Analyze pitch decks to auto-build profile │
│  + ~~CRM: Sync settings with HubSpot/Pipedrive fields            │
└──────────────────────────────────────────────────────────────────┘
```

---

## What I Will Configure

I will define the following parameters in your local environment:

1.  **Sales Methodology** (e.g., MEDDIC, SPIN, Challenger)
2.  **Ideal Customer Profile (ICP)** (Target Buyer Role)
3.  **Target Geography** (Primary Market)
4.  **Language Preference** (English, French, or Bilingual)
5.  **PARA File Structure** (Data Organization)

All data is stored locally in `sales/data/2-Domaines/sales-profile.json`.

---

## Onboarding Flow

### Step 0: Language Selection

I will first ask for your preferred communication language:

1.  **English** (Default)
2.  **Français**
3.  **Bilingual** (English Mon/Tue/Thu, French Wed/Fri)

### Step 1: Sales DNA Calibration

I will ask 5 specific questions to calibrate the AI model:

1.  **"What do you sell?"** (Product/Service Description)
2.  **"Who is your buyer?"** (Decision Maker Title)
3.  **"What problem do you solve?"** (Primary Pain Point)
4.  **"How do you sell?"** (Preferred Methodology)
5.  **"Where are your clients?"** (Geography/Timezone)

### Step 2: File Structure Setup

I will create the standardized PARA structure for Sales:

```
sales/data/
├── 0-Inbox/              # Unprocessed leads and lists
├── 1-Projets/            # Active deals and campaigns
│   ├── active-deals/     # Deal rooms
│   └── campaigns/        # Outreach sequences
├── 2-Domaines/           # Strategic context
│   ├── sales-profile.json
│   ├── voice-dna.json
│   └── LinkedIn/         # Prospect database & logs
├── 3-Ressources/         # Templates and playbooks
└── 4-Archives/           # Lost or closed deals
```

### Step 3: Activation Summary

```
Sales OS Setup Complete.

Current Profile:
- Role: Founder-Led Sales
- Methodology: MEDDIC
- Focus: B2B SaaS in France/UK

Next Steps:
1. Launch routine: /sales:linkedin
2. Find prospects: /sales:prospect
3. Draft outreach: /sales:engage
```

---

## Agent Instructions

### Execution Steps

```python
config_file = "${CLAUDE_PLUGIN_ROOT}/data/2-Domaines/sales-profile.json"

# 1. Check existing config
if file_exists(config_file):
    ask("Sales OS is already active. Options: [Update] [Reset] [Cancel]")

# 2. Language Selection
language = ask_choice(["English", "Français", "Bilingual"])
lang_code = "fr" if language == "Français" else "en"

# 3. DNA Calibration
print("Calibrating Sales DNA...")
selling_what = ask("What do you sell? (One sentence pitch)")
target_buyer = ask("Who is the decision maker? (Job titles)")
methodology = ask_choice(["MEDDIC", "SPIN", "Challenger", "Sandler", "Custom"])
geo = ask("Primary target geography? (e.g., France, EMEA, US)")

# 4. Create PARA Structure
mkdir -p sales/data/{0-Inbox,1-Projets,2-Domaines,3-Ressources,4-Archives}
mkdir -p sales/data/2-Domaines/LinkedIn
mkdir -p sales/data/1-Projets/{active-deals,campaigns}

# 5. Save Configuration
profile_data = {
    "language": language,
    "product": selling_what,
    "icp": {
        "roles": target_buyer,
        "geography": geo
    },
    "methodology": methodology,
    "setup_date": current_date()
}
write_json(config_file, profile_data)

# 6. Initialize Core Files
if not file_exists("sales/data/2-Domaines/LinkedIn/prospects.md"):
    write_file("sales/data/2-Domaines/LinkedIn/prospects.md", PROSPECT_TEMPLATE)

if not file_exists("sales/data/2-Domaines/LinkedIn/activity_log.md"):
    write_file("sales/data/2-Domaines/LinkedIn/activity_log.md", LOG_TEMPLATE)

# 7. Final Handshake
print("Sales OS Ready.")
suggest_next_step("/sales:linkedin")
```
