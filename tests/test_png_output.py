"""Kiểm tra hợp đồng đầu ra: PNG/TXT, chỉ giữ PDF nguyên bản trong ban_goc."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import tkinter as tk
import unittest

from cat_hich_tuong_si import BOOK
from cong_cu.models import Box
from cong_cu.storage import sha256
from cong_cu.ui import CropWindow
from cong_cu.workspace import Workspace


class PngOutputTests(unittest.TestCase):
    def setUp(self):
        if not BOOK.sources[0].path.is_file():
            self.skipTest("Thiếu PDF Hịch tướng sĩ tại máy; xem DATA_SETUP.md.")
        scratch = Path(__file__).resolve().parents[1] / ".test-tmp"
        scratch.mkdir(exist_ok=True)
        self.temp = TemporaryDirectory(dir=scratch)
        self.workspace = Workspace(BOOK, Path(self.temp.name))
        self.before = sha256(BOOK.sources[0].path)

    def tearDown(self):
        self.assertEqual(sha256(BOOK.sources[0].path), self.before)
        self.temp.cleanup()

    def assert_no_generated_pdf(self):
        pdfs = list(self.workspace.root.rglob("*.pdf"))
        self.assertEqual(len(pdfs), 1)  # Bản sao PDF nguồn vẫn còn.
        self.assertTrue(all("ban_goc" in path.parts for path in pdfs))
        manifest = self.workspace.manifest()
        self.assertFalse(any(path.endswith(".pdf") for path in manifest["artifacts"]))
        self.assertTrue(self.workspace.check()["ok"])

    def test_two_crops_same_work_save_png_only_and_retry_does_not_duplicate(self):
        arguments = dict(source_key="chung", box=Box(.11, .27, .9, .5),
                         work="hich_tuong_si", kind="dich_nghia", dpi=72)
        first = self.workspace.save_pdf_region(page=4, **arguments)
        second = self.workspace.save_pdf_region(page=5, **arguments)
        self.assertEqual([first["sequence"], second["sequence"]], [1, 2])
        for result in (first, second):
            self.assertEqual(len(result["work_outputs"]), 1)
            self.assertTrue(result["work_outputs"][0].endswith(".png"))
            self.assertTrue((self.workspace.root / result["work_outputs"][0]).is_file())
        retry = self.workspace.save_pdf_region(page=5, **arguments)
        self.assertTrue(retry["skipped"])
        self.assertEqual(retry["work_outputs"], second["work_outputs"])
        self.assertEqual(len(self.workspace.manifest()["records"]), 2)
        self.assert_no_generated_pdf()

    def test_optional_text_is_merged_and_external_edits_are_preserved(self):
        arguments = dict(source_key="chung", box=Box(.11, .27, .9, .5),
                         work="hich_tuong_si", kind="dich_nghia", dpi=72, extract_text=True)
        self.workspace.save_pdf_region(page=4, **arguments)
        result = self.workspace.save_pdf_region(page=5, **arguments)
        self.assertEqual({Path(p).suffix for p in result["work_outputs"]}, {".png", ".txt"})
        records = self.workspace.manifest()["records"]
        pieces = [(self.workspace.root / r["text_file"]).read_text(encoding="utf-8") for r in records]
        merged = self.workspace.root / next(p for p in result["work_outputs"] if p.endswith(".txt"))
        self.assertEqual(merged.read_text(encoding="utf-8"), "\n".join(pieces))
        self.assertIn("Ta thường nghe", pieces[0])
        self.assert_no_generated_pdf()
        merged.write_text("Ghi chú người dùng, giữ nguyên.", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.workspace.save_pdf_region(page=6, **arguments)
        self.assertEqual(merged.read_text(encoding="utf-8"), "Ghi chú người dùng, giữ nguyên.")

    def test_gui_save_exports_png(self):
        self.workspace.prepare()
        root = tk.Tk(); root.withdraw()
        try:
            window = CropWindow(root, self.workspace)
            root.update_idletasks()
            window.start_drag(SimpleNamespace(x=100, y=100))
            window.drag(SimpleNamespace(x=200, y=200))
            window.end_drag(SimpleNamespace(x=200, y=200))
            window.save_region()
            result = self.workspace.manifest()["records"][0]
            self.assertEqual(len(result["work_outputs"]), 1)
            self.assertTrue(result["work_outputs"][0].endswith(".png"))
            self.assert_no_generated_pdf()
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
