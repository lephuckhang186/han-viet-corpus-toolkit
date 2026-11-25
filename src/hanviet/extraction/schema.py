"""Shared OCR record schema and coordinate-space builders (null when engine lacks bbox/confidence)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Any

from hanviet.common.io import bytes_hash, json_bytes


@dataclass(frozen=True)
class OCRRecord:
    record_id: str
    source_id: str
    region_id: str | int
    work_id: str
    corpus_id: str
    member_id: str
    variant: str
    pdf_page: int | None
    reading_order: int | None
    engine: str
    model_version: str
    text: str
    bbox: list[Any] | None
    confidence: float | None
    image_reference: str
    input_sha256: str
    status: str = "OK"
    coordinate_space: str | None = "source_image_pixels"
    preprocess_transform: dict[str, Any] | None = None
    schema_version: str = "1.0"
    polygon: list[Any] | None = None
    layout: str | None = None
    original_image_sha256: str | None = None
    processed_image_sha256: str | None = None
    run_id: str | None = None
    request_id: str | None = None
    processing_time: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.confidence is not None and not math.isfinite(float(self.confidence)):
            raise ValueError(f"Non-finite confidence for record {self.record_id}: {self.confidence!r}")
        if self.variant not in {"han", "dich_am", "dich_nghia", "dich_tho"}:
            raise ValueError(f"Invalid variant: {self.variant!r}")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        extra = payload.pop("extra", {})
        if extra:
            payload["extra"] = extra
        return payload


def make_ocr_record_id(source_id: str, engine: str, region_id: str | int, reading_order: int | None) -> str:
    return bytes_hash(json_bytes([source_id, engine, region_id, reading_order]))[:24]
