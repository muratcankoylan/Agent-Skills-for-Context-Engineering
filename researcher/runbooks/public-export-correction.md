# Public export correction and removal

Publication is not reversible. A later deletion cannot make already distributed data private again.

When a public projection is incorrect or should no longer be used:

1. Disable further renders of the affected request or transform.
2. Preserve the private plan, render receipt, and failed validation evidence.
3. Open a corrective pull request with a new public correction or tombstone record that names the public projection and safe reason code.
4. Remove or replace the projected body in that pull request when appropriate. Do not rewrite Git history as the normal response.
5. A human maintainer reviews and merges the correction.
6. Downstream indexes mark the prior projection superseded or unavailable while retaining non-sensitive decision lineage.

If the event exposed an actual credential, revoke and rotate it outside this repository. Do not add the value or matched scanner excerpt to the public incident record.
