# Alignment Structured Repair Prompt (v1.0.0)

## Role
Propose structured, schema-validated repair operations for issues detected during post-alignment verification, strictly **for human manual approval** (`approved` stays `false`).

## Allowed Operations
- `KEEP`: Aligned group is accurate.
- `MERGE`: Merge contiguous links/units in the same column (`han_ids` / `am_ids` / `nghia_ids` / `tho_ids`).
- `SPLIT`: Split an over-grouped link into smaller contiguous links covering the exact same span.
- `RELINK`: Reassign segment IDs between existing `han_ids` and target IDs strictly within work bounds & monotone order.
- `ADD_LINK`: Link previously unaligned existing IDs.
- `REMOVE_LINK`: Unlink a spurious pairing (units become unmatched and require `skipped` reason).
- `FLAG_OCR`: Issue requires returning to OCR stage (`requires_earlier_stage: "ocr"`).
- `FLAG_CLEANING`: Issue requires returning to text cleaning/segmentation stage (`requires_earlier_stage: "cleaning"`).
- `REQUEST_REVIEW`: Ambiguous pairing requiring human inspection.

## Hard Rules
- Preserve exact `work` and `fingerprint`.
- Do NOT rewrite text, create `[MASK]` without evidence, invent IDs, or output `approved: true`.
- Output strictly valid JSON matching `schemas/alignment_repair.schema.json`.
