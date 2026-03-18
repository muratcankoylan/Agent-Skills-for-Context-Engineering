# Changelog

## [2.5.0] — 2026-02-20

### Added
- **`/solo:diagnose` command** — Build, run, share, and analyze scored diagnostic assessments. Five types: Lead (qualify prospects), Client (monitor health), Onboarding (check readiness), Product (validate demand), Self (assess your business). Full qualification loop: conversational session → scored result → pipeline routing → follow-up draft.
- **`diagnostic-builder` skill** — 6-step guided creation: purpose → dimensions → questions → scoring → band recommendations → routing. Outputs a reusable `.json` definition.
- **`diagnostic-runner` skill** — Runs assessments live in-session or generates a self-service Claude prompt package. Scores answers in real time, delivers personalized band recommendations, routes results to client cards and pipeline stages automatically.
- **`diagnostic-analyzer` skill** — Analyzes patterns across all responses: score distribution, dimension averages, ICP segment signals, actionable recommendations.
- **`tally-integration` skill** — Publishes diagnostics as live Tally forms via MCP. Creates the form directly (no manual Tally builder required), returns a shareable URL, fetches and scores submissions back into Solo.
- **`~~forms` connector category** — Added to `CONNECTORS.md` and `.mcp.json`. Default: Tally. Alternatives: Typeform, Fillout. Required for `--tally` flag on `/solo:diagnose share` and `results`.
- **`diagnostic-monitor-agent`** — Background agent that scans for new completions and flags high-band leads in the Monday briefing.
- **`data/2-Domaines/diagnostics/`** — Definition storage (one `.json` per diagnostic).
- **`data/1-Projets/diagnostics/`** — Response storage (one `.md` per session, organized by diagnostic slug).
- **`lead-qualifier-v1.json`** — Pre-built example diagnostic included as a starter template.

### Changed
- `monday-morning-agent` — Now reads `data/1-Projets/diagnostics/*/responses/` as a data source. Alerts when high-band leads complete a diagnostic this week.
- `client-lifecycle-agent` — Prospect → Lead transition now also triggers on `diagnostic_band == "high"`, not only on `qualified == True`.
- `check-connections.md` — Added Tally detection and recommendation logic (surfaces when `/solo:diagnose` is used 3+ times without Tally connected).
- `README.md` — Added Lead Qualification workflow section, `/solo:diagnose` to command table and area overview.
- `plugin.json` — Version bump 2.4.0 → 2.5.0. Updated description.
- `CLAUDE.md` — Skill count updated to 68.

### Skill Count
- v2.4.0: 31 skills
- v2.5.0: 35 skills (+4: diagnostic-builder, diagnostic-runner, diagnostic-analyzer, tally-integration)

---

## [2.4.0] — 2026-02-18

### Changed
- Delegated all content creation to the **copywriter** companion plugin. Solo's identity is now pure business operations: client management, product building, sales, finance.
- `/solo:plan` stripped of `content` sub-command (content calendar planning moved to `/copywriter:plan`). Kept `organize` (PARA) and `review` (projects).
- README updated: removed content creation from feature table, Voice DNA description scoped to proposals/outreach, added copywriter companion section.
- CONNECTORS.md: added Companion Plugins section documenting copywriter and solo-studio integrations and shared data files.

### Removed
- `content-calendar-planner` skill (use `/copywriter:plan`)
- `linkedin-post` skill (use `/copywriter:write social`)
- `newsletter-writer` skill (use `/copywriter:write newsletter`)
- `seo-blog-writer` skill (use `/copywriter:write blog`)
- `antislop-expert` skill (use `/copywriter:audit`)
- `press-release` skill (use copywriter for written publishing artifacts)
- `/solo:write` command (use `/copywriter:write`)
- `content-multiplier-agent` (use copywriter's agent suite)

### Kept
- `voice-dna-creator` — retained so solo works standalone; voice-dna.json feeds both `draft-outreach` and `proposal-generator`

### Skill Count
- v2.3.0: 37 skills
- v2.4.0: 31 skills (−6 content creation skills)

---

## [2.3.0] — 2026-02-18

### Changed
- Rewrote `prd-development` as a 5-section, 30-minute solo build spec (What / Who / Why / Scope v1 / Done When). Removed OKRs, stakeholder language, guardrail metrics, and 8-phase workflow.
- Rewrote `user-story` as plain feature card format. Removed INVEST table, Fibonacci story points, Gherkin syntax, and team-facing Definition of Done.
- Merged `validation-checkpoint` + `pol-probe-advisor` into a new `idea-test` skill. Part 1: Go/No-Go/Pivot checklist. Part 2: 5 cheapest-test methods (Smoke Test, Concierge, Wizard of Oz, Narrative, Spike).
- Updated `customer-journey-map` trigger phrases with builder-friendly language ("map the pain points", "where do users get stuck")
- Updated `proto-persona` trigger phrases with builder-friendly language ("who am I building for", "describe my customer")
- Updated `/solo:build` command: Phase 2 now references `idea-test`; removed `jobs-to-be-done` from DISCOVER flow; updated Skills Used list

### Removed
- `lean-ux-canvas` skill (workshop artifact, flow covered by pipeline)
- `jobs-to-be-done` skill (covered by `user-discovery`)
- `validation-checkpoint` skill (merged into `idea-test`)
- `pol-probe-advisor` skill (merged into `idea-test`)

### Skill Count
- v2.2.0: 40 skills
- v2.3.0: 37 skills (−4 removed/merged, +1 new `idea-test`)

---

## [2.2.0] — 2026-02-18

### Fixed
- Translated `discovery-interview-prep` skill from French to English (skill was invisible to English users)
- Removed dead references to deleted skills (`opportunity-solution-tree`, `product-strategy-session`) from `discovery-process`
- Fixed README build pipeline description that incorrectly promised prototyping (now in solo-studio)
- Added missing `/solo:check-connections` command to README command reference table

### Changed
- Consolidated `discovery-interview-prep` + `discovery-process` into a single `user-discovery` skill with 5 reference files
- Rewrote README as marketplace-ready copy with clear value proposition, agent table, and skill inventory
- Updated language support section from French-only to language-agnostic (Claude responds in user's language)
- Removed Figma from solo connectors (now documented under solo-studio)

### Removed
- `context-engineering-advisor` skill (Claude tutorial, not a business workflow)
- `memory-management` skill (internal architecture docs, not user-facing)
- `eol-message` skill (product sunset messaging, too niche for core solopreneur audience)
- `discovery-interview-prep` skill directory (merged into `user-discovery`)
- `discovery-process` skill directory (merged into `user-discovery`)

### Skill Count
- v2.1.0: 43 skills
- v2.2.0: 40 skills (−5 removed/merged, +2 consolidated into `user-discovery`)

---

## [2.1.0] — 2026-02-13

### Changed
- Extracted prototyping skills (Stitch, Figma, Remotion, storyboard, voiceover) into companion plugin `solo-studio`
- Removed enterprise/team-oriented PM skills (epic planning, opportunity-solution-tree, workshop facilitation, etc.)
- Deleted all French `.fr.md` variant files; plugin now English-only with language-aware output
- Updated build pipeline to reflect discover → validate → design scope (prototype moved to solo-studio)
- Bumped from v2.0.0 to v2.1.0

### Removed (PM skills)
- epic-breakdown-advisor, epic-hypothesis, user-story-mapping, user-story-mapping-workshop
- user-story-splitting, opportunity-solution-tree, workshop-facilitation, product-strategy-session
- prioritization-advisor, roadmap-planning, problem-framing-canvas, pestel-analysis

### Moved to solo-studio
- stitch-design-md, stitch-enhance-prompt, stitch-loop, stitch-asset-bridge
- figma-prototype, prototype-to-video, remotion-video-generator, voiceover-generator, storyboard

---

## [2.0.0] — 2026-01-01

Initial public release of Solo as a unified solopreneur OS plugin.
