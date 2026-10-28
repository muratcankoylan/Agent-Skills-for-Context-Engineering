# Examples

Short input and output pairs. For a filled root file in a TypeScript project, see [output-template.md](./output-template.md).

## Compacting an existing file

```
Input:  Root AGENTS.md of 340 lines: a role persona, a test tutorial, a
        copy of the API guide, two commands that no longer exist in CI.
Output: About 60 lines. Persona and tutorial removed. API guide replaced
        by "For endpoint changes, read docs/api.md". Stale commands dropped
        after checking CI.
Report: 4 removed, 1 moved to a link, 0 unresolved.
```

## Scoped file in a monorepo

```
Input:  Root file covers a pnpm workspace. packages/payments uses its own
        make targets and a schema directory.
Output: packages/payments/AGENTS.md (delta only):
        - Scope: packages/payments/**.
        - Use `make test-payments`; do not run the root test command here.
        - Schema source of truth: packages/payments/schema/.
Omitted: any summary of the inherited root rules.
```

## Preserving a working shared source

```
Input:  CLAUDE.md already contains the shared rules; the team also uses a
        tool that reads AGENTS.md.
Output: Keep the rules where they are and add AGENTS.md that points to the
        same source, or keep an existing symlink. Create no second copy.
Reason: Two always-loaded copies diverge and double the context cost.
```

## Unverifiable command

```
Input:  README mentions `npm run e2e`, but package.json has no such script
        and CI does not run it.
Output: Command not persisted. Reported as unresolved with both source
        paths, and the user decides only if the rule is needed.
```
