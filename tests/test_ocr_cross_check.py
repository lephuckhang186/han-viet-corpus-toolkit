"""Tests for Dual-OCR schema, adapters (Paddle/CLC/Tesseract/VietOCR), cross-check, and manual fixing."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import tests  # noqa: F401
from hanviet.common.io import sha256
from hanviet.extraction.cross_check.aligner import compare_han_texts, compare_viet_texts, cross_check_records
from hanviet.extraction.engines.clc_han import CLCOCRAdapter, import_clc_ocr_json, parse_clc_ocr_response
from hanviet.extraction.engines.tesseract_viet import TesseractVietEngine, parse_tesseract_tsv
from hanviet.extraction.engines.vietocr_viet import VietOCREngine
from hanviet.extraction.manual_review.reviewer import apply_manual_ocr_decisions, build_ocr_review_table, render_ocr_diff_html
from hanviet.extraction.schema import OCRRecord


def _make_rec(engine, text, order=1, region_id=0, bbox=None, conf=None, status="OK"):
    return OCRRecord(
        record_id=f"{engine}_{region_id}_{order}",
        source_id="src01",
        region_id=region_id,
        work_id="bai0024",
        corpus_id="CPO_11",
        member_id="TV04",
        variant="han" if engine in {"paddleocr", "clc_ocr"} else "dich_nghia",
        pdf_page=608,
        reading_order=order,
        engine=engine,
        model_version="test_v1",
        text=text,
        bbox=bbox,
        confidence=conf,
        image_reference="phan0001_pdfp0608.png",
        input_sha256="deadbeef",
        status=status,
    )


class TestOCRCrossCheckAndManualReview(unittest.TestCase):
    def test_exact_match_is_agreed_unverified(self):
        p = [_make_rec("paddleocr", "臣對明主", 1, 0, [[0, 0], [10, 0], [10, 50], [0, 50]], 0.95)]
        s = [_make_rec("clc_ocr", "臣對明主", 1, 0, [[0, 0], [10, 0], [10, 50], [0, 50]], None)]
        res = cross_check_records(p, s, variant="han")
        self.assertEqual(res["status"], "COMPLETE")
        self.assertEqual(res["items"][0]["status"], "AGREED_UNVERIFIED")

    def test_han_diff_substitution_insertion_deletion_astral_and_mask(self):
        # Includes Extension B astral character 𠀖 (U+20016) and [MASK]
        comp = compare_han_texts("臣𠀖[MASK]主之", "臣共主之地")
        self.assertFalse(comp["agreed"])
        ops = [o["op"] for o in comp["char_ops"]]
        self.assertIn("substitution", ops)
        self.assertIn("deletion", ops)
        self.assertIn("insertion", ops)

    def test_viet_tone_and_number_mismatch(self):
        comp = compare_viet_texts("Ngày 24 người thượng tướng", "Ngày 25 ngưởi thương tướng")
        self.assertIn("tone_mismatch", comp["issue_types"])
        self.assertIn("number_or_era_mismatch", comp["issue_types"])
        self.assertEqual([m["primary"] for m in comp["tone_mismatches"]], ["người", "thượng"])
        self.assertEqual(comp["number_mismatches"][0]["primary"], "24")

    def test_missing_region_and_reading_order_mismatch(self):
        p = [
            _make_rec("paddleocr", "第一", 1, 0, [[80, 0], [100, 0], [100, 50], [80, 50]], 0.9),
            _make_rec("paddleocr", "第二", 2, 1, [[10, 0], [30, 0], [30, 50], [10, 50]], 0.9),
        ]
        # Second line missing, first line bbox matched with order=2
        s = [_make_rec("clc_ocr", "第一", 2, 0, [[80, 0], [100, 0], [100, 50], [80, 50]], None)]
        res = cross_check_records(p, s, variant="han")
        self.assertEqual(res["status"], "NEEDS_REVIEW")
        self.assertIn("reading_order_mismatch", res["items"][0]["issue_types"])
        self.assertEqual(res["items"][1]["status"], "MISSING_REGION")

    def test_null_bbox_and_confidence_and_raw_immutability(self):
        rec = _make_rec("clc_ocr", "承", 1, 0, bbox=None, conf=None)
        d = rec.to_dict()
        self.assertIsNone(d["bbox"])
        self.assertIsNone(d["confidence"])

    def test_clc_timeout_invalid_response_and_import_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            img = tmp_path / "test.png"
            img.write_bytes(b"fake_png_bytes")
            err_log = tmp_path / "clc_err.jsonl"

            fake_session = MagicMock()
            fake_session.headers = {}
            fake_session.post.side_effect = TimeoutError("CLC timeout")
            adapter = CLCOCRAdapter(
                max_retries=1,
                backoff_seconds=0.0,
                min_delay_seconds=0.0,
                session=fake_session,
                quota_log_path=tmp_path / "clc.sqlite3",
            )
            recs = adapter.recognize_image(
                img,
                source_id="s1",
                work_id="bai0024",
                corpus_id="CPO_11",
                member_id="TV04",
                error_log_path=err_log,
            )
            self.assertEqual(recs[0].status, "FAILED")
            self.assertTrue(err_log.is_file())

            with self.assertRaises(ValueError):
                parse_clc_ocr_response(
                    {"is_success": False, "code": "999999", "data": None},
                    source_id="s1", work_id="bai0024", corpus_id="CPO_11", member_id="TV04",
                    variant="han", image_reference="test.png", input_sha256="abc",
                )

            with self.assertRaises(ValueError):
                CLCOCRAdapter(base_url="https://kimhannom.fit.hcmus.edu.vn/api/web/clc-sinonom/sentence-alignment")

            # Import existing JSON fixture mode
            sample_json = tmp_path / "clc_saved.json"
            sample_json.write_text(json.dumps({
                "identity": {"sha256": sha256(img), "options": {"ocr_id": 1, "lang_type": 1}},
                "response": {"is_success": True, "code": "000000", "data": {"result_ocr_text": ["承"], "result_bbox": []}},
            }), encoding="utf-8")
            imported = import_clc_ocr_json(
                sample_json, source_id="s1", work_id="bai0024", corpus_id="CPO_11", member_id="TV04"
            )
            self.assertEqual(imported[0].status, "IMPORTED")
            self.assertEqual(imported[0].text, "承")
            self.assertIsNone(imported[0].bbox)
            self.assertIsNone(imported[0].confidence)

    def test_manual_fixing_preserves_raw_and_explicit_mask_only(self):
        p = [_make_rec("paddleocr", "臣對", 1, 0, conf=0.9)]
        s = [_make_rec("clc_ocr", "臣封", 1, 0, conf=None)]
        report = cross_check_records(p, s, variant="han")
        rows = build_ocr_review_table(report)
        self.assertEqual(len(rows), 1)
        html = render_ocr_diff_html(report)
        self.assertIn("<mark", html)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Without INSERT_MASK, [MASK] is NEVER inserted automatically on disagreement
            res_defer = apply_manual_ocr_decisions(report, [{"item_id": "xc_0001", "decision": "DEFER"}])
            self.assertEqual(res_defer["transcription_text"], "")

            # Explicit ACCEPT_SECONDARY & INSERT_MASK
            res = apply_manual_ocr_decisions(
                report,
                [{"item_id": "xc_0001", "decision": "INSERT_MASK", "corrected_text": "臣[MASK]", "note": "blurred on crop"}],
                corrected_text_path=tmp_path / "corrected.txt",
                correction_log_path=tmp_path / "correction_log.jsonl",
            )
            self.assertEqual(res["transcription_text"], "臣[MASK]")
            self.assertTrue((tmp_path / "corrected.txt").is_file())
            self.assertTrue((tmp_path / "correction_log.jsonl").is_file())

    def test_incomplete_cross_check_single_engine_allowed(self):
        p = [_make_rec("paddleocr", "臣對", 1, 0)]
        report = cross_check_records(p, [], variant="han")
        self.assertEqual(report["status"], "CROSS_CHECK_INCOMPLETE")
        res = apply_manual_ocr_decisions(report, [{"item_id": "xc_0001", "decision": "ACCEPT_PRIMARY"}])
        self.assertEqual(res["records"][0]["status"], "REVIEWED_SINGLE_ENGINE_ONLY")
        self.assertFalse(res["records"][0]["cross_check_complete"])

    def test_tesseract_tsv_parser_and_vietocr_line_requirement(self):
        sample_tsv = (
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
            "5\t1\t1\t1\t1\t1\t10\t20\t40\t18\t92\tNgày\n"
            "5\t1\t1\t1\t1\t2\t55\t20\t25\t18\t88\t24\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            img = Path(tmp) / "viet.png"
            img.write_bytes(b"png")
            engine = TesseractVietEngine(runner=lambda *_: sample_tsv)
            recs = engine.recognize_image(
                img, source_id="s_v", work_id="bai0024", corpus_id="CPO_11", member_id="TV04"
            )
            self.assertEqual(len(recs), 1)
            self.assertEqual(recs[0].text, "Ngày 24")
            self.assertAlmostEqual(recs[0].confidence, 0.90)
            self.assertEqual(recs[0].bbox, [[10, 20], [80, 20], [80, 38], [10, 38]])

            vietocr = VietOCREngine(detector=None, recognizer=None)
            with self.assertRaises(RuntimeError):
                vietocr.recognize_lines(
                    img, None, source_id="s_v", work_id="bai0024", corpus_id="CPO_11", member_id="TV04"
                )


if __name__ == "__main__":
    unittest.main()
