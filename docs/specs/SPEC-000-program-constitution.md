# SPEC-000: Program constitution and authority model

- Status: implementing
- Wave: 0
- Classification: public
- Depends on: none

## Decision

The organization operates under a versioned, machine-testable constitution. Agents may research, evaluate, edit permitted artifacts, create proposal branches, push candidate commits, open pull requests, and respond to review. Only the human maintainer may merge, alter constitutional authority, expose a private record, authorize credential destinations, or approve weight-level training. A human-merged commit is the sole promotion event.

## Invariants

1. No automated identity has merge or production-activation authority.
2. A candidate author cannot be its sole evaluator or release attestor.
3. Production points to an exact merged commit and immutable configuration digest.
4. Ordinary experiments cannot edit the constitution, hidden tests, acceptance gates, evaluator policy, permission ceilings, or public/private boundary.
5. Chat approval is not authority unless converted into an authenticated command or GitHub action and recorded.
6. Unlisted authority is denied.
7. Emergency disable stops work without changing artifact history or granting authority.
8. Automated authorship and review are disclosed.

## Interfaces

- `governance/constitution.yaml`: canonical policy.
- `governance/authority.schema.json`: public interchange schema.
- `Constitution.decide(actor, action, resource, context)`: deterministic decision with matched rule, reason code, version, and digest.
- `validate_governance.py --check|--write|--decision`: CI, generated-view, and diagnostic interface.

Constitution states are `draft -> reviewed -> merged -> effective -> superseded`. Only a merged revision becomes effective. Startup fails closed on digest mismatch. In-flight work retains its starting version for provenance; a newly forbidden action is denied at execution and later orchestration records `policy_blocked` without destroying its checkpoint.

## Acceptance criteria

- [x] Human merge is the only permitted promotion transition.
- [x] Protected surfaces are enumerated and denied to ordinary actors.
- [x] Current durable `AGENTS.md` authority is represented or classified as non-constitutional guidance.
- [x] The validator has no network dependency and runs in CI.
- [x] Amendment and emergency-disable procedures are documented.
- [x] Exhaustive actor/action/resource decisions and critical negative fixtures are tested.

Runtime command integration, authenticated identity binding, event emission, and mid-run reconciliation are delivered by later orchestration specs. Until then, this is a read-only authority oracle and CI contract.
