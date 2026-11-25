"""Standalone Stage 02 tool: Cross-check saved primary & secondary OCR JSONs and emit manual review CSV/HTML."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hanviet.common.io import read_json, write_json
from hanviet.common.manifests import stage_manifest_payload, write_stage_manifest
from hanviet.extraction.cross_check.aligner import cross_check_records
from hanviet.extraction.manual_review.reviewer import (
    build_ocr_review_table,
    export_ocr_review_csv,
    render_ocr_diff_html,
)
from hanviet.extraction.schema import OCRRecord


def _load_records(path: Path) -> list[OCRRecord]:
    raw = read_json(path)
    items = raw if isinstance(raw, list) else raw.get("records", [])
    return [OCRRecord(**{k: v for k, v in item.items() if k != "extra"}, extra=item.get("extra", {})) for item in items]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", required=True, type=Path, help="Primary OCR records JSON (PaddleOCR or Tesseract).")
    parser.add_argument("--secondary", type=Path, help="Secondary OCR records JSON (CLC OCR or VietOCR).")
    parser.add_argument("--variant", required=True, choices=["han", "dich_am", "dich_nghia", "dich_tho"])
    parser.add_argument("--output-dir", required=True, type=Path, help="Destination cross_check directory.")
    args = parser.parse_args(argv)

    primary = _load_records(args.primary)
    secondary = _load_records(args.secondary) if args.secondary and args.secondary.is_file() else []
    report = cross_check_records(primary, secondary, variant=args.variant)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / "cross_check.json"
    write_json(report_path, report)
    rows = build_ocr_review_table(report)
    if rows:
        export_ocr_review_csv(args.output_dir / "cross_check_review.csv", rows)
    (args.output_dir / "cross_check_diff.html").write_text(render_ocr_diff_html(report), encoding="utf-8")

    manifest = stage_manifest_payload(
        stage="02_ocr_cross_check",
        version="1.0.0",
        input_manifest={"primary": str(args.primary), "secondary": str(args.secondary) if args.secondary else None},
        output_manifest={"cross_check_json": str(report_path)},
        config_snapshot={"variant": args.variant},
        review_status=report["status"],
        statistics=report["summary"],
    )
    write_stage_manifest(args.output_dir / "stage_manifest.json", manifest)
    print("Cross-check complete:", report["status"], report["summary"])


if __name__ == "__main__":
    main()
