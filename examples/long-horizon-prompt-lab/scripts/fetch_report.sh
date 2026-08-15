#!/usr/bin/env bash
# Fetch the most recent published CDC report (prompt + candidate proof) that the
# long-horizon-prompting skill is anchored on, extract text, and record provenance.
#
# Usage: examples/long-horizon-prompt-lab/scripts/fetch_report.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$(cd "$HERE/.." && pwd)/report"
mkdir -p "$OUT"

PROMPT_URL="https://cdn.openai.com/pdf/04d1d1e4-bc75-476a-97cf-49055cd98d31/cdc_prompt.pdf"
PROOF_URL="https://cdn.openai.com/pdf/04d1d1e4-bc75-476a-97cf-49055cd98d31/cdc_proof.pdf"

echo "Fetching prompt PDF..."
curl -sSL -o "$OUT/cdc_prompt.pdf" "$PROMPT_URL"
echo "Fetching proof PDF..."
curl -sSL -o "$OUT/cdc_proof.pdf" "$PROOF_URL"

echo "Extracting text (requires pypdf: pip install pypdf)..."
python3 - "$OUT" <<'PY'
import sys
from pathlib import Path
from pypdf import PdfReader
out = Path(sys.argv[1])
for name in ("cdc_prompt", "cdc_proof"):
    reader = PdfReader(str(out / f"{name}.pdf"))
    text = "\n".join(page.extract_text() for page in reader.pages)
    text = "".join(
        character
        if character in "\t\n\r\f" or 32 <= ord(character) < 127 or ord(character) >= 160
        else "\N{REPLACEMENT CHARACTER}"
        for character in text
    )
    (out / f"{name}.txt").write_text(text, encoding="utf-8")
    print(f"  {name}: {len(reader.pages)} pages -> {name}.txt")
PY

echo "SHA-256:"
sha256sum "$OUT"/*.pdf

echo "Done. See report/PROVENANCE.md for recorded hashes and caveats."
