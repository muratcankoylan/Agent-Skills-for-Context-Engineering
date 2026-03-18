# Organization Configuration (PARA Method)

Customize this file for your folder structure using the PARA methodology from "Building a Second Brain".

## PARA Folder Structure

```yaml
folders:
  0-Inbox:
    - _REVISE # Files requiring manual attention
  1-Projects: # Active work with deadlines
    - Work
    - Personal
  2-Areas: # Ongoing responsibilities
    - Finances
    - Health
    - Legal
    - Career
    - Home
  3-Resources: # Reference material by topic
    Media:
      - Images
      - Videos
      - Audio
      - Captures
    Tools:
      - Installers
      - Utilities
    Learning:
      - Articles
      - Books
      - Courses
    Templates: []
  4-Archives: # Inactive or completed items
    - Completed-Projects
    - Past-Areas
    - Old-Resources
```

## Project/Client Codes

Define short codes for PARA categories:

```yaml
codes:
  # Projects (active work)
  PROJ: "Active Project"
  CLIENT: "Client Work"

  # Areas (responsibilities)
  FIN: "Finances"
  HEALTH: "Health"
  LEG: "Legal"
  CARR: "Career"

  # Resources (reference)
  REF: "Reference Material"
  LEARN: "Learning"

  # General
  GEN: "General/Uncategorized"
```

## Content Detection Keywords

Keywords to automatically categorize into PARA folders:

```yaml
detection:
  1-Projects:
    - "project"
    - "deadline"
    - "deliverable"
    - "milestone"
    - "sprint"
    - "draft"
    - "revision"
    - "in-progress"
    - "final"

  2-Areas/Finances:
    - "invoice"
    - "receipt"
    - "statement"
    - "tax"
    - "bank"
    - "payment"
    - "expense"
    - "budget"

  2-Areas/Health:
    - "medical"
    - "health"
    - "prescription"
    - "insurance"
    - "doctor"
    - "dental"
    - "laboratory"
    - "results"

  2-Areas/Legal:
    - "contract"
    - "agreement"
    - "nda"
    - "lease"
    - "deed"
    - "will"
    - "court"
    - "legal"

  3-Resources/Media:
    extensions:
      - ".jpg"
      - ".jpeg"
      - ".png"
      - ".gif"
      - ".mp4"
      - ".mov"
      - ".mp3"
      - ".wav"
    patterns:
      - "IMG_*"
      - "DSC_*"
      - "Screenshot*"
      - "Capture*"

  3-Resources/Tools:
    extensions:
      - ".dmg"
      - ".exe"
      - ".pkg"
      - ".msi"
      - ".app"
    keywords:
      - "installer"
      - "setup"
      - "update"

  3-Resources/Learning:
    - "guide"
    - "tutorial"
    - "course"
    - "ebook"
    - "syllabus"
    - "lecture"
    - "reference"
    - "documentation"
```

## Inbox Workflow

Prompts for processing files in 0-Inbox:

```yaml
inbox_workflow:
  daily_review_prompt: |
    It's time for your daily Inbox review! Process the files in 0-Inbox:

    For each file, ask:
    - Is it actionable with a deadline? → 1-Projects
    - Is it an ongoing responsibility? → 2-Areas
    - Is it useful reference material? → 3-Resources
    - Is it completed/inactive? → 4-Archives
    - None of the above? → Delete or keep in Inbox

  weekly_review_prompt: |
    Weekly review time! Let's go:
    1. Empty remaining items from 0-Inbox
    2. Archive completed projects in 1-Projects
    3. Review 2-Areas for items that are no longer relevant
    4. Clean up duplicates in 3-Resources
    5. Organize 4-Archives by year/category
```

## Sensitivity Indicators

Flag files containing:

| Type        | Indicators                    | PARA Location    | Action            |
| :---------- | :---------------------------- | :--------------- | :---------------- |
| Financial   | IBAN, account numbers, taxes  | 2-Areas/Finances | Flag for review   |
| Medical     | Health records, prescriptions | 2-Areas/Health   | Flag for review   |
| Legal       | Contracts, agreements         | 2-Areas/Legal    | Flag for review   |
| Credentials | Passwords, API keys           | DO NOT MOVE      | Alert immediately |

## Behavior Settings

```yaml
settings:
  require_approval_for_renames: true
  require_approval_for_moves: false # Only for HIGH confidence
  require_approval_for_sensitive: true
  never_delete_files: true
  preserve_original_dates: true
  create_review_folder_for_uncertain: true
  skip_files_larger_than_mb: 500
  inbox_processing_enabled: true
  auto_prompt_daily_review: true
  auto_prompt_weekly_review: true
```
