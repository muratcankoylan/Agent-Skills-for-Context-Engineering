---
name: voice-dna-creator
description: >
  Shared skill. When Solo core plugin is installed, the canonical version from
  ../solo/skills/voice-dna-creator/ is used automatically. This file is a passthrough for
  standalone mode — the full skill logic is maintained in Solo.
bundle: identity-tools
triggers:
  - "create voice DNA"
  - "analyze my writing style"
  - "build my voice profile"
tools:
  standalone: [filesystem]
  supercharged: [knowledge-base]
version: 1.0.0
---

# voice-dna-creator

## Ecosystem Mode (Solo installed)

This skill defers to the canonical version in Solo:
`../solo/skills/voice-dna-creator/SKILL.md`

Solo's version is the most complete and is kept up to date as the single source of truth.

## Standalone Mode (Solo not installed)

When running Sales without Solo, this skill operates with reduced reference data.
For the full experience, install Solo as the core plugin.

**Triggers**: Same as the canonical version — see Solo's skill file for full trigger list.
