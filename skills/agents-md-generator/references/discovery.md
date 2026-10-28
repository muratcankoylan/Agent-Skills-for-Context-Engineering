# Repository discovery

Use this checklist to collect only facts that can change persistent agent behavior.

## Optional detector

For a broad or unfamiliar repository, use the detector to index instruction paths and declared signals. A focused known-file edit can use direct inspection. Run it from the installed skill directory:

```text
python3 <skill-directory>/scripts/detect-agent-context.py --root <repository-root> --format json
```

The JSON schema is versioned and contains:

- `instruction_sources`: project and optional global instruction paths, tool, scope, kind, and legacy status.
- `agent_configs`: known project and optional global agent configuration paths.
- `project_evidence`: manifests, lockfiles, environment files, CI, documentation, and common source directories.
- `declared_commands`: runnable package or Make commands only when their runner can be verified.
- `technology_signals`: frameworks, libraries, test tools, and quality tools declared by selected manifests, with their evidence paths.
- `warnings`: precedence conflicts, legacy formats, or ambiguous package-manager evidence.
- `errors`: non-fatal parse failures; do not silently treat missing data as verified.

Use `--format text` for a concise report. Use `--include-global` only when global conflicts are relevant and path access is permitted. Increase `--max-depth` only for a repository whose meaningful configuration lives deeper than the default scan.

The detector is deliberately read-only. It never reads `.env` files, credentials, arbitrary source files, or instruction contents. It ignores dependency/build directories, refuses symlinked manifests, and limits parsed manifest size. Use the Python result when structured output or conflict checks matter. Verify each selected command or rule in the reported source before persisting it.

## Evidence priority

Prefer evidence in this order:

1. Active repository instructions and explicit user requirements.
2. CI workflows and executable project scripts.
3. Lockfiles, manifests, version files, container configuration, and framework config.
4. Maintained repository documentation.
5. Representative source code and tests.
6. User confirmation when local evidence is absent or conflicting.

Do not infer a command from a framework default when the repository defines its own script. Do not infer architecture from folder names alone; verify imports, routes, package boundaries, or nearby tests.

## Minimum useful scan

Collect these facts when present:

- Repository type: single project, monorepo, or multi-service workspace.
- Runtime and package manager chosen by lockfiles or version files.
- Whether commands run on the host, in a container, through a wrapper, or in a devcontainer.
- Install, lint, format, type-check, targeted test, full test, build, and generated-file commands actually used by CI.
- Source-of-truth files for schemas, routes, API contracts, generated code, design rules, deployment, and security policy.
- Important module boundaries and shared surfaces that must be reused.
- Files or directories that are generated and must not be edited directly.
- Required approvals or platform-specific limitations.

Skip facts that are obvious from standard configuration unless an agent could reasonably choose the wrong path or command.

## Confidence labels

Use confidence internally; do not write labels into `AGENTS.md`.

- **Verified**: directly supported by a current config, script, CI job, source file, or explicit user statement.
- **Probable**: supported by multiple indirect signals but not an authoritative source.
- **Unknown**: missing or conflicting evidence.

Write verified facts. Omit probable facts unless they are harmless and clearly qualified. Ask about unknown facts only when omission would make the instructions unsafe or materially incomplete.

## Command verification

For every command considered for persistent instructions:

1. Locate its definition in a manifest, Makefile, task runner, script, container config, or CI workflow.
2. Preserve required wrappers and service names.
3. Distinguish targeted checks from the complete suite.
4. Record required environment or platform limitations only when durable and non-sensitive.
5. Never embed secret values or local absolute home paths.

## Documentation routing

Do not list every document. Add a routed reference only when an agent should consult it for a recognizable class of task.

Examples:

- "For database schema changes, read `docs/database-migrations.md` before editing migrations."
- "For UI work, follow `docs/DESIGN_SYSTEM.md`; do not duplicate its token tables here."
- "For production deploys, follow `deploy/README.md` and obtain the approvals documented there."

## Monorepos

Keep shared commands and policies in the root file. Use nested instructions only for real differences such as:

- A different runtime or package manager.
- Service-specific build and test commands.
- A separate generated-code workflow.
- Distinct architecture or security boundaries.

Do not copy the root file into every package. Nested files should contain only the delta.
