"""Run a notebook cell with an explicit work configuration."""

import re

from .dong_hang import (
    HEADERS, VERSIONS, alignment_audit_dir, clean_book_root, clean_sources_by_work,
    content_line_spans, read_json, run_alignment,
)


def show_alignment(alignment, *, preview=True):
    print("Thư mục duyệt", alignment["audit"])
    for version, status in alignment["status"].items():
        print(version, status, sep=" | ")
    if "unmatched" in alignment:
        print("Số đơn vị chưa ghép", {kind: len(ids) for kind, ids in alignment["unmatched"].items()})
    for file in alignment.get("files", []):
        print(file)
    if preview:
        import pandas as pd
        from IPython.display import display

        display(pd.DataFrame([row["cells"] for row in alignment["rows"][:20]], columns=HEADERS))


def show_sources(book_root, book, member, work, keyword):
    """Print numbered rows using the same numbering as alignment ranges."""
    sources = clean_sources_by_work(book_root, book, member).get(work, {})
    if not sources:
        raise FileNotFoundError(f"Chưa có TXT sạch cho {book}/{work}/{member}.")
    query = keyword.strip().casefold()
    for kind, label in zip(VERSIONS, HEADERS):
        for path in sources.get(kind, []):
            text = path.read_bytes().decode("utf-8-sig")
            spans = content_line_spans(text)
            lines = [(n, text[start:end]) for n, (start, end) in enumerate(spans, 1)
                     if query in text[start:end].casefold()]
            print(f"{label} · {len(lines)}/{len(spans)} dòng", path.name)
            for n, line in lines[:20]:
                print(f"{n:>4}  {line}")


def run_book_cell(project, book, work, *, member="TV02", genre="prose", titles=None,
                  section=None, ranges=None, mode="nhap", keyword="", preview=True):
    if mode not in {"nguon", "nhap", "xuat"}:
        raise ValueError("CHE_DO phải là 'nguon', 'nhap' hoặc 'xuat'.")
    if not (re.fullmatch(r"CPO_\d{2}", book) and re.fullmatch(r"TV\d{2}", member)
            and re.fullmatch(r"(?:bai|quyen)[0-9]+", work)):
        raise ValueError("Mã tác phẩm, thành viên hoặc số bài/quyển không hợp lệ.")
    if section is not None and not re.fullmatch(r"muc[0-9]+", section):
        raise ValueError("Mã mục không hợp lệ.")

    print(f"{book}/{work}/{member}" + (f"/{section}" if section else ""), flush=True)
    if mode == "nguon":
        show_sources(clean_book_root(project, book, member), book, member, work, keyword)
        return

    settings = {"genre": genre, "titles": titles or {}, "ranges": ranges}
    if mode == "xuat":
        book_root = clean_book_root(project, book, member)
        draft_path = alignment_audit_dir(book_root, member, work, section) / "draft.json"
        if not draft_path.is_file():
            raise FileNotFoundError(f"Chạy CHE_DO = 'nhap' trước để tạo {draft_path}.")
        settings.update(read_json(draft_path).get("settings", {}))
    if mode == "nhap" and book == "CPO_09" and not ranges:
        raise ValueError("Thêm cặp khoảng dòng Hán–Việt của quyển và mục vào KHOANG_DONG_THEO_MUC.")

    print("Đang tạo bản nháp…" if mode == "nhap" else "Đang xuất bản đã duyệt…", flush=True)
    alignment = run_alignment(project, book, work, member=member, section=section,
                              export=mode == "xuat", **settings)
    show_alignment(alignment, preview=preview)
    return alignment


def run_book_batch(project, book, selections, *, member="TV02", mode="nhap", keyword=""):
    """Run each configured selection in order using the single-work workflow."""
    labels = ["_".join(filter(None, (item["work"], item.get("section")))) for item in selections]
    if not labels or len(labels) != len(set(labels)):
        raise ValueError("Danh sách chạy hàng loạt phải có ít nhất một bài/mục và mỗi mục chỉ xuất hiện một lần.")
    if mode not in {"nguon", "nhap", "xuat"}:
        raise ValueError("CHE_DO phải là 'nguon', 'nhap' hoặc 'xuat'.")

    results, errors = {}, {}
    for index, (label, selection) in enumerate(zip(labels, selections), 1):
        print(f"\n[{index}/{len(labels)}] {label}", flush=True)
        try:
            results[label] = run_book_cell(project, book, **selection, member=member,
                                           mode=mode, keyword=keyword, preview=False)
        except (OSError, RuntimeError, ValueError) as error:
            errors[label] = str(error)
            print(f"Lỗi | {error}", flush=True)

    print(f"\nĐã chạy {len(results)}/{len(labels)} bài/mục. Lỗi xử lý: {len(errors)}.")
    return {"results": results, "errors": errors}
