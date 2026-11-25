"""Golden regression tests for Protected Logic (Source Prep, Cleaning, Segmentation, Alignment).

Verifies that before and after refactoring, with identical inputs and configuration,
all protected algorithms produce byte-for-byte / exact equal outputs to the baseline fixtures.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "tests" / "fixtures" / "baseline"


class TestProtectedAlignmentAndSegmentationRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads((FIXTURES / "alignment_baseline.json").read_text(encoding="utf-8"))
        from cong_cu import alignment_backends, dong_hang
        cls.dong_hang = dong_hang
        cls.backends = alignment_backends

    def test_segmentation_matches_baseline(self):
        inp = self.baseline["inputs"]
        exp = self.baseline["segmentation"]
        self.assertEqual(
            self.dong_hang.segment(inp["han_sample"], "han", "CPO_11/bai0024/TV04", "prose", titles=1),
            exp["han_prose"],
        )
        self.assertEqual(
            self.dong_hang.segment(inp["han_sample"], "han", "CPO_12/bai0314/TV04", "poetry", titles=0),
            exp["han_poetry"],
        )
        self.assertEqual(
            self.dong_hang.segment(inp["han_sample"], "han", "CPO_09/TV04/muc1", "prose", keep_lines=True),
            exp["han_keep_lines"],
        )
        self.assertEqual(
            self.dong_hang.segment(inp["am_sample"], "am", "CPO_11/bai0024/TV04", "prose", titles=1),
            exp["am_prose"],
        )
        self.assertEqual(
            self.dong_hang.segment(inp["nghia_sample"], "nghia", "CPO_11/bai0024/TV04", "prose"),
            exp["nghia_prose"],
        )
        self.assertEqual(
            self.dong_hang.segment(inp["tho_sample"], "tho", "CPO_12/bai0314/TV04", "poetry"),
            exp["tho_poetry"],
        )

    def test_phonetic_dp_and_lab_text_match_baseline(self):
        seg = self.baseline["segmentation"]
        self.assertEqual(
            self.dong_hang.phonetic_links(seg["han_prose"], seg["am_prose"]),
            self.baseline["dp_phonetic_links"],
        )
        self.assertEqual(
            self.dong_hang.lab_text("臣對[MASK]！《詩》曰：「關關」。", "han"),
            self.baseline["lab_text"]["han"],
        )
        self.assertEqual(
            self.dong_hang.lab_text("Thần đối [MASK]! «Thi» viết: «Quan quan».", "am"),
            self.baseline["lab_text"]["am"],
        )

    def test_clc_request_and_make_rows_match_baseline(self):
        seg = self.baseline["segmentation"]
        req = self.backends.clc_request(
            self.dong_hang.public_units(seg["han_prose"]),
            self.dong_hang.public_units(seg["nghia_prose"]),
        )
        self.assertEqual(req, self.baseline["clc_request"])

        sample_links = {
            "am": self.baseline["dp_phonetic_links"],
            "nghia": [{"han_ids": [seg["han_prose"][1]["id"]], "nghia_ids": [seg["nghia_prose"][1]["id"]]}],
            "tho": [{"han_ids": [seg["han_prose"][-1]["id"]], "tho_ids": [seg["tho_poetry"][0]["id"], seg["tho_poetry"][1]["id"]]}],
        }
        sample_units = {
            "han": seg["han_prose"],
            "am": seg["am_prose"],
            "nghia": seg["nghia_prose"],
            "tho": seg["tho_poetry"],
        }
        self.assertEqual(self.dong_hang.make_rows(sample_units, sample_links), self.baseline["make_rows"])
        self.assertEqual(self.dong_hang.unmatched_ids(sample_units, sample_links), self.baseline["unmatched_ids"])

    def test_export_reviewed_4col_structure(self):
        seg = self.baseline["segmentation"]
        units = {"han": seg["han_prose"][:1], "am": seg["am_prose"][:1], "nghia": [], "tho": []}
        links = {
            "am": [{"han_ids": [units["han"][0]["id"]], "am_ids": [units["am"][0]["id"]]}],
            "nghia": [],
            "tho": [],
        }
        review = {"work": "CPO_11/bai0024/TV04", "fingerprint": "fp", "approved": True, "links": links, "skipped": {}}
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "04_dong_hang"
            rows, files = self.dong_hang.export_reviewed(out_dir, "CPO_11_bai0024", "CPO_11/bai0024/TV04", units, review, [])
            self.assertEqual(len(rows), 1)
            self.assertEqual(len(rows[0]["cells"]), 4)
            self.assertTrue((out_dir / "CPO_11_bai0024_parallel.tsv").is_file())
            self.assertTrue((out_dir / "CPO_11_bai0024_parallel.xlsx").is_file())
            self.assertTrue((out_dir / "notes.xlsx").is_file())


class TestProtectedSourcePrepRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads((FIXTURES / "source_prep_baseline.json").read_text(encoding="utf-8"))
        from cong_cu import models, workspace
        cls.models = models
        cls.workspace_cls = workspace.Workspace

    def test_source_prep_matches_baseline(self):
        self.assertEqual(self.models.Box(0.1, 0.2, 0.8, 0.9).as_list(), self.baseline["box_valid"])
        with self.assertRaises(ValueError):
            self.models.Box(0.8, 0.2, 0.5, 0.9)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src_txt = tmp_path / "sample.txt"
            src_txt.write_text("Dong 1\nDong 2\nDong 3\n", encoding="utf-8")
            book = self.models.Book(
                code="CPO_12",
                title="Test Book",
                sources=(self.models.Source("chung", src_txt, ((187, 366),)),),
                first_work="bai0131",
                work_range=(131, 207),
                note="test",
            )
            ws = self.workspace_cls(book, output_root=tmp_path / "out")
            ws.prepare()
            rec1 = ws.save_text_region(src_txt, "bai0131", "dich_nghia", 1, line_start=1, line_end=2, note="p1")
            self.assertEqual(len(rec1["fingerprint"]), 64)
            self.assertEqual((ws.root / rec1["text_file"]).read_text(encoding="utf-8"), self.baseline["rec1_text_file_content"])
            self.assertEqual(ws.summary("bai0131", 1), self.baseline["summary_draft"])
            ws.regions.mark_reviewed("bai0131", "dich_nghia", 1, True)
            self.assertEqual(ws.summary("bai0131", 1), self.baseline["summary_complete"])
            fp = ws.region_fingerprint({
                "work": "bai0131", "kind": "han", "version": 1, "source_key": "chung",
                "source_path": "a", "page": 187, "box": [0.1, 0.1, 0.9, 0.9], "mode": "pdf_image", "dpi": 300,
            })
            self.assertEqual(fp, self.baseline["sample_region_fingerprint"])


class TestProtectedCleaningRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads((FIXTURES / "cleaning_baseline.json").read_text(encoding="utf-8"))
        SRC = ROOT / "src"
        if str(SRC) not in sys.path:
            sys.path.insert(0, str(SRC))
        from hanviet.cleaning import han_cleaner, pipeline, viet_cleaner
        cls.han_cleaner = han_cleaner
        cls.viet_cleaner = viet_cleaner
        cls.pipeline = pipeline

    def test_clean_han_and_viet_match_baseline(self):
        cases = self.baseline["cases"]
        for item in cases["han"]:
            self.assertEqual(list(self.han_cleaner.clean_han(item["input"])), item["output"])
        for item in cases["viet_am"]:
            self.assertEqual(
                list(self.viet_cleaner.clean_viet(item["input"], "dich_am", native_pdf=False)),
                item["output"],
            )
        for item in cases["viet_nghia_native"]:
            self.assertEqual(
                list(self.viet_cleaner.clean_viet(item["input"], "dich_nghia", native_pdf=True)),
                item["output"],
            )
        for item in cases["suffix_digit_suggestions"]:
            self.assertEqual(self.viet_cleaner.suffix_digit_suggestion(item["input"]), item["output"])

    def test_build_apply_assemble_match_baseline(self):
        sample_sources = [
            {
                "code": "CPO_11",
                "kind": "han",
                "work": "CPO_11_TV04_bai0024_han_v01",
                "stage": "02_ocr_tho",
                "relative_path": "ThiDinh/02_ocr_tho/han/CPO_11_TV04_bai0024_han_v01/phan0001_pdfp0608.txt",
                "text": "  臣對（） \n第一名\f詩曰：關關\n123",
                "source_sha256": "abc123",
            },
            {
                "code": "CPO_09",
                "kind": "dich_nghia",
                "work": "CPO_09_TV04_quyen01_dich_nghia_v01",
                "stage": "01_nguon",
                "relative_path": "BacSu/01_nguon/viet/dich_nghia/CPO_09_TV04_quyen01_dich_nghia_v01.txt",
                "text": "Dịch nghĩa:\nNgƣời thƣợng tƣớng [53b]\fCâu hai.",
                "source_sha256": "def456",
            },
        ]
        records = self.pipeline.build_records(sample_sources, {"thần", "đối", "người"})
        self.assertEqual(records, self.baseline["records"])
        decisions = {
            records[0]["row_id"]: {"action": "keep", "replacement": "", "note": "ok"},
            records[2]["row_id"]: {"action": "join_next", "replacement": "", "note": "joined"},
            records[3]["row_id"]: {"action": "replace", "replacement": "123.", "note": "punct"},
        }
        rows_out, audit_out = self.pipeline.apply_decisions(records, decisions)
        self.assertEqual(rows_out, self.baseline["applied_rows"])
        self.assertEqual(audit_out, self.baseline["audit_log"])
        assembled = {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in self.pipeline.assemble_works(rows_out).items()}
        self.assertEqual(assembled, self.baseline["assembled_works"])

    def test_review_csv_22_columns_and_allowed_actions(self):
        import csv

        expected_columns = [
            "row_id",
            "relative_path",
            "source_sha256",
            "code",
            "kind",
            "work",
            "page",
            "line",
            "raw",
            "clean",
            "pdf_page",
            "source_image",
            "polygon",
            "automatic_rules",
            "reasons",
            "suggested",
            "context_before",
            "context_after",
            "oov_tokens",
            "action",
            "replacement",
            "note",
        ]
        sample_sources = [
            {
                "code": "CPO_11",
                "kind": "han",
                "work": "CPO_11_TV04_bai0024_han_v01",
                "stage": "02_ocr_tho",
                "relative_path": "ThiDinh/02_ocr_tho/han/CPO_11_TV04_bai0024_han_v01/phan0001_pdfp0608.txt",
                "text": "  臣對（） \n第一名",
                "source_sha256": "abc123",
            }
        ]
        records = self.pipeline.build_records(sample_sources, {"thần", "đối"})
        review_rows = [
            dict(row, polygon=json.dumps(row["polygon"]) if row["polygon"] else "", action="", replacement="", note="")
            for row in records
        ]
        self.assertEqual(list(review_rows[0].keys()), expected_columns)
        self.assertEqual(len(expected_columns), 22)

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "duyet_lam_sach.csv"
            csv_path.write_bytes(self.pipeline.csv_bytes(review_rows, expected_columns))
            loaded_rows = self.pipeline.review_csv_rows(csv_path, records)
            self.assertEqual(len(loaded_rows), len(records))
            self.assertEqual(list(loaded_rows[0].keys()), expected_columns)

            for action in ("", "keep", "replace", "delete", "join_next"):
                rows_copy = [dict(row) for row in loaded_rows]
                rows_copy[0]["action"] = action
                rows_copy[0]["replacement"] = "臣對" if action == "replace" else ""
                csv_path.write_bytes(self.pipeline.csv_bytes(rows_copy, expected_columns))
                decisions = self.pipeline.read_decisions(csv_path, records)
                self.assertEqual(decisions[records[0]["row_id"]]["action"], action)

            bad_rows = [dict(row) for row in loaded_rows]
            bad_rows[0]["action"] = "modify"
            csv_path.write_bytes(self.pipeline.csv_bytes(bad_rows, expected_columns))
            with self.assertRaises(ValueError):
                self.pipeline.read_decisions(csv_path, records)

            multiline_rows = [dict(row) for row in loaded_rows]
            multiline_rows[0]["action"] = "replace"
            multiline_rows[0]["replacement"] = "dong 1\ndong 2"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=expected_columns)
                writer.writeheader()
                writer.writerows(multiline_rows)
            with self.assertRaises(ValueError):
                self.pipeline.read_decisions(csv_path, records)


if __name__ == "__main__":
    unittest.main()
