"""Export approved 4-column parallel TSV/XLSX tables and review notes."""
from __future__ import annotations

from datetime import datetime
import io
from pathlib import Path

from hanviet.common.io import write_protected
from hanviet.segmentation.segmenter import clean_spacing

HEADERS = ("Hán", "Dịch âm", "Dịch nghĩa", "Dịch thơ")


def xlsx_bytes(sheet_name: str, headers, rows) -> bytes:
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


def export_reviewed(folder: Path, stem: str, work: str, units: dict, review: dict, diagnostics: list):
    from hanviet.alignment.validation.validators import make_rows, unmatched_ids

    if not isinstance(review.get("links"), dict) or set(review["links"]) != {"am", "nghia", "tho"}:
        raise ValueError("review.json cần đủ ba danh sách liên kết am, nghia và tho.")
    rows = make_rows(units, review["links"])
    if not rows:
        raise ValueError("Bảng duyệt chưa có cặp hợp lệ.")
    missing = unmatched_ids(units, review["links"])
    expected = {unit_id for ids in missing.values() for unit_id in ids}
    skipped = review.get("skipped", {})
    if not isinstance(skipped, dict) or set(skipped) != expected or any(
        not isinstance(note, str) or not note.strip() for note in skipped.values()
    ):
        raise ValueError("Ghi lý do ở skipped cho từng ID chưa dóng trong bảng duyệt.")
    cells = [r["cells"] for r in rows]
    lookup = {u["id"]: (kind, u["text"]) for kind, members in units.items() for u in members}
    note_rows = [
        [
            work,
            lookup[i][1] if lookup[i][0] == "han" else "",
            lookup[i][1] if lookup[i][0] != "han" else "",
            "MISSING",
            reason,
        ]
        for i, reason in skipped.items()
    ]
    note_rows.extend(
        [
            work,
            entry["han"],
            entry["am"],
            f"Lab ghi nhận {entry['mismatch_count']} vị trí chưa khớp",
            entry["suggestion"],
        ]
        for entry in diagnostics
    )
    for kind in ("am", "nghia", "tho"):
        if not units[kind]:
            note_rows.append([work, "", "", "Thiếu phiên bản", f"Nguồn hiện không có bản {kind}."])
        for link in review["links"].get(kind, []):
            if link.get("note"):
                note_rows.append(
                    [
                        work,
                        " ".join(lookup[i][1] for i in link["han_ids"]),
                        " ".join(lookup[i][1] for i in link[f"{kind}_ids"]),
                        "Ghi chú dóng hàng",
                        clean_spacing(str(link["note"])),
                    ]
                )
    files = {
        folder / f"{stem}_parallel.tsv": "".join("\t".join(row) + "\n" for row in cells).encode("utf-8"),
        folder / f"{stem}_parallel.xlsx": xlsx_bytes("DONG_HANG", HEADERS, cells),
        folder / "notes.xlsx": xlsx_bytes("NOTES", ("Tên tác phẩm", "Câu Hán", "Câu Việt", "Lỗi", "Chỉnh sửa"), note_rows),
    }
    write_protected(files)
    return rows, [str(path) for path in files]
