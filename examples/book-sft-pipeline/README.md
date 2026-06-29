# Book SFT Pipeline

A standalone example skill for training language models to write in any author's style. It is not published as a separate Claude Code marketplace plugin from this repository.

## Installation

### Claude Code / Cursor / Codex

Agent Skills hosts expect a directory containing `SKILL.md`, not a flat copied markdown file. From the repository root, copy the whole example directory into the target skill root:

```bash
# Claude Code project-scoped install
mkdir -p .claude/skills
cp -R examples/book-sft-pipeline .claude/skills/book-sft-pipeline

# Cursor project-scoped install
mkdir -p .cursor/skills
cp -R examples/book-sft-pipeline .cursor/skills/book-sft-pipeline

# Codex / OpenAI Agent Skills install
mkdir -p .agents/skills
cp -R examples/book-sft-pipeline .agents/skills/book-sft-pipeline
```

### Manual

Reference the `examples/book-sft-pipeline/SKILL.md` file directly only if your agent does not support the Agent Skills directory layout.

## What's Included

```
book-sft-pipeline/
├── README.md                 # This file
├── SKILL.md                  # Complete skill documentation (standalone)
├── examples/
│   └── gertrude-stein/       # Complete case study with real outputs
│       ├── README.md         # Results and analysis
│       ├── sample_outputs.md # Raw model outputs
│       ├── training_config.json
│       ├── dataset_sample.jsonl
│       └── pangram/          # AI detector screenshots
├── scripts/
│   └── pipeline_example.py   # Conceptual implementation
└── references/
    ├── segmentation-strategies.md
    ├── tinker-format.md
    └── tinker.txt
```

## Key Results

Trained Qwen3-8B-Base on Gertrude Stein's "Three Lives" (1909):

| Metric | Value |
|--------|-------|
| Training examples | 592 |
| Loss reduction | 97% |
| Pangram AI detector | 70% Human |
| Training time | 15 minutes |
| Total cost | $2 |

## Related Context Engineering Skills

This skill applies patterns from the [Agent Skills for Context Engineering](../../README.md) collection:

| Skill | Application |
|-------|-------------|
| [project-development](../../skills/project-development/) | Staged pipeline architecture |
| [context-compression](../../skills/context-compression/) | Segmentation strategy |
| [multi-agent-patterns](../../skills/multi-agent-patterns/) | Orchestrator pattern |
| [evaluation](../../skills/evaluation/) | Modern scenario testing |
| [context-fundamentals](../../skills/context-fundamentals/) | Prompt diversity |

## Resources

- [Dataset on Hugging Face](https://huggingface.co/datasets/MuratcanKoylan/gertrude-stein-style-sft)
- [Research Paper](https://arxiv.org/pdf/2510.13939) (Chakrabarty et al. 2025)

## License

MIT

