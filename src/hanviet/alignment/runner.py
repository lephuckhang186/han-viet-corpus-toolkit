"""Protected alignment workflow runner preserving draft/review/export semantics."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
from runpy import run_path

from hanviet.common.io import json_bytes, read_json
from hanviet.exporters.tabular import export_reviewed
from hanviet.segmentation.segmenter import segment
from .backends.clc_aligner import CLCTextMismatch, align_clc, clc_request
from .backends.lab_aligner import run_lab
from .validation.validators import (
    VERSIONS,
    lab_text,
    make_rows,
    phonetic_links,
    public_units,
    unmatched_ids,
    validate_links,
    verify_identity,
)


def clean_book_root(project, book, member, *, output_root: Path | None = None, topic: str | None = None):
    project = Path(project)
    if topic is None:
        topic = run_path(str(project / "ten_file.py"))["MA_DE_TAI"]
    base = Path(output_root) if output_root is not None else (project / "san_pham")
    return base / member / f"{topic}_{book}"


def clean_sources_by_work(book_root, book, member, *, data_root: Path | None = None):
    """Index assembled files and, for LyTran, ordered per-page parts."""
    prefix = f"{book}_{member}_"
    name = re.compile(rf"{re.escape(prefix)}((?:bai|quyen)\d+)_.*\.txt")
    works = {}
    for kind, folder in VERSIONS.items():
        for path in sorted((book_root / "03_text_sach" / folder).glob(f"{prefix}*.txt")):
            match = name.fullmatch(path.name)
            if match and path.is_file():
                works.setdefault(match[1], {}).setdefault(kind, []).append(path)
        if book == "CPO_12":
            base_data = Path(data_root) if data_root is not None else (book_root.parents[2] / "data")
            source = base_data / "LyTran" / "03_text_sach" / folder
            directory_name = re.compile(rf"{re.escape(prefix)}((?:bai|quyen)\d+)_{re.escape(folder.split('/')[-1])}_v\d+")
            for directory in sorted(source.glob(f"{prefix}*")):
                match = directory_name.fullmatch(directory.name)
                if match and directory.is_dir():
                    parts = sorted(directory.glob("phan[0-9]*_pdfp[0-9]*.txt"))
                    if parts:
                        works.setdefault(match[1], {}).setdefault(kind, []).extend(parts)
    return works


def alignment_audit_dir(book_root, member, work, section=None):
    selection = f"{work}_{section}" if section else work
    return book_root / "05_quan_ly" / "dong_hang" / member / selection


def load_work(project, book, work, member, genre, titles, section=None, ranges=None, *, data_root=None, output_root=None):
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

    book_root = clean_book_root(project, book, member, output_root=output_root)
    work_sources = clean_sources_by_work(book_root, book, member, data_root=data_root).get(work, {})
    id_prefix = f"{book}/{work}/{member}"
    if section:
        id_prefix += f"/{section}"
    units, sources = {}, {}
    for kind in VERSIONS:
        paths = work_sources.get(kind, [])
        if len(paths) > 1 and (len({path.parent for path in paths}) != 1 or paths[0].parent.name in {"han", "dich_am", "dich_nghia", "dich_tho"}):
            raise ValueError(f"Có nhiều TXT cho {id_prefix}/{kind}: {paths}")
        if paths:
            if ranges is not None and kind not in ranges:
                raise ValueError(f"Chưa khai báo khoảng dòng tương ứng cho {kind} trong {id_prefix}.")
            data = [path.read_bytes() for path in paths]
            records = []
            for path, content in zip(paths, data):
                try:
                    rel = path.relative_to(project).as_posix()
                except ValueError:
                    rel = path.as_posix()
                records.append({"file": rel, "sha256": hashlib.sha256(content).hexdigest()})
            sources[kind] = records[0] if len(records) == 1 else {"parts": records}
            units[kind] = segment(
                "\f".join(content.decode("utf-8-sig") for content in data),
                kind,
                id_prefix,
                genre,
                titles.get(kind, 0),
                (ranges or {}).get(kind),
                keep_lines=book == "CPO_09" and kind == "han",
            )
        else:
            units[kind] = []
    if not units["han"]:
        raise FileNotFoundError(f"Chưa có TXT Hán sạch: {id_prefix}")
    if not any(units[kind] for kind in ("am", "nghia", "tho")):
        raise ValueError(f"Chưa có phiên bản Việt để dóng: {id_prefix}")
    fingerprint = hashlib.sha256(json_bytes({"sources": sources, "units": units})).hexdigest()
    return book_root, id_prefix, units, sources, fingerprint


def run_alignment(project, book, work, *, member="TV02", genre="poetry", titles=None, section=None, ranges=None, export=False, data_root=None, output_root=None, dict_root=None):
    project = Path(project).resolve()
    titles = titles or {}
    root, work_id, units, sources, fingerprint = load_work(
        project, book, work, member, genre, titles, section, ranges, data_root=data_root, output_root=output_root
    )
    selection = work if section is None else f"{work}_{section}"
    audit = alignment_audit_dir(root, member, work, section)
    audit.mkdir(parents=True, exist_ok=True)
    identity = {"work": work_id, "fingerprint": fingerprint}
    review_path = audit / "review.json"
    han = public_units(units["han"])
    settings = {"genre": genre, "titles": titles, "ranges": ranges}
    report = {**identity, "sources": sources, "units": units, "audit": str(audit), "settings": settings}
    tools_root = (Path(output_root) if output_root else (project / "san_pham")) / member / "05_quan_ly" / "alignment_tools"

    if export:
        if not review_path.is_file():
            raise FileNotFoundError(f"Chưa có bản duyệt: {review_path}")
        review = read_json(review_path)
        verify_identity(review, work_id, fingerprint)
        if review.get("approved") is not True:
            raise ValueError("Duyệt liên kết trong review.json rồi đặt approved=true.")
        draft = read_json(audit / "draft.json")
        verify_identity(draft, work_id, fingerprint)
        rows, files = export_reviewed(
            root / "04_dong_hang" / selection, f"{book}_{selection}", work_id, units, review, draft["lab_diagnostics"]
        )
        return {**report, "status": {"export": f"Đã xuất {len(rows)} hàng đã duyệt."}, "rows": rows, "files": files}

    links = {kind: [] for kind in ("am", "nghia", "tho")}
    diagnostics, status = [], {}
    if units["am"]:
        am_by_id = {u["id"]: u["text"] for u in units["am"]}
        han_by_id = {u["id"]: u["text"] for u in units["han"]}
        links["am"] = phonetic_links(units["han"], units["am"])
        pairs = [
            {
                "ID": link["han_ids"][0],
                "HanNom": lab_text(" ".join(han_by_id[i] for i in link["han_ids"]), "han"),
                "DichAm": lab_text(" ".join(am_by_id[i] for i in link["am_ids"]), "am"),
            }
            for link in links["am"]
        ]
        if pairs:
            resolved_dict = Path(dict_root) if dict_root else (project / "dict")
            dictionaries = (
                resolved_dict / "QuocNgu_SinoNom_TongHop3.csv",
                resolved_dict / "SinoNom_Similar_Dic_v2.csv",
            )
            for path in dictionaries:
                if not path.is_file():
                    raise FileNotFoundError(path)
            results, statistics = run_lab(
                tools_root / "SN-QN-alignment" / "align_texts.py", dictionaries, audit / "lab", pairs
            )
            for pair, result in zip(pairs, results):
                mismatch_count = statistics[pair["ID"]]["hannom_error_count"]
                if mismatch_count or (pair["HanNom"], pair["DichAm"]) != (result["HanNom"], result["DichAm"]):
                    diagnostics.append(
                        {
                            "id": pair["ID"],
                            "han": pair["HanNom"],
                            "am": pair["DichAm"],
                            "mismatch_count": mismatch_count,
                            "suggestion": f'{result["HanNom"]} / {result["DichAm"]}',
                        }
                    )
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
            "instruction": (
                "Ghép câu/khổ thơ đã có với đoạn Hán cùng nghĩa. Trả work, fingerprint và "
                "links gồm han_ids, tho_ids, note. Dùng ID từ danh sách, theo thứ tự. "
                "Bỏ liên kết chưa đủ căn cứ và ghi chú riêng khi cần."
            ),
            "han": han,
            "tho": public_units(units["tho"]),
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
    draft = {
        **report,
        "links": links,
        "rows": rows,
        "unmatched": missing,
        "status": status,
        "meaning_candidates": meaning,
        "meaning_backend": chosen,
        "lab_diagnostics": diagnostics,
    }
    (audit / "draft.json").write_bytes(json_bytes(draft))
    template = {
        **identity,
        "approved": False,
        "links": links,
        "skipped": {i: "" for ids in missing.values() for i in ids},
    }
    (audit / "review_template.json").write_bytes(json_bytes(template))
    return draft
