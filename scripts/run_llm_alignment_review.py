"""Standalone Stage 06 tool: LLM alignment verification & repair proposal validation on draft.json."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hanviet.alignment.llm_review.patch_validator import validate_alignment_proposals
from hanviet.alignment.llm_review.verifier import run_llm_alignment_verification
from hanviet.common.config import load_method_config
from hanviet.common.io import read_json, write_json
from hanviet.common.llm_client import LLMConfig
from hanviet.common.manifests import stage_manifest_payload, write_stage_manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", required=True, type=Path, help="Path to alignment draft.json.")
    parser.add_argument("--stage-dir", required=True, type=Path, help="Output 06_llm_hau_kiem directory.")
    parser.add_argument("--review", type=Path, help="Optional existing review.json (will never be overwritten if approved=true).")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    args = parser.parse_args(argv)

    cfg = load_method_config("llm")
    llm_cfg = LLMConfig(
        provider=args.provider or cfg.get("provider"),
        model=args.model or cfg.get("model"),
        timeout_seconds=cfg.get("timeout_seconds", 60.0),
        max_retries=cfg.get("max_retries", 2),
        cache_dir=args.stage_dir / "cache",
        prompt_version=cfg.get("prompt_versions", {}).get("alignment_verification", "1.0.0"),
    )
    draft = read_json(args.draft)
    existing_review = read_json(args.review) if args.review and args.review.is_file() else None
    report = run_llm_alignment_verification(draft, llm_config=llm_cfg, stage_dir=args.stage_dir)

    validated = None
    if report["status"] == "OK" and report.get("response"):
        validated = validate_alignment_proposals(draft, report["response"], existing_review=existing_review)
        write_json(args.stage_dir / "patches" / "validated_patches.json", validated)

    manifest = stage_manifest_payload(
        stage="06_llm_alignment_verification",
        version="1.0.0",
        input_manifest={"draft": str(args.draft), "work": draft["work"], "fingerprint": draft["fingerprint"]},
        output_manifest={"stage_dir": str(args.stage_dir)},
        config_snapshot={"provider": llm_cfg.provider, "model": llm_cfg.model},
        review_status=report["status"],
        statistics={
            "valid_proposals": len(validated["valid_proposals"]) if validated else 0,
            "rejected_proposals": len(validated["rejected_proposals"]) if validated else 0,
        },
    )
    write_stage_manifest(args.stage_dir / "stage_manifest.json", manifest)
    print("LLM Alignment Verification status:", report["status"])


if __name__ == "__main__":
    main()
