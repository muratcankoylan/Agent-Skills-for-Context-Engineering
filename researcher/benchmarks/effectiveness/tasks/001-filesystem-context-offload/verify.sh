#!/usr/bin/env bash
# Verifier for task 001-filesystem-context-offload.
# Runs inside the temp workspace built by the SDK runner. Exit 0 = task passed.
set -uo pipefail

EXPECTED_VALUE="8475"
EXPECTED_LINE="API_RATE_LIMIT=${EXPECTED_VALUE}"

# Check 1: the agent actually located the right value in its final response.
# The runner writes the agent's final assistant text to .runner/final.txt before invoking verify.
if [ ! -f .runner/final.txt ]; then
    echo "verify: missing .runner/final.txt (runner did not stage final response)" >&2
    exit 11
fi

# An exact assignment is required. Substring matching also accepts 84750,
# suffixes, and answers that contain both the right and a contradictory value.
ASSIGNMENTS=$(LC_ALL=C grep -Eo '(^|[^[:alnum:]_])API_RATE_LIMIT[[:space:]]*=[[:space:]]*[^[:space:]`";,}]*' .runner/final.txt || true)
if [ -z "$ASSIGNMENTS" ] || [ "$(printf '%s\n' "$ASSIGNMENTS" | LC_ALL=C sed -E 's/^[^[:alnum:]_]//; s/[[:space:]]//g' | sort -u)" != "$EXPECTED_LINE" ]; then
    echo "verify: final response does not contain ${EXPECTED_LINE}" >&2
    exit 12
fi

# Check 2 (skill-behavior signal): scratch directory exists.
if [ ! -d scratch ]; then
    echo "verify: no scratch/ directory; agent did not offload (still counts as task pass on response, but logged)" >&2
    echo "scratch_dir_missing" > .runner/notes.txt
    exit 0
fi

# Check 3 (skill-behavior signal): something in scratch/ contains lines copied from tool_output.txt.
shopt -s nullglob
if compgen -G "scratch/*" > /dev/null; then
    if grep -F -l -m 1 -q "API_RATE_LIMIT" scratch/* 2>/dev/null; then
        echo "scratch_used" > .runner/notes.txt
    else
        echo "scratch_empty_or_unrelated" > .runner/notes.txt
    fi
fi

exit 0
