"""Secondary Vietnamese OCR engine using line-level VietOCR + optional Paddle TextDetection."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from hanviet.common.io import sha256, write_json
from hanviet.extraction.preprocessing.han_preprocess import text_order
from hanviet.extraction.preprocessing.viet_preprocess import line_crop
from hanviet.extraction.schema import OCRRecord, make_ocr_record_id


class VietOCREngine:
    """Line-level VietOCR adapter. Requires detected polygons or pre-cropped line boxes (never assumes page-level detection)."""

    name = "vietocr"

    def __init__(
        self,
        *,
        model_name: str = "vgg_transformer",
        weights_path: str | Path | None = None,
        device: str = "auto",
        max_width: int = 512,
        max_length: int = 256,
        crop_padding: int = 2,
        reading_order: str = "top_to_bottom",
        detector: Any = None,
        recognizer: Any = None,
    ):
        self.model_name = model_name
        self.weights_path = Path(weights_path) if weights_path else None
        self.device = device
        self.max_width = max_width
        self.max_length = max_length
        self.crop_padding = crop_padding
        self.reading_order = reading_order
        self._detector = detector
        self._recognizer = recognizer
        self.model_version = model_name

    def recognize_lines(
        self,
        image_path: Path,
        polygons: list[list[list[float]]] | None = None,
        *,
        source_id: str,
        work_id: str,
        corpus_id: str,
        member_id: str,
        variant: str = "dich_nghia",
        pdf_page: int | None = None,
        raw_output_path: Path | None = None,
    ) -> list[OCRRecord]:
        """Run VietOCR on line regions identified by `polygons` or via `self._detector`."""
        from PIL import Image  # noqa: PLC0415

        image_path = Path(image_path)
        digest = sha256(image_path)
        if polygons is None:
            if self._detector is None:
                raise RuntimeError(
                    "VietOCR is a line-level recognizer and does not perform page-level text detection. "
                    "Supply line polygons (e.g. from Paddle TextDetection or Tesseract TSV) or configure detector."
                )
            det_res = list(self._detector.predict(input=str(image_path), batch_size=1))[0]
            raw_det = det_res.json if hasattr(det_res, "json") else det_res
            polygons = (raw_det.get("res") or raw_det)["dt_polys"]

        if self._recognizer is None:
            raise RuntimeError(
                "VietOCR recognizer not loaded. Initialize VietLineReader or install requirements/ocr.txt."
            )

        order = text_order({"rec_texts": [""] * len(polygons), "rec_polys": polygons}, self.reading_order)
        with Image.open(image_path) as orig:
            rgb = orig.convert("RGB")

        records: list[OCRRecord] = []
        raw_rows = []
        for rank, det_idx in enumerate(order, 1):
            poly = polygons[det_idx]
            crop, _ = line_crop(rgb, poly, self.crop_padding)
            text, score = self._recognizer.predict(crop, return_prob=True)
            conf = float(score) if score is not None and math.isfinite(float(score)) else None
            flags = []
            if crop.width * 32 / max(1, crop.height) > self.max_width:
                flags.append("width_clamped")
            if len(text) >= self.max_length:
                flags.append("possible_decode_limit")
            rec = OCRRecord(
                record_id=make_ocr_record_id(source_id, self.name, det_idx, rank),
                source_id=source_id,
                region_id=det_idx,
                work_id=work_id,
                corpus_id=corpus_id,
                member_id=member_id,
                variant=variant,
                pdf_page=pdf_page,
                reading_order=rank,
                engine=self.name,
                model_version=self.model_version,
                text=str(text),
                bbox=poly,
                confidence=conf,
                image_reference=str(image_path),
                input_sha256=digest,
                status="OK" if str(text).strip() else "EMPTY",
                coordinate_space="source_image_pixels",
                extra={"flags": flags} if flags else {},
            )
            records.append(rec)
            raw_rows.append(rec.to_dict())

        if raw_output_path is not None:
            write_json(Path(raw_output_path), {"pipeline": "vietocr_line_level", "records": raw_rows})
        return records
