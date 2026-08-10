# Constitution amendment and emergency disable

## Amendment

1. Create a proposal branch from the current default branch.
2. Change `governance/constitution.yaml`, increment `constitution_version`, and update the related spec and decision record.
3. Run `python researcher/scripts/validate_governance.py --write` and the full deterministic validation suite.
4. Open a pull request using the constitutional-change template. The PR must state changed authority, affected actors, migration behavior, and rollback digest.
5. A human maintainer reviews the latest commit and merges only after required checks pass. Chat text is supporting context, not the promotion event.
6. Runtime reconciliation observes the merged commit, pins the new constitution digest, and records the previous digest as superseded. In-flight work retains its original version for provenance, but newly denied actions fail at execution.

Rollback means pinning the last effective constitution digest in the runtime configuration and opening a corrective PR. Do not delete historical constitutions or rewrite Git history.

## Emergency disable

Emergency disable stops new dispatch and prevents further side effects. It does not grant authority, rewrite state, delete artifacts, approve a candidate, or merge a pull request. The operator records the reason and affected work IDs, then uses ordinary reconciliation to classify in-flight attempts as paused, cancelled, or unknown.

Recovery requires an authenticated human command or reviewed configuration change. Resume from immutable checkpoints only after the loaded constitution digest matches the configured digest.
