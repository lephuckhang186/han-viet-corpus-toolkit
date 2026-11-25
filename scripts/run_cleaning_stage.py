"""Standalone Stage 03 tool: Rule-based Han/Viet text cleaning and CSV review export."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hanviet.cleaning.pipeline import build_records, csv_bytes, read_sources, write_once
from hanviet.cleaning.viet_cleaner import load_pronunciation_vocabulary
from hanviet.common.manifests import stage_manifest_payload, write_stage_manifest
from hanviet.common.paths import resolve_paths


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-path", type=Path, help="Input OCR directory or ZIP (defaults to configured data_root).")
    parser.add_argument("--output-dir", required=True, type=Path, help="Output directory for rule-based & review CSV.")
    parser.add_argument("--member", type=int, default=4, help="Member number (e.g. 2 or 4).")
    parser.add_argument("--codes", nargs="+", default=["CPO_09", "CPO_11", "CPO_12"])
    parser.add_argument("--kinds", nargs="+", default=["han", "dich_am", "dich_nghia", "dich_tho"])
    parser.add_argument("--granularity", choices=["parts", "merged"], default="parts")
    args = parser.parse_args(argv)

    paths = resolve_paths()
    input_path = args.input_path or paths.data_root
    dict_path = paths.dict_root / "QuocNgu_SinoNom_TongHop3.csv"
    vocab = load_pronunciation_vocabulary(dict_path)
    sources = read_sources(
        input_path,
        selected_codes=set(args.codes),
        selected_kinds=set(args.kinds),
        member_number=args.member,
        input_granularity=args.granularity,
    )
    records = build_records(sources, vocab)
    review_rows = [
        dict(row, polygon=json.dumps(row["polygon"]) if row["polygon"] else "", action="", replacement="", note="")
        for row in records
    ]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "duyet_lam_sach.csv"
    if not csv_path.exists() and review_rows:
        write_once(csv_path, csv_bytes(review_rows, list(review_rows[0].keys())))

    manifest = stage_manifest_payload(
        stage="03_rule_based_cleaning",
        version="1.0.0",
        input_manifest=[{"relative_path": s["relative_path"], "sha256": s["source_sha256"]} for s in sources],
        output_manifest={"review_csv": str(csv_path)},
        config_snapshot={"codes": args.codes, "kinds": args.kinds, "member": args.member, "granularity": args.granularity},
        review_status="PENDING_MANUAL_REVIEW",
        statistics={"records": len(records), "flagged": sum(bool(r["reasons"]) for r in records)},
    )
    write_stage_manifest(args.output_dir / "stage_manifest.json", manifest)
    print(f"Prepared {len(records)} cleaning records -> {csv_path}")


if __name__ == "__main__":
    main()
