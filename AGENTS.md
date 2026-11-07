# NLP corpus preparation — TV2

## Sources of truth
- Read `CONTEXT.md` (the user's saved teacher rules), the local `Guideline.pdf`
  when available, and `phan_buoc_3_guideline.md` before changing corpus behavior.
  PDFs are local inputs and are not distributed in Git. Preserve these files.
- This project is currently step 3: source preservation, work boundaries and names.
  OCR, linguistic correction, sentence alignment and quota certification are later.
- `data/` contains immutable input PDFs. Never overwrite, rename or move them.
- Group material by **work and text version**, not by PDF page. A work can have
  several regions/pages; a page can contain several works.
- Retain Hán, dịch âm, dịch nghĩa, dịch thơ as distinct versions of the same work.
  Missing versions must be recorded explicitly; never fabricate a translation.
- Keep source footnotes intact at this stage. Step 5 removes notes outside the
  Hán main content; do not silently rewrite source text during cropping.

## Ownership and structure
- `ten_file.py`: input names, output root, topic/member codes and naming rules only.
- Each `cat_*.py` owns its book's ranges and instructions.
- `cong_cu/`: separate modules for PDF, text, storage, workspace, CLI and UI.
- TV2: Lý–Trần works 131–207 / PDF 187–366; Văn sách 14–18 / PDF 188–365;
  Bắc sứ Việt PDF 39–75. Bắc sứ Hán PDF 54–106 is an inventory assignment,
  **not** a translation mapping. Hịch is a shared review example.
- Output belongs in `san_pham/TV02/<MA_DE_TAI>_<MA_TAC_PHAM>/`.
- Read the current topic code from `ten_file.py`; preserve the user's setting.
- This directory is a Git repository. Preserve existing work and the user's
  current branch; publish only when explicitly requested.

## Validation
- Python >=3.11 with Tkinter (Pillow 13 requires it). Dependencies are pinned in `requirements.txt`.
- `.venv/Scripts/python.exe -m unittest discover -s tests -v` runs focused tests.
- `.venv/Scripts/python.exe cat_ly_tran.py --check` verifies saved hashes.
- The four `cat_*.py` entry points launch their GUI without arguments; `--info`
  is read-only; `--prepare` builds folders/backups; CSV plans preview by default.
- Source hashes, crop geometry, work assembly order, text boundaries and
  no-overwrite behavior need validation. Do not report a draft crop as complete.
- Export crops as PNG grouped by work/version, with optional raw TXT extraction.
  Do not generate or assemble cropped PDFs. Preserve original PDF backups and
  page/region order in the manifest.
- `region_actions.py` owns region edits/removal and review progress; `history.py`
  journals changed files and manifests for rollback/undo. Never modify source
  backups through edit/undo. Preserve legacy records without an `id` field.
- A source hash may be reused only within a process after full verification and
  while original/backup path, size, mtime and ctime match. `--check` stays a full
  hash verification. PDFium operations remain on the main thread.
- `complete` means a user confirmed a text version's coverage, not alignment or
  quota correctness. Invalidate it when that version's regions change.
