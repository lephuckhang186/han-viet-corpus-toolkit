"""Prepare per-page Thi Dinh sources and export unreviewed notebook drafts (protected logic)."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path

from hanviet.common.io import json_bytes, write_protected
from hanviet.exporters.tabular import HEADERS, xlsx_bytes
from .backends.clc_aligner import CLC_ALIGNMENT_URL, clc_request, clc_result, clc_span
from .runner import clean_book_root
from .validation.validators import make_rows, unmatched_ids, validate_links


def prepare_sources(project, member, work):
    """Assemble source parts in page order, without overwriting different files."""
    source = Path(project) / "data" / "ThiDinh" / "03_text_sach"
    dest = clean_book_root(Path(project), "CPO_11", member) / "03_text_sach"
    prepared, manifest = {}, []
    for folder, suffix in (("han", ""), ("viet/dich_am", "_dich_am"), ("viet/dich_nghia", "_dich_nghia")):
        name = f"CPO_11_{member}_{work}{suffix}"
        parts = sorted((source / folder / name).glob("phan*.txt"))
        if not parts:
            raise FileNotFoundError(f"Chưa có các phần TXT: {source / folder / name}")
        text = "\f".join(p.read_bytes().decode("utf-8-sig") for p in parts)
        target = dest / folder / f"{name if suffix else name + '_han'}.txt"
        prepared[target] = text.encode("utf-8")
        manifest.append({"target": str(target), "parts": [
            {"file": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in parts]})
    write_protected(prepared)
    return manifest


def export_draft(project, member, work, draft):
    """Export candidate links and retain unmatched units in separate rows."""
    units = draft["units"]
    for source in draft["sources"].values():
        if hashlib.sha256((Path(project) / source["file"]).read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError("TXT nguồn đã thay đổi sau khi tạo bản nháp; chạy lại.")
    links = {kind: list(draft["links"][kind]) for kind in ("am", "nghia", "tho")}
    audit = Path(draft["audit"])
    rejected = []
    response_file = audit / "clc_response.json"
    if not links["nghia"] and response_file.is_file():
        cached = json.loads(response_file.read_text(encoding="utf-8"))
        body = clc_request(units["han"], units["nghia"])
        identity = hashlib.sha256(json.dumps([CLC_ALIGNMENT_URL, body], sort_keys=True).encode("utf-8")).hexdigest()
        if cached.get("request_sha256") == identity:
            next_han = next_vi = 0
            for index, row in enumerate(clc_result(cached.get("response"))):
                try:
                    first_han, last_han = clc_span(row, "han", "han_text", units["han"], next_han)
                    first_vi, last_vi = clc_span(row, "vi", "vietnamese_text", units["nghia"], next_vi)
                    link = {"han_ids": [u["id"] for u in units["han"][first_han:last_han]],
                            "nghia_ids": [u["id"] for u in units["nghia"][first_vi:last_vi]]}
                    score = row.get("score")
                    if type(score) in (float, int) and math.isfinite(score):
                        link["clc_score"] = score
                    links["nghia"].append(link)
                    next_han, next_vi = last_han, last_vi
                except ValueError as error:
                    rejected.append({"index": index, "error": str(error), "response": row,
                                     "details": getattr(error, "details", {})})
    validate_links(links["nghia"], units["han"], units["nghia"], "nghia")
    missing = unmatched_ids(units, links)
    rows = [row["cells"] for row in make_rows(units, links)]
    lookup = {u["id"]: u["text"] for entries in units.values() for u in entries}
    for kind, column in (("han", 0), ("am", 1), ("nghia", 2), ("tho", 3)):
        for uid in missing[kind]:
            row = [""] * 4
            row[column] = lookup[uid]
            rows.append(row)
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")
    writer.writerow(HEADERS)
    writer.writerows(rows)
    folder = clean_book_root(Path(project), "CPO_11", member) / "04_dong_hang" / work
    stem = f"CPO_11_{member}_{work}_ban_nhap"
    files = {folder / f"{stem}.tsv": output.getvalue().encode("utf-8-sig"),
             folder / f"{stem}.xlsx": xlsx_bytes("DONG_HANG", HEADERS, rows),
             folder / f"{stem}_thong_tin.json": json_bytes({
                 "status": "draft_not_reviewed", "source_fingerprint": draft["fingerprint"],
                 "links": links, "unmatched": missing, "rejected_clc": rejected,
                 "note": "Các đơn vị chưa dóng được đặt ở hàng riêng cuối bảng."})}
    write_protected(files)
    return {"files": list(files), "unmatched": missing, "rejected": len(rejected)}
