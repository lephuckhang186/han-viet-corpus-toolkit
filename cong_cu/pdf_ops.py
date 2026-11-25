"""Backward-compatible shim for hanviet.source_preparation.pdf_ops."""
from hanviet.source_preparation.pdf_ops import crop_png, extract_text, info, render_page

__all__ = ["crop_png", "extract_text", "info", "render_page"]
