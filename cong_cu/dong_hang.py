"""Prepare and review four-version alignments from the per-work clean TXT files."""

import hashlib
import io
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from .alignment_backends import CLCTextMismatch, align_clc, clc_request, run_lab
# from .alignment_backends import align_bert, align_vecalign, load_embedding_model


VERSIONS = {
    "han": "han",
    "am": "viet/dich_am",
    "nghia": "viet/dich_nghia",
    "tho": "viet/dich_tho",
}
HEADERS = ("Hán", "Dịch âm", "Dịch nghĩa", "Dịch thơ")


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def clean_spacing(text):
    return " ".join(text.split())


def content_line_spans(text):
    return [match.span() for match in re.finditer(r"[^\r\n\f]+", text) if match.group().strip()]


def split_prose(text, start, end, kind):
    """Split on sentence punctuation while retaining original TXT offsets."""
    pattern = r"[。！？；]+[」』”’]*" if kind == "han" else r"[.!?…]+[\"”’»)]*(?=\s|$)"
    if kind == "nghia":
        # OCR can glue sentences across a period, for example "kịp.Vậy".
        pattern += r"|(?<=[^\W\d_]{2})\.(?=[^\W\d_])"
    cursor = start
    for mark in re.finditer(pattern, text[start:end]):
        stop = start + mark.end()
        if kind == "nghia" and stop < end and not (text[stop].isspace() or text[stop].isupper()):
            continue
        prefix = text[start + mark.start() - min(mark.start(), 10):stop]
        if kind != "han" and re.search(r"\b(?:TS|GS|PGS|ThS|TP|Q|tr|vd)\.$", prefix, re.I):
            continue
        if text[cursor:stop].strip():
            yield cursor, stop
        cursor = stop
    if text[cursor:end].strip():
        yield cursor, end


def segment(text, kind, id_prefix, genre, titles=0, line_range=None, *, keep_lines=False):
    lines = content_line_spans(text)
    if line_range is not None:
        first, last = line_range
        if not 1 <= first <= last <= len(lines):
            raise ValueError(f"Khoảng dòng {line_range} nằm ngoài file {kind}.")
        lines = lines[first - 1:last]
    if not 0 <= titles < len(lines):
        raise ValueError(f"Số dòng tiêu đề không hợp lệ cho {kind}.")
    lines = lines[titles:]
    start, end = lines[0][0], lines[-1][1]
    # A line of classical Chinese with no sentence marks is only a draft unit.
    use_lines = keep_lines or genre == "poetry" or (kind == "han" and not re.search(r"[。！？；]", text[start:end]))
    spans = lines if use_lines else split_prose(text, start, end, kind)
    units = []
    for index, (start, end) in enumerate(spans, 1):
        start += len(text[start:end]) - len(text[start:end].lstrip())
        units.append({
            "id": f"{id_prefix}/{kind}/{index:04}",
            "text": clean_spacing(text[start:end]),
            "start": start,
            "end": end,
            "part": text.count("\f", 0, start) + 1,
        })
    return units


def clean_book_root(project, book, member):
    from runpy import run_path

    topic = run_path(str(project / "ten_file.py"))["MA_DE_TAI"]
    return project / "san_pham" / member / f"{topic}_{book}"


def clean_sources_by_work(book_root, book, member):
    """Index the per-work TXT files, keeping all hits so duplicates can be reported."""
    prefix = f"{book}_{member}_"
    name = re.compile(rf"{re.escape(prefix)}((?:bai|quyen)\d+)_.*\.txt")
    works = {}
    for kind, folder in VERSIONS.items():
        for path in sorted((book_root / "03_text_sach" / folder).glob(f"{prefix}*.txt")):
            match = name.fullmatch(path.name)
            if match and path.is_file():
                works.setdefault(match[1], {}).setdefault(kind, []).append(path)
    return works


def alignment_audit_dir(book_root, member, work, section=None):
    selection = f"{work}_{section}" if section else work
    return book_root / "05_quan_ly" / "dong_hang" / member / selection


def load_work(project, book, work, member, genre, titles, section=None, ranges=None):
    if not re.fullmatch(r"CPO_\d{2}", book) or not re.fullmatch(r"(?:bai|quyen)\d+", work):
        raise ValueError("Mã sách hoặc bài/quyển không hợp lệ.")
    if not re.fullmatch(r"TV\d{2}", member) or (section and not re.fullmatch(r"muc\d+", section)):
        raise ValueError("Mã thành viên hoặc mục không hợp lệ.")
    if genre not in {"poetry", "prose"}:
        raise ValueError("genre phải là poetry hoặc prose.")
    if bool(section) != bool(ranges):
        raise ValueError("Khi chọn một mục, khai báo cả section và ranges.")
    if book == "CPO_09" and (not section or not {"han", "nghia"} <= ranges.keys()):
        raise ValueError("Bắc Sứ cần mã mục và khoảng dòng Hán/Việt có cùng phạm vi nội dung.")

    book_root = clean_book_root(project, book, member)
    work_sources = clean_sources_by_work(book_root, book, member).get(work, {})
    id_prefix = f"{book}/{work}/{member}"
    if section:
        id_prefix += f"/{section}"
    units, sources = {}, {}
    for kind in VERSIONS:
        paths = work_sources.get(kind, [])
        if len(paths) > 1:
            raise ValueError(f"Có nhiều TXT cho {id_prefix}/{kind}: {paths}")
        if paths:
            if ranges is not None and kind not in ranges:
                raise ValueError(f"Chưa khai báo khoảng dòng tương ứng cho {kind} trong {id_prefix}.")
            data = paths[0].read_bytes()
            sources[kind] = {
                "file": paths[0].relative_to(project).as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            # Bắc Sứ OCR has sporadic punctuation. Keep its Hán lines as draft units.
            units[kind] = segment(data.decode("utf-8-sig"), kind, id_prefix, genre,
                                  titles.get(kind, 0), (ranges or {}).get(kind),
                                  keep_lines=book == "CPO_09" and kind == "han")
        else:
            units[kind] = []
    if not units["han"]:
        raise FileNotFoundError(f"Chưa có TXT Hán sạch: {id_prefix}")
    if not any(units[kind] for kind in ("am", "nghia", "tho")):
        raise ValueError(f"Chưa có phiên bản Việt để dóng: {id_prefix}")
    fingerprint = hashlib.sha256(json_bytes({"sources": sources, "units": units})).hexdigest()
    return book_root, id_prefix, units, sources, fingerprint


def public_units(units):
    return [{"id": item["id"], "text": item["text"]} for item in units]


def lab_text(text, kind):
    """Strip punctuation on the comparison copy, preserving [MASK] and tone marks."""
    chunks = re.split(r"(\[MASK\])", unicodedata.normalize("NFC", text))
    separator = "" if kind == "han" else " "
    for i in range(0, len(chunks), 2):
        chunks[i] = "".join(separator if unicodedata.category(c)[0] in "PS" else c for c in chunks[i])
    return separator.join("".join(chunks).split())


def phonetic_links(han, am):
    """Propose adjacent spans by length before the Lab's character alignment."""
    glyphs = [len(re.sub(r"\[MASK\]", "□", lab_text(u["text"], "han"))) for u in han]
    syllables = [len(lab_text(u["text"], "am").split()) for u in am]
    steps = ((1, 1), (1, 2), (2, 1), (1, 0), (0, 1))
    costs = {(0, 0): 0}
    back = {}
    for i in range(len(han) + 1):
        for j in range(len(am) + 1):
            if (i, j) == (0, 0):
                continue
            candidates = []
            for a, b in steps:
                if i < a or j < b:
                    continue
                size_h, size_a = sum(glyphs[i-a:i]), sum(syllables[j-b:j])
                if a and b and size_h and size_a:
                    cost = abs(size_h - size_a) / max(size_h, size_a) + (0.1 if a != b else 0)
                elif a and b:
                    continue
                else:
                    cost = 0.7
                if (i-a, j-b) in costs:
                    candidates.append((costs[i-a, j-b] + cost, (a, b)))
            costs[i, j], back[i, j] = min(candidates, key=lambda candidate: candidate[0])
    links = []
    i, j = len(han), len(am)
    while i or j:
        a, b = back[i, j]
        if a and b:
            links.append({"han_ids": [u["id"] for u in han[i-a:i]],
                          "am_ids": [u["id"] for u in am[j-b:j]]})
        i, j = i-a, j-b
    return links[::-1]


def indices(ids, lookup):
    if not isinstance(ids, list) or not ids or any(not isinstance(i, str) or i not in lookup for i in ids):
        raise ValueError(f"Danh sách ID không hợp lệ: {ids}")
    values = [lookup[i] for i in ids]
    if values != list(range(values[0], values[0] + len(values))):
        raise ValueError(f"Các ID phải liền nhau và theo đúng thứ tự: {ids}")
    return values


def validate_links(links, han, viet, kind):
    if not isinstance(links, list):
        raise ValueError(f"Danh sách liên kết {kind} không hợp lệ.")
    han_ids = {u["id"]: i for i, u in enumerate(han)}
    viet_ids = {u["id"]: i for i, u in enumerate(viet)}
    previous_han = previous_viet = -1
    for link in links:
        if not isinstance(link, dict):
            raise ValueError(f"Liên kết {kind} phải là một object.")
        h = indices(link.get("han_ids"), han_ids)
        v = indices(link.get(f"{kind}_ids"), viet_ids)
        if h[0] <= previous_han or v[0] <= previous_viet:
            raise ValueError(f"Liên kết {kind} trùng hoặc chéo thứ tự.")
        previous_han, previous_viet = h[-1], v[-1]
    return links


def make_rows(units, links):
    han_position = {u["id"]: i for i, u in enumerate(units["han"])}
    text = {u["id"]: u["text"] for entries in units.values() for u in entries}
    ranges = []
    for kind in ("am", "nghia", "tho"):
        validate_links(links.get(kind, []), units["han"], units[kind], kind)
        for link in links.get(kind, []):
            first, last = (han_position[link["han_ids"][i]] for i in (0, -1))
            ranges.append((first, last, kind, link[f"{kind}_ids"]))
    groups = []
    for first, last, kind, target in sorted(ranges):
        if groups and first <= groups[-1]["end"]:
            group = groups[-1]
            group["end"] = max(group["end"], last)
            group[kind].extend(target)
        else:
            group = dict(start=first, end=last, am=[], nghia=[], tho=[])
            group[kind].extend(target)
            groups.append(group)
    rows = []
    for group in groups:
        ids = [u["id"] for u in units["han"][group["start"]:group["end"] + 1]]
        rows.append({
            "han_ids": ids,
            "cells": [" ".join(text[i] for i in selected)
                      for selected in (ids, group["am"], group["nghia"], group["tho"])],
        })
    return rows


def unmatched_ids(units, links):
    used = {kind: set() for kind in VERSIONS}
    for kind in ("am", "nghia", "tho"):
        for link in links.get(kind, []):
            used["han"].update(link["han_ids"])
            used[kind].update(link[f"{kind}_ids"])
    return {kind: [u["id"] for u in members if u["id"] not in used[kind]]
            for kind, members in units.items()}


def verify_identity(record, work, fingerprint):
    if record.get("work") != work or record.get("fingerprint") != fingerprint:
        raise ValueError("Mã bài hoặc dấu vân tay văn bản không khớp. Lấy lại JSON hiện tại.")


def write_protected(files):
    for path, data in files.items():
        if path.exists() and path.read_bytes() != data:
            raise FileExistsError(f"Đã có bản xuất khác nội dung: {path}")
    for path, data in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(data)


def xlsx_bytes(sheet_name, headers, rows):
    import xlsxwriter

    output = io.BytesIO()
    with xlsxwriter.Workbook(output, {"in_memory": True}) as workbook:
        workbook.set_properties({"created": datetime(2000, 1, 1)})
        sheet = workbook.add_worksheet(sheet_name)
        sheet.freeze_panes(1, 0)
        sheet.set_column(0, len(headers) - 1, 38)
        for row_no, row in enumerate([headers, *rows]):
            for col_no, text in enumerate(row):
                if sheet.write_string(row_no, col_no, text) != 0:
                    raise ValueError(f"Dữ liệu vượt giới hạn Excel ở {sheet_name}, hàng {row_no + 1}, cột {col_no + 1}.")
    return output.getvalue()


def export_reviewed(folder, stem, work, units, review, diagnostics):
    if not isinstance(review.get("links"), dict) or set(review["links"]) != {"am", "nghia", "tho"}:
        raise ValueError("review.json cần đủ ba danh sách liên kết am, nghia và tho.")
    rows = make_rows(units, review["links"])
    if not rows:
        raise ValueError("Bảng duyệt chưa có cặp hợp lệ.")
    missing = unmatched_ids(units, review["links"])
    expected = {unit_id for ids in missing.values() for unit_id in ids}
    skipped = review.get("skipped", {})
    if not isinstance(skipped, dict) or set(skipped) != expected or any(not isinstance(note, str) or not note.strip()
                                        for note in skipped.values()):
        raise ValueError("Ghi lý do ở skipped cho từng ID chưa dóng trong bảng duyệt.")
    cells = [r["cells"] for r in rows]
    lookup = {u["id"]: (kind, u["text"]) for kind, members in units.items() for u in members}
    note_rows = [[work, lookup[i][1] if lookup[i][0] == "han" else "",
                  lookup[i][1] if lookup[i][0] != "han" else "", "MISSING", reason]
                 for i, reason in skipped.items()]
    note_rows.extend([work, entry["han"], entry["am"],
                      f"Lab ghi nhận {entry['mismatch_count']} vị trí chưa khớp", entry["suggestion"]]
                     for entry in diagnostics)
    for kind in ("am", "nghia", "tho"):
        if not units[kind]:
            note_rows.append([work, "", "", "Thiếu phiên bản", f"Nguồn hiện không có bản {kind}."])
        for link in review["links"].get(kind, []):
            if link.get("note"):
                note_rows.append([work, " ".join(lookup[i][1] for i in link["han_ids"]),
                                  " ".join(lookup[i][1] for i in link[f"{kind}_ids"]),
                                  "Ghi chú dóng hàng", clean_spacing(str(link["note"]))])
    files = {
        folder / f"{stem}_parallel.tsv": "".join("\t".join(row) + "\n" for row in cells).encode("utf-8"),
        folder / f"{stem}_parallel.xlsx": xlsx_bytes("DONG_HANG", HEADERS, cells),
        folder / "notes.xlsx": xlsx_bytes("NOTES", ("Tên tác phẩm", "Câu Hán", "Câu Việt", "Lỗi", "Chỉnh sửa"), note_rows),
    }
    write_protected(files)
    return rows, [str(path) for path in files]


def run_alignment(project, book, work, *, member="TV02", genre="poetry", titles=None,
                  section=None, ranges=None, export=False):
    project = Path(project).resolve()
    titles = titles or {}
    root, work_id, units, sources, fingerprint = load_work(
        project, book, work, member, genre, titles, section, ranges)
    selection = work if section is None else f"{work}_{section}"
    audit = alignment_audit_dir(root, member, work, section)
    audit.mkdir(parents=True, exist_ok=True)
    identity = {"work": work_id, "fingerprint": fingerprint}
    review_path = audit / "review.json"
    han = public_units(units["han"])
    settings = {"genre": genre, "titles": titles, "ranges": ranges}
    report = {**identity, "sources": sources, "units": units, "audit": str(audit), "settings": settings}
    tools_root = project / "san_pham" / member / "05_quan_ly" / "alignment_tools"

    if export:
        if not review_path.is_file():
            raise FileNotFoundError(f"Chưa có bản duyệt: {review_path}")
        review = read_json(review_path)
        verify_identity(review, work_id, fingerprint)
        if review.get("approved") is not True:
            raise ValueError("Duyệt liên kết trong review.json rồi đặt approved=true.")
        draft = read_json(audit / "draft.json")
        verify_identity(draft, work_id, fingerprint)
        rows, files = export_reviewed(root / "04_dong_hang" / selection, f"{book}_{selection}",
                                      work_id, units, review, draft["lab_diagnostics"])
        return {**report, "status": {"export": f"Đã xuất {len(rows)} hàng đã duyệt."},
                "rows": rows, "files": files}

    links = {kind: [] for kind in ("am", "nghia", "tho")}
    diagnostics, status = [], {}
    if units["am"]:
        am_by_id = {u["id"]: u["text"] for u in units["am"]}
        han_by_id = {u["id"]: u["text"] for u in units["han"]}
        links["am"] = phonetic_links(units["han"], units["am"])
        pairs = [{"ID": link["han_ids"][0],
                  "HanNom": lab_text(" ".join(han_by_id[i] for i in link["han_ids"]), "han"),
                  "DichAm": lab_text(" ".join(am_by_id[i] for i in link["am_ids"]), "am")}
                 for link in links["am"]]
        if pairs:
            dict_root = project / "dict"
            dictionaries = (dict_root / "QuocNgu_SinoNom_TongHop3.csv", dict_root / "SinoNom_Similar_Dic_v2.csv")
            for path in dictionaries:
                if not path.is_file():
                    raise FileNotFoundError(path)
            results, statistics = run_lab(tools_root / "SN-QN-alignment" / "align_texts.py", dictionaries,
                                          audit / "lab", pairs)
            for pair, result in zip(pairs, results):
                mismatch_count = statistics[pair["ID"]]["hannom_error_count"]
                if mismatch_count or (pair["HanNom"], pair["DichAm"]) != (result["HanNom"], result["DichAm"]):
                    diagnostics.append({"id": pair["ID"], "han": pair["HanNom"], "am": pair["DichAm"],
                                        "mismatch_count": mismatch_count,
                                        "suggestion": f'{result["HanNom"]} / {result["DichAm"]}'})
        status["am"] = f"Lab đã xử lý {len(pairs)} nhóm. Có {len(diagnostics)} nhóm cần xem đề xuất."
    else:
        status["am"] = "Nguồn chưa có bản dịch âm."

    meaning = {}
    chosen = None
    if units["nghia"]:
        nghia = public_units(units["nghia"])
        (audit / "clc_request.json").write_bytes(json_bytes(clc_request(han, nghia)))
        try:
            response_path = audit / "clc_response.json"
            candidate = validate_links(align_clc(han, nghia, response_path=response_path), han, nghia, "nghia")
        except CLCTextMismatch as error:
            mismatch_path = audit / "clc_mismatch.json"
            mismatch_path.write_bytes(json_bytes({**identity, **error.details}))
            status["CLC"] = f"Chưa có kết quả: {error} Xem {mismatch_path.name} trong thư mục duyệt."
        except (ImportError, OSError, RuntimeError, ValueError) as error:
            status["CLC"] = f"Chưa có kết quả: {error}"
        else:
            if candidate:
                meaning["CLC"] = candidate
            status["CLC"] = f"{len(candidate)} nhóm Hán–nghĩa đề xuất."
        if meaning:
            chosen = "CLC"
            links["nghia"] = meaning[chosen]
            status["nghia"] = f"Đề xuất từ {chosen}. Cần duyệt nội dung."
        else:
            status["nghia"] = "Có bản dịch nghĩa, đang chờ dóng."
    else:
        status["nghia"] = "Nguồn chưa có dịch nghĩa. Ô dịch nghĩa để trống."

    if units["tho"]:
        prompt = {
            **identity,
            "instruction": ("Ghép câu/khổ thơ đã có với đoạn Hán cùng nghĩa. Trả work, fingerprint và "
                            "links gồm han_ids, tho_ids, note. Dùng ID từ danh sách, theo thứ tự. "
                            "Bỏ liên kết chưa đủ căn cứ và ghi chú riêng khi cần."),
            "han": han, "tho": public_units(units["tho"]),
        }
        (audit / "poetry_prompt.json").write_bytes(json_bytes(prompt))
        poetry_path = audit / "poetry_result.json"
        if poetry_path.is_file():
            poetry = read_json(poetry_path)
            verify_identity(poetry, work_id, fingerprint)
            links["tho"] = validate_links(poetry.get("links"), units["han"], units["tho"], "tho")
            status["tho"] = f"{len(links['tho'])} nhóm đọc từ {poetry_path.name} trong thư mục duyệt."
        else:
            status["tho"] = "Có prompt theo ID, chờ poetry_result.json."
    else:
        status["tho"] = "Nguồn chưa có dịch thơ."

    rows = make_rows(units, links)
    missing = unmatched_ids(units, links)
    draft = {**report, "links": links, "rows": rows, "unmatched": missing, "status": status,
             "meaning_candidates": meaning, "meaning_backend": chosen, "lab_diagnostics": diagnostics}
    (audit / "draft.json").write_bytes(json_bytes(draft))
    template = {**identity, "approved": False, "links": links,
                "skipped": {i: "" for ids in missing.values() for i in ids}}
    (audit / "review_template.json").write_bytes(json_bytes(template))
    return draft
