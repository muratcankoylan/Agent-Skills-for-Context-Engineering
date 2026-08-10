# Private artifact storage

`researcher/artifacts/private/` is an ignored local default for SPEC-003 content-addressed bodies, reference records, storage bindings, freeze receipts, and locks. Deployments should configure a private root outside the public checkout.

`ArtifactRef` is portable and contains no storage locator. It records the target's native or legacy ID origin, and validation resolves the target kind and version before enforcing that schema's typed-ID prefix. `StorageBinding` is private metadata. Neither is authority. Callers supply an `ArtifactAuthority` for every read, and authorization occurs before object existence is checked. Every read loads and validates both records and proves that the binding locator matches the reference digest.

`LocalArtifactStore.put()` is for registered JSON records, not arbitrary bytes. It validates the body, kind, version, typed ID, and classification before writing. Candidate file bodies use the lower-level CAS only after a candidate record and editable-surface policy have passed freeze validation.

`head()` may inspect a validated `tombstoned` or `unavailable` reference for audit purposes. `put()`, `get()`, `verify()`, and `materialize()` deny that state even if bytes remain in CAS; a writer cannot silently resurrect an immutable reference.

The local CAS layout is `sha256/<first-two-hex>/<full-hex>`. Exact bytes are written with mode `0600`, fsynced, atomically linked into place, and verified. A digest has one conservative classification high-water mark. Output files and candidate directories publish with no-clobber primitives and do not chmod caller-owned parents. The implementation targets Unix filesystems with `fcntl`, directory fsync, and native exclusive directory rename. Windows support is deferred until its locking and atomic-publish contract has equivalent tests.

SPEC-004 and SPEC-010 must use this body store through an adapter rather than creating competing CAS implementations.
