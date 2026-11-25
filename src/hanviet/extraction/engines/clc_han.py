"""Secondary Han OCR engine adapter for the Kim Han Nom (CLC) web OCR API.

API contract verified directly from TaiLieuAPI_HanNom_CLC.pdf (pages 1-6) and cong_cu/clc_ocr.py:
- Upload endpoint: POST {base_url}image-upload (form-data image_file -> data.file_name)
- OCR endpoint:    POST {base_url}image-ocr (JSON ocr_id, lang_type, reading_direction, epitaph, tag, file_name)
- Distinct from sentence alignment endpoint (/sentence-alignment).
"""
from __future__ import annotations

import logging
from pathlib import Path
import time
from typing import Any

from hanviet.alignment.backends.clc_aligner import CLC_USER_AGENT, reserve_clc_request
from hanviet.common.config import get_credential
from hanviet.common.io import bytes_hash, json_bytes, read_json, write_json
from hanviet.extraction.schema import OCRRecord, make_ocr_record_id

CLC_OCR_BASE_URL = "https://kimhannom.fit.hcmus.edu.vn/api/web/clc-sinonom/"
DEFAULT_CLC_OCR_OPTIONS = {
    "ocr_id": 1,            # 1: vertical standard, 2: administrative, 3: outdoor, 4: horizontal standard
    "lang_type": 1,         # 0: unknown, 1: Han, 2: Nom
    "reading_direction": 1, # 1: vertical (default), 2: horizontal
    "epitaph": 0,           # 0: normal document, 1: stele/epitaph
    "tag": None,
}

logger = logging.getLogger(__name__)


def validate_clc_ocr_options(options: dict[str, Any]) -> dict[str, Any]:
    merged = {**DEFAULT_CLC_OCR_OPTIONS, **options}
    if merged["ocr_id"] not in {1, 2, 3, 4}:
        raise ValueError(f"Invalid CLC ocr_id: {merged['ocr_id']!r} (expected 1..4).")
    if merged["lang_type"] not in {0, 1, 2}:
        raise ValueError(f"Invalid CLC lang_type: {merged['lang_type']!r} (expected 0..2).")
    if merged["reading_direction"] not in {1, 2}:
        raise ValueError(f"Invalid CLC reading_direction: {merged['reading_direction']!r} (expected 1 or 2).")
    if merged["epitaph"] not in {0, 1}:
        raise ValueError(f"Invalid CLC epitaph: {merged['epitaph']!r} (expected 0 or 1).")
    return merged


def parse_clc_ocr_response(
    response: dict[str, Any],
    *,
    source_id: str,
    work_id: str,
    corpus_id: str,
    member_id: str,
    variant: str,
    image_reference: str,
    input_sha256: str,
    pdf_page: int | None = None,
    options: dict[str, Any] | None = None,
    status_override: str | None = None,
) -> list[OCRRecord]:
    """Parse verified CLC image-ocr JSON payload into OCRRecord entries (never fabricates bbox/confidence)."""
    if not isinstance(response, dict) or response.get("is_success") is not True or response.get("code") != "000000":
        raise ValueError(f"CLC OCR API error or malformed payload: code={response.get('code') if isinstance(response, dict) else None!r}")
    data = response.get("data") or {}
    lines = data.get("result_ocr_text")
    if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
        raise ValueError("CLC OCR response missing list 'data.result_ocr_text'.")
    bboxes = data.get("result_bbox")
    has_aligned_boxes = isinstance(bboxes, list) and len(bboxes) == len(lines)
    model_version = f"clc_ocr_id{options.get('ocr_id', 1)}_lang{options.get('lang_type', 1)}" if options else "clc_ocr"

    if not lines:
        return [
            OCRRecord(
                record_id=make_ocr_record_id(source_id, "clc_ocr", 0, 1),
                source_id=source_id,
                region_id=0,
                work_id=work_id,
                corpus_id=corpus_id,
                member_id=member_id,
                variant=variant,
                pdf_page=pdf_page,
                reading_order=1,
                engine="clc_ocr",
                model_version=model_version,
                text="",
                bbox=None,
                confidence=None,
                image_reference=image_reference,
                input_sha256=input_sha256,
                status=status_override or "EMPTY",
                coordinate_space=None,
            )
        ]

    records: list[OCRRecord] = []
    for idx, text in enumerate(lines, 1):
        raw_box = bboxes[idx - 1] if has_aligned_boxes and bboxes[idx - 1] else None
        records.append(
            OCRRecord(
                record_id=make_ocr_record_id(source_id, "clc_ocr", idx - 1, idx),
                source_id=source_id,
                region_id=idx - 1,
                work_id=work_id,
                corpus_id=corpus_id,
                member_id=member_id,
                variant=variant,
                pdf_page=pdf_page,
                reading_order=idx,
                engine="clc_ocr",
                model_version=model_version,
                text=text,
                bbox=raw_box,
                confidence=None,  # CLC image-ocr endpoint does not return confidence scores.
                image_reference=image_reference,
                input_sha256=input_sha256,
                status=status_override or ("OK" if text.strip() else "EMPTY"),
                coordinate_space="source_image_pixels" if raw_box is not None else None,
            )
        )
    return records


def import_clc_ocr_json(
    json_path: Path,
    *,
    source_id: str,
    work_id: str,
    corpus_id: str,
    member_id: str,
    variant: str = "han",
    image_reference: str = "",
    input_sha256: str | None = None,
    pdf_page: int | None = None,
) -> list[OCRRecord]:
    """Import an already-saved CLC OCR JSON file (supporting offline review without API calls)."""
    payload = read_json(Path(json_path))
    response = payload.get("response", payload)
    identity = payload.get("identity", {})
    digest = input_sha256 or identity.get("sha256") or bytes_hash(Path(json_path).read_bytes())
    options = identity.get("options")
    return parse_clc_ocr_response(
        response,
        source_id=source_id,
        work_id=work_id,
        corpus_id=corpus_id,
        member_id=member_id,
        variant=variant,
        image_reference=image_reference or str(json_path),
        input_sha256=digest,
        pdf_page=pdf_page,
        options=options,
        status_override="IMPORTED",
    )


class CLCOCRAdapter:
    """HTTP adapter for CLC image-upload + image-ocr with caching, rate limiting, retries, and error logs."""

    name = "clc_ocr"

    def __init__(
        self,
        *,
        base_url: str = CLC_OCR_BASE_URL,
        api_key_env: str = "CLC_OCR_API_KEY",
        options: dict[str, Any] | None = None,
        timeout: tuple[float, float] = (10.0, 60.0),
        max_retries: int = 2,
        backoff_seconds: float = 2.0,
        min_delay_seconds: float = 3.0,
        session: Any = None,
        quota_log_path: Path | None = None,
        project_root: Path | None = None,
    ):
        self.base_url = base_url if base_url.endswith("/") else base_url + "/"
        if "sentence-alignment" in self.base_url:
            raise ValueError("CLC OCR must NOT use the sentence-alignment endpoint.")
        self.api_key_env = api_key_env
        self.options = validate_clc_ocr_options(options or {})
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.min_delay_seconds = min_delay_seconds
        self._session = session
        self.quota_log_path = quota_log_path
        self.project_root = project_root
        self.model_version = f"clc_ocr_id{self.options['ocr_id']}_lang{self.options['lang_type']}"

    def _post_with_retry(self, session: Any, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            reserve_clc_request(self.quota_log_path)
            try:
                response = session.post(
                    self.base_url + endpoint,
                    timeout=self.timeout,
                    allow_redirects=False,
                    **kwargs,
                )
                if response.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                    time.sleep(self.backoff_seconds * (2**attempt))
                    continue
                if response.status_code != 200:
                    raise ValueError(f"CLC {endpoint}: HTTP {response.status_code}")
                body = response.json()
                if not isinstance(body, dict) or body.get("is_success") is not True or body.get("code") != "000000":
                    raise ValueError(f"CLC {endpoint}: code={body.get('code') if isinstance(body, dict) else None!r}")
                return body
            except Exception as exc:
                last_error = exc
                logger.warning("CLC OCR %s attempt %s failed: %s", endpoint, attempt + 1, type(exc).__name__)
                if attempt < self.max_retries and not isinstance(exc, ValueError):
                    time.sleep(self.backoff_seconds * (2**attempt))
                    continue
                break
            finally:
                if self.min_delay_seconds > 0:
                    time.sleep(self.min_delay_seconds)
        raise ValueError(f"CLC OCR {endpoint} failed: {last_error}") from last_error

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
        cache_meta_path: Path | None = None,
        error_log_path: Path | None = None,
    ) -> list[OCRRecord]:
        image_path = Path(image_path)
        source_bytes = image_path.read_bytes()
        digest = bytes_hash(source_bytes)
        identity = {"sha256": digest, "options": self.options}

        if cache_meta_path is not None and Path(cache_meta_path).is_file():
            saved = read_json(Path(cache_meta_path))
            if saved.get("identity") == identity and isinstance(saved.get("response"), dict):
                return parse_clc_ocr_response(
                    saved["response"],
                    source_id=source_id,
                    work_id=work_id,
                    corpus_id=corpus_id,
                    member_id=member_id,
                    variant=variant,
                    image_reference=str(image_path),
                    input_sha256=digest,
                    pdf_page=pdf_page,
                    options=self.options,
                )

        token = get_credential(self.api_key_env, project_root=self.project_root)
        if not token and self._session is None:
            record = OCRRecord(
                record_id=make_ocr_record_id(source_id, self.name, 0, None),
                source_id=source_id,
                region_id=0,
                work_id=work_id,
                corpus_id=corpus_id,
                member_id=member_id,
                variant=variant,
                pdf_page=pdf_page,
                reading_order=None,
                engine=self.name,
                model_version=self.model_version,
                text="",
                bbox=None,
                confidence=None,
                image_reference=str(image_path),
                input_sha256=digest,
                status="UNPROCESSED",
                coordinate_space=None,
                extra={"reason": f"Missing {self.api_key_env}; run offline or import cached JSON."},
            )
            return [record]

        import requests  # noqa: PLC0415

        session = self._session or requests.Session()
        # Note: Authorization header is attached to session only in memory, never serialized to disk.
        session.headers.update({"User-Agent": CLC_USER_AGENT, "Authorization": f"Bearer {token or ''}"})
        try:
            upload = self._post_with_retry(
                session,
                "image-upload",
                files={"image_file": (image_path.name, source_bytes, "image/png")},
            )
            file_name = upload["data"]["file_name"].strip()
            result = self._post_with_retry(
                session,
                "image-ocr",
                json={**self.options, "file_name": file_name},
            )
            if cache_meta_path is not None:
                # Credential-free raw cache
                write_json(Path(cache_meta_path), {"identity": identity, "response": result})
            return parse_clc_ocr_response(
                result,
                source_id=source_id,
                work_id=work_id,
                corpus_id=corpus_id,
                member_id=member_id,
                variant=variant,
                image_reference=str(image_path),
                input_sha256=digest,
                pdf_page=pdf_page,
                options=self.options,
            )
        except Exception as exc:
            if error_log_path is not None:
                Path(error_log_path).parent.mkdir(parents=True, exist_ok=True)
                with Path(error_log_path).open("ab") as log_stream:
                    log_stream.write(json_bytes({"source_id": source_id, "image": str(image_path), "error": str(exc)}))
            return [
                OCRRecord(
                    record_id=make_ocr_record_id(source_id, self.name, 0, None),
                    source_id=source_id,
                    region_id=0,
                    work_id=work_id,
                    corpus_id=corpus_id,
                    member_id=member_id,
                    variant=variant,
                    pdf_page=pdf_page,
                    reading_order=None,
                    engine=self.name,
                    model_version=self.model_version,
                    text="",
                    bbox=None,
                    confidence=None,
                    image_reference=str(image_path),
                    input_sha256=digest,
                    status="FAILED",
                    coordinate_space=None,
                    extra={"error": str(exc)},
                )
            ]
        finally:
            if self._session is None:
                session.close()
