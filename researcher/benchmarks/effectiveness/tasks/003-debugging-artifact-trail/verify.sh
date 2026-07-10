#!/usr/bin/env bash
set -uo pipefail
fail() { echo "verify: $1" >&2; exit "$2"; }
[ -f HANDOFF.md ] || fail "missing HANDOFF.md" 21
size=$(wc -c < HANDOFF.md)
[ "$size" -le 2500 ] || fail "HANDOFF.md exceeds 2500 bytes: $size" 22
heading_count=$(grep -Ec '^#{1,3}[[:space:]]+' HANDOFF.md || true)
[ "$heading_count" -ge 6 ] || fail "expected at least 6 explicit Markdown sections; found $heading_count" 23
anchors=(
  "UPSTREAM_POOL_EXHAUSTED E5037"
  "trace-91af"
  "acquireLease()"
  "services/orders/pool.ts"
  "middleware/retry.ts"
  "tests/orders/pool-leak.test.ts"
  "config/order-gateway.yaml"
  "12 failures/30s"
  "58 passed, 1 failing"
  "arm64"
  "ord_8N4K"
  "Nadia"
  "acme-eu"
)
for anchor in "${anchors[@]}"; do
  grep -Fq "$anchor" HANDOFF.md || fail "missing anchor: $anchor" 24
done
expected=$(sha256sum history.md | cut -d' ' -f1)
[ "$expected" = "f4e6e332765101b4dfb4b4fd8af4fcd4df7017921e2a931f343cec0ffd307926" ] || fail "history.md was modified" 25
echo "handoff_valid bytes=$size anchors=${#anchors[@]}"
echo "structured_handoff" > .runner/notes.txt
exit 0
