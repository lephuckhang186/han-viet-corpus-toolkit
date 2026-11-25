"""Cross-platform portability, path handling, CPU fallback, and dependency check tests."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tests  # noqa: F401
from hanviet.common.config import check_dependencies, check_tesseract
from hanviet.common.paths import detect_runtime, resolve_device, resolve_paths, resolve_project_root


class TestPortability(unittest.TestCase):
    def test_user_and_env_and_vietnamese_space_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "thư mục có dấu cách" / "Dự Án Hán Việt"
            base.mkdir(parents=True)
            (base / "ten_file.py").write_text("MA_DE_TAI = 'CV06'\n", encoding="utf-8")

            # Explicit user path
            self.assertEqual(resolve_project_root(user_root=base), base.resolve())

            # Env var override
            with patch.dict(os.environ, {"HANVIET_PROJECT_ROOT": str(base)}):
                self.assertEqual(resolve_project_root(), base.resolve())

            paths = resolve_paths(user_root=base, data_root="Dữ liệu/Ngữ liệu UTF8", output_root="Sản phẩm xuất")
            self.assertEqual(paths.data_root, (base / "Dữ liệu/Ngữ liệu UTF8").resolve())
            self.assertEqual(paths.output_root, (base / "Sản phẩm xuất").resolve())

    def test_runtime_detection_and_cpu_fallback(self):
        with patch.dict(os.environ, {"HANVIET_ENV": "local", "HANVIET_DEVICE": "cpu"}):
            self.assertEqual(detect_runtime(), "local")
            self.assertEqual(resolve_device(), "cpu")
        with patch.dict(os.environ, {"HANVIET_DEVICE": "auto"}):
            dev = resolve_device("auto")
            self.assertIn(dev, {"cpu", "gpu:0"})

    def test_missing_tesseract_and_dependency_checks(self):
        with patch("hanviet.common.config.shutil.which", return_value=None):
            with patch.dict(os.environ, {"TESSERACT_CMD": ""}):
                tess = check_tesseract()
                self.assertFalse(tess["ok"])
                self.assertIn("Tesseract binary not found", tess["message"])
                dep = check_dependencies("ocr_viet", require_tesseract=True)
                self.assertFalse(dep["ok"])

        base_check = check_dependencies("base")
        self.assertTrue(base_check["ok"], base_check)


if __name__ == "__main__":
    unittest.main()
