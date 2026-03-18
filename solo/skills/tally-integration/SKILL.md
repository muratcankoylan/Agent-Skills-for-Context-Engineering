---
name: tally-integration
description: >
  Handles all interactions with Tally via the Model Context Protocol (MCP).
  Creates Tally forms from diagnostic definitions, fetches submissions, registers
  webhooks, and syncs response data back into Solo's data layer.
  Triggered internally by diagnostic-builder (publish step), diagnostic-runner
  (share --tally), and diagnostic-analyzer (results --tally).
version: 1.0.0
requires_mcp: tally
bundle: diagnostics
triggers:
  - "tally form"
  - "connect tally"
  - "tally responses"
tools:
  standalone: ["tally"]
  supercharged: ["tally"]
---

# Skill: Tally Integration

This skill is the bridge between Solo's diagnostic system and Tally forms. It uses the Tally MCP server to create, manage, and read forms — so that diagnostics built in Solo can be shared as polished Tally forms, and responses collected in Tally flow back into Solo automatically.

---

## MCP Configuration

The Tally MCP server runs at `https://api.tally.so/mcp`.

**How Claude connects:**

The user must have the Tally MCP server configured in their Claude setup. Two methods:

**Option A — OAuth (recommended, claude.ai):**
Add to MCP servers: `https://api.tally.so/mcp`
Claude will prompt for OAuth on first use.

**Option B — API Key (Claude Desktop / CLI):**
```json
{
  "mcpServers": {
    "tally": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://api.tally.so/mcp",
        "--header",
        "Authorization: Bearer YOUR_TALLY_API_KEY"
      ]
    }
  }
}
```

Get your API key at: https://tally.so/settings/api-keys

**Checking connection:**
Before any Tally operation, verify the MCP server is available. If not, surface a clear setup message (see "MCP Not Connected" section below).

---

## Operation 1: Create Form from Diagnostic

**Triggered by:** `diagnostic-builder` (end of build flow) or `diagnostic-runner` (share --tally)

**Input:** A diagnostic definition JSON file

**What it does:**
Translates the diagnostic definition into a Tally form with all questions, options, and metadata — then creates it via MCP.

### Form Structure Mapping

```
Diagnostic definition → Tally form

definition.tally_export.form_title       → form title
definition.tally_export.form_description → form description
definition.tally_export.collect_fields   → lead fields at the start

Then, for each dimension:
  dimension.name                         → section header block
  Each question in dimension.questions   → multiple choice block
    question.text                        → question label
    Each option in question.options      → answer choice
```

### Question-to-Form-Field Mapping

| Diagnostic field type | Tally block type      |
|----------------------|----------------------|
| `multiple_choice`    | `MULTIPLE_CHOICE`    |
| Text collection      | `INPUT_TEXT`         |
| Email collection     | `INPUT_EMAIL`        |
| Dimension separator  | `FORM_TITLE` (H2)    |

### Building the Form (step by step)

```python
def create_tally_form_from_diagnostic(definition):
    blocks = []
    
    # 1. Intro / welcome block
    blocks.append({
        "type": "FORM_TITLE",
        "payload": {
            "html": f"<h1>{definition['tally_export']['form_title']}</h1>"
                    f"<p>{definition['tally_export']['form_description']}</p>"
        }
    })
    
    # 2. Lead capture fields (before the questions)
    collect_fields = definition["tally_export"].get("collect_fields", [])
    
    if "name" in collect_fields:
        blocks.append({
            "type": "INPUT_TEXT",
            "payload": { "label": "Your name", "isRequired": True }
        })
    if "email" in collect_fields:
        blocks.append({
            "type": "INPUT_EMAIL",
            "payload": { "label": "Your email", "isRequired": True }
        })
    if "company" in collect_fields:
        blocks.append({
            "type": "INPUT_TEXT",
            "payload": { "label": "Company", "isRequired": False }
        })
    
    # 3. For each dimension: section header + questions
    for dim in definition["dimensions"]:
        
        # Section header
        blocks.append({
            "type": "FORM_TITLE",
            "payload": {
                "html": f"<h2>{dim['name']}</h2>"
            }
        })
        
        # Questions
        for q in dim["questions"]:
            blocks.append({
                "type": "MULTIPLE_CHOICE",
                "payload": {
                    "label": q["text"],
                    "isRequired": True,
                    "options": [
                        { "text": opt["label"] }
                        for opt in q["options"]
                    ]
                }
            })
    
    # 4. Create the form via MCP
    form = mcp_tally.create_form({
        "name": definition["tally_export"]["form_title"],
        "blocks": blocks
    })
    
    return form  # { "id": "abc123", "url": "https://tally.so/r/abc123" }
```

### After Form Creation

1. **Save the Tally form ID back to the diagnostic definition:**
```python
definition["tally_export"]["form_id"] = form["id"]
definition["tally_export"]["form_url"] = form["url"]
definition["updated"] = today()
write_file(definition_path, definition)
```

2. **Register a webhook** (if the user has a webhook endpoint, or skip and use manual pull):
```python
# Optional — see Operation 3: Webhook Setup
```

3. **Confirm to user:**
```
✓ Tally form created: [form_title]
🔗 Share this URL: https://tally.so/r/[form_id]

Responses will appear in Tally as prospects complete the form.
Run `/solo:diagnose results [name] --tally` to pull submissions back into Solo.
```

---

## Operation 2: Fetch Submissions from Tally

**Triggered by:** `diagnostic-analyzer` when `--tally` flag is used, or when `tally_export.form_id` exists in definition

**Input:** `form_id` from `definition.tally_export.form_id`

**What it does:** Fetches all submissions from Tally, maps answers back to question scores, and imports them as Solo response files.

### Fetching Submissions

```python
def fetch_tally_submissions(form_id):
    submissions = mcp_tally.list_submissions(form_id=form_id)
    return submissions
    # Returns: list of { id, createdAt, fields: [{ label, value }] }
```

### Mapping Submission Answers to Scores

Because Tally stores the option text (not the score), the mapper must match answer text back to the diagnostic definition to recover scores.

```python
def map_submission_to_scores(submission, definition):
    """
    Match each submission field back to a question in the diagnostic definition,
    then look up the score for the selected answer label.
    """
    scored_answers = []
    
    for field in submission["fields"]:
        question = find_question_by_text(field["label"], definition)
        if not question:
            continue  # Skip lead-capture fields (name, email, company)
        
        selected_option = find_option_by_label(field["value"], question["options"])
        scored_answers.append({
            "question_id": question["id"],
            "selected": field["value"],
            "score": selected_option["score"] if selected_option else 0
        })
    
    return scored_answers

def find_option_by_label(answer_text, options):
    """Fuzzy match answer text to option label."""
    for opt in options:
        if opt["label"].strip().lower() == answer_text.strip().lower():
            return opt
    # Fallback: partial match
    for opt in options:
        if opt["label"].strip().lower() in answer_text.strip().lower():
            return opt
    return None
```

### Calculating Score from Submission

Once answers are mapped to scores, apply the same scoring formula as the conversational runner:

```python
def score_submission(scored_answers, definition):
    dimension_scores = {}
    
    for dim in definition["dimensions"]:
        dim_raw = sum(
            a["score"] for a in scored_answers
            if get_question_dimension(a["question_id"], definition) == dim["id"]
        )
        dim_max = dim["max_points"]
        dim_weight = dim["weight"]
        
        contribution = (dim_raw / dim_max) * dim_weight * 100
        dimension_scores[dim["id"]] = {
            "raw": dim_raw,
            "max": dim_max,
            "percentage": round((dim_raw / dim_max) * 100),
            "weighted_contribution": round(contribution, 1)
        }
    
    total = round(sum(d["weighted_contribution"] for d in dimension_scores.values()))
    band = get_band(total, definition["scoring"]["bands"])
    
    return total, band, dimension_scores
```

### Saving Imported Submissions

For each new submission, generate a Solo response file using the same format as `_RESPONSE-TEMPLATE.md`:

```python
def save_tally_submission(submission, definition, total, band, dim_scores):
    respondent_name = get_field_value(submission, "Your name") or "Unknown"
    respondent_email = get_field_value(submission, "Your email") or ""
    respondent_company = get_field_value(submission, "Company") or ""
    date_str = submission["createdAt"][:10]
    slug = slugify(respondent_name)
    
    path = f"{definition['routing']['save_response_to']}{date_str}-{slug}-tally.md"
    
    # Check if already imported (avoid duplicates)
    if file_exists(path):
        return None
    
    content = render_response_template(
        definition=definition,
        respondent={"name": respondent_name, "email": respondent_email, "company": respondent_company},
        total=total,
        band=band,
        dim_scores=dim_scores,
        answers=submission["fields"],
        mode="tally",
        date=date_str
    )
    
    write_file(path, content)
    return path
```

### Sync Summary

After processing all submissions, report:

```
## Tally Sync — [Diagnostic Name]

Fetched [N] submissions from Tally
  → [X] new responses imported
  → [Y] already on file (skipped)

New responses saved to: data/1-Projets/diagnostics/[id]/responses/

Run `/solo:diagnose results [name]` to analyze all responses.
```

---

## Operation 3: Webhook Setup (Optional)

**Purpose:** Register a Tally webhook so new submissions auto-import into Solo without manual sync.

**Note:** This requires a publicly accessible webhook endpoint. Most Solo users won't have one. Default is manual sync via `--tally` flag. Offer webhook setup only when the user has an endpoint URL.

```python
def register_tally_webhook(form_id, endpoint_url):
    webhook = mcp_tally.create_webhook({
        "formId": form_id,
        "url": endpoint_url,
        "events": ["FORM_RESPONSE"]
    })
    return webhook
```

---

## Operation 4: Update Existing Form

**Triggered by:** User asks to update a Tally form after modifying a diagnostic definition

```python
def update_tally_form(form_id, definition):
    # Rebuild blocks from updated definition
    blocks = build_blocks_from_definition(definition)
    
    mcp_tally.update_form(form_id=form_id, payload={"blocks": blocks})
    
    print(f"✓ Tally form updated: https://tally.so/r/{form_id}")
```

---

## Diagnostic Schema Extension

The `tally_export` field in every diagnostic `.json` is extended to store Tally state:

```json
"tally_export": {
  "form_title": "Is Now the Right Time?",
  "form_description": "8 minutes. Honest answers. A clear picture of where things stand.",
  "collect_fields": ["name", "email", "company"],

  "form_id": null,
  "form_url": null,
  "published_at": null,
  "last_synced_at": null,
  "submission_count": 0
}
```

| Field | Set when | Used by |
|---|---|---|
| `form_id` | Form is created | Sync, update, fetch |
| `form_url` | Form is created | Display to user |
| `published_at` | Form is first created | Audit trail |
| `last_synced_at` | Submissions are fetched | Incremental sync |
| `submission_count` | After each sync | Quick status |

---

## MCP Not Connected

If the Tally MCP server is not configured, surface this message and stop:

```
⚠️  Tally MCP server not connected.

To use Tally features, add the Tally MCP server to your Claude setup:

  Server URL: https://api.tally.so/mcp

Options:
  A) OAuth (claude.ai): Add the URL above to your MCP servers.
     Claude will prompt you to authorize via Tally.

  B) API key (Claude Desktop):
     Get your key → https://tally.so/settings/api-keys
     Add to claude_desktop_config.json:

     {
       "mcpServers": {
         "tally": {
           "command": "npx",
           "args": [
             "mcp-remote",
             "https://api.tally.so/mcp",
             "--header",
             "Authorization: Bearer YOUR_KEY_HERE"
           ]
         }
       }
     }

Once connected, re-run the command.
Without Tally, you can still use /solo:diagnose share [name] --claude
to generate a self-service package.
```

---

## Error Handling

| Error | Cause | Recovery |
|---|---|---|
| MCP not available | Server not configured | Show setup message above |
| Form creation failed | API error or invalid payload | Log error, fall back to spec output |
| Submission fetch returned 0 | Form has no submissions yet | Inform user, suggest sharing form URL |
| Answer label not matched | Option text changed in Tally | Log unmatched field, score as 0, flag in report |
| Duplicate import | Submission already saved | Skip silently, count in sync summary |
| Form ID not found | Tally form was deleted | Clear `form_id` from definition, offer to recreate |
