# CDC Report Provenance

The exemplar the long-horizon-prompting skill is built on: OpenAI's published prompt
and candidate proof for the Cycle Double Cover Conjecture, produced by GPT-5.6 Sol Ultra
running a 64-subagent orchestration.

## Files

| File | Source URL | Bytes | SHA-256 |
| --- | --- | --- | --- |
| `cdc_prompt.pdf` | https://cdn.openai.com/pdf/04d1d1e4-bc75-476a-97cf-49055cd98d31/cdc_prompt.pdf | 123015 | `0e48deee28caba82ee5b4191d4c5c6ec4d62e5d27890fa7f0d2c8868f8b758f3` |
| `cdc_proof.pdf` | https://cdn.openai.com/pdf/04d1d1e4-bc75-476a-97cf-49055cd98d31/cdc_proof.pdf | 325198 | `b4797f5053d9067329b3dcfcbf913f8bb40d13467453b1300f6d78d08460fc13` |

`cdc_prompt.txt` and `cdc_proof.txt` are text extractions (pypdf) kept for grep-ability and
diffing. Non-text control characters introduced by PDF extraction are replaced with the Unicode
replacement character; form feeds that preserve page boundaries remain. The PDFs are the
authoritative artifacts.

## Retrieval

- Retrieved: 2026-07-11 (this run), via `scripts/fetch_report.sh`.
- PDF internal `CreationDate`: `D:20260710` for both files, consistent with the documented
  2026-07-10 publication date.
- Producer: `pdfTeX-1.40.28`, `LaTeX with hyperref` (both).
- Prompt PDF: 2 pages. Proof PDF: 3 pages.

## Cross-check against the repo skill reference

`scripts/verify_report.py` re-extracts the prompt text and asserts that every block-quote in
`skills/long-horizon-prompting/references/cdc-prompt-annotated.md` appears verbatim in the
published prompt. Result at retrieval time: 0 drifted fragments. This confirms the skill's
annotated reference is faithful to the primary source, not paraphrased.

## Caveats (carried from the skill, do not drop)

- The candidate proof had no independent peer review, no Lean/Coq formalization, and no arXiv
  posting at publication time. The validated artifact of interest is the prompt structure, not
  the theorem.
- No public ablation isolates which prompt elements carried the result. Per-element evidence in
  the skill comes from independent academic work (see `references/research-evidence.md`), not
  from this single run.
- The proof's own statement of AI use: "The proof in this note is entirely due to GPT 5.6 Sol
  Ultra and the writeup with Codex (with GPT 5.6 Sol)."
