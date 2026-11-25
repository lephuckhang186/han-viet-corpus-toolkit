"""Tests for stage outputs, manifest contracts, evaluation metrics, and legacy loader isolation."""
import tempfile
import unittest
from pathlib import Path

import tests  # noqa: F401
from hanviet.alignment.runner import clean_sources_by_work
from hanviet.common.io import write_json
from hanviet.common.manifests import stage_manifest_payload, write_stage_manifest
from hanviet.common.llm_client import validate_against_schema
from hanviet.evaluation.metrics import compute_alignment_eval, compute_cer_wer, summarize_ocr_cross_check


class TestStageOutputsAndEvaluation(unittest.TestCase):
    def test_legacy_loader_does_not_read_llm_proposals_or_draft_subfolders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book_root = root / "san_pham" / "TV04" / "CV06_CPO_11"
            approved = book_root / "03_text_sach" / "han" / "CPO_11_TV04_bai0024_han.txt"
            llm_prop = book_root / "03_text_sach" / "llm_proposals" / "CPO_11_TV04_bai0024_han.txt"
            rule_draft = book_root / "03_text_sach" / "rule_based" / "CPO_11_TV04_bai0024_han.txt"
            for p, content in ((approved, "approved"), (llm_prop, "llm"), (rule_draft, "draft")):
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
            found = clean_sources_by_work(book_root, "CPO_11", "TV04", data_root=root / "data")
            self.assertEqual(found["bai0024"]["han"], [approved])

    def test_stage_manifest_validates_against_schema(self):
        schema_path = Path(__file__).resolve().parents[1] / "schemas" / "stage_manifest.schema.json"
        import json
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        manifest = stage_manifest_payload(
            stage="03_text_cleaning",
            version="1.0.0",
            input_manifest={"files": ["a.txt"]},
            output_manifest={"files": ["b.txt"]},
            config_snapshot={"granularity": "parts"},
            review_status="PENDING_MANUAL_REVIEW",
            statistics={"lines": 10},
        )
        errors = validate_against_schema(manifest, schema)
        self.assertEqual(errors, [])

    def test_evaluation_distinguishes_gold_from_disagreement(self):
        self.assertFalse(compute_cer_wer([], [])["reference_available"])
        self.assertFalse(compute_alignment_eval([], [])["gold_available"])
        cer_res = compute_cer_wer(["abc", "def"], ["axc", "def"])
        self.assertAlmostEqual(cer_res["cer"], 1 / 6, places=5)
        stats = summarize_ocr_cross_check({"status": "COMPLETE", "summary": {"total": 2, "agreed_unverified": 1, "disagreements": 1}})
        self.assertEqual(stats["model_agreed_unverified"], 1)
        self.assertIsNone(stats["human_confirmed_errors"])


if __name__ == "__main__":
    unittest.main()
