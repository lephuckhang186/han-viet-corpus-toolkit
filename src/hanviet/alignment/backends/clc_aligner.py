"""Protected CLC Sentence Alignment adapter (distinct from CLC image-ocr)."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
from threading import Lock
import time

from hanviet.common.io import read_json, write_json
from hanviet.common.paths import resolve_paths

CLC_ALIGNMENT_URL = "https://kimhannom.fit.hcmus.edu.vn/api/web/clc-sinonom/sentence-alignment"
CLC_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"
)
CLC_MIN_DELAY_SECONDS = 3.0
CLC_REQUEST_LIMITS = (
    ("phút", 60, 25),
    ("giờ", 3_600, 50),
    ("ngày", 86_400, 200),
    ("tuần", 604_800, 600),
)


def _default_clc_log() -> Path:
    try:
        return resolve_paths().output_root / "05_quan_ly" / "clc_requests.sqlite3"
    except FileNotFoundError:
        return Path.cwd() / "san_pham" / "05_quan_ly" / "clc_requests.sqlite3"


CLC_REQUEST_LOG = _default_clc_log()

if "_clc_request_lock" not in globals():
    _clc_request_lock = Lock()
    _clc_next_request_at = 0.0


def clc_request(han, nghia):
    return {
        "han": "\n".join(unit["text"] for unit in han),
        "vi": "\n".join(unit["text"] for unit in nghia),
    }


class CLCTextMismatch(ValueError):
    def __init__(self, language, start, end, selected, echoed):
        super().__init__(f"Văn bản CLC trả về không khớp với {language}[{start}:{end}], tính từ 0 và gồm cả hai đầu.")
        self.details = {
            "language": language,
            "start": start,
            "end": end,
            "input_units": selected,
            "response_text": echoed,
        }


def clc_span(row, key, text_field, units, first_available=0):
    start, end = row.get(f"{key}_start"), row.get(f"{key}_end")
    if type(start) is not int or type(end) is not int or not 0 <= start <= end:
        raise ValueError(f"CLC trả về khoảng dòng {key} ngoài phạm vi đầu vào.")
    selected = units[start:end + 1]
    echoed = row.get(text_field)
    target = "".join(echoed.split()) if isinstance(echoed, str) else ""
    if not target:
        raise CLCTextMismatch(key, start, end, selected, echoed)

    texts = ["".join(unit["text"].split()) for unit in units]
    if first_available <= start <= end < len(units) and "".join(texts[start:end + 1]) == target:
        return start, end + 1

    match = None
    for first in range(first_available, len(texts)):
        offset = 0
        for last in range(first, len(texts)):
            if not target.startswith(texts[last], offset):
                break
            offset += len(texts[last])
            if offset == len(target):
                if match is not None:
                    raise CLCTextMismatch(key, start, end, selected, echoed)
                match = first, last + 1
                break
    if match is None:
        raise CLCTextMismatch(key, start, end, selected, echoed)
    return match


def clc_result(payload):
    if not isinstance(payload, dict):
        raise ValueError("CLC trả về JSON sai cấu trúc.")
    code = payload.get("code")
    if payload.get("is_success") is not True or code != "000000":
        if isinstance(code, str) and len(code) == 6 and code.isascii() and code.isdigit():
            raise ValueError(f"CLC trả mã lỗi {code}.")
        raise ValueError("CLC báo lỗi hoặc thiếu mã kết quả.")
    data = payload.get("data")
    result = data.get("result") if isinstance(data, dict) else None
    if not isinstance(result, list):
        raise ValueError("CLC trả về thiếu danh sách data.result.")
    return result


def clc_response(payload, han, nghia):
    links = []
    next_han = next_vi = 0
    for row in clc_result(payload):
        if not isinstance(row, dict):
            raise ValueError("CLC trả về liên kết sai cấu trúc.")
        first_han, next_han = clc_span(row, "han", "han_text", han, next_han)
        first_vi, next_vi = clc_span(row, "vi", "vietnamese_text", nghia, next_vi)
        link = {
            "han_ids": [unit["id"] for unit in han[first_han:next_han]],
            "nghia_ids": [unit["id"] for unit in nghia[first_vi:next_vi]],
        }
        score = row.get("score")
        if type(score) is int or (type(score) is float and math.isfinite(score)):
            link["clc_score"] = score
        links.append(link)
    return links


def reserve_clc_request(log_path: Path | None = None):
    """Check rolling quotas against requests sent from this workspace."""
    db_path = Path(log_path) if log_path is not None else CLC_REQUEST_LOG
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(db_path, timeout=10)) as history:
            history.execute("CREATE TABLE IF NOT EXISTS requests (sent_at REAL NOT NULL)")
            while True:
                with history:
                    history.execute("BEGIN IMMEDIATE")
                    now = time.time()
                    history.execute("DELETE FROM requests WHERE sent_at <= ?", (now - CLC_REQUEST_LIMITS[-1][1],))
                    timestamps = [row[0] for row in history.execute("SELECT sent_at FROM requests ORDER BY sent_at")]
                    reached = []
                    retry_at = now
                    for window, seconds, limit in CLC_REQUEST_LIMITS:
                        if len(timestamps) >= limit and timestamps[-limit] > now - seconds:
                            reached.append(f"{limit} lượt/{window}")
                            retry_at = max(retry_at, timestamps[-limit] + seconds)
                    if reached:
                        raise ValueError(
                            f"Đã đạt quota CLC trong project ({', '.join(reached)}). "
                            f"Thử lại sau ít nhất {math.ceil(retry_at - now)} giây."
                        )
                    wait = timestamps[-1] + CLC_MIN_DELAY_SECONDS - now if timestamps else 0
                    if wait <= 0:
                        history.execute("INSERT INTO requests (sent_at) VALUES (?)", (now,))
                        return
                time.sleep(wait)
    except (OSError, sqlite3.Error):
        raise ValueError("Không cập nhật được bộ đếm request CLC trong project.") from None


def request_clc(body):
    global _clc_next_request_at

    token = os.getenv("CLC_API_KEY", "").strip()
    if not token or any(character.isspace() for character in token):
        raise ValueError("Kernel cần biến môi trường CLC_API_KEY với token Kim Hán Nôm.")

    import requests

    with _clc_request_lock:
        wait = _clc_next_request_at - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        reserve_clc_request()
        try:
            response = requests.post(
                CLC_ALIGNMENT_URL,
                json=body,
                headers={"User-Agent": CLC_USER_AGENT, "Authorization": f"Bearer {token}"},
                timeout=(10, 60),
                allow_redirects=False,
            )
        except requests.RequestException:
            raise ValueError("Không kết nối được với API CLC.") from None
        finally:
            _clc_next_request_at = time.monotonic() + CLC_MIN_DELAY_SECONDS
    if response.status_code != 200:
        raise ValueError(f"CLC trả HTTP {response.status_code}.")
    try:
        return response.json()
    except ValueError:
        raise ValueError("CLC trả về nội dung ngoài định dạng JSON.") from None


def align_clc(han, nghia, *, response_path=None):
    body = clc_request(han, nghia)
    if response_path is None:
        return clc_response(request_clc(body), han, nghia)

    request_id = hashlib.sha256(json.dumps([CLC_ALIGNMENT_URL, body], sort_keys=True).encode("utf-8")).hexdigest()
    try:
        cached = read_json(response_path, None)
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError):
        cached = None
    if isinstance(cached, dict) and cached.get("request_sha256") == request_id:
        return clc_response(cached.get("response"), han, nghia)

    result = clc_result(request_clc(body))
    payload = {"is_success": True, "code": "000000", "data": {"result": result}}
    write_json(response_path, {"request_sha256": request_id, "response": payload})
    return clc_response(payload, han, nghia)
