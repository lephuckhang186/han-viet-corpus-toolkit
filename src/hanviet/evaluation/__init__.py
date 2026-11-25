"""Stage evaluation metrics and research evidence reporters (strict separation of disagreement vs human-confirmed truth)."""

from .metrics import (
    compute_alignment_eval,
    compute_cer_wer,
    summarize_alignment_review,
    summarize_cleaning_stage,
    summarize_ocr_cross_check,
)

__all__ = [
    "compute_alignment_eval",
    "compute_cer_wer",
    "summarize_alignment_review",
    "summarize_cleaning_stage",
    "summarize_ocr_cross_check",
]
