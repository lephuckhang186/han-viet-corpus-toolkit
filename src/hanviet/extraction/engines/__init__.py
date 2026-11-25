"""OCR engine adapters (lazy initialization; zero download or API call at import time)."""

from .clc_han import CLC_OCR_BASE_URL, CLCOCRAdapter, import_clc_ocr_json
from .paddle_han import PaddleHanEngine
from .tesseract_viet import TesseractVietEngine
from .vietocr_viet import VietOCREngine

__all__ = [
    "CLC_OCR_BASE_URL",
    "CLCOCRAdapter",
    "PaddleHanEngine",
    "TesseractVietEngine",
    "VietOCREngine",
    "import_clc_ocr_json",
]
