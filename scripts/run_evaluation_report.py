"""Standalone Stage 07 tool: Generate evaluation summary JSON + Markdown from stage artifacts."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hanviet.common.io import read_json
from hanviet.evaluation.metrics import summarize_alignment_review
from hanviet.evaluation.reports import export_evaluation_report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", required=True, type=Path, help="Path to alignment draft.json.")
    parser.add_argument("--llm-response", type=Path, help="Optional verification_response.json from 06_llm_hau_kiem.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Output 07_danh_gia directory.")
    parser.add_argument("--name", default="alignment_evaluation")
    args = parser.parse_args(argv)

    draft = read_json(args.draft)
    llm_resp = read_json(args.llm_response) if args.llm_response and args.llm_response.is_file() else None
    metrics = summarize_alignment_review(draft, llm_resp)
    json_path, md_path = export_evaluation_report(args.output_dir, report_name=args.name, metrics=metrics)
    print("Evaluation reports written:", json_path, md_path)


if __name__ == "__main__":
    main()
