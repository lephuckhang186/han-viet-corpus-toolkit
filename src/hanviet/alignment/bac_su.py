"""Align the numbered Bac Su TXT collection with the Vietnamese source (protected logic)."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from runpy import run_path

from hanviet.common.io import json_bytes, write_protected
from hanviet.exporters.tabular import HEADERS, xlsx_bytes
from hanviet.segmentation.segmenter import segment
from .backends.clc_aligner import align_clc, clc_result, clc_span
from .validation.validators import validate_links


def exclude_couplets(han_text, viet_text):
    """Mask verified couplet passages while retaining source offsets."""
    exclusions = []

    def mask(text, language, start, end, reason):
        exclusions.append({"language": language, "start": start, "end": end,
                           "reason": reason, "text": text[start:end]})
        return text[:start] + "".join("\n" if c == "\n" else " " for c in text[start:end]) + text[end:]

    for begin, finish, reason in (
        ("圖繪雲臺", "Tăng thất", "Bốn câu đối miếu Phục Ba, gồm Hán, phiên âm và dịch nghĩa"),
        ("氣備四時", "Phía trƣớc có ba", "Câu đối Quốc Tử Giám, gồm Hán, phiên âm và dịch nghĩa"),
    ):
        start = viet_text.find(begin)
        if start < 0:
            raise ValueError(f"Không tìm thấy mốc câu đối Việt: {begin}")
        end = viet_text.find(finish, start)
        if end < 0:
            raise ValueError(f"Không tìm thấy cuối đoạn câu đối Việt: {finish}")
        viet_text = mask(viet_text, "nghia", start, end, reason)
    start = han_text.find("圖給雲")
    if start >= 0:
        end_marker = "漢宝恩𠗆"
        end = han_text.find(end_marker, start)
        if end < 0:
            raise ValueError("Không xác định được cuối câu đối Phục Ba trong Hán.")
        han_text = mask(han_text, "han", start, end + len(end_marker),
                        "Bốn câu đối Phục Ba, kéo qua hai tệp Hán")
    cursor = 0
    found = 0
    for line in han_text.splitlines(keepends=True):
        if "日月鬼神" in line and "教垂萬世" in line:
            han_text = mask(han_text, "han", cursor, cursor + len(line),
                            "Hai vế câu đối Quốc Tử Giám trong OCR Hán")
            found += 1
        cursor += len(line)
    if found != 1:
        raise ValueError("Cần xác nhận lại vị trí câu đối Quốc Tử Giám trong Hán.")
    return han_text, viet_text, exclusions


def run(project, first=150, last=202, han_lines=None, viet_lines=None, preview=False, skip_couplets=True):
    project = Path(project)
    if not 150 <= first <= last <= 202:
        raise ValueError("Chọn phạm vi tệp từ 150 đến 202.")
    source = project / "data/BacSu/03_text_sach"
    files = [source / "han" / f"CP0_09_TV04_bai{page}.txt" for page in range(first, last + 1)]
    viet = source / "viet/viet.txt"
    texts = [p.read_bytes() for p in [*files, viet]]
    sources = [{"file": p.relative_to(project).as_posix(), "sha256": hashlib.sha256(raw).hexdigest()}
               for p, raw in zip([*files, viet], texts)]
    han_text = "\f".join(raw.decode("utf-8-sig") for raw in texts[:-1])
    viet_text = texts[-1].decode("utf-8-sig")
    exclusions = []
    if skip_couplets:
        han_text, viet_text, exclusions = exclude_couplets(han_text, viet_text)
    han = segment(han_text, "han", "CPO_09/TV04", "prose", line_range=han_lines, keep_lines=True)
    vi = segment(viet_text, "nghia", "CPO_09/TV04", "prose", line_range=viet_lines)
    if preview:
        for kind, units in (("Hán", han), ("Việt", vi)):
            print(kind, len(units), "đơn vị")
            for unit in units[:20]:
                print(unit["id"], unit["text"])
        return {"han": han, "nghia": vi, "excluded": exclusions}
    identity = hashlib.sha256(json_bytes({"sources": sources, "han_lines": han_lines,
                                         "viet_lines": viet_lines, "excluded": exclusions})).hexdigest()
    topic = run_path(str(project / "ten_file.py"))["MA_DE_TAI"]
    folder = project / "san_pham/TV04" / f"{topic}_CPO_09" / "04_dong_hang" / f"trang{first}-{last}_{identity[:12]}"
    folder.mkdir(parents=True, exist_ok=True)
    cache = folder / "clc_response.json"
    status, links, rejected = "", [], []
    try:
        links = align_clc(han, vi, response_path=cache)
    except (OSError, RuntimeError, ValueError, ImportError) as error:
        status = str(error)
        if cache.is_file():
            saved = json.loads(cache.read_text(encoding="utf-8"))
            next_han = next_vi = 0
            for index, row in enumerate(clc_result(saved["response"])):
                try:
                    a, b = clc_span(row, "han", "han_text", han, next_han)
                    c, d = clc_span(row, "vi", "vietnamese_text", vi, next_vi)
                    link = {"han_ids": [u["id"] for u in han[a:b]],
                            "nghia_ids": [u["id"] for u in vi[c:d]]}
                    score = row.get("score")
                    if type(score) in (int, float) and math.isfinite(score):
                        link["clc_score"] = score
                    links.append(link)
                    next_han, next_vi = b, d
                except ValueError as mismatch:
                    rejected.append({"index": index, "error": str(mismatch), "response": row})
    validate_links(links, han, vi, "nghia")
    lookup = {u["id"]: u["text"] for u in [*han, *vi]}
    used_han = {uid for link in links for uid in link["han_ids"]}
    used_vi = {uid for link in links for uid in link["nghia_ids"]}
    rows = [[" ".join(lookup[uid] for uid in link["han_ids"]), "",
             " ".join(lookup[uid] for uid in link["nghia_ids"]), ""] for link in links]
    missing_han = [u for u in han if u["id"] not in used_han]
    missing_vi = [u for u in vi if u["id"] not in used_vi]
    rows.extend([[u["text"], "", "", ""] for u in missing_han])
    rows.extend([["", "", u["text"], ""] for u in missing_vi])
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter="\t", lineterminator="\n")
    writer.writerow(HEADERS)
    writer.writerows(rows)
    report = {"status": "draft_requires_review", "api_status": status, "sources": sources,
              "excluded": exclusions,
              "units": {"han": han, "nghia": vi}, "links": links, "rejected": rejected,
              "unmatched": {"han": [u["id"] for u in missing_han],
                            "nghia": [u["id"] for u in missing_vi]}}
    write_protected({folder / "bac_su_ban_nhap.tsv": buffer.getvalue().encode("utf-8-sig"),
                     folder / "bac_su_ban_nhap.xlsx": xlsx_bytes("DONG_HANG", HEADERS, rows),
                     folder / "draft.json": json_bytes(report)})
    print("Liên kết đề xuất:", len(links), "| Chưa dóng:", len(missing_han), "Hán,", len(missing_vi), "Việt")
    print("Kết quả:", folder)
    if status:
        print("CLC:", status)
    return report
