"""Manual OCR fixing, decision validation, HTML diff preview, and correction logging."""

from .reviewer import (
    OCR_DECISIONS,
    apply_manual_ocr_decisions,
    build_ocr_review_table,
    export_ocr_review_csv,
    render_ocr_diff_html,
)

__all__ = [
    "OCR_DECISIONS",
    "apply_manual_ocr_decisions",
    "build_ocr_review_table",
    "export_ocr_review_csv",
    "render_ocr_diff_html",
]
