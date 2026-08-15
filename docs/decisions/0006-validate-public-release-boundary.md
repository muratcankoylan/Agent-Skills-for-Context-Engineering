# ADR-0006: Validate the complete public release boundary

- Status: accepted
- Date: 2026-08-10
- Specs: SPEC-000, SPEC-002

## Context

The export policy proves that registered private records produce allowlisted public projections. It does not inspect unrelated tracked documentation, dependency resolution, or Git history. A developer-local path remained in a published example even though the export checks passed. No credential was found, but the incident demonstrated that projection validation and repository-release validation are different contracts.

The validation environment also contained two floating direct Python dependencies. A release gate whose parser or reference validator can change without a repository diff is not reproducible.

## Decision

The public release boundary has two independent scanners:

1. Gitleaks scans Git history for credential patterns on every push and pull request. The action and scanner version are immutable inputs.
2. `validate_public_repo.py` inspects every Git-tracked regular file for repository-specific invariants: developer-local absolute paths, credential-bearing filenames, private-key block headers, and tracked local drafting or private roots.

The deterministic validator reports stable codes and locations but never echoes matched secret or path content. Binary files are left to Gitleaks. Intentional adversarial fixtures construct sensitive markers at runtime so test data cannot be mistaken for release material.

GitHub Actions are pinned to immutable, Node 24-compatible release commits. Python direct and transitive dependencies are compiled into a hash-locked requirements file, and CI installs them in hash-checking mode. The Cursor SDK direct dependency is exact and its lockfile remains authoritative. Reported transitive SDK advisories require a separately tested dependency migration; the repository does not apply an unreviewed automated audit fix to a paid benchmark surface.

## Consequences

- A documentation-only change can fail the release boundary even when export fixtures remain valid.
- A forced add from `outputs/` or `Private/` fails CI rather than relying only on ignore rules.
- Validation semantics and package bytes change only through reviewable lockfile diffs.
- Gitleaks requires a license when the repository moves from a personal GitHub account into an organization account; that migration is owned by SPEC-024.
- The deterministic gate is deliberately narrower than a general secret scanner. Both checks remain required.
- The deterministic path policy applies to the candidate tracked tree, not to non-secret workstation paths already published in historical commits. Removing historical non-secret data requires a separate, coordinated history-rewrite decision; credential signatures remain history-scanned by Gitleaks.

## Alternatives considered

- Rely only on `.gitignore`. Rejected because files can be force-added and existing tracked files are unaffected by new ignore rules.
- Rely only on Gitleaks. Rejected because workstation paths and repository-specific private roots are not credential signatures.
- Extend the export validator to scan the repository. Rejected because export closure and public release closure have different inputs and failure semantics.
- Run `npm audit fix` automatically. Rejected because dependency rewrites on the paid benchmark runner require SDK typecheck, dry-run, and behavior regression evidence.

## Verification

Unit tests cover local Unix and Windows path families, forbidden filenames, private-key headers, binary inputs, path traversal, duplicate inputs, and private-root force-adds. CI compiles and executes the deterministic scanner after a full-history checkout, while Gitleaks runs as an independent preceding step. A fresh virtual environment must install the Python lock with `--require-hashes`.
