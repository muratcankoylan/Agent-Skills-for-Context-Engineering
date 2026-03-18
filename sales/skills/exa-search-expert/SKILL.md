---
name: exa-search-expert
description: >
  Shared skill. When Solo core plugin is installed, the canonical version from
  ../solo/skills/exa-search-expert/ is used automatically. This file is a passthrough for
  standalone mode — the full skill logic is maintained in Solo.
bundle: prospecting
triggers:
  - "deep search"
  - "semantic search"
  - "research with Exa"
tools:
  standalone: [exa]
  supercharged: [exa]
version: 1.0.0
---

# exa-search-expert

## Ecosystem Mode (Solo installed)

This skill defers to the canonical version in Solo:
`../solo/skills/exa-search-expert/SKILL.md`

Solo's version is the most complete and is kept up to date as the single source of truth.

## Standalone Mode (Solo not installed)

When running Sales without Solo, this skill operates with reduced reference data.
For the full experience, install Solo as the core plugin.

**Triggers**: Same as the canonical version — see Solo's skill file for full trigger list.
