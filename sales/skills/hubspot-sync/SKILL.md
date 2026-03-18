---
name: hubspot-sync
description: >
  Synchronize local LinkedIn prospect data to HubSpot CRM.
  Trigger with "sync to HubSpot", "update CRM", or "push prospects".
  Reads `data/linkedin/prospects.md`, parses the markdown table, and uses the HubSpot Connector to create/update contacts.
  Handles custom properties like `touch_count`, `last_touch_date`, and `linkedin_profile`.
  Supports bilingual logging (EN/FR).
bundle: pipeline-ops
triggers:
  - "sync to HubSpot"
  - "update CRM"
  - "push prospects"
tools:
  standalone: [hubspot]
  supercharged: [hubspot]
version: 1.0.0
---

# HubSpot Sync

Synchronize your local "Source of Truth" (`data/linkedin/prospects.md`) with your System of Record (HubSpot).

## Mechanics

This skill does NOT use a custom Python backend. It relies on the standard **HubSpot Connector**.
It leverages Claude's ability to read the markdown file and translate it into Connector calls.

### Trigger Phrases

- "sync to hubspot"
- "update crm"
- "push prospects"
- "save to hubspot"

## Workflow

1.  **Read Source**: Read `data/linkedin/prospects.md`.
2.  **Read Config**: Read `sales-profile.json` to get the `~~HubSpotKey` logic (handled by connector, but good to check pipeline mapping).
3.  **Parse**: Extract the table rows.
4.  **Sync Loop**: For each prospect in the list:
    - **Check**: Search HubSpot for existing contact by Email or LinkedIn URL (`hubspot_crm.search_contacts`).
    - **Upsert**:
      - If found: Update properties (`touch_count`, `last_touch_date`, `status`).
      - If not found: Create new contact (`hubspot_crm.create_contact`).
5.  **Log**: Report success/failure for each record.

## Property Mapping

| Local Column    | HubSpot Property        | Logic                                              |
| :-------------- | :---------------------- | :------------------------------------------------- |
| **Name**        | `firstname`, `lastname` | Split by first space                               |
| **Role**        | `jobtitle`              | Direct map                                         |
| **Company**     | `company`               | _Note: Requires Company association in v2_         |
| **Email**       | `email`                 | Primary key                                        |
| **Profile URL** | `linkedin_profile`      | Custom Property (Must exist)                       |
| **Status**      | `lifecyclestage`        | Map: `Lead` -> `Subscriber`, `Qualified` -> `Lead` |
| **Touches**     | `touch_count`           | Custom Property (Number)                           |

## Prerequisite: Custom Properties

If the user runs this for the first time, check if these properties exist. If not, ask the user to create them in HubSpot or try to create them via connector if permissions allow:

- `linkedin_profile` (Text)
- `touch_count` (Number)
- `last_touch_date` (Date)

## Instructions for the Agent

1.  **Always** read `data/linkedin/prospects.md` first.
2.  **Ask** for confirmation if syncing > 10 records at once ("Ready to sync 15 prospects?").
3.  **Error Handling**: If HubSpot Connector fails, output a clear error: "HubSpot Connector not active. Please run `/sales:start` to connect."
4.  **Bilingual Output**: Check `sales-profile.json` `language_preference`. If "FR", output logs in French ("✅ Synchronisé: John Doe").

## Example Command

```bash
# User says "Sync John Doe"
# Agent action:
read_file("data/linkedin/prospects.md")
# ... finds John Doe row ...
hubspot_crm.search_contacts(query="john@doe.com")
# ... returns ID 123 ...
hubspot_crm.update_contact(contact_id="123", properties={"touch_count": "3"})
```
