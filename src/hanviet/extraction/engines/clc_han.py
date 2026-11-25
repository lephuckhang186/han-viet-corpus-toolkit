"""Secondary Han OCR engine adapter for the Kim Han Nom (CLC) web OCR API.

API contract verified directly from TaiLieuAPI_HanNom_CLC.pdf (pages 1-6) and cong_cu/clc_ocr.py:
- Upload endpoint: POST {base_url}image-upload (form-data image_file -> data.file_name)
- OCR endpoint:    POST {base_url}image-ocr (JSON ocr_id, lang_type, reading_direction, epitaph, tag, file_name)
- Distinct from sentence alignment endpoint (/sentence-alignment).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
import time
from typing import Any

from hanviet.alignment.backends.clc_aligner import CLC_USER_AGENT, reserve_clc_request
from hanviet.common.config import get_credential
from hanviet.common.io import bytes_hash, json_bytes, read_json, write_json
from hanviet.extraction.schema import OCRRecord, make_ocr_record_id

CLC_OCR_BASE_URL = "https://kimhannom.fit.hcmus.edu.vn/api/web/clc-sinonom/"
CLC_OCR_PARSER_VERSION = "1.1"
DEFAULT_CLC_OCR_OPTIONS = {
    "ocr_id": 1,            # 1: vertical standard, 2: administrative, 3: outdoor, 4: horizontal standard
    "lang_type": 1,         # 0: unknown, 1: Han, 2: Nom
    "reading_direction": 1, # 1: vertical (default), 2: horizontal
    "epitaph": 0,           # 0: normal document, 1: stele/epitaph
    "tag": None,
}

logger = logging.getLogger(__name__)


class CLCNonRetryableError(ValueError):
    """Non-retryable CLC API error (401/403/4xx client/auth/validation errors)."""


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
    cache_status: str | None = None,
    run_id: str | None = None,
    processing_time: float | None = None,
) -> list[OCRRecord]:
    """Parse verified CLC image-ocr JSON payload into OCRRecord entries (never fabricates bbox/confidence)."""
    if not isinstance(response, dict) or response.get("is_success") is not True or response.get("code") != "000000":
        raise ValueError(
            f"CLC OCR API error or malformed payload: code={response.get('code') if isinstance(response, dict) else None!r}"
        )
    data = response.get("data") or {}
    lines = data.get("result_ocr_text")
    if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
        raise ValueError("CLC OCR response missing list 'data.result_ocr_text'.")
    bboxes = data.get("result_bbox")
    has_aligned_boxes = isinstance(bboxes, list) and len(bboxes) == len(lines)
    model_version = f"clc_ocr_id{options.get('ocr_id', 1)}_lang{options.get('lang_type', 1)}" if options else "clc_ocr"
    extra = {"cache_status": cache_status} if cache_status else {}
    direction = (options or {}).get("reading_direction")
    layout = "vertical_rtl" if direction == 1 else ("horizontal_ltr" if direction == 2 else None)

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
                layout=layout,
                image_reference=image_reference,
                input_sha256=input_sha256,
                original_image_sha256=input_sha256,
                run_id=run_id,
                processing_time=processing_time,
                status=status_override or "EMPTY",
                coordinate_space=None,
                extra=extra,
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
                polygon=raw_box,
                confidence=None,  # CLC image-ocr endpoint does not return confidence scores.
                layout=layout,
                image_reference=image_reference,
                input_sha256=input_sha256,
                original_image_sha256=input_sha256,
                run_id=run_id,
                processing_time=processing_time,
                status=status_override or ("OK" if text.strip() else "EMPTY"),
                coordinate_space="source_image_pixels" if raw_box is not None else None,
                extra=dict(extra),
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
    run_id: str | None = None,
) -> list[OCRRecord]:
    """Import an already-saved CLC OCR JSON file with explicit source/work/page mapping."""
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
        cache_status="MANUAL_IMPORT",
        run_id=run_id,
    )


def import_clc_ocr_text(
    text_or_path: Path | str,
    *,
    source_id: str,
    work_id: str,
    corpus_id: str,
    member_id: str,
    pdf_page: int,
    region_id: str | int = 0,
    variant: str = "han",
    image_reference: str = "",
    input_sha256: str | None = None,
    split_lines: bool = True,
    run_id: str | None = None,
) -> list[OCRRecord]:
    """Import plain TXT exported from CLC web tool using explicit source/region/page metadata (never fuzzy-matched)."""
    if not source_id or pdf_page is None:
        raise ValueError("Manual CLC import requires explicit source_id and pdf_page.")
    if isinstance(text_or_path, Path) or (isinstance(text_or_path, str) and Path(text_or_path).is_file()):
        raw_bytes = Path(text_or_path).read_bytes()
        raw_text = raw_bytes.decode("utf-8-sig")
        digest = input_sha256 or bytes_hash(raw_bytes)
        ref = image_reference or str(text_or_path)
    else:
        raw_text = str(text_or_path)
        digest = input_sha256 or bytes_hash(raw_text.encode("utf-8"))
        ref = image_reference or f"manual_import:{source_id}"

    lines = raw_text.splitlines() if split_lines else [raw_text]
    lines = [ln for ln in lines if ln != ""] or [""]
    records: list[OCRRecord] = []
    for order, line in enumerate(lines, 1):
        rid = region_id if len(lines) == 1 else f"{region_id}_{order - 1}"
        records.append(
            OCRRecord(
                record_id=make_ocr_record_id(source_id, "clc_ocr", rid, order),
                source_id=source_id,
                region_id=rid,
                work_id=work_id,
                corpus_id=corpus_id,
                member_id=member_id,
                variant=variant,
                pdf_page=pdf_page,
                reading_order=order,
                engine="clc_ocr",
                model_version="clc_manual_import",
                text=line,
                bbox=None,
                polygon=None,
                confidence=None,
                image_reference=ref,
                input_sha256=digest,
                original_image_sha256=digest,
                run_id=run_id,
                status="MANUAL_IMPORT",
                coordinate_space=None,
                extra={"cache_status": "MANUAL_IMPORT"},
            )
        )
    return records


def _parse_retry_after(header_value: Any) -> float | None:
    if header_value is None:
        return None
    try:
        secs = float(str(header_value).strip())
        return max(0.0, secs)
    except ValueError:
        return None


class CLCOCRAdapter:
    """HTTP adapter for CLC image-upload + image-ocr with caching, rate limiting, retries, and error logs."""

    name = "clc_ocr"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key_env: str = "CLC_OCR_API_KEY",
        options: dict[str, Any] | None = None,
        timeout: tuple[float, float] | None = None,
        max_retries: int | None = None,
        backoff_seconds: float = 2.0,
        min_delay_seconds: float = 3.0,
        session: Any = None,
        quota_log_path: Path | None = None,
        project_root: Path | None = None,
    ):
        env_url = os.getenv("CLC_OCR_API_URL", "").strip()
        resolved_url = base_url or env_url or CLC_OCR_BASE_URL
        self.base_url = resolved_url if resolved_url.endswith("/") else resolved_url + "/"
        if "sentence-alignment" in self.base_url:
            raise ValueError("CLC OCR must NOT use the sentence-alignment endpoint.")
        self.api_key_env = api_key_env
        self.options = validate_clc_ocr_options(options or {})

        if timeout is None:
            env_timeout = os.getenv("CLC_OCR_TIMEOUT", "").strip()
            read_t = float(env_timeout) if env_timeout else 60.0
            self.timeout: tuple[float, float] = (10.0, read_t)
        else:
            self.timeout = timeout

        if max_retries is None:
            env_retries = os.getenv("CLC_OCR_MAX_RETRIES", "").strip()
            self.max_retries = int(env_retries) if env_retries else 2
        else:
            self.max_retries = max_retries

        self.backoff_seconds = backoff_seconds
        self.min_delay_seconds = min_delay_seconds
        self._session = session
        self.quota_log_path = quota_log_path
        self.project_root = project_root
        self.model_version = f"clc_ocr_id{self.options['ocr_id']}_lang{self.options['lang_type']}"

    def build_cache_identity(self, input_sha256: str) -> dict[str, Any]:
        return {
            "sha256": input_sha256,
            "service": self.base_url,
            "options": self.options,
            "model_version": self.model_version,
            "parser_version": CLC_OCR_PARSER_VERSION,
        }

    def _cache_matches(self, saved_identity: dict[str, Any], image_digest: str) -> bool:
        expected = self.build_cache_identity(image_digest)
        if saved_identity == expected:
            return True
        # Legacy saved JSON fixtures store only {"sha256", "options"}
        if set(saved_identity) <= {"sha256", "options"} and saved_identity.get("sha256") == image_digest:
            opts = saved_identity.get("options")
            return opts is None or opts == self.options
        return False

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
                code = response.status_code
                if code in {401, 403}:
                    raise CLCNonRetryableError(f"CLC {endpoint}: authentication/permission denied (HTTP {code})")
                if 400 <= code < 500 and code != 429:
                    raise CLCNonRetryableError(f"CLC {endpoint}: invalid client request (HTTP {code})")
                if code in {429, 500, 502, 503, 504}:
                    if attempt < self.max_retries:
                        retry_after = _parse_retry_after(getattr(response, "headers", {}).get("Retry-After"))
                        wait = retry_after if retry_after is not None else self.backoff_seconds * (2**attempt)
                        time.sleep(wait)
                        continue
                    raise ValueError(f"CLC {endpoint}: retry exhausted after HTTP {code}")
                if code != 200:
                    raise ValueError(f"CLC {endpoint}: HTTP {code}")
                body = response.json()
                if not isinstance(body, dict) or body.get("is_success") is not True or body.get("code") != "000000":
                    raise CLCNonRetryableError(
                        f"CLC {endpoint}: invalid response code={body.get('code') if isinstance(body, dict) else None!r}"
                    )
                return body
            except CLCNonRetryableError as exc:
                last_error = exc
                logger.warning("CLC OCR %s non-retryable failure: %s", endpoint, exc)
                break
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
        run_id: str | None = None,
    ) -> list[OCRRecord]:
        t0 = time.perf_counter()
        image_path = Path(image_path)
        source_bytes = image_path.read_bytes()
        digest = bytes_hash(source_bytes)
        identity = self.build_cache_identity(digest)

        if cache_meta_path is not None and Path(cache_meta_path).is_file():
            saved = read_json(Path(cache_meta_path))
            if self._cache_matches(saved.get("identity", {}), digest) and isinstance(saved.get("response"), dict):
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
                    cache_status="CACHE_HIT",
                    run_id=run_id,
                    processing_time=round(time.perf_counter() - t0, 4),
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
                original_image_sha256=digest,
                run_id=run_id,
                status="API_NOT_CONFIGURED",
                coordinate_space=None,
                extra={
                    "cache_status": "CACHE_MISS",
                    "reason": f"Missing {self.api_key_env}; run offline or import cached/exported CLC results.",
                },
            )
            return [record]

        import requests  # noqa: PLC0415

        session = self._session or requests.Session()
        # Authorization header stays in memory only, never serialized to cache/logs.
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
            elapsed = round(time.perf_counter() - t0, 4)
            if cache_meta_path is not None:
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
                cache_status="CACHE_MISS",
                run_id=run_id,
                processing_time=elapsed,
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
                    original_image_sha256=digest,
                    run_id=run_id,
                    processing_time=round(time.perf_counter() - t0, 4),
                    status="FAILED",
                    coordinate_space=None,
                    extra={"error": str(exc), "cache_status": "CACHE_MISS"},
                )
            ]
        finally:
            if self._session is None:
                session.close()
