"""Comprehensive tests for Han Dual-OCR cross-check, normalization, DP matching, safe manual fixing, metrics, and Stage 03 cleaning compatibility."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import tests  # noqa: F401
from hanviet.cleaning.pipeline import attach_review_pages, build_records, read_sources
from hanviet.common.io import sha256
from hanviet.evaluation.metrics import compute_han_ocr_evaluation, experiment_matrix_template
from hanviet.extraction.cross_check import (
    compare_han_texts,
    cross_check_records,
    match_lines_dp,
    tokenize_han_with_spans,
)
from hanviet.extraction.engines.clc_han import (
    CLCOCRAdapter,
    import_clc_ocr_text,
)
from hanviet.extraction.engines.paddle_han import PaddleHanEngine
from hanviet.extraction.exporter import (
    export_cleaning_compatible_han_transcription,
    export_cross_check_bundle,
    save_independent_engine_outputs,
    stage_han_dirs,
)
from hanviet.extraction.manual_review import apply_manual_ocr_decisions, render_ocr_diff_html, render_region_overlay_png
from hanviet.extraction.schema import OCRRecord


def _han_rec(
    engine: str,
    text: str,
    order: int,
    region_id: int | str,
    *,
    bbox: list | None = None,
    conf: float | None = None,
    work_id: str = "bai0024",
    source_id: str = "phan0001_pdfp0608",
    pdf_page: int = 608,
    input_sha256: str = "fp001",
    status: str = "OK",
) -> OCRRecord:
    return OCRRecord(
        record_id=f"{engine}_{source_id}_{region_id}_{order}",
        source_id=source_id,
        region_id=region_id,
        work_id=work_id,
        corpus_id="CPO_11",
        member_id="TV04",
        variant="han",
        pdf_page=pdf_page,
        reading_order=order,
        engine=engine,
        model_version=f"{engine}_v1",
        text=text,
        bbox=bbox,
        confidence=conf,
        image_reference=f"{source_id}.png",
        input_sha256=input_sha256,
        status=status,
    )


class TestHanNormalizationAndCharAlignment(unittest.TestCase):
    def test_15_character_alignment_edge_cases(self):
        # 1. Exact match
        self.assertTrue(compare_han_texts("古南交", "古南交")["agreed"])
        # 2. Single substitution (常 <-> 裳)
        sub = compare_han_texts("古南交周號越常", "古南交周號越裳")
        self.assertEqual([o["op"] for o in sub["char_ops"]], ["equal"] * 6 + ["substitution"])
        # 3. Missing char at start
        self.assertEqual(compare_han_texts("天地", "地")["char_ops"][0]["op"], "deletion")
        # 4. Missing char in middle (周 deleted in secondary)
        mid = compare_han_texts("古南交周號越裳", "古南交號越裳")
        dels = [o for o in mid["char_ops"] if o["op"] != "equal"]
        self.assertEqual(len(dels), 1)
        self.assertEqual((dels[0]["op"], dels[0]["a"]), ("deletion", "周"))
        # 5. Missing char at end
        self.assertEqual(compare_han_texts("天地", "天")["char_ops"][-1]["op"], "deletion")
        # 6. Extra char (insertion in secondary)
        ins = compare_han_texts("天地之間", "天地之之間")
        ins_ops = [o for o in ins["char_ops"] if o["op"] != "equal"]
        self.assertEqual((ins_ops[0]["op"], ins_ops[0]["b"]), ("insertion", "之"))
        # 7. Multiple diffs
        self.assertEqual(compare_han_texts("甲乙丙丁", "甲戊己丁")["disagreement_count"], 2)
        # 8. Repeated chars tie-breaking consistency
        rep1 = compare_han_texts("之之間", "之間")["char_ops"]
        rep2 = compare_han_texts("之之間", "之間")["char_ops"]
        self.assertEqual(rep1, rep2)
        # 9. One empty string
        self.assertEqual(compare_han_texts("臣對", "")["disagreement_count"], 2)
        # 10. Both empty
        both_empty = compare_han_texts("", "")
        self.assertTrue(both_empty["agreed"])
        self.assertEqual(both_empty["agreement_rate"], 1.0)
        # 11. CJK Extension B+ rare char preserved
        astral = compare_han_texts("臣𠀖對", "臣𠀗對")
        self.assertEqual(astral["disagreement_count"], 1)
        # 12. Variation selector kept attached to base glyph (single unit)
        vs_toks = tokenize_han_with_spans("葛\U000E0100城").tokens
        self.assertEqual(len(vs_toks), 2)
        self.assertEqual(vs_toks[0].unit, "葛\U000E0100")
        self.assertEqual((vs_toks[0].orig_start, vs_toks[0].orig_end), (0, 2))
        # 13. Atomic [MASK] preserved
        mask_res = compare_han_texts("臣[MASK]主", "臣[MASK]主")
        self.assertTrue(mask_res["agreed"])
        # 14 & 15. Strict preserves punctuation/whitespace; content collapses whitespace
        strict_diff = compare_han_texts("臣對。\n第一", "臣對。 第一", profile="strict")
        self.assertFalse(strict_diff["agreed"])
        self.assertTrue(strict_diff["content_comparison"]["agreed"])


class TestHanRegionAndDPLineMatching(unittest.TestCase):
    def test_dp_line_matching_1_to_n_and_n_to_1_and_cross_scope_isolation(self):
        # Prompt Section 13 exact scenario: L001 splits into CLC L001 + L002
        p_lines = [
            _han_rec("paddleocr", "古南交周號越裳", 1, 0),
            _han_rec("paddleocr", "山川形勢之不同", 2, 1),
            _han_rec("paddleocr", "自古聖賢之道", 3, 2),
        ]
        s_lines = [
            _han_rec("clc_ocr", "古南交周號", 1, 0),
            _han_rec("clc_ocr", "越裳", 2, 1),
            _han_rec("clc_ocr", "山川形勢之不同", 3, 2),
            _han_rec("clc_ocr", "自古聖賢之道", 4, 3),
        ]
        groups = match_lines_dp(p_lines, s_lines)
        self.assertEqual([(g.match_type, g.primary_indices, g.secondary_indices) for g in groups], [
            ("1-n", (0,), (0, 1)),
            ("1-1", (1,), (2,)),
            ("1-1", (2,), (3,)),
        ])

        report = cross_check_records(p_lines, s_lines, variant="han", use_dp_line_match=True)
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(report["summary"]["agreed_unverified"], 3)

        # Cross-work isolation: different work_ids must NOT cross-match
        p_other = [_han_rec("paddleocr", "臣對", 1, 0, work_id="bai0023")]
        s_other = [_han_rec("clc_ocr", "臣對", 1, 0, work_id="bai0024")]
        iso_report = cross_check_records(p_other, s_other, variant="han", use_dp_line_match=True)
        self.assertEqual(iso_report["status"], "NEEDS_REVIEW")
        self.assertEqual(len(iso_report["items"]), 2)
        self.assertTrue(all(it["status"] == "MISSING_REGION" for it in iso_report["items"]))

    def test_structured_disagreement_taxonomy_and_priority(self):
        p = [_han_rec("paddleocr", "景興19年越常𠀖[MASK]", 1, 0, bbox=[[0, 0], [50, 0], [50, 200], [0, 200]], conf=0.45)]
        s = [_han_rec("clc_ocr", "景興18年越裳𠀗承", 2, 0, bbox=[[0, 0], [50, 0], [50, 200], [0, 200]], conf=None)]
        report = cross_check_records(p, s, variant="han", low_confidence_threshold=0.60)
        cats = {d["error_category"] for d in report["disagreements"]}
        self.assertIn("READING_ORDER_MISMATCH", cats)
        self.assertIn("LOW_CONFIDENCE", cats)
        self.assertIn("NUMBER_MISMATCH", cats)
        self.assertIn("CHARACTER_MISMATCH", cats)
        self.assertIn("RARE_CHARACTER_MISMATCH", cats)
        self.assertIn("UNREADABLE_CHARACTER", cats)


class TestCLCRetryCacheAndManualImport(unittest.TestCase):
    def test_clc_auth_401_retry_after_429_and_manual_txt_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            img = tmp_path / "p0049.png"
            img.write_bytes(b"pngdata")

            # HTTP 401 -> immediate failure without retries
            sess_401 = MagicMock()
            sess_401.headers = {}
            resp_401 = MagicMock(status_code=401, headers={})
            sess_401.post.return_value = resp_401
            adapter_401 = CLCOCRAdapter(
                max_retries=2, backoff_seconds=0.0, min_delay_seconds=0.0,
                session=sess_401, quota_log_path=tmp_path / "q.sqlite3",
            )
            recs_401 = adapter_401.recognize_image(img, source_id="s", work_id="w", corpus_id="CPO_09", member_id="TV02")
            self.assertEqual(recs_401[0].status, "FAILED")
            self.assertEqual(sess_401.post.call_count, 1)

            # HTTP 429 with Retry-After -> retries and succeeds
            sess_429 = MagicMock()
            sess_429.headers = {}
            resp_429 = MagicMock(status_code=429, headers={"Retry-After": "0"})
            resp_up = MagicMock(status_code=200, json=lambda: {"is_success": True, "code": "000000", "data": {"file_name": "f.png"}})
            resp_ok = MagicMock(status_code=200, json=lambda: {"is_success": True, "code": "000000", "data": {"result_ocr_text": ["古南交"]}})
            sess_429.post.side_effect = [resp_429, resp_up, resp_ok]
            adapter_ok = CLCOCRAdapter(
                max_retries=2, backoff_seconds=0.0, min_delay_seconds=0.0,
                session=sess_429, quota_log_path=tmp_path / "q2.sqlite3",
            )
            cache_path = tmp_path / "clc_cache.json"
            recs_ok = adapter_ok.recognize_image(
                img, source_id="s", work_id="w", corpus_id="CPO_09", member_id="TV02", cache_meta_path=cache_path
            )
            self.assertEqual(recs_ok[0].text, "古南交")
            self.assertTrue(cache_path.is_file())

            # Second call with unchanged image hits cache without hitting network
            sess_429.post.reset_mock()
            recs_hit = adapter_ok.recognize_image(
                img, source_id="s", work_id="w", corpus_id="CPO_09", member_id="TV02", cache_meta_path=cache_path
            )
            self.assertEqual(recs_hit[0].extra.get("cache_status"), "CACHE_HIT")
            self.assertEqual(sess_429.post.call_count, 0)

            # Manual plain TXT import requires explicit metadata
            txt_file = tmp_path / "clc_export.txt"
            txt_file.write_text("古南交\n越裳", encoding="utf-8")
            manual_recs = import_clc_ocr_text(
                txt_file, source_id="s", work_id="w", corpus_id="CPO_09", member_id="TV02", pdf_page=49
            )
            self.assertEqual([r.status for r in manual_recs], ["MANUAL_IMPORT", "MANUAL_IMPORT"])
            self.assertIsNone(manual_recs[0].confidence)


class TestSafeManualFixingMetricsAndCleaningCompatibility(unittest.TestCase):
    def test_safe_correction_guards_evaluation_and_stage03_compatibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create dummy source PNG so Paddle overlay & metadata hashes can verify cleanly
            from PIL import Image

            img_dir = root / "san_pham" / "TV04" / "CV06_CPO_11" / "01_nguon" / "han" / "CPO_11_TV04_bai0024_han_v01"
            img_dir.mkdir(parents=True, exist_ok=True)
            img_path = img_dir / "phan0001_pdfp0608.png"
            Image.new("RGB", (120, 120), color=(255, 255, 255)).save(img_path, format="PNG")
            img_sha = sha256(img_path)

            paddle = PaddleHanEngine()
            p_recs = paddle.parse_raw_prediction(
                {"rec_texts": ["臣對", "越常"], "rec_scores": [0.91, 0.82], "rec_polys": [[[0, 0], [40, 0], [40, 40], [0, 40]], [[0, 50], [40, 50], [40, 90], [0, 90]]]},
                source_id="phan0001_pdfp0608",
                work_id="CPO_11_TV04_bai0024_han_v01",
                corpus_id="CPO_11",
                member_id="TV04",
                variant="han",
                image_reference=str(img_path),
                input_sha256=img_sha,
                pdf_page=608,
                reading_order_mode="top_to_bottom",
            )
            s_recs = [
                _han_rec("clc_ocr", "臣對", 1, 0, work_id="CPO_11_TV04_bai0024_han_v01", source_id="phan0001_pdfp0608", input_sha256=img_sha),
                _han_rec("clc_ocr", "越裳", 2, 1, work_id="CPO_11_TV04_bai0024_han_v01", source_id="phan0001_pdfp0608", input_sha256=img_sha),
            ]
            dirs = stage_han_dirs(root / "han_stage")
            save_independent_engine_outputs(
                dirs["root"] / "paddle_ocr",
                engine_name="paddleocr",
                records=[r.to_dict() for r in p_recs],
                part_stem="phan0001_pdfp0608",
                image_path=img_path,
                render_overlay=True,
            )
            self.assertTrue((dirs["paddle_vis"] / "phan0001_pdfp0608_overlay.png").is_file())

            report = cross_check_records(p_recs, s_recs, variant="han", use_dp_line_match=True)
            bundle = export_cross_check_bundle(dirs["cross_check"], report)
            self.assertTrue(bundle["comparison_xlsx"].is_file())
            self.assertTrue(bundle["disagreements"].is_file())
            self.assertIn("[SUB:", render_ocr_diff_html(report))

            # Stale fingerprint / duplicate / raw overwrite / approved overwrite guards
            with self.assertRaises(ValueError):
                apply_manual_ocr_decisions(
                    report,
                    [{"item_id": "xc_0001", "decision": "KEEP_BOTH_AGREED", "base_fingerprint": "wrong_sha"}],
                )
            with self.assertRaises(PermissionError):
                apply_manual_ocr_decisions(
                    report,
                    [{"item_id": "xc_0001", "decision": "KEEP_BOTH_AGREED"}],
                    corrected_text_path=dirs["root"] / "paddle_ocr" / "text" / "phan0001_pdfp0608.txt",
                    raw_protected_roots=[dirs["root"] / "paddle_ocr", dirs["root"] / "clc_ocr"],
                )

            reviewed_json = dirs["manual_review"] / "reviewed.json"
            manual_res = apply_manual_ocr_decisions(
                report,
                [
                    {"item_id": "xc_0001", "decision": "KEEP_BOTH_AGREED", "base_fingerprint": img_sha},
                    {"item_id": "xc_0002", "decision": "ACCEPT_SECONDARY", "base_fingerprint": img_sha, "note": "confirmed"},
                ],
                corrected_text_path=dirs["corrected_parts"] / "phan0001_pdfp0608.txt",
                correction_log_path=dirs["manual_review"] / "correction_log.jsonl",
                reviewed_json_path=reviewed_json,
                reviewer="TV04",
            )
            self.assertTrue(manual_res["approved"])
            self.assertEqual(manual_res["transcription_text"], "臣對\n越裳")

            # Attempt to overwrite approved transcription must fail
            with self.assertRaises(FileExistsError):
                apply_manual_ocr_decisions(
                    report,
                    [{"item_id": "xc_0001", "decision": "ACCEPT_PRIMARY"}],
                    reviewed_json_path=reviewed_json,
                )

            # Evaluation metrics against explicit gold
            ev = compute_han_ocr_evaluation(report, manual_res, gold_references=["臣對", "越裳"])
            self.assertEqual(ev["cer"]["status"], "COMPUTED_AGAINST_GOLD")
            self.assertEqual(ev["cer"]["corrected"]["micro_cer"], 0.0)
            self.assertEqual(len(experiment_matrix_template()), 6)

            # Text Cleaning compatibility projection: Stage 03 reads ONLY reviewed output via read_sources & build_records
            clean_proj = root / "cleaning_input"
            export_cleaning_compatible_han_transcription(
                clean_proj,
                corpus_id="CPO_11",
                work_stem="CPO_11_TV04_bai0024_han_v01",
                part_transcriptions=[
                    {
                        "image_name": "phan0001_pdfp0608.png",
                        "text": manual_res["transcription_text"],
                        "source_sha256": img_sha,
                    }
                ],
                approved=True,
            )
            # Copy source PNG under expected BookFolder/01_nguon/han/<work_stem>/ for attach_review_pages check
            proj_img = clean_proj / "ThiDinh" / "01_nguon" / "han" / "CPO_11_TV04_bai0024_han_v01" / "phan0001_pdfp0608.png"
            proj_img.parent.mkdir(parents=True, exist_ok=True)
            proj_img.write_bytes(img_path.read_bytes())

            sources = read_sources(clean_proj, selected_codes={"CPO_11"}, selected_kinds={"han"}, member_number=4, input_granularity="parts")
            attach_review_pages(sources, clean_proj)
            records = build_records(sources, set())
            self.assertEqual([r["clean"] for r in records], ["臣對", "越裳"])
            self.assertEqual(records[0]["pdf_page"], 608)


if __name__ == "__main__":
    unittest.main()
