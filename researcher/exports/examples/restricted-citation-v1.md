# Restricted citation projection example

The adjacent generated staging tree proves that a synthetic `restricted_source` record can export allowlisted citation metadata while excluding its raw `body`. `export-manifest.json` contains output and transformation digests but no source path or private input digest.

Validate with:

```bash
python researcher/scripts/validate_export.py check \
  --staging-dir researcher/exports/examples/restricted-citation-v1
```

The example source is intentionally synthetic and committed under `researcher/fixtures/export/`; real restricted bodies do not belong in this repository.
