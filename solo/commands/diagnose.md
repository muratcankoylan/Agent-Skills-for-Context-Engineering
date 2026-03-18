---
description: "Create, run, and analyze scored diagnostic assessments — qualify leads, monitor clients, validate products, and assess your own business"
argument-hint: "[create | run | results | library | share]"
allowed-tools: Read, Write, Glob
model: sonnet
---

# /solo:diagnose

> Diagnostics work standalone. No external tools required. Every question, score, and recommendation runs natively through Claude.

A diagnostic is a set of weighted questions that produces a personalized score and recommendation. Unlike a survey (which collects opinions) or a form (which captures data), a diagnostic delivers a **verdict with context** — this person is ready for a proposal, this client is at risk, this market signal is strong.

## Usage

```
/solo:diagnose create              # Build a new diagnostic from scratch (guided)
/solo:diagnose run [name]          # Run a diagnostic live in this session
/solo:diagnose results [name]      # Analyze responses across all runs
/solo:diagnose library             # See all your saved diagnostics
/solo:diagnose share [name]        # Generate a self-service package to send async
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                    DIAGNOSTIC SYSTEM                              │
├──────────────────────────────────────────────────────────────────┤
│  ALWAYS WORKS (standalone)                                        │
│  ✓ Build: guided 6-step creation — purpose, dimensions,          │
│    questions, scoring, band recommendations, routing             │
│  ✓ Run: conversational session — Claude asks, scores, delivers   │
│  ✓ Share: self-service package to send via email or Claude prompt│
│  ✓ Analyze: pattern analysis across all responses                │
│  ✓ Route: results automatically flow into clients, pipeline,     │
│    project files, and weekly briefing                            │
├──────────────────────────────────────────────────────────────────┤
│  SUPERCHARGED (when connected)                                    │
│  + tally: publish diagnostics as real Tally forms — no Tally    │
│    builder required. Claude creates the form, returns the URL,  │
│    and pulls submissions back for scoring. One command.          │
│    → /solo:diagnose share [name] --tally                        │
│    → /solo:diagnose results [name] --tally                      │
│    Setup: add https://api.tally.so/mcp to your MCP servers      │
│  + ~~email: send self-service packages directly from Solo        │
│  + ~~CRM: sync scores and bands to HubSpot / Pipedrive fields   │
│  + ~~calendar: auto-book follow-up calls for high-band leads     │
└──────────────────────────────────────────────────────────────────┘
```

---

## The 5 Diagnostic Types

| Type | Use case | Connects to |
|------|---------|-------------|
| **Lead** | Qualify prospects before the first call | `sales-pipeline`, `draft-outreach` |
| **Client** | Monitor health and early churn signals | `client-lifecycle-agent`, client card |
| **Onboarding** | Check readiness before project kickoff | `client-onboarding`, `project-management` |
| **Product** | Validate market demand signal | `/solo:build validate` |
| **Self** | Assess your own business, pricing, or positioning | `business-health-advisor`, `weekly-review` |

---

## /solo:diagnose create

Build a new diagnostic. Claude guides you through the full design in ~15 minutes.

**What I'll do:**

1. Clarify your purpose (what decision does this diagnostic inform?)
2. Propose 4–6 dimensions, confirm and set weights
3. Draft 2–3 questions per dimension with scored answer options
4. Write three band recommendations (Low / Medium / High) in your voice
5. Configure routing (where do results go in Solo?)
6. Save the definition and generate a Tally form spec (optional)

**Then:**
Run it immediately with `/solo:diagnose run [name]`
Or send async with `/solo:diagnose share [name]`

**Starting the creation:**

Tell me:
```
What's the diagnostic for? 
(e.g., "qualifying leads before I send proposals", 
       "checking if my clients are happy mid-project",
       "validating if there's demand for my SaaS idea")
```

---

## /solo:diagnose run [name]

Run a diagnostic live in this Claude session — with you, a prospect, or a client.

**Usage:**
```
/solo:diagnose run lead-qualifier
/solo:diagnose run client-health-q2
/solo:diagnose run "my business clarity check"
```

**If no name is given:** I'll show your diagnostic library and ask which one to run.

**What happens:**
1. I load the diagnostic definition
2. I ask you: who is this session for? (or "run it on myself" for self-assessments)
3. I conduct the session — one question at a time — and track scores invisibly
4. After the last question, I reveal the score, dimension breakdown, and personalized recommendation
5. I route the result into Solo (lead card / client card / project log) based on your routing configuration
6. If it's a lead diagnostic, I offer to draft a follow-up message in your voice

**Session example:**

```
Running: Lead Qualifier v1
For: Sarah Chen, VP Product at Acme Corp

I'm going to walk Sarah through 12 questions across 4 areas.
It takes about 8 minutes. Ready to start?

[If yes:]

---

Sarah, I'm going to ask you a few questions to understand where 
your team is right now. There are no right answers — just where 
things actually stand. This takes about 8 minutes.

Ready? Let's start with how your team currently handles [area].

**Q1: How would you describe the problem you're trying to solve right now?**

A) I have a general sense that something isn't working but can't fully articulate it yet
B) I know what the problem is but I'm not sure if it's the right priority
C) I can describe the problem clearly — I just need help solving it
D) I've already diagnosed the root cause and I know what a solution looks like
```

---

## /solo:diagnose results [name]

Analyze all responses collected for a diagnostic. Shows score distribution, dimension averages, segment patterns, and actionable recommendations.

**Usage:**
```
/solo:diagnose results lead-qualifier
/solo:diagnose results              # Shows results for all diagnostics
/solo:diagnose results lead-qualifier --since 2026-01-01
/solo:diagnose results lead-qualifier --tally   # Pull latest submissions from Tally first, then analyze
```

**`--tally` flag:** If the diagnostic has a linked Tally form (`tally_export.form_id` is set), fetches all new submissions from Tally via MCP, scores and imports them, then runs the full analysis on the combined dataset.

**Requires:** 3+ responses for basic analysis, 10+ for reliable patterns.

**Output preview:**

```
## Lead Qualifier Results — 23 responses (Jan–Feb 2026)

Score distribution:
🟢 High (66–100): 8 respondents — 35% — avg 74
🟡 Medium (36–65): 11 respondents — 48% — avg 51
🔴 Low (0–35): 4 respondents — 17% — avg 28

Dimension averages:
  Problem Clarity:    71% ████████████████████░░░░
  Pain Acuity:        64% ████████████████░░░░░░░░
  Decision Readiness: 48% ████████████░░░░░░░░░░░░ ← lowest
  Budget Reality:     55% █████████████░░░░░░░░░░░

Key finding: Decision Readiness is consistently the weakest dimension.
Most respondents are still exploring, not ready to commit. 
Your CTA is reaching people too early in their process.

Recommendations:
→ Add nurture content between form completion and call booking
→ Adjust medium-band CTA from "book a call" to "download the guide"
→ Consider adding a Timeline question to filter for urgency
```

---

## /solo:diagnose library

View all saved diagnostic definitions.

**Output:**

```
## Your Diagnostic Library

| Name | Type | Questions | Responses | Last run |
|------|------|-----------|-----------|---------|
| Lead Qualifier v1 | Lead | 12 | 23 | Feb 15 |
| Client Health Check | Client | 10 | 8 | Feb 12 |
| SaaS Idea Validator | Product | 8 | 0 | — |
| Pricing Clarity | Self | 6 | — | Feb 10 (self) |

Commands:
  /solo:diagnose run [name]      # Run a session
  /solo:diagnose results [name]  # See analysis
  /solo:diagnose share [name]    # Generate async package
```

---

## /solo:diagnose share [name]

Generate a self-service package to send to a prospect or client asynchronously.

Two formats:

**Format 1: Claude self-service prompt**
A standalone block of text the respondent pastes into their own Claude conversation. Claude walks them through the assessment and delivers their score immediately. They send you the result.

**Format 2: Tally form (live)**
Creates a real, shareable Tally form via the Tally MCP server. No manual building required — Claude translates the diagnostic definition into a complete Tally form with all questions, collect fields, and section headers, then returns the live URL.

Requires the Tally MCP server to be connected (`https://api.tally.so/mcp`).
See `skills/tally-integration/SKILL.md` for setup instructions.

**Usage:**
```
/solo:diagnose share lead-qualifier              # Outputs Claude self-service package
/solo:diagnose share lead-qualifier --tally      # Creates real Tally form via MCP → returns live URL
/solo:diagnose share lead-qualifier --claude     # Claude package only
```

**What `--tally` does:**
1. Reads the diagnostic definition
2. Invokes `tally-integration` skill to create the form via MCP
3. Saves the Tally `form_id` and `form_url` back to the diagnostic definition
4. Returns the shareable URL: `https://tally.so/r/[form_id]`
5. Confirms how to pull submissions back: `/solo:diagnose results [name] --tally`

**With `~~email` connected:**
```
/solo:diagnose share lead-qualifier --send sarah@acme.com
```

---

## Integration Map

Diagnostics connect to the rest of Solo automatically based on type and routing configuration:

```
Lead diagnostic completed
  → Lead card created in data/1-Projets/clients/
  → Pipeline stage set (high = Proposal, medium = Discovery)
  → monday-morning-agent briefed on high-band leads
  → draft-outreach invoked for follow-up message

Client health diagnostic completed
  → health_score field updated in client card
  → If score < 40: ⚠️ flag set, client-lifecycle-agent notified
  → Pattern feeds into business-health-advisor monthly scan

Onboarding diagnostic completed
  → Readiness score logged to project folder
  → If score < 60: kickoff delayed, pre-onboarding checklist generated
  → client-onboarding skill uses results for Day 0 sequencing

Product validation diagnostic completed
  → Score and dimension breakdown appended to validation-results.md
  → Aggregate data feeds /solo:build validate decision gate

Self-assessment completed
  → Saved to data/2-Domaines/ with date
  → Flagged dimensions surface in weekly-review
  → business-health-advisor reads diagnostic history for trend analysis
```

---

## Skills Used

| Command | Skills invoked |
|---------|---------------|
| `create` | `diagnostic-builder` |
| `run` | `diagnostic-runner`, optionally `draft-outreach` |
| `results` | `diagnostic-analyzer`, optionally `tally-integration` (with `--tally`) |
| `share --claude` | `diagnostic-runner` (self-service mode) |
| `share --tally` | `tally-integration` (form creation via MCP) |
| Weekly background | `diagnostic-monitor-agent` |

---

## Quick Examples

```
# First diagnostic: qualify your leads
/solo:diagnose create
→ "qualifying prospects before I send a proposal"

# Run it live in this session
/solo:diagnose run lead-qualifier

# Publish it as a real Tally form (requires Tally MCP connected)
/solo:diagnose share lead-qualifier --tally
→ Returns: https://tally.so/r/abc123

# Send async to a prospect who can't do a call
/solo:diagnose share lead-qualifier --claude

# After 10 runs, pull Tally submissions + analyze
/solo:diagnose results lead-qualifier --tally
```
