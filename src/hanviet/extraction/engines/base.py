"""Base OCR engine protocol ensuring lazy model initialization and uniform OCRRecord outputs."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from hanviet.extraction.schema import OCRRecord


class OCREngine(Protocol):
    name: str
    model_version: str

    def recognize_image(
        self,
        image_path: Path,
        *,
        source_id: str,
        work_id: str,
        corpus_id: str,
        member_id: str,
        variant: str,
        pdf_page: int | None = None,
        **kwargs: Any,
    ) -> list[OCRRecord]:
        ...
