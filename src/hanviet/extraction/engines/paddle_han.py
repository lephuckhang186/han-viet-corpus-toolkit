"""Primary Han OCR engine adapter using PaddleOCR (PP-OCRv6 / vertical_rtl & horizontal_ltr)."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from hanviet.common.io import sha256
from hanviet.extraction.preprocessing.han_preprocess import horizontal_han_rows, text_order
from hanviet.extraction.schema import OCRRecord, make_ocr_record_id


class PaddleHanEngine:
    name = "paddleocr"

    def __init__(
        self,
        *,
        detection_model: str = "PP-OCRv6_medium_det",
        recognition_model: str = "PP-OCRv6_medium_rec",
        inference_engine: str = "transformers",
        device: str = "auto",
        batch_size: int = 1,
        rec_score_threshold: float = 0.0,
        detection_max_side: int = 2048,
        predictor: Any = None,
    ):
        self.detection_model = detection_model
        self.recognition_model = recognition_model
        self.inference_engine = inference_engine
        self.device = device
        self.batch_size = batch_size
        self.rec_score_threshold = rec_score_threshold
        self.detection_max_side = detection_max_side
        self.model_version = f"{detection_model}+{recognition_model}"
        self._predictor = predictor
        self._row_recognizer = None

    def _ensure_column_ocr(self) -> Any:
        if self._predictor is not None:
            return self._predictor
        from hanviet.common.paths import resolve_device  # noqa: PLC0415

        try:
            from paddleocr import PaddleOCR  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "PaddleOCR is not installed in this environment. Install requirements/ocr.txt."
            ) from exc
        resolved_device = resolve_device(self.device)
        self._predictor = PaddleOCR(
            text_detection_model_name=self.detection_model,
            text_recognition_model_name=self.recognition_model,
            text_recognition_batch_size=self.batch_size,
            engine=self.inference_engine,
            device=resolved_device,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        return self._predictor

    def _ensure_row_recognizer(self) -> Any:
        if self._row_recognizer is not None:
            return self._row_recognizer
        if self._predictor is not None:
            return self._predictor
        from hanviet.common.paths import resolve_device  # noqa: PLC0415

        try:
            from paddleocr import TextRecognition  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "PaddleOCR TextRecognition is not installed in this environment. Install requirements/ocr.txt."
            ) from exc
        self._row_recognizer = TextRecognition(
            model_name=self.recognition_model,
            engine=self.inference_engine,
            device=resolve_device(self.device),
        )
        return self._row_recognizer

    def parse_raw_prediction(
        self,
        raw: dict[str, Any],
        *,
        source_id: str,
        work_id: str,
        corpus_id: str,
        member_id: str,
        variant: str,
        image_reference: str,
        input_sha256: str,
        pdf_page: int | None = None,
        reading_order_mode: str = "vertical_rtl",
        column_center_ratio: float = 0.45,
        preprocess_transform: dict[str, Any] | None = None,
    ) -> list[OCRRecord]:
        """Normalize raw PaddleOCR JSON dict into Shared OCRRecord entries."""
        data = raw.get("res", raw)
        texts = data.get("rec_texts", [])
        scores = data.get("rec_scores", [None] * len(texts))
        polys = data.get("rec_polys", [None] * len(texts))
        if len(texts) != len(scores):
            raise ValueError("rec_texts and rec_scores length mismatch.")
        order = text_order(
            {"rec_texts": texts, "rec_polys": polys if all(p is not None for p in polys) else None},
            reading_order_mode if all(p is not None for p in polys) else "model",
            column_center_ratio=column_center_ratio,
        )
        records: list[OCRRecord] = []
        for rank, idx in enumerate(order, 1):
            score_raw = scores[idx]
            conf = float(score_raw) if score_raw is not None and math.isfinite(float(score_raw)) else None
            bbox = polys[idx] if idx < len(polys) and polys[idx] is not None else None
            text = str(texts[idx])
            records.append(
                OCRRecord(
                    record_id=make_ocr_record_id(source_id, self.name, idx, rank),
                    source_id=source_id,
                    region_id=idx,
                    work_id=work_id,
                    corpus_id=corpus_id,
                    member_id=member_id,
                    variant=variant,
                    pdf_page=pdf_page,
                    reading_order=rank,
                    engine=self.name,
                    model_version=self.model_version,
                    text=text,
                    bbox=bbox,
                    confidence=conf,
                    image_reference=image_reference,
                    input_sha256=input_sha256,
                    status="OK" if text.strip() else "EMPTY",
                    coordinate_space="source_image_pixels",
                    preprocess_transform=preprocess_transform,
                )
            )
        return records

    def recognize_image(
        self,
        image_path: Path,
        *,
        source_id: str,
        work_id: str,
        corpus_id: str,
        member_id: str,
        variant: str = "han",
        pdf_page: int | None = None,
        layout: str = "vertical_rtl",
        reading_order_mode: str | None = None,
        row_settings: dict[str, Any] | None = None,
        manual_boxes: list[list[int]] | None = None,
        preprocess_transform: dict[str, Any] | None = None,
        raw_output_path: Path | None = None,
    ) -> list[OCRRecord]:
        image_path = Path(image_path)
        digest = sha256(image_path)

        if layout == "horizontal_ltr":
            import tempfile  # noqa: PLC0415
            from PIL import Image  # noqa: PLC0415

            recognizer = self._ensure_row_recognizer()
            with Image.open(image_path) as orig:
                rgb = orig.convert("RGB")
            boxes, detection_meta = horizontal_han_rows(rgb, row_settings, manual_boxes)
            texts, scores, polys = [], [], []
            with tempfile.TemporaryDirectory(prefix="han_rows_") as tmpdir:
                for idx, box in enumerate(boxes):
                    crop = rgb.crop(box)
                    tmp_file = Path(tmpdir) / f"row_{idx:04d}.png"
                    crop.save(tmp_file, format="PNG", compress_level=0)
                    preds = list(recognizer.predict(input=str(tmp_file), batch_size=self.batch_size))
                    if len(preds) != 1:
                        raise ValueError("Horizontal Han row recognition must return 1 item per row.")
                    raw_item = preds[0].json if hasattr(preds[0], "json") else preds[0]
                    raw_item = json.loads(raw_item) if isinstance(raw_item, str) else raw_item
                    res = raw_item.get("res", raw_item)
                    texts.append(res["rec_text"])
                    scores.append(res.get("rec_score"))
                    x1, y1, x2, y2 = box
                    polys.append([[x1, y1], [x2, y1], [x2, y2], [x1, y2]])
            raw_payload: dict[str, Any] = {
                "res": {
                    "pipeline": "paddle_han_horizontal_rows",
                    "rec_texts": texts,
                    "rec_scores": scores,
                    "rec_polys": polys,
                    "row_detection": detection_meta,
                }
            }
            order_mode = reading_order_mode or "top_to_bottom"
        else:
            ocr = self._ensure_column_ocr()
            preds = list(
                ocr.predict(
                    input=str(image_path),
                    text_rec_score_thresh=self.rec_score_threshold,
                    text_det_limit_side_len=self.detection_max_side,
                    text_det_limit_type="max",
                )
            )
            if len(preds) != 1:
                raise ValueError("Expected single prediction result per image.")
            raw_payload = preds[0].json if hasattr(preds[0], "json") else preds[0]
            raw_payload = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
            order_mode = reading_order_mode or "vertical_rtl"

        if raw_output_path is not None:
            from hanviet.common.io import write_json  # noqa: PLC0415

            write_json(raw_output_path, raw_payload)

        return self.parse_raw_prediction(
            raw_payload,
            source_id=source_id,
            work_id=work_id,
            corpus_id=corpus_id,
            member_id=member_id,
            variant=variant,
            image_reference=str(image_path),
            input_sha256=digest,
            pdf_page=pdf_page,
            reading_order_mode=order_mode,
            preprocess_transform=preprocess_transform,
        )
