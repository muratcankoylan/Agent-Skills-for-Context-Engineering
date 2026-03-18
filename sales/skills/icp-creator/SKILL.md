---
name: icp-creator
description: >
  Shared skill. When Solo core plugin is installed, the canonical version from
  ../solo/skills/icp-creator/ is used automatically. This file is a passthrough for
  standalone mode — the full skill logic is maintained in Solo.
bundle: identity-tools
triggers:
  - "create ICP"
  - "define my ideal client"
  - "who is my target customer"
tools:
  standalone: [filesystem]
  supercharged: [exa]
version: 1.0.0
---

# icp-creator

## Ecosystem Mode (Solo installed)

This skill defers to the canonical version in Solo:
`../solo/skills/icp-creator/SKILL.md`

Solo's version is the most complete and is kept up to date as the single source of truth.

## Standalone Mode (Solo not installed)

When running Sales without Solo, this skill operates with reduced reference data.
For the full experience, install Solo as the core plugin.

**Triggers**: Same as the canonical version — see Solo's skill file for full trigger list.
