"""Điều phối các chế độ chạy, không chứa cấu hình riêng của sách."""
import argparse
import csv
import json
import sys
from pathlib import Path

from ten_file import CAC_BAN, DPI
from .models import Box, validate_assignment
from .workspace import Workspace
from . import pdf_ops


def parser_for(book):
    parser = argparse.ArgumentParser(description=f"Cắt theo tác phẩm: {book.title}")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--prepare", action="store_true", help="Tạo bố cục và sao lưu nguyên bản, không cắt/OCR.")
    actions.add_argument("--info", action="store_true", help="Xem nguồn và phân công, không ghi file.")
    actions.add_argument("--check", action="store_true", help="Kiểm tra file/hash đã lưu.")
    actions.add_argument("--plan", type=Path, help="CSV các vùng đã chọn; mặc định chỉ xem trước.")
    actions.add_argument("--mark-absent", choices=CAC_BAN, help="Ghi rõ một bản văn không có trong nguồn.")
    actions.add_argument("--summary", action="store_true", help="Xem đủ/thiếu bốn bản văn của tác phẩm.")
    parser.add_argument("--source", default=book.sources[0].key, choices=[s.key for s in book.sources])
    parser.add_argument("--work", default=book.first_work, help="Mã tác phẩm, ví dụ bai0131. Giữ cùng mã khi qua trang.")
    parser.add_argument("--kind", choices=CAC_BAN, default="han")
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--page", type=int, help="Số trang trong PDF gốc, bắt đầu từ 1.")
    parser.add_argument("--box", type=float, nargs=4, metavar=("X0", "Y0", "X1", "Y1"), help="Vùng tỷ lệ 0..1, gốc trên-trái.")
    parser.add_argument("--dpi", type=int, default=DPI)
    parser.add_argument("--extract-text", action="store_true", help="Lấy lớp chữ vùng PDF (bước 4 tùy chọn), không OCR.")
    parser.add_argument("--text-file", type=Path, help="Cắt TXT UTF-8 có sẵn theo dòng.")
    parser.add_argument("--lines", type=int, nargs=2, metavar=("DAU", "CUOI"))
    parser.add_argument("--note", default="")
    parser.add_argument("--allow-outside-scope", action="store_true", help="Cho phép lấy ngữ cảnh/mẫu chung ngoài phân công.")
    parser.add_argument("--apply-plan", action="store_true", help="Thực thi CSV đã xem trước.")
    return parser


def run_plan(workspace, path: Path, apply: bool = False):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    requests = []
    for index, row in enumerate(rows, start=2):
        try:
            if row.get("reviewed", "").strip().lower() != "yes":
                raise ValueError("Chỉ chạy dòng đã kiểm tra và đặt reviewed=yes.")
            source = workspace.book.source(row["source"])
            work, kind = row["work"], row["kind"]
            page, version = int(row["page"]), int(row.get("version") or 1)
            allow = row.get("allow_outside", "").strip().lower() == "yes"
            box = Box(*(float(row[key]) for key in ("x0", "y0", "x1", "y1")))
            workspace._validate_variant(work, kind, version)
            validate_assignment(workspace.book, work, source, page, allow)
            if page > pdf_ops.info(source.path)["pages"]:
                raise ValueError("Trang vượt PDF nguồn.")
            requests.append(dict(source_key=source.key, page=page, box=box, work=work, kind=kind,
                                 version=version, dpi=int(row.get("dpi") or DPI),
                                 extract_text=row.get("extract_text", "").strip().lower() == "yes",
                                 note=row.get("note", ""), allow_outside=allow))
        except (KeyError, ValueError) as error:
            raise ValueError(f"CSV dòng {index}: {error}") from error
    if not requests:
        raise ValueError("CSV chưa có vùng nào.")
    print(f"{len(requests)} vùng; thứ tự dòng CSV là thứ tự ghép trong mỗi tác phẩm/bản văn.")
    for request in requests:
        print(request["work"], request["kind"], request["source_key"], request["page"], request["box"].as_list())
    if apply:
        for request in requests:
            result = workspace.save_pdf_region(**request)
            print("Đã có, bỏ qua" if result.get("skipped") else "Đã lưu", result["work"], result["sequence"])
    else:
        print("Chưa ghi file. Thêm --apply-plan sau khi kiểm tra các vùng.")


def run(book, argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = parser_for(book)
    args = parser.parse_args(argv)
    workspace = Workspace(book)
    try:
        if args.info:
            print(book.title, "\n", book.note)
            for source in book.sources:
                print(source.key, source.path, "phạm vi", source.ranges, pdf_ops.info(source.path), source.note)
            return
        if args.prepare:
            sources = workspace.prepare()
            print(f"Đã tạo {workspace.root}\nĐã kiểm tra {len(sources)} bản sao nguồn.")
            return
        if args.check:
            result = workspace.check()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if not result["ok"]:
                raise SystemExit(1)
            return
        if args.summary:
            print(json.dumps(workspace.summary(args.work, args.version), ensure_ascii=False, indent=2))
            return
        if args.mark_absent:
            workspace.mark_absent(args.work, args.mark_absent, args.version, args.note)
            print("Đã ghi nhận bản văn không có, không tạo file rỗng.")
            return
        if args.plan:
            run_plan(workspace, args.plan, args.apply_plan)
            return
        if args.apply_plan:
            parser.error("--apply-plan cần --plan FILE.csv.")
        if args.text_file:
            if not args.lines:
                parser.error("--text-file cần --lines DAU CUOI.")
            result = workspace.save_text_region(args.text_file.resolve(), args.work, args.kind, args.version,
                                                line_start=args.lines[0], line_end=args.lines[1], note=args.note)
        elif args.box:
            if args.page is None:
                parser.error("--box cần --page.")
            result = workspace.save_pdf_region(args.source, args.page, Box(*args.box), args.work, args.kind,
                                               args.version, args.dpi, args.extract_text, args.note, args.allow_outside_scope)
        else:
            from .ui import open_window
            open_window(workspace)
            return
        print("Đã có, bỏ qua" if result.get("skipped") else "Đã lưu", result["work"], result["kind"], result["sequence"])
        print("Sản phẩm:", *result["work_outputs"], sep="\n")
    except (ValueError, FileNotFoundError, FileExistsError, RuntimeError, OSError) as error:
        parser.exit(2, f"Lỗi: {error}\n")
