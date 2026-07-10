#!/usr/bin/env bash
set -uo pipefail
fail() { echo "verify: $1" >&2; exit "$2"; }
[ -f HANDOFF.md ] || fail "missing HANDOFF.md" 21
size=$(wc -c < HANDOFF.md)
[ "$size" -le 2500 ] || fail "HANDOFF.md exceeds 2500 bytes: $size" 22
heading_count=$(grep -Ec '^#{1,3}[[:space:]]+' HANDOFF.md || true)
[ "$heading_count" -ge 6 ] || fail "expected at least 6 explicit Markdown sections; found $heading_count" 23
anchors=(
  "SCHEMA_COMPATIBILITY_BREAK E1904"
  "batch_2026_07_10_42"
  "encodeEnvelopeV2()"
  "ingestion/envelope_v2.py"
  "consumers/dual_write.py"
  "tests/ingestion/schema_compat_test.py"
  "infra/kafka/topics.yaml"
  "legacy_customer_id"
  "events-v1"
  "CAB-2048"
  "14 days"
  "44 passed, 3 failing"
  "2,304,118 events"
  "Mara"
  "DPO-771"
  "ap-southeast-2"
)
for anchor in "${anchors[@]}"; do
  grep -Fq "$anchor" HANDOFF.md || fail "missing anchor: $anchor" 24
done
expected=$(sha256sum history.md | cut -d' ' -f1)
[ "$expected" = "34acb3d52427f61921a50e0924db0717e6afcb3737745171569d6d05f6c79833" ] || fail "history.md was modified" 25
echo "handoff_valid bytes=$size anchors=${#anchors[@]}"
echo "structured_handoff" > .runner/notes.txt
exit 0
