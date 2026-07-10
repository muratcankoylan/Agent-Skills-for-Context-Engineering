#!/usr/bin/env bash
set -uo pipefail

fail() { echo "verify: $1" >&2; exit "$2"; }

[ -f HANDOFF.md ] || fail "missing HANDOFF.md" 21
size=$(wc -c < HANDOFF.md)
[ "$size" -le 2500 ] || fail "HANDOFF.md exceeds 2500 bytes: $size" 22

heading_count=$(grep -Ec '^#{1,3}[[:space:]]+' HANDOFF.md || true)
[ "$heading_count" -ge 6 ] || fail "expected at least 6 explicit Markdown sections; found $heading_count" 23

anchors=(
  "WEBHOOK_REPLAY_DIVERGENCE E7421"
  "evt_7QX9"
  "normalizeEventTimestamp()"
  "src/webhooks/normalize.ts"
  "src/idempotency/key.ts"
  "tests/webhooks/replay.test.ts"
  "config/payments.yaml"
  "provider_event_id"
  "Postgres advisory lock"
  "37 passed, 2 failing"
  "184 charges"
  "explicit human approval"
  "eu-west-1"
)
for anchor in "${anchors[@]}"; do
  grep -Fq "$anchor" HANDOFF.md || fail "missing anchor: $anchor" 24
done

expected=$(sha256sum history.md | cut -d' ' -f1)
[ "$expected" = "b58adf8efa640f1d91115fd77869c624e5d0673233193f6a5fb60b7cad72828c" ] || fail "history.md was modified" 25

echo "handoff_valid bytes=$size anchors=${#anchors[@]}"
echo "structured_handoff" > .runner/notes.txt
exit 0
