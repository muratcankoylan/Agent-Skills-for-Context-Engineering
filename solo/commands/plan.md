---
description: "Organize your files with PARA methodology and review active projects"
argument-hint: "[organize | review]"
allowed-tools: Read, Write, Glob
model: sonnet
---

# /solo:plan

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

Organize your digital workspace and review active projects. Keep files structured with the PARA methodology (Projects, Areas, Resources, Archives).

## Usage

```
/solo:plan organize    # Organize files with PARA method
/solo:plan review      # Review current projects and pipeline
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                    PLANNING & ORGANIZATION                        │
├──────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                        │
│  ✓ Content calendar: 30-day editorial plan with pillar rotation  │
│  ✓ PARA organization: Smart file categorization                  │
│  ✓ Project review: Current status across all active work         │
│  ✓ Inbox triage: Process new files and ideas                     │
├──────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when you connect your tools)                       │
│  + ~~social: Pull performance data to optimize content mix       │
│  + ~~calendar: Auto-schedule content publication dates           │
│  + ~~project tracker: Sync PARA projects with task management    │
│  + ~~knowledge base: Index organized files for search            │
└──────────────────────────────────────────────────────────────────┘
```

---

## /solo:plan organize

Organize your files using the PARA methodology (Projects, Areas, Resources, Archives).

### What is PARA?

| #     | Category  | Contains                      | Lifespan   |
| ----- | --------- | ----------------------------- | ---------- |
| **0** | Inbox     | New files awaiting processing | Temporary  |
| **1** | Projects  | Active work with deadlines    | Short-term |
| **2** | Areas     | Ongoing responsibilities      | Long-term  |
| **3** | Resources | Reference material by topic   | Permanent  |
| **4** | Archives  | Inactive or completed items   | Preserved  |

### Usage

```
/solo:plan organize              # Full PARA setup
/solo:plan organize --inbox      # Process inbox only
/solo:plan organize --review     # Review current structure
```

### Interactive Flow

1. **Scan Current State**
   - Count files in each directory
   - Identify poorly named files
   - Assess organization quality

2. **Create PARA Structure** (if needed)

   ```
   data/
   ├── 0-Inbox/
   ├── 1-Projets/
   │   ├── clients/
   │   ├── invoices/
   │   └── [project-name]/
   ├── 2-Domaines/
   │   ├── business-profile.json
   │   ├── voice-dna.json
   │   └── icp.json
   ├── 3-Ressources/
   │   ├── templates/
   │   └── references/
   ├── 4-Archives/
   └── _ORG/
       ├── _PLAN.md
       ├── _LOG.md
       └── _MANIFEST.md
   ```

3. **Process Inbox**
   - For each file, ask: "Is this actionable with a deadline?"
     - Yes → Move to `1-Projets/`
     - No → Continue...
   - "Is this an ongoing responsibility?"
     - Yes → Move to `2-Domaines/`
     - No → Continue...
   - "Is this useful reference material?"
     - Yes → Move to `3-Ressources/`
     - No → Move to `4-Archives/` or delete

4. **Rename Poorly Named Files**
   - Generic names: `Document1.pdf`, `Untitled.docx`
   - Camera names: `IMG_1234.jpg`, `DSC_5678.png`
   - Suggest format: `YYYY-MM-DD_CATEGORY_description.ext`

### Output

```
✅ PARA Organization Complete

Files organized:
  - 0-Inbox: 0 files (cleared!)
  - 1-Projets: 12 files (5 active projects)
  - 2-Domaines: 8 files (business data)
  - 3-Ressources: 24 files (templates, references)
  - 4-Archives: 156 files (old projects)

Actions taken:
  - Renamed 8 files with generic names
  - Moved 15 files from Inbox to Projects
  - Archived 3 completed projects
  - Created 2 new project folders

Organization log saved to:
  data/_ORG/_MANIFEST.md

Next steps:
  - Review projects: /solo:plan review
  - Weekly inbox review: /solo:plan organize --inbox
  - Archive old projects monthly
```

---

## /solo:plan review

Review current projects, content status, and upcoming work.

### Output

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROJECT & CONTENT REVIEW — February 13, 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 ACTIVE PROJECTS (5)

| Project                 | Status      | Phase     | Next Action           | Due    |
| ----------------------- | ----------- | --------- | --------------------- | ------ |
| Client Portal           | In progress | Prototype | Finish Figma mockups  | Feb 20 |
| Website Redesign (Acme) | Active      | Design    | Send design brief     | Feb 15 |
| Newsletter System       | Planning    | Discover  | User interviews       | Feb 18 |
| Personal Brand Refresh  | Stalled     | -         | Resume or archive?    | -      |
| SaaS Idea Validation    | Active      | Validate  | Run landing page test | Feb 25 |

⚠️ 1 project stalled (Personal Brand Refresh)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 CONTENT STATUS

This week's content (Week 2):
✅ Mon: LinkedIn post published (Social Proof)
✅ Tue: Blog post published (Expertise)
🔄 Wed: LinkedIn post in draft (Opinion)
⏳ Thu: Newsletter not started
⏳ Fri: LinkedIn post idea only

Status: 2/5 complete (40%)

Next week's content (Week 3):
💡 All in "Idea" status
⚠️ Need to start drafting by Friday

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📥 INBOX STATUS

- 0-Inbox: 3 files awaiting processing
- Last processed: 5 days ago

⚠️ Inbox needs attention

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RECOMMENDED ACTIONS:

Priority 1: Complete this week's content

- Finish Wed LinkedIn post (Opinion pillar)
- Draft Thu newsletter
- Outline Fri LinkedIn post

Priority 2: Process inbox

- Run: /solo:plan organize --inbox

Priority 3: Review stalled project

- Decision needed: Resume or archive "Personal Brand Refresh"

Quick commands:
/solo:write newsletter "How to validate product ideas in 48 hours"
/solo:plan organize --inbox
/solo:build status "Client Portal"
```

---

## Agent Instructions

### /solo:plan organize

```python
# 1. Scan current state
files = scan_directory("data/")
poorly_named = identify_generic_names(files)
inbox_files = list_files("data/0-Inbox/")

# 2. Check if PARA structure exists
if not para_structure_exists():
    create_para_structure()
    create_org_tracking_files()

# 3. Process inbox
if get_flag("--inbox") or inbox_files:
    for file in inbox_files:
        category = ask_choice([
            "1-Projets (active work with deadline)",
            "2-Domaines (ongoing responsibility)",
            "3-Ressources (reference material)",
            "4-Archives (completed/inactive)",
            "Delete"
        ])

        if category != "Delete":
            destination = map_category_to_path(category)
            move_file(file, destination)
            log_to_manifest(file, destination)

# 4. Rename poorly named files
if poorly_named:
    for file in poorly_named:
        content_summary = analyze_file_content(file)
        suggested_name = suggest_filename(content_summary)

        if ask_yes_no(f"Rename '{file.name}' to '{suggested_name}'?"):
            rename_file(file, suggested_name)
            log_to_manifest(file, suggested_name)

# 5. Display summary
display_para_summary(files_by_category, actions_taken)
```

### /solo:plan review

```python
# 1. Scan projects
project_dirs = glob("data/1-Projets/*/")
projects = []

for project_dir in project_dirs:
    if project_dir in ["clients", "invoices"]:
        continue  # Skip special directories

    status_file = f"{project_dir}/pipeline-status.md"
    if file_exists(status_file):
        status = parse_pipeline_status(status_file)
        projects.append(status)

# 2. Check content calendar
calendar_file = find_current_content_calendar()
if calendar_file:
    calendar = parse_content_calendar(calendar_file)
    content_status = analyze_content_progress(calendar)
else:
    content_status = None

# 3. Check inbox
inbox_count = count_files("data/0-Inbox/")
last_processed = get_last_inbox_process_date()

# 4. Display review
display_project_review(projects, content_status, inbox_count, last_processed)
```

---

## Tips

1. **Plan content in batches** — Create a month's calendar, then batch-write Week 1, then Week 2, etc. More efficient than daily planning.

2. **Rotate pillars evenly** — Don't post 5 "Expertise" posts in a row. Mix it up to keep your audience engaged.

3. **Process inbox weekly** — Set a recurring calendar event. 15 minutes every Friday to clear your inbox.

4. **Archive completed projects** — When a project is done, move it to `4-Archives/[project-name]/`. Keeps your active projects list clean.

**PARA is flexible** — The categories are guidelines. Adapt the structure to your workflow.

---

## Integration with Other Commands

- **For project planning:** Use `/solo:build discover` to start new product projects
- **Weekly review:** Use `/solo:weekly-review` to see content + projects + business metrics together

---

## Skills Used

This command uses these skills:

- `para-organizer` — PARA file organization
- `project-management` — Project status tracking
