"""Backward-compatible shim for alignment, segmentation, and exporter modules."""
from hanviet.alignment.backends import CLCTextMismatch, align_clc, clc_request, run_lab
from hanviet.alignment.runner import (
    VERSIONS,
    alignment_audit_dir,
    clean_book_root,
    clean_sources_by_work,
    load_work,
    run_alignment,
)
from hanviet.alignment.validation.validators import (
    indices,
    lab_text,
    make_rows,
    phonetic_links,
    public_units,
    unmatched_ids,
    validate_links,
    verify_identity,
)
from hanviet.common.io import json_bytes, read_json
from hanviet.exporters.tabular import HEADERS, export_reviewed, write_protected, xlsx_bytes
from hanviet.segmentation.segmenter import clean_spacing, content_line_spans, segment, split_prose

__all__ = [
    "CLCTextMismatch",
    "HEADERS",
    "VERSIONS",
    "align_clc",
    "alignment_audit_dir",
    "clean_book_root",
    "clean_sources_by_work",
    "clean_spacing",
    "clc_request",
    "content_line_spans",
    "export_reviewed",
    "indices",
    "json_bytes",
    "lab_text",
    "load_work",
    "make_rows",
    "phonetic_links",
    "public_units",
    "read_json",
    "run_alignment",
    "run_lab",
    "segment",
    "split_prose",
    "unmatched_ids",
    "validate_links",
    "verify_identity",
    "write_protected",
    "xlsx_bytes",
]
