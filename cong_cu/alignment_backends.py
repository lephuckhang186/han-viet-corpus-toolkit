"""Adapters for the Lab script, CLC and the local sentence aligners."""

import csv
import hashlib
import json
import math
import os
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from functools import lru_cache, partial
from pathlib import Path
from threading import Lock
from unittest.mock import patch
from urllib.request import urlopen

from .storage import read_json, write_json


LAB_REVISION = "57d4ff99d410ece36914f4d046450ba3be36232a"
LAB_SCRIPT_URL = (
    f"https://raw.githubusercontent.com/VongHaiYen11/SN-QN-alignment/{LAB_REVISION}/align_texts.py"
)
LAB_SCRIPT_SHA256 = "43dad2b97b4b75c3caed3ae9d367e3b6b20114734d3a45ff3b6f462253e97c3d"
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
CLC_REQUEST_LOG = Path(__file__).resolve().parents[1] / "san_pham" / "05_quan_ly" / "clc_requests.sqlite3"
# Keep the current kernel's cooldown and lock when a notebook reloads this module.
if "_clc_request_lock" not in globals():
    _clc_request_lock = Lock()
    _clc_next_request_at = 0.0

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
EMBEDDING_ONNX_FILE = "onnx/model_quint8_avx2.onnx"
EMBEDDING_FILES = (
    "config.json", "config_sentence_transformers.json", "modules.json", "sentence_bert_config.json",
    "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "1_Pooling/config.json",
    EMBEDDING_ONNX_FILE,
)
MAX_ALIGNMENT_SIZE = 5

def lab_script(path):
    path = Path(path)
    if not path.is_file():
        with urlopen(LAB_SCRIPT_URL, timeout=20) as response:
            code = response.read()
        if hashlib.sha256(code).hexdigest() != LAB_SCRIPT_SHA256:
            raise ValueError("Hash của code Lab tải về không khớp phiên bản đã chốt.")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(code)
    if hashlib.sha256(path.read_bytes()).hexdigest() != LAB_SCRIPT_SHA256:
        raise ValueError(f"Code Lab đã thay đổi hoặc không đúng phiên bản: {path}")
    return path.resolve()


def run_lab(script_path, dictionaries, folder, pairs):
    """Run the original CLI. Return the Lab's proposed changes by pair ID."""
    import yaml

    script = lab_script(script_path)
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    input_file = folder / "input.csv"
    config_file = folder / "config.yaml"
    result_file = folder / "lab.tsv"
    with input_file.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["ID", "HanNom", "DichAm"])
        writer.writeheader()
        writer.writerows(pairs)
    config = {
        "dataset": {"name": folder.parent.name, "input_file": str(input_file),
                    "columns": {"encoding": "utf-8-sig", "id_column": "ID",
                                "sinonom_column": "HanNom", "quocngu_column": "DichAm",
                                "fallback_column": None}},
        "dictionary": {"translation_dict": str(dictionaries[0].resolve()),
                       "similarity_dict": str(dictionaries[1].resolve()), "encoding": "utf-8-sig"},
        "alignment": {"damaged_tokens": ["[MASK]"],
                      "costs": {"match": 0, "mismatch": 1, "insertion": 1, "deletion": 1}},
        "output": {"directory": str(folder), "filename": result_file.name,
                   "statistics_filename": "statistic.json"},
        "processing": {"verbose": False, "show_progress": False},
        "quick_test": False,
    }
    config_file.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    try:
        result = subprocess.run([sys.executable, str(script), str(config_file)], cwd=folder,
                                capture_output=True, encoding="utf-8", errors="replace",
                                env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=180)
    except subprocess.TimeoutExpired as error:
        raise ValueError("Code Lab vượt quá thời gian chạy cho bài hiện tại.") from error
    if result.returncode or not result_file.is_file():
        raise ValueError(f"Code Lab chưa tạo kết quả: {(result.stderr or result.stdout)[-1200:]}")
    with result_file.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if [row["ID"] for row in rows] != [pair["ID"] for pair in pairs]:
        raise ValueError("Kết quả code Lab không khớp danh sách ID đầu vào.")
    statistics = json.loads((folder / "statistic.json").read_text(encoding="utf-8"))
    return rows, {row["ID"]: row for row in statistics["rows"]}


def clc_request(han, nghia):
    return {"han": "\n".join(unit["text"] for unit in han),
            "vi": "\n".join(unit["text"] for unit in nghia)}


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

    # CLC can split a line again. Recover only a unique, exact span of whole source units.
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
        link = {"han_ids": [unit["id"] for unit in han[first_han:next_han]],
                "nghia_ids": [unit["id"] for unit in nghia[first_vi:next_vi]]}
        score = row.get("score")
        if type(score) is int or (type(score) is float and math.isfinite(score)):
            link["clc_score"] = score
        links.append(link)
    return links


def reserve_clc_request():
    """Check the rolling quotas against requests sent from this workspace."""
    try:
        CLC_REQUEST_LOG.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(CLC_REQUEST_LOG, timeout=10)) as history:
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
                        raise ValueError(f"Đã đạt quota CLC trong project ({', '.join(reached)}). "
                                         f"Thử lại sau ít nhất {math.ceil(retry_at - now)} giây.")
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
                CLC_ALIGNMENT_URL, json=body,
                headers={"User-Agent": CLC_USER_AGENT, "Authorization": f"Bearer {token}"},
                timeout=(10, 60), allow_redirects=False,
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


@lru_cache(maxsize=1)
def load_embedding_model(cache_dir):
    for name in ("bertalign", "vecalign"):
        checkout = cache_dir.parent / name
        if checkout.is_dir() and str(checkout) not in sys.path:
            sys.path.append(str(checkout))

    from huggingface_hub import snapshot_download
    from huggingface_hub.errors import LocalEntryNotFoundError
    from sentence_transformers import SentenceTransformer

    options = {"revision": EMBEDDING_REVISION, "cache_dir": cache_dir, "token": False}
    try:
        snapshot = Path(snapshot_download(EMBEDDING_MODEL, local_files_only=True, **options))
    except LocalEntryNotFoundError:
        snapshot = None
    if snapshot is None or not all((snapshot / file).is_file() for file in EMBEDDING_FILES):
        snapshot = Path(snapshot_download(EMBEDDING_MODEL, allow_patterns=EMBEDDING_FILES, **options))
    return SentenceTransformer(
        str(snapshot), device="cpu", backend="onnx", local_files_only=True, token=False,
        model_kwargs={"file_name": EMBEDDING_ONNX_FILE, "provider": "CPUExecutionProvider", "export": False},
    )


def links_from_indices(han, nghia, alignments):
    links = []
    for source, target in alignments:
        if any(not 0 <= i < len(han) for i in source) or any(not 0 <= i < len(nghia) for i in target):
            raise ValueError("Model trả về vị trí ngoài danh sách đơn vị đầu vào.")
        if len(source) and len(target):
            links.append({"han_ids": [han[i]["id"] for i in source],
                          "nghia_ids": [nghia[i]["id"] for i in target]})
    return links


def align_bert(han, nghia, encoder):
    """Use the upstream two-pass aligner with presegmented text and local language labels."""
    # Inject the shared encoder so upstream's eager import does not load a second model.
    with patch("sentence_transformers.SentenceTransformer", return_value=encoder):
        from bertalign import aligner

    src = "\n".join(item["text"] for item in han)
    dst = "\n".join(item["text"] for item in nghia)
    encode = partial(encoder.encode, normalize_embeddings=True, show_progress_bar=False)
    with patch.object(aligner, "detect_lang", side_effect=["zh", "vi"]), \
            patch.dict(aligner.LANG.ISO, {"zh": "Chinese", "vi": "Vietnamese"}), \
            patch.object(encoder, "encode", encode), \
            patch.object(aligner.model, "model", encoder), \
            patch.object(aligner.model, "model_name", EMBEDDING_MODEL):
        model = aligner.Bertalign(src, dst, is_split=True, max_align=MAX_ALIGNMENT_SIZE,
                                  top_k=min(3, len(nghia)))
        model.align_sents()
    return links_from_indices(han, nghia, model.result)


def vecalign_embeddings(units, encoder, dp_utils):
    import numpy as np

    lines = [item["text"] for item in units]
    overlap_count = MAX_ALIGNMENT_SIZE - 1
    overlaps = list(dict.fromkeys(dp_utils.yield_overlaps(lines, overlap_count)))
    values = encoder.encode(overlaps, normalize_embeddings=True, show_progress_bar=False)
    embeddings = np.ascontiguousarray(values, dtype=np.float32)
    positions = {line: i for i, line in enumerate(overlaps)}
    return dp_utils.make_doc_embedding(positions, embeddings, lines, overlap_count)


def align_vecalign(han, nghia, encoder):
    """Run upstream VecAlign on the same embedding space as BERTAlign."""
    import numpy as np
    from vecalign import dp_utils

    source = vecalign_embeddings(han, encoder, dp_utils)
    target = vecalign_embeddings(nghia, encoder, dp_utils)
    previous_state = np.random.get_state()
    try:
        np.random.seed(42)
        stack = dp_utils.vecalign(
            vecs0=source, vecs1=target, final_alignment_types=dp_utils.make_alignment_types(MAX_ALIGNMENT_SIZE),
            del_percentile_frac=0.2, width_over2=8, max_size_full_dp=300,
            costs_sample_size=20_000, num_samps_for_norm=100,
        )
    finally:
        np.random.set_state(previous_state)
    return links_from_indices(han, nghia, stack[0]["final_alignments"])
