"""Protected alignment backends, DP/validation helpers, stage runners, and LLM verification."""

from .runner import VERSIONS, alignment_audit_dir, clean_book_root, clean_sources_by_work, load_work, run_alignment
from .validation.validators import (
    indices,
    lab_text,
    make_rows,
    phonetic_links,
    public_units,
    unmatched_ids,
    validate_links,
    verify_identity,
)

__all__ = [
    "VERSIONS",
    "alignment_audit_dir",
    "clean_book_root",
    "clean_sources_by_work",
    "indices",
    "lab_text",
    "load_work",
    "make_rows",
    "phonetic_links",
    "public_units",
    "run_alignment",
    "unmatched_ids",
    "validate_links",
    "verify_identity",
]
