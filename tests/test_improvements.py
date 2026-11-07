"""Các thao tác sửa/hoàn tác, nhớ phiên làm việc và kiểm tra nguồn có bộ nhớ đệm."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import tkinter as tk
import unittest

from cat_bac_su import BOOK as BAC_SU
from cat_hich_tuong_si import BOOK
from cong_cu import history
from cong_cu.models import Box
from cong_cu.region_actions import region_id
from cong_cu.storage import read_json, sha256, write_json
from cong_cu.ui import CropWindow
from cong_cu.workspace import Workspace


class ImprovementTests(unittest.TestCase):
    def setUp(self):
        if not BOOK.sources[0].path.is_file():
            self.skipTest("Thiếu PDF Hịch tướng sĩ tại máy; xem DATA_SETUP.md.")
        scratch = Path(__file__).resolve().parents[1] / ".test-tmp"
        scratch.mkdir(exist_ok=True)
        self.temp = TemporaryDirectory(dir=scratch)
        self.output = Path(self.temp.name)
        self.w = Workspace(BOOK, self.output)
        self.w.prepare()
        self.source_hash = sha256(BOOK.sources[0].path)

    def tearDown(self):
        self.assertEqual(sha256(BOOK.sources[0].path), self.source_hash)
        self.temp.cleanup()

    def save(self, page=4, text=False):
        return self.w.save_pdf_region("chung", page, Box(.11, .27, .9, .5),
            "hich_tuong_si", "dich_nghia", dpi=72, extract_text=text)

    def test_replace_changes_page_and_undo_restores_original_png_and_provenance(self):
        old = self.save()
        png = self.w.root / old["work_outputs"][0]
        digest = sha256(png)
        changed = self.w.regions.replace_pdf(region_id(old), 5, Box(.2, .3, .8, .6))
        self.assertEqual(region_id(changed), region_id(old))
        self.assertEqual(changed["sequence"], old["sequence"])
        self.assertEqual(changed["page"], 5)
        self.assertFalse(png.exists())
        replacement_png = self.w.root / changed["work_outputs"][0]
        self.assertTrue(replacement_png.exists())
        self.assertTrue(self.w.check()["ok"])
        self.w.undo_last()
        self.assertEqual(sha256(png), digest)
        self.assertFalse(replacement_png.exists())
        self.assertEqual(self.w.regions.find(region_id(old))["page"], 4)
        self.assertTrue(self.w.check()["ok"])

    def test_remove_middle_text_part_rebuilds_order_and_undo_restores_all(self):
        first = self.save(4, True); middle = self.save(5, True); last = self.save(6, True)
        merged = self.w.root / next(p for p in last["work_outputs"] if p.endswith(".txt"))
        digest = sha256(merged)
        texts = [(self.w.root / r["text_file"]).read_text(encoding="utf-8") for r in (first, middle, last)]
        self.w.regions.remove(region_id(middle))
        self.assertEqual(merged.read_text(encoding="utf-8"), texts[0]+"\n"+texts[2])
        self.assertEqual([r["sequence"] for r in self.w.regions.list()], [1, 3])
        self.assertTrue(self.w.check()["ok"])
        self.w.undo_last()
        self.assertEqual(sha256(merged), digest)
        self.assertEqual([r["sequence"] for r in self.w.regions.list()], [1, 2, 3])

    def test_replace_txt_unicode_and_undo(self):
        source = self.output / "nguon.txt"
        raw = "Hán 𠀀\nDịch nghĩa Việt\nDịch thơ\n"
        source.write_text(raw, encoding="utf-8")
        record = self.w.save_text_region(source, "hich_tuong_si", "dich_am", char_start=0, char_end=5)
        path = self.w.root / record["work_outputs"][0]
        original = path.read_text(encoding="utf-8")
        self.w.regions.replace_text(region_id(record), raw.index("Dịch"), len(raw))
        self.assertEqual(path.read_text(encoding="utf-8"), raw[raw.index("Dịch"):])
        self.w.undo_last()
        self.assertEqual(path.read_text(encoding="utf-8"), original)
        self.assertEqual(source.read_text(encoding="utf-8"), raw)

    def test_legacy_region_without_id_can_be_edited_and_restored(self):
        record = self.save()
        legacy = self.w.manifest()
        legacy.pop("history_tip")
        legacy["records"][0].pop("id")
        write_json(self.w.manifest_path, legacy)
        self.w.regions.replace_pdf(record["fingerprint"], 5, Box(.2, .3, .8, .6))
        self.w.undo_last()
        self.assertEqual(self.w.manifest(), legacy)
        self.assertTrue(self.w.check()["ok"])

    def test_undo_and_edit_preserve_externally_modified_png(self):
        record = self.save()
        path = self.w.root / record["work_outputs"][0]
        path.write_bytes(b"USER_EDIT")
        with self.assertRaises(FileExistsError):
            self.w.undo_last()
        with self.assertRaises(FileExistsError):
            self.w.regions.remove(region_id(record))
        self.assertEqual(path.read_bytes(), b"USER_EDIT")

    def test_progress_is_manual_and_invalidated_by_new_region(self):
        self.save()
        self.w.regions.mark_reviewed("hich_tuong_si", "dich_nghia", 1)
        self.assertEqual(self.w.summary("hich_tuong_si")["dich_nghia"]["status"], "complete")
        self.save(5)
        self.assertEqual(self.w.summary("hich_tuong_si")["dich_nghia"]["status"], "draft")
        self.w.undo_last()
        self.assertEqual(self.w.summary("hich_tuong_si")["dich_nghia"]["status"], "complete")

    def test_unchanged_sources_are_not_rehashed_per_save_but_changed_backup_is_checked(self):
        with patch("cong_cu.storage.sha256", wraps=sha256) as storage_hash, patch("cong_cu.workspace.sha256", wraps=sha256) as workspace_hash:
            self.save(); self.save(5)
            calls = storage_hash.call_args_list + workspace_hash.call_args_list
            self.assertFalse([call for call in calls if Path(call.args[0]).suffix == ".pdf"])
            source = read_json(self.w.sources_path, {})["chung"]
            (self.w.root / source["backup"]).touch()
            self.save(6)
            calls = storage_hash.call_args_list + workspace_hash.call_args_list
            self.assertTrue([call for call in calls if Path(call.args[0]).suffix == ".pdf"])

    def test_failed_file_update_rolls_back_and_pending_write_recovers_on_reopen(self):
        record = self.save()
        original = self.w.manifest()
        real_apply = history._apply
        def fail_after_write(root, folder, meta, side):
            real_apply(root, folder, meta, side)
            if side == "after":
                raise OSError("Simulated interruption")
        with patch("cong_cu.history._apply", side_effect=fail_after_write):
            with self.assertRaises(OSError):
                self.w.regions.replace_pdf(region_id(record), 5, Box(.2, .3, .8, .6))
        self.assertEqual(self.w.manifest(), original)
        self.assertTrue(self.w.check()["ok"])
        self.w.regions.replace_pdf(region_id(record), 5, Box(.2, .3, .8, .6))
        token = self.w.manifest()["history_tip"]
        folder = self.w.manage / "lich_su" / token
        meta = history._read_meta(folder); meta["status"] = "pending"; history._write_meta(folder, meta)
        write_json(history.pending_path(self.w.root), {"id": token})
        reopened = Workspace(BOOK, self.output); reopened.prepare()
        self.assertEqual(reopened.manifest(), original)
        self.assertTrue(reopened.check()["ok"])

    def test_gui_defaults_follow_source_and_session_resumes(self):
        if not all(source.path.is_file() for source in BAC_SU.sources):
            self.skipTest("Thiếu PDF Bắc sứ tại máy; xem DATA_SETUP.md.")
        w = Workspace(BAC_SU, self.output)
        root = tk.Tk(); root.withdraw()
        with patch("tkinter.messagebox.showerror", side_effect=AssertionError):
            try:
                app = CropWindow(root, w)
                self.assertEqual(app.source_key.get(), "viet")
                self.assertEqual(app.kind(), "dich_nghia")
                app.source_key.set("han"); app.change_source()
                self.assertEqual(app.kind(), "han")
                app.page.set(55); app.load_page(); app.work.set("doan0002")
                app.version.set(2); app.preview_dpi.set(75); app.persist_state()
            finally:
                root.destroy()
        root = tk.Tk(); root.withdraw()
        try:
            app = CropWindow(root, Workspace(BAC_SU, self.output))
            self.assertEqual((app.source_key.get(), app.page.get(), app.work.get(), app.version.get(), app.preview_dpi.get()),
                             ("han", 55, "doan0002", 2, 75))
        finally:
            root.destroy()

    def test_gui_saved_boxes_overlap_warning_and_edit_save(self):
        record = self.save()
        root = tk.Tk(); root.withdraw()
        with patch("tkinter.messagebox.showerror", side_effect=AssertionError):
            try:
                app = CropWindow(root, self.w)
                app.kind_label.set("Dịch nghĩa"); app.context_changed()
                self.assertTrue(app.canvas.find_withtag("saved"))
                self.assertEqual(len(app.panel.tree.get_children()), 1)
                app.selection = Box(.111, .27, .901, .5)
                with patch("tkinter.messagebox.askyesno", return_value=False) as warning:
                    app.save_region()
                    warning.assert_called_once()
                self.assertEqual(len(self.w.regions.list()), 1)
                app.edit_region(record)
                app.selection = Box(.2, .3, .8, .6)
                app.save_region()
                self.assertIsNone(app.editing_id)
                self.assertEqual(self.w.regions.find(region_id(record))["box"], [.2, .3, .8, .6])
                app.undo_last()
                self.assertEqual(self.w.regions.find(region_id(record))["box"], record["box"])
            finally:
                root.destroy()


if __name__ == "__main__":
    unittest.main()
