"""Stage 02 output directory manager, bundle exporter, and Text Cleaning compatibility adapter."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from hanviet.common.io import atomic_bytes, bytes_hash, sha256, write_json
from hanviet.extraction.manual_review.reviewer import (
    build_ocr_review_table,
    export_cross_check_xlsx,
    export_ocr_review_csv,
    render_ocr_diff_html,
    render_region_overlay_png,
)

BOOK_FOLDERS = {"CPO_09": "BacSu", "CPO_10": "HichTuongSi", "CPO_11": "ThiDinh", "CPO_12": "LyTran"}


def stage_han_dirs(han_root: Path) -> dict[str, Path]:
    """Create and return standardized Task 13 directory paths under 02_ocr_tho/han/."""
    han_root = Path(han_root)
    dirs = {
        "root": han_root,
        "paddle_text": han_root / "paddle_ocr" / "text",
        "paddle_meta": han_root / "paddle_ocr" / "metadata",
        "paddle_vis": han_root / "paddle_ocr" / "visualization",
        "clc_text": han_root / "clc_ocr" / "text",
        "clc_meta": han_root / "clc_ocr" / "metadata",
        "clc_req": han_root / "clc_ocr" / "requests",
        "clc_resp": han_root / "clc_ocr" / "responses",
        "cross_check": han_root / "cross_check",
        "manual_review": han_root / "manual_review",
        "corrected_parts": han_root / "corrected" / "parts",
        "corrected_merged": han_root / "corrected" / "merged",
        "eval_gold": han_root / "evaluation" / "gold_samples",
        "eval_figures": han_root / "evaluation" / "figures",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def save_independent_engine_outputs(
    engine_dir: Path,
    *,
    engine_name: str,
    records: list[dict[str, Any]],
    part_stem: str,
    image_path: Path | None = None,
    render_overlay: bool = False,
) -> dict[str, Path]:
    """Save primary or secondary OCR outputs independently under text/, metadata/, and manifest.json."""
    engine_dir = Path(engine_dir)
    text_dir = engine_dir / "text"
    meta_dir = engine_dir / "metadata"
    vis_dir = engine_dir / "visualization"
    text_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    joined_text = "\n".join(str(r.get("text", "")) for r in records)
    txt_bytes = joined_text.encode("utf-8")
    txt_path = text_dir / f"{part_stem}.txt"
    atomic_bytes(txt_path, txt_bytes)

    meta_path = meta_dir / f"{part_stem}.records.json"
    write_json(
        meta_path,
        {
            "engine": engine_name,
            "part_stem": part_stem,
            "txt_sha256": bytes_hash(txt_bytes),
            "record_count": len(records),
            "records": records,
        },
    )

    outputs: dict[str, Path] = {"txt": txt_path, "meta": meta_path}
    if render_overlay and image_path is not None and Path(image_path).is_file():
        vis_dir.mkdir(parents=True, exist_ok=True)
        outputs["overlay"] = render_region_overlay_png(
            Path(image_path), records, vis_dir / f"{part_stem}_overlay.png"
        )

    manifest_path = engine_dir / "manifest.json"
    existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {"parts": {}}
    existing_manifest["engine"] = engine_name
    existing_manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    existing_manifest["parts"][part_stem] = {
        "txt": txt_path.relative_to(engine_dir).as_posix(),
        "meta": meta_path.relative_to(engine_dir).as_posix(),
        "txt_sha256": bytes_hash(txt_bytes),
        "record_count": len(records),
    }
    write_json(manifest_path, existing_manifest)
    outputs["manifest"] = manifest_path
    return outputs


def export_cross_check_bundle(
    cross_check_dir: Path,
    cross_check_report: dict[str, Any],
    statistics: dict[str, Any] | None = None,
) -> dict[str, Path]:
    """Write standardized Task 13 JSONL, CSV, HTML, XLSX, and statistics artifacts into cross_check/."""
    cross_check_dir = Path(cross_check_dir)
    cross_check_dir.mkdir(parents=True, exist_ok=True)
    items = cross_check_report.get("items", [])

    def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
        payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8")
        atomic_bytes(path, payload)
        return path

    region_rows = [
        {
            "item_id": it["item_id"],
            "source_id": it["source_id"],
            "match_type": it.get("match_type", "1-1"),
            "match_method": it.get("match_method"),
            "status": it["status"],
            "primary_record_ids": it.get("primary_record_ids", []),
            "secondary_record_ids": it.get("secondary_record_ids", []),
        }
        for it in items
    ]
    line_rows = [
        {
            "item_id": it["item_id"],
            "primary_text": (it.get("primary") or {}).get("text", ""),
            "secondary_text": (it.get("secondary") or {}).get("text", ""),
            "issue_types": it.get("issue_types", []),
        }
        for it in items
    ]
    char_rows = [
        {
            "item_id": it["item_id"],
            "agreed": (it.get("comparison") or {}).get("agreed"),
            "agreement_rate": (it.get("comparison") or {}).get("agreement_rate"),
            "char_ops": [op for op in (it.get("comparison") or {}).get("char_ops", []) if op.get("op") != "equal"],
        }
        for it in items
        if it.get("comparison")
    ]
    disagreements = cross_check_report.get("disagreements", [])

    review_rows = build_ocr_review_table(cross_check_report)
    unmatched_rows = [r for r in review_rows if r["status"] in {"MISSING_REGION", "CROSS_CHECK_INCOMPLETE"}]

    paths: dict[str, Path] = {
        "region_matches": _write_jsonl(cross_check_dir / "region_matches.jsonl", region_rows),
        "line_matches": _write_jsonl(cross_check_dir / "line_matches.jsonl", line_rows),
        "character_alignment": _write_jsonl(cross_check_dir / "character_alignment.jsonl", char_rows),
        "disagreements": _write_jsonl(cross_check_dir / "disagreements.jsonl", disagreements),
        "comparison_xlsx": export_cross_check_xlsx(cross_check_dir / "comparison.xlsx", review_rows, sheet_name="COMPARISON"),
        "unmatched_xlsx": export_cross_check_xlsx(cross_check_dir / "unmatched_regions.xlsx", unmatched_rows, sheet_name="UNMATCHED"),
    }
    if review_rows:
        paths["review_queue_csv"] = export_ocr_review_csv(cross_check_dir / "review_queue.csv", review_rows)
    html_path = cross_check_dir / "diff_report.html"
    atomic_bytes(html_path, render_ocr_diff_html(cross_check_report).encode("utf-8"))
    paths["diff_html"] = html_path
    stats_path = cross_check_dir / "statistics.json"
    write_json(stats_path, statistics or cross_check_report.get("summary", {}))
    paths["statistics"] = stats_path
    return paths


def export_cleaning_compatible_han_transcription(
    projection_root: Path,
    *,
    corpus_id: str,
    work_stem: str,
    part_transcriptions: list[dict[str, Any]],
    approved: bool,
    allow_draft: bool = False,
) -> dict[str, Path]:
    """Export the chosen reviewed Han transcription in exact Stage 03 clean_text input layout.

    `hanviet.cleaning.pipeline.read_sources()` requires:
    - `<projection_root>/<BookFolder>/02_ocr_tho/han/<work_stem>/<part_name>.txt` (for `parts` mode)
    - `<projection_root>/<BookFolder>/02_ocr_tho/han/<work_stem>/<work_stem>_ocr_tho.txt` (for `merged` mode)
    - Raw PaddleOCR/CLC directories MUST NOT coexist under `projection_root` so Text Cleaning reads ONLY
      this single reviewed transcription without changing any protected cleaning code.
    """
    if not approved and not allow_draft:
        raise PermissionError(
            "Official Text Cleaning export requires human approval (approved=True). "
            "Pass allow_draft=True only for draft preview export."
        )
    if corpus_id not in BOOK_FOLDERS:
        raise ValueError(f"Unsupported corpus_id for Text Cleaning compatibility export: {corpus_id!r}")
    if not part_transcriptions:
        raise ValueError("part_transcriptions must not be empty.")

    book_folder = BOOK_FOLDERS[corpus_id]
    projection_root = Path(projection_root)
    work_ocr_dir = projection_root / book_folder / "02_ocr_tho" / "han" / work_stem
    work_ocr_dir.mkdir(parents=True, exist_ok=True)

    written: dict[str, Path] = {}
    part_names: list[str] = []
    merged_segments: list[str] = []

    for part in part_transcriptions:
        image_name = str(part["image_name"])
        part_stem = Path(image_name).stem
        text = str(part["text"])
        txt_path = work_ocr_dir / f"{part_stem}.txt"
        txt_bytes = text.encode("utf-8")
        atomic_bytes(txt_path, txt_bytes)

        source_sha = str(part.get("source_sha256") or "")
        meta_path = work_ocr_dir / f"{part_stem}.meta.json"
        lines = text.split("\n")
        reading_map = part.get("reading_map") or [
            {"txt_line": idx, "polygon": None} for idx in range(1, len(lines) + 1)
        ]
        write_json(
            meta_path,
            {
                "identity": {"source_sha256": source_sha, "source_file": image_name},
                "output_hashes": {"txt": bytes_hash(txt_bytes)},
                "review": {"reading_map": reading_map},
                "reviewed_export": {"approved": approved, "status": "APPROVED" if approved else "DRAFT"},
            },
        )
        part_names.append(image_name)
        merged_segments.append(text)
        written[part_stem] = txt_path

    merged_bytes = "\f".join(merged_segments).encode("utf-8")
    merged_path = work_ocr_dir / f"{work_stem}_ocr_tho.txt"
    atomic_bytes(merged_path, merged_bytes)
    written["merged"] = merged_path

    manifest_path = projection_root / "05_quan_ly" / "ghep_theo_tac_pham.json"
    existing = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else []
    filtered = [r for r in existing if not (r.get("work") == work_stem)]
    filtered.append(
        {
            "work": work_stem,
            "sha256": bytes_hash(merged_bytes),
            "status": "merged",
            "source_files": part_names,
            "approved": approved,
        }
    )
    write_json(manifest_path, filtered)
    written["manifest"] = manifest_path
    return written
