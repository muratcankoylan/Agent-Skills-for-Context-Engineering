# Sales Plugin: Solo Skill Reuse Analysis

## Executive Summary

The `solo` plugin contains ~64 skills, many of which are "best-in-class" implementations of core business tasks. The `sales` plugin (6 skills) is currently under-powered.

**Strategy:** Instead of reinventing the wheel, we should **port 20+ skills** from `solo` to `sales`, adapting them for a "Team" context where necessary.

---

## 1. Direct Ports (Copy & Paste)

These skills are foundational and context-agnostic. They should be copied entirely to `sales/skills/`.

| Solo Skill                        | Why it's needed in Sales                                 | Adjustment needed                   |
| :-------------------------------- | :------------------------------------------------------- | :---------------------------------- |
| **`voice-dna-creator`**           | Sales reps need to sound authentic, not like ChatGPT.    | None.                               |
| **`icp-creator`**                 | Defines who we are selling to (Ideal Customer Profile).  | None.                               |
| **`exa-search-expert`**           | The engine for deep account research.                    | None.                               |
| **`antislop-expert`**             | Essential for reviewing emails/proposals before sending. | None.                               |
| **`linkedin-post`**               | Social selling is critical for B2B sales.                | Rename context to "Social Selling". |
| **`context-engineering-advisor`** | Handles RAG/Retrieval for large PDF contracts/RFPs.      | None.                               |

---

## 2. Adaptation Candidates (Logic Reuse, Context Shift)

These skills contain excellent logic but need "Single Player" -> "Multiplayer/Team" adjustments.

| Solo Skill                 | Target in Sales      | Changes Required                                                    |
| :------------------------- | :------------------- | :------------------------------------------------------------------ |
| `draft-outreach`           | `outbound-sequence`  | Add "Sequence" logic (Step 1, 2, 3) and Team Templates.             |
| `discovery-call`           | `discovery-master`   | Add "Methodology" enforcement (MEDDIC/SPIN check).                  |
| `proposal-generator`       | `proposal-builder`   | Add "Price Book" and "Legal Terms" locking for teams.               |
| `monday-morning-agent`     | `daily-standup`      | Focus on "Pipeline Updates" instead of "Solopreneur Tasks".         |
| `pipeline-staleness-agent` | `pipeline-guardian`  | Add "Manager Alert" mode (cc the manager if deal rots).             |
| `client-management`        | `account-management` | Add support for "Buying Committee" (multiple contacts per account). |

---

## 3. Consolidation (Merge Solo Logic into Sales Skills)

Merging superior `solo` logic into existing `sales` placeholders.

| Existing Sales Skill       | Upgrade Source (Solo)                       | Strategy                                                                                         |
| :------------------------- | :------------------------------------------ | :----------------------------------------------------------------------------------------------- |
| `account-search`           | `company-research` + `exa-search-expert`    | **Replace completely**. The Solo version searches the web; Sales version is likely basic.        |
| `call-prep`                | `discovery-interview-prep`                  | **Merge**. Add the "Question Architecture" from Solo to the Sales prep.                          |
| `competitive-intelligence` | `positioning-statement` + `pestel-analysis` | **Enhance**. Use Solo's strategic frameworks to analyze competitors deeper than just "features". |

---

## 4. New "Sales-Specific" Skills (No Equivalent in Solo)

Gaps that `solo` cannot fill.

| Missing Skill               | Description                                                 |
| :-------------------------- | :---------------------------------------------------------- |
| **`negotiation-advisor`**   | BATNA analysis, concession planning, pricing defense.       |
| **`rfp-shredder`**          | Analyzing complex RFPs (Request for Proposal) for Go/No-Go. |
| **`territory-planner`**     | Planning account coverage for a team.                       |
| **`commission-calculator`** | Motivating reps by showing potential earnings.              |

---

## Recommendation for "Phase 1" Implementation

Don't build from scratch. **Immediately port these 5 high-impact skills**:

1.  `voice-dna-creator` (Identity)
2.  `exa-search-expert` (Intelligence)
3.  `antislop-expert` (Quality Control)
4.  `discovery-call` (Process)
5.  `draft-outreach` (Execution)

This instantly gives the `sales` plugin "Superpowers" without writing new logic.
