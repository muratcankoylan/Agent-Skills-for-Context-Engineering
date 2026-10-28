# Compact output template

Use this as a selection guide, not as mandatory boilerplate. Omit headings with no verified, non-obvious content.

```markdown
# Repository instructions

## Scope and sources of truth

- [State what this file governs.]
- For [recognizable task], read `[authoritative path]` before changing `[owned area]`.
- Edit `[canonical source]`; do not edit `[generated copy]` directly.

## Environment and commands

- Use `[package manager or wrapper]`; `[reason only if non-obvious]`.
- Install: `[verified command]`
- Targeted test: `[verified command or pattern]`
- Full validation: `[verified command]`

## Architecture and boundaries

- `[path or module]` owns `[responsibility]`.
- Reuse `[shared surface]` before creating `[project-specific duplicate risk]`.
- Keep `[concern]` out of `[boundary]`; place it in `[owner]`.

## Implementation rules

- When `[condition]`, do `[concrete action]`.
- Do not edit `[generated or protected path]`; run `[generator command]`.

## Verification

- For `[change type]`, run `[targeted check]`.
- For `[repository-specific integration or release condition]`, run `[required check]`.
- `[Any explicit repository limit or approval requirement for broader checks.]`

## Safety and approvals

- Ask before `[repository-specific high-impact action]`.
```

## Selection rules

- Keep the title neutral. Do not add a role persona.
- Prefer one bullet per rule. Use sub-bullets only for a necessary exception.
- Include install or development commands only when agents will actually need them.
- Do not duplicate commands already obvious and unambiguous from a short manifest unless the required wrapper, order, or environment is non-obvious.
- Include Git conventions only when this repository differs from the user's or tool's normal workflow.
- Include security rules only when repository-specific; generic secure-coding advice belongs elsewhere.
- Include deployment rules only when they apply broadly. Keep detailed runbooks in deployment documentation.
- Keep the file edit-free: content that changes with the code (procedures, examples, error catalogs, inventories, API or schema detail) appears only as a conditional link to its owner, never as a copy.

## Filled example

A TypeScript service whose CI runs `pnpm lint` and `pnpm test`, with generated code in `src/generated/` and design notes in `docs/architecture.md`:

```markdown
# Repository instructions

- Use pnpm. CI runs `pnpm lint`, then `pnpm test`.
- Do not edit `src/generated/`; run `pnpm codegen`.
- For structural changes, read `docs/architecture.md` first.
```

Install steps, the language, and the test framework are omitted because the manifest already makes them obvious.

## Nested file template

Nested files inherit broader instructions. State scope and differences only:

```markdown
# Payments service instructions

- Scope: `services/payments/**`.
- Use `make test-payments`; do not run the root JavaScript test command here.
- Schema source of truth: `services/payments/schema/`.
- Obtain the approval defined in `services/payments/DEPLOY.md` before rotating keys.
```

Do not add a summary of inherited root rules.

## Compatibility files

For Claude Code sharing the root instructions:

```markdown
@AGENTS.md
```

If Claude-specific rules are explicitly requested:

```markdown
@AGENTS.md

## Claude Code

- [Only the rules that cannot be shared.]
```
