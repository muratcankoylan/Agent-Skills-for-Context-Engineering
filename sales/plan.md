# Plan: Sales Plugin — "RevOps in a Box" for Small Teams

## Context

The current `sales` plugin is a set of useful but disconnected tools. We are upgrading it to a **Stage 3 Plugin** (Agents + Bilingual + Onboarding), acting as a virtual Sales Manager.
Requires `cowork-plugin-customizer` for initial setup.

**Small Team Painpoints:**

1.  **Pipeline Chaos**: Deals rot.
2.  **Inconsistent Process**: No playbook.
3.  **Admin Overload**: CRM data entry is ignored.
4.  **Bilingual Reality**: Selling in EN/FR.

---

## Phase 1: Structural Fixes (Cowork Standard)

### 1.1 Bilingual Infrastructure & Configuration

- **`CLAUDE.md`**: Add "Sales DNA" loader and `~~Placeholders` for personalization.
- **`data/2-Domaines/sales-profile.json`**: Store team specific settings.
  - _Customization Points_: `~~SellingMethodology` (MEDDIC/SPIN), `~~PricingModel`, `~~Competitors`.
  - Used by `cowork-plugin-customizer` to "hydrate" the plugin.

### 1.2 Connector Overhaul (`CONNECTORS.md`)

- **CRM**: HubSpot (Standard Connector), Salesforce.
- **Enrichment**: Clay, Apollo.

---

## Phase 2: The "Virtual Sales Ops" (Agents)

### 2.1 `pipeline-guardian-agent` (The bad cop)

- **Role**: Scans CRM for >14 days stale deals.
- **Logic**: Reads `data/sales/pipeline.md` (or connected CRM) and pings user.

### 2.2 `prep-master-agent` (The EA)

- **Role**: Pre-call battle cards.
- **Trigger**: Calendar event 15m before.

### 2.3 `roleplay-dojo-agent` (The Trainer)

- **Role**: Simulates "The CFO" or "The Skeptic".
- **Logic**: Scores based on `sales-profile.json` methodology.

---

## Phase 3: Bilingual Command Suite

Renaming and wrapping for EN/FR support.

### 3.1 Onboarding (`/sales:start`)

New wizard powered by `cowork-plugin-customizer`.

- Detects language (FR/EN).
- Configures `sales-profile.json` by replacing `~~` placeholders.
- Sets up MCP connections.

### 3.2 Forecasting & Debrief

- `/sales:forecast`: Weighted pipeline analysis.
- `/sales:debrief`: Call to Deal Object sync.

---

## Phase 5: The Sales OS LinkedIn Module ("The Nexius Way")

**Architecture: Local-First, Connector-Second.**
We port the "360Brew" ecosystem from Nexius Labs, adapted for Bilingual Sales.

### 5.1 Infrastructure: The Hub

- **`data/linkedin/prospects.md`**: The local "Source of Truth".
- **`skills/hubspot-sync`**: A **Skill** (not a custom MCP server) that orchestrates the sync.
  - _Mechanism_: Uses the standard **HubSpot Connector** (defined in `CONNECTORS.md`) to read/write data.
  - _Logic_: The Skill prompt handles the intelligence—mapping `prospects.md` columns to HubSpot properties (`touch_count`, `last_touch_date`) and determining Pipeline Stages.
  - _Benefit_: No custom Python code to maintain; leverages the platform's native connectivity.

### 5.2 `linkedin-orchestrator` (The Manager)

- **Port of**: `linkedin-daily-planner`.
- **Role**: Manages the "3-3-3 Rule" and "Golden Windows".
- **Adaptation**:
  - Checks `sales-profile.json` for `~~TargetGeography` (instead of hardcoded ASEAN).
  - Supports "Bilingual Posting Schedule" (EN Tue/Thu, FR Wed/Fri).

### 5.3 `linkedin-prospector` (The Hunter)

- **Port of**: `linkedin-icp-finder`.
- **Requirements**: **MUST use Claude for Chrome**.
- **Mechanism**:
  1.  **Browser Context**: The Agent "sees" what the user sees on LinkedIn via the extension.
  2.  **Scraping**: It reads the DOM (Search Results, Comments) directly from the active tab.
  3.  **Processing**: It filters candidates against `sales-profile.json` criteria _in memory_.
  4.  **Storage**: It writes qualified leads to `data/linkedin/prospects.md`.
- **Why**: Bypasses API limits and "looks like a human" to LinkedIn.

### 5.4 `linkedin-engager` (The Diplomat)

- **Port of**: `linkedin-pro-commenter` + `linkedin-icp-warmer`.
- **Role**: Generates authentic comments (15-50 words).
- **Adaptation**: **Language Detection**. If post is FR, generate FR comment. If EN, generate EN.

### 5.5 `linkedin-creator` (The Author)

- **Port of**: `linkedin-elite-post`.
- **Role**: Creates "Save-Worthy Assets" (Schemas, Checklists).
- **Format**: Markdown with "See More" hooks.

### 5.6 Memory & Rules

- **Activity Log**: `data/linkedin/activity_log.md` must be updated daily (Critical Rule from `memory/MEMORY.md`).
- **Dedup**: Store `author_slug + post_content_hash` to prevent double commenting.

---

## Phase 6: The Autonomous Growth Engine

### 6.1 "Waterfall" Enrichment

- Trigger: New entry in `prospects.md`.
- Action: Clay/Apollo Connector -> update `prospects.md` -> sync to HubSpot.

### 6.2 Signal-Based Outreach

- Trigger: `signal-trapper` detects news.
- Action: Drafts email -> pushes to CRM draft.

---

## Implementation Roadmap

**Standard**: All new skills must be created using the `cowork-plugin-customizer` pattern (using `~~` placeholders for all team-specific values).

| Priority | Component             | Source                     | Adaptation                           |
| :------- | :-------------------- | :------------------------- | :----------------------------------- |
| **P1**   | **HubSpot Connector** | `CONNECTORS.md`            | Config & Auth                        |
| **P1**   | **HubSpot Skill**     | `crm-integration/skill.md` | Port logic to Prompt (No Python)     |
| **P1**   | **Orchestrator**      | `linkedin-daily-planner`   | Read `sales-profile.json`            |
| **P2**   | **Prospector**        | `linkedin-icp-finder`      | Add "Claude for Chrome" Instructions |
| **P2**   | **Engager**           | `linkedin-pro-commenter`   | Add FR Support                       |
| **P3**   | **Creator**           | `linkedin-elite-post`      | Add FR Templates                     |

## Metric of Success

A rep runs `/sales:start`, defines their ICP (FR/EN), and the next day `linkedin-orchestrator` hands them a list of 9 comments to make and 3 connections to send, all synced to HubSpot automatically.
