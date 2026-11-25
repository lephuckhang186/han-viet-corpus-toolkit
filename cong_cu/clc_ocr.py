"""Run the CLC web OCR API on the Thi Dinh work 24 v03 crops."""

import hashlib
import json
import os
import time
from pathlib import Path
from runpy import run_path

import requests

from .alignment_backends import CLC_USER_AGENT, reserve_clc_request
from .dong_hang import json_bytes, write_protected

BASE = "https://kimhannom.fit.hcmus.edu.vn/api/web/clc-sinonom/"
STEM = "CPO_11_TV04_bai0024_han_v03"
OPTIONS = dict(ocr_id=1, lang_type=1, reading_direction=1, epitaph=0, tag=None)


def run(project):
    project = Path(project)
    token = os.getenv("CLC_OCR_API_KEY", "").strip()
    env_file = project / ".env.clc_ocr"
    if not token and env_file.is_file():
        token = next((line.partition("=")[2].strip() for line in
                      env_file.read_text(encoding="utf-8-sig").splitlines()
                      if line.startswith("CLC_OCR_API_KEY=")), "")
    if not token:
        raise ValueError("Thiếu CLC_OCR_API_KEY trong .env.clc_ocr.")
    images = sorted((project / "data/ThiDinh/01_nguon/han" / STEM).glob("*.png"))
    if len(images) != 20:
        raise ValueError(f"Cần đủ 20 ảnh nguồn v03, tìm thấy {len(images)}.")
    topic = run_path(str(project / "ten_file.py"))["MA_DE_TAI"]
    book = project / "san_pham/TV04" / f"{topic}_CPO_11"
    out = book / "02_ocr_tho/han" / f"{STEM}_clc"
    with requests.Session() as session:
        session.headers.update({"User-Agent": CLC_USER_AGENT, "Authorization": f"Bearer {token}"})

        def post(endpoint, **kwargs):
            reserve_clc_request()
            try:
                response = session.post(BASE + endpoint, timeout=(10, 60), allow_redirects=False, **kwargs)
                if response.status_code != 200:
                    raise ValueError(f"CLC {endpoint}: HTTP {response.status_code}")
                body = response.json()
                if body.get("is_success") is not True or body.get("code") != "000000":
                    raise ValueError(f"CLC {endpoint}: mã {body.get('code')}")
                return body
            finally:
                time.sleep(3)

        for image in images:
            source = image.read_bytes()
            identity = {"sha256": hashlib.sha256(source).hexdigest(), "options": OPTIONS}
            txt = out / f"{image.stem}.txt"
            meta = out / f"{image.stem}.json"
            if meta.is_file():
                saved = json.loads(meta.read_text(encoding="utf-8"))
                if saved["identity"] != identity:
                    raise ValueError(f"Nguồn đã thay đổi: {image.name}")
                result = saved["response"]
            else:
                upload = post("image-upload", files={"image_file": (image.name, source, "image/png")})
                result = post("image-ocr", json={**OPTIONS, "file_name": upload["data"]["file_name"].strip()})
            lines = result["data"]["result_ocr_text"]
            if not isinstance(lines, list) or not lines or not all(isinstance(line, str) for line in lines):
                raise ValueError(f"CLC trả văn bản không hợp lệ: {image.name}")
            write_protected({meta: json_bytes({"identity": identity, "response": result}),
                             txt: "\n".join(lines).encode("utf-8")})
            print(image.name, flush=True)
    return out
