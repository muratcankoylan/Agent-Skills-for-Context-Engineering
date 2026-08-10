# Governance policy

`constitution.yaml` is the machine-readable authority model for the research organization. It is intentionally conservative: an unlisted operation is denied, explicit denies override allows, and only an authenticated human maintainer may merge or activate production.

The file uses YAML because it is reviewed by humans and parsed with `yaml.safe_load`. Its executable semantics live in `researcher/scripts/governance_policy.py`; the JSON Schema describes the public interchange shape. Domain validation remains in the executable policy checker so authorization behavior never depends on a schema implementation detail.

Run:

```bash
python researcher/scripts/validate_governance.py --check
python researcher/scripts/validate_governance.py --decision \
  --actor change_author \
  --action open_pull_request \
  --resource pull_request \
  --context-json '{"automated_identity_disclosed":true,"human_review_path":"pull_request"}'
```

`effective_commit: "$SELF"` means the commit containing the constitution. This avoids a self-referential hash while still pinning the policy to immutable Git history. Runtimes pin the SHA-256 digest returned by the checker, not a mutable path.

The generated authority view is derived from the policy. Do not edit it manually.
