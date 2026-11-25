"""Primary Vietnamese OCR engine using Tesseract OCR (language pack 'vie')."""
from __future__ import annotations

import csv
import io
from pathlib import Path
import statistics
import subprocess
from typing import Any, Callable

from hanviet.common.config import check_tesseract
from hanviet.common.io import sha256, write_json
from hanviet.extraction.schema import OCRRecord, make_ocr_record_id


def parse_tesseract_tsv(
    tsv_text: str,
    *,
    source_id: str,
    work_id: str,
    corpus_id: str,
    member_id: str,
    variant: str,
    image_reference: str,
    input_sha256: str,
    model_version: str,
    pdf_page: int | None = None,
) -> list[OCRRecord]:
    """Aggregate Tesseract word rows (level=5) by (block_num, par_num, line_num) into line OCRRecords."""
    reader = csv.DictReader(io.StringIO(tsv_text), delimiter="\t")
    lines: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in reader:
        if row.get("level") != "5":
            continue
        word = (row.get("text") or "").strip()
        if not word:
            continue
        key = (row.get("block_num", "0"), row.get("par_num", "0"), row.get("line_num", "0"))
        entry = lines.setdefault(key, {"words": [], "confs": [], "boxes": []})
        entry["words"].append(word)
        try:
            conf = float(row["conf"])
            if conf >= 0:
                entry["confs"].append(conf / 100.0)
        except (KeyError, TypeError, ValueError):
            pass
        try:
            x, y, w, h = int(row["left"]), int(row["top"]), int(row["width"]), int(row["height"])
            entry["boxes"].append((x, y, x + w, y + h))
        except (KeyError, TypeError, ValueError):
            pass

    records: list[OCRRecord] = []
    for order, (_, entry) in enumerate(lines.items(), 1):
        boxes = entry["boxes"]
        if boxes:
            x1 = min(b[0] for b in boxes)
            y1 = min(b[1] for b in boxes)
            x2 = max(b[2] for b in boxes)
            y2 = max(b[3] for b in boxes)
            polygon: list[Any] | None = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
        else:
            polygon = None
        mean_conf = round(statistics.mean(entry["confs"]), 4) if entry["confs"] else None
        text = " ".join(entry["words"])
        records.append(
            OCRRecord(
                record_id=make_ocr_record_id(source_id, "tesseract", order - 1, order),
                source_id=source_id,
                region_id=order - 1,
                work_id=work_id,
                corpus_id=corpus_id,
                member_id=member_id,
                variant=variant,
                pdf_page=pdf_page,
                reading_order=order,
                engine="tesseract",
                model_version=model_version,
                text=text,
                bbox=polygon,
                confidence=mean_conf,
                image_reference=image_reference,
                input_sha256=input_sha256,
                status="OK" if text else "EMPTY",
                coordinate_space="source_image_pixels" if polygon is not None else None,
            )
        )
    return records


class TesseractVietEngine:
    """Tesseract OCR adapter configured for Vietnamese (`vie`)."""

    name = "tesseract"

    def __init__(
        self,
        *,
        lang: str = "vie",
        psm: int = 6,
        oem: int = 3,
        tesseract_cmd: str | None = None,
        runner: Callable[[Path, str, int, int], str] | None = None,
    ):
        self.lang = lang
        self.psm = psm
        self.oem = oem
        self.tesseract_cmd = tesseract_cmd
        self._runner = runner
        self.model_version = f"tesseract_{lang}_oem{oem}_psm{psm}"

    def _run_tsv(self, image_path: Path) -> str:
        if self._runner is not None:
            return self._runner(image_path, self.lang, self.oem, self.psm)
        status = check_tesseract(self.tesseract_cmd, lang=self.lang)
        if not status["ok"]:
            raise RuntimeError(status["message"])
        cmd = [
            status["binary"],
            str(image_path),
            "stdout",
            "-l",
            self.lang,
            "--oem",
            str(self.oem),
            "--psm",
            str(self.psm),
            "tsv",
        ]
        proc = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", check=False, timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(f"Tesseract failed ({proc.returncode}): {proc.stderr.strip()}")
        return proc.stdout

    def recognize_image(
        self,
        image_path: Path,
        *,
        source_id: str,
        work_id: str,
        corpus_id: str,
        member_id: str,
        variant: str = "dich_nghia",
        pdf_page: int | None = None,
        raw_output_path: Path | None = None,
    ) -> list[OCRRecord]:
        image_path = Path(image_path)
        digest = sha256(image_path)
        tsv_text = self._run_tsv(image_path)
        records = parse_tesseract_tsv(
            tsv_text,
            source_id=source_id,
            work_id=work_id,
            corpus_id=corpus_id,
            member_id=member_id,
            variant=variant,
            image_reference=str(image_path),
            input_sha256=digest,
            model_version=self.model_version,
            pdf_page=pdf_page,
        )
        if raw_output_path is not None:
            write_json(Path(raw_output_path), {"tsv": tsv_text, "records": [r.to_dict() for r in records]})
        return records
