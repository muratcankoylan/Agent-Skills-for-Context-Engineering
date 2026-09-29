#!/usr/bin/env bash
# The checked-in launchd definitions are legacy migration evidence, not an
# authorized production activation path.
set -euo pipefail

echo "Legacy launchd activation is disabled." >&2
echo "SPEC-025 must authorize a reviewed activation epoch over implemented dependencies." >&2
echo "No files or launchd services were changed." >&2
exit 78
