"""Dual-OCR cross-check alignment and disagreement detection."""

from .aligner import (
    CrossCheckItem,
    bbox_iou,
    compare_han_texts,
    compare_viet_texts,
    cross_check_records,
    levenshtein_align,
)

__all__ = [
    "CrossCheckItem",
    "bbox_iou",
    "compare_han_texts",
    "compare_viet_texts",
    "cross_check_records",
    "levenshtein_align",
]
