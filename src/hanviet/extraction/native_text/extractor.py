"""Native text extraction for digital PDF Text and existing UTF-8 TXT (no OCR or API calls)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from hanviet.common.io import bytes_hash, sha256, write_json, write_protected
from hanviet.source_preparation import pdf_ops
from hanviet.source_preparation.models import Box


def copy_native_txt(
    source_path: Path,
    destination_path: Path,
    *,
    index_json_path: Path | None = None,
) -> dict[str, Any]:
    """Preserve raw UTF-8 bytes and U+000C page boundaries from digital TXT sources without OCR."""
    src = Path(source_path)
    dst = Path(destination_path)
    raw = src.read_bytes()
    digest = bytes_hash(raw)
    text = raw.decode("utf-8-sig")
    pages = text.split("\f")
    write_protected({dst: raw})
    report = {
        "mode": "native_text",
        "source": str(src),
        "destination": str(dst),
        "sha256": digest,
        "page_count": len(pages),
        "ocr_called": False,
        "ready_for_user_inspection": True,
    }
    if index_json_path is not None:
        write_json(index_json_path, report)
    return report


def extract_pdf_text_region(
    pdf_path: Path,
    page_number: int,
    box: Box,
) -> dict[str, Any]:
    """Extract PDF text layer directly via pypdfium2 without running OCR."""
    text = pdf_ops.extract_text(Path(pdf_path), page_number, box)
    return {
        "mode": "pdf_text",
        "pdf_page": page_number,
        "box": box.as_list(),
        "source_sha256": sha256(Path(pdf_path)),
        "text": text,
        "ocr_called": False,
    }
