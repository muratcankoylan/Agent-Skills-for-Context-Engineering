# Tool compatibility

Use this reference only when the project targets more than one coding agent or instruction precedence affects the requested file layout. Tool behavior changes over time; verify current official documentation before making a compatibility claim that affects files or configuration.

## Codex

- Shared repository instructions: `AGENTS.md`.
- Same-directory override: `AGENTS.override.md` takes precedence and causes that directory's `AGENTS.md` to be ignored.
- Discovery: global file first, then one instruction file per directory from repository root toward the current working directory.
- Files closer to the working directory appear later in the combined instructions.
- Additional fallback filenames and the byte limit are configured through Codex configuration.
- Project-scoped `.codex/config.toml` can be intentionally versioned; do not ignore `.codex/` wholesale.

Official reference: <https://developers.openai.com/codex/guides/agents-md>

## Claude Code

- Primary shared project file: `CLAUDE.md`.
- Import an existing shared file with `@AGENTS.md`.
- A symlink can work, but an import is more portable across operating systems.
- `.claude/rules/` supports focused project rules, including path-scoped rules.
- `CLAUDE.local.md` is suitable for private project-local preferences and normally should not be committed.
- Imports organize content but do not reduce loaded context; keep the imported `AGENTS.md` concise.

Official reference: <https://code.claude.com/docs/en/memory>

## GitHub Copilot

- Repository-wide instructions may use `.github/copilot-instructions.md`.
- Path-specific instructions may use `.github/instructions/**/*.instructions.md`.
- Support for `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` varies by Copilot surface; check the support matrix for the surfaces the team uses.
- Avoid duplicating the same always-loaded rules across `AGENTS.md` and Copilot-specific files.

Official reference: <https://docs.github.com/en/copilot/reference/custom-instructions-support>

## Cursor

- Current project rules live under `.cursor/rules/` and can be scoped.
- Root `.cursorrules` is legacy; detect it for migration but do not generate it as the default.
- Project rules are commonly version-controlled; do not ignore `.cursor/` wholesale without inspecting its contents.

Official reference: <https://docs.cursor.com/context/rules>

## Other tools

Some agents read `AGENTS.md` directly, while others use their own rules files or configuration. Detect actual project usage before generating compatibility files. Do not create a catalog of every possible agent tool inside repository instructions.

## Cross-tool layout

Use this default when the team wants a shared source:

```text
AGENTS.md                 # concise shared rules
CLAUDE.md                 # optional: @AGENTS.md
.claude/rules/            # optional path-scoped Claude-only rules
.github/instructions/     # optional path-scoped Copilot-only rules
.cursor/rules/            # optional scoped Cursor-only rules
```

Create only the files required by the tools the team actively uses.
