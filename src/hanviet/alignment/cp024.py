"""CP024 source inventory, reproducible section plans, and notebook workflow."""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import io
from pathlib import Path
import re

from hanviet.common.io import json_bytes, read_json, sha256, write_json, write_protected
from hanviet.common.paths import resolve_paths
from hanviet.exporters.tabular import HEADERS, xlsx_bytes
from hanviet.segmentation.segmenter import clean_spacing, content_line_spans
from .runner import alignment_audit_dir, clean_book_root, load_work, run_alignment
from .validation.validators import make_rows, unmatched_ids, verify_identity


def discover_sources(text_root):
    root = Path(text_root)
    files, errors = {}, []
    for kind, folder in (("han", "han"), ("viet", "viet")):
        directory = root / folder
        if not directory.is_dir():
            errors.append(f"Không tìm thấy thư mục: {directory}")
            continue
        for path in sorted(directory.iterdir()):
            if not path.is_file() or path.suffix.lower() != ".txt":
                continue
            match = re.fullmatch(rf"([0-9]+)\.{kind}\.txt", path.name)
            if not match:
                errors.append(f"Tên TXT không hợp lệ: {path}")
                continue
            number = int(match[1])
            files.setdefault(number, {}).setdefault(kind, []).append(path)
    result = []
    for number, pair in sorted(files.items()):
        row = {"file_id": number, "work": f"bai{number:04d}"}
        problems = []
        for kind in ("han", "viet"):
            paths = pair.get(kind, [])
            row[f"{kind}_path"] = paths[0] if len(paths) == 1 else None
            row[f"{kind}_name"] = ", ".join(p.name for p in paths)
            row[f"{kind}_lines"] = 0
            if len(paths) != 1:
                problems.append(f"{kind}: {'thiếu' if not paths else 'trùng mã'}")
            else:
                try:
                    content = paths[0].read_bytes().decode("utf-8-sig")
                    row[f"{kind}_lines"] = len(content_line_spans(content))
                    if not row[f"{kind}_lines"]:
                        problems.append(f"{kind}: rỗng")
                except UnicodeError:
                    problems.append(f"{kind}: không phải UTF-8")
        row["status"] = "; ".join(problems) or "ok"
        result.append(row)
    return result, errors


def sections(han_count, viet_count, size=10, manual=None, whole=False):
    if not han_count or not viet_count:
        raise ValueError("Hai bản phải có dòng nội dung.")
    if whole and manual is not None:
        raise ValueError("Không dùng đồng thời toàn file và khoảng thủ công.")
    if whole:
        manual = {1: {"han": [1, han_count], "nghia": [1, viet_count]}}
    elif manual is None:
        if type(size) is not int or size < 1:
            raise ValueError("SO_DONG_MOI_MUC phải là số nguyên dương.")
        if han_count != viet_count:
            raise ValueError("Số dòng hai bản khác nhau; khai báo khoảng thủ công hoặc chọn toàn file.")
        manual = {i + 1: {"han": [start, min(start + size - 1, han_count)],
                          "nghia": [start, min(start + size - 1, viet_count)]}
                  for i, start in enumerate(range(1, han_count + 1, size))}
    result, next_line = [], {"han": 1, "nghia": 1}
    if not manual or any(type(n) is not int or n < 1 for n in manual):
        raise ValueError("Số mục phải là số nguyên dương.")
    for number in sorted(manual):
        ranges = manual[number]
        if not isinstance(ranges, dict) or set(ranges) != {"han", "nghia"}:
            raise ValueError("Mỗi mục cần khoảng han và nghia.")
        for kind, limit in (("han", han_count), ("nghia", viet_count)):
            pair = ranges[kind]
            if (not isinstance(pair, (tuple, list)) or len(pair) != 2
                or any(type(v) is not int for v in pair)
                or pair[0] != next_line[kind] or not pair[0] <= pair[1] <= limit):
                raise ValueError(f"Khoảng {kind} phải liên tục, đúng thứ tự, không chồng lấn và nằm trong nguồn.")
            next_line[kind] = pair[1] + 1
        result.append({"section": f"muc{number:04d}", "ranges": {k: list(ranges[k]) for k in ("han", "nghia")}})
    if next_line != {"han": han_count + 1, "nghia": viet_count + 1}:
        raise ValueError("Khoảng mục chưa bao phủ toàn bộ dòng nguồn.")
    return result


def quality(draft):
    links = draft["links"]["nghia"]
    units = draft["units"]
    dist = Counter(("1" if len(link["han_ids"]) == 1 else "N") + "-" +
                   ("1" if len(link["nghia_ids"]) == 1 else "N") for link in links)
    missing = draft["unmatched"]
    counts = {k: len(units[k]) for k in ("han", "nghia")}
    matched = {k: counts[k] - len(missing[k]) for k in counts}
    return {"units": counts, "groups": len(links), "types": {k: dist[k] for k in ("1-1", "N-1", "1-N", "N-N")},
            "matched": matched, "unmatched": {k: missing[k] for k in counts},
            "coverage": {k: matched[k] / counts[k] if counts[k] else 0 for k in counts},
            "single_viet_ratio": sum(len(x["nghia_ids"]) == 1 for x in links) / len(links) if links else 0,
            "multi_viet": [x for x in links if len(x["nghia_ids"]) > 1],
            "scores": [x.get("clc_score") for x in links if "clc_score" in x]}


def clc_line_units(path, kind, line_range, work_id):
    """Represent selected source lines for the CLC request."""
    text = Path(path).read_bytes().decode("utf-8-sig")
    spans = content_line_spans(text)
    first, last = line_range
    selected = spans[first - 1:last]
    lines = []
    for number, (start, end) in enumerate(selected, first):
        line_id = f"{work_id}/{kind}/source_line{number:04d}"
        lines.append({"id": line_id, "text": clean_spacing(text[start:end])})
    return lines


def export_draft_preview(audit, label, draft, units, work_id, fingerprint):
    """Write unapproved alignment proposals separately from approved exports."""
    verify_identity(draft, work_id, fingerprint)
    links = draft["links"]
    rows = [row["cells"] for row in make_rows(units, links)]
    missing = unmatched_ids(units, links)
    lookup = {unit["id"]: unit["text"] for group in units.values() for unit in group}
    for kind, column in (("han", 0), ("am", 1), ("nghia", 2), ("tho", 3)):
        for unit_id in missing[kind]:
            row = [""] * len(HEADERS)
            row[column] = lookup[unit_id]
            rows.append(row)
    if not rows:
        raise ValueError("Không có dữ liệu nháp để xuất.")
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")
    writer.writerow(HEADERS)
    writer.writerows(rows)
    folder = Path(audit) / "ban_nhap"
    stem = f"CP024_{label}_ban_nhap"
    files = {
        folder / f"{stem}.tsv": output.getvalue().encode("utf-8-sig"),
        folder / f"{stem}.xlsx": xlsx_bytes("DONG_HANG", HEADERS, rows),
    }
    write_protected(files)
    print("Bảng nháp chưa duyệt:", *(str(path) for path in files), sep="\n")
    if any(missing.values()):
        print("Đơn vị chưa dóng được đặt riêng ở cuối bảng:", {k: len(v) for k, v in missing.items()})
    return list(files)


def aggregate_work_json(project, file_number, *, member="TV04", data_root=None, output_root=None):
    """Create an immutable review bundle containing every JSON from each planned section."""
    if type(file_number) is not int or file_number < 0 or not re.fullmatch(r"TV\d{2}", member):
        raise ValueError("Mã file hoặc thành viên không hợp lệ.")
    paths = resolve_paths(user_root=project, data_root=data_root, output_root=output_root)
    book_root = clean_book_root(paths.root, "CP024", member, output_root=paths.output_root)
    work = f"bai{file_number:04d}"
    work_dir = alignment_audit_dir(book_root, member, work)
    plan_path = work_dir / "alignment_plan.json"
    plan = read_json(plan_path)
    if (plan.get("corpus"), plan.get("work"), plan.get("member")) != ("CP024", work, member):
        raise ValueError("Định danh kế hoạch không khớp file hoặc thành viên.")
    entries = plan.get("sections")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Kế hoạch không có mục.")
    section_names = [entry.get("section") for entry in entries]
    if (any(not isinstance(name, str) or not re.fullmatch(r"muc\d+", name) for name in section_names)
        or len(set(section_names)) != len(section_names)):
        raise ValueError("Danh sách mục trong kế hoạch không hợp lệ hoặc bị trùng.")
    selected = sorted(entries, key=lambda entry: int(entry["section"][3:]))
    bundle_sections = []
    for entry in selected:
        section = entry["section"]
        audit = alignment_audit_dir(book_root, member, work, section)
        draft = read_json(audit / "draft.json")
        _, work_id, units, _, fingerprint = load_work(paths.root, "CP024", work, member, plan["genre"], {},
                                                     section, entry["ranges"], data_root=paths.data_root,
                                                     output_root=paths.output_root)
        verify_identity(draft, work_id, fingerprint)
        if not draft.get("links", {}).get("nghia"):
            raise ValueError(f"{work}/{section} chưa có nháp CLC hợp lệ.")
        make_rows(units, draft["links"])
        json_files = {path.name: read_json(path) for path in sorted(audit.glob("*.json")) if path.is_file()}
        bundle_sections.append({"section": section, "ranges": entry["ranges"], "files": json_files})
    payload = {
        "format": "cp024_section_review_bundle_v1",
        "corpus": "CP024", "work": work, "member": member,
        "status": "TONG_HOP_DE_REVIEW_CHUA_PHE_DUYET",
        "note": ("Mỗi mục giữ JSON gốc; clc_mismatch.json có thể là lỗi lịch sử trước khi tạo nháp thành công. "
                 "File tổng hợp chỉ để xem, không tự cập nhật hoặc phê duyệt review.json của từng mục."),
        "plan": plan, "section_count": len(bundle_sections), "sections": bundle_sections,
    }
    content = json_bytes(payload)
    digest = hashlib.sha256(content).hexdigest()[:12]
    path = work_dir / f"CP024_{work}_review_tong_hop_{digest}.json"
    write_protected({path: content})
    return path


def align_meaning_dp(han, viet):
    """Propose monotonic links using relative text length, with no external service."""
    from math import log

    sizes = [[0] for _ in range(2)]
    for prefix, units in zip(sizes, (han, viet)):
        for unit in units:
            prefix.append(prefix[-1] + max(1, sum(c.isalnum() for c in unit["text"])))
    h, v = sizes
    ratio = v[-1] / h[-1]
    states = {(0, 0): (0, 0, 0)}
    for i in range(len(h)):
        for j in range(len(v)):
            if (i, j) not in states:
                continue
            for a, b in ((1, 1), (2, 1), (1, 2), (3, 1), (1, 3), (2, 2), (1, 0), (0, 1)):
                x, y = i + a, j + b
                if x >= len(h) or y >= len(v):
                    continue
                penalty = abs(log((v[y] - v[j]) / ((h[x] - h[i]) * ratio))) + .45 * (a + b - 2) if a and b else 1.5
                cost = states[i, j][0] + penalty
                if (x, y) not in states or cost < states[x, y][0]:
                    states[x, y] = (cost, i, j)
    links = []
    x, y = len(han), len(viet)
    while x or y:
        _, i, j = states[x, y]
        if x > i and y > j:
            links.append({"han_ids": [u["id"] for u in han[i:x]], "nghia_ids": [u["id"] for u in viet[j:y]]})
        x, y = i, j
    return links[::-1]


def run_cp024(project, *, member="TV04", mode="nguon", batch=False, file_number=5, file_numbers=(),
              genre="prose", section_number=None, lines_per_section=10, keyword="", confirmed=False,
              whole_files=(), manual_ranges=None, data_root=None, output_root=None, continue_on_error=False,
              section_previews=True, method="clc"):
    if method not in {"clc", "dp"}:
        raise ValueError("PHUONG_PHAP phải là clc hoặc dp.")
    if mode not in {"nguon", "nhap", "xuat"} or genre != "prose" or not re.fullmatch(r"TV\d{2}", member):
        raise ValueError("Chế độ, thể loại hoặc mã thành viên không hợp lệ.")
    paths = resolve_paths(user_root=project, data_root=data_root, output_root=output_root)
    source_root = paths.data_root / "CP024" / "03_text_sach"
    output = clean_book_root(paths.root, "CP024", member, output_root=paths.output_root)
    inventory, errors = discover_sources(source_root)
    print("Nguồn:", source_root, "\nĐầu ra:", output)
    for row in inventory:
        print({k: row[k] for k in ("file_id", "work", "han_name", "viet_name", "han_lines", "viet_lines", "status")})
    if errors:
        raise ValueError("; ".join(errors))
    selected = list(file_numbers) if batch and file_numbers else ([r["file_id"] for r in inventory] if batch else [file_number])
    if not selected or any(type(n) is not int or n < 0 for n in selected) or len(set(selected)) != len(selected):
        raise ValueError("Danh sách file rỗng, trùng hoặc không hợp lệ.")
    if section_number is not None and (type(section_number) is not int or section_number < 1):
        raise ValueError("SO_MUC phải là None hoặc số nguyên dương.")
    index = {r["file_id"]: r for r in inventory}
    results, failures = {}, {}
    for number in sorted(selected):
        try:
            if number not in index or index[number]["status"] != "ok":
                raise ValueError(f"File {number}: " + (index[number]["status"] if number in index else "không tồn tại"))
            row = index[number]
            work = row["work"]
            # Keep full-file plans and audits independent of existing section drafts.
            full_file_mode = whole_files is None
            plan_name = "alignment_plan_toan_file.json" if full_file_mode else "alignment_plan.json"
            plan_path = alignment_audit_dir(output, member, work) / plan_name
            sources = {k: {"path": str(row[f"{k}_path"].resolve()), "sha256": sha256(row[f"{k}_path"])} for k in ("han", "viet")}
            if mode == "xuat":
                plan = read_json(plan_path)
                if (plan.get("corpus"), plan.get("work"), plan.get("member"), plan.get("sources")) != ("CP024", work, member, sources):
                    raise ValueError("Nguồn hoặc định danh không khớp kế hoạch đã lưu.")
            else:
                planned = sections(row["han_lines"], row["viet_lines"], lines_per_section,
                                   (manual_ranges or {}).get(number), full_file_mode or number in whole_files)
                if full_file_mode:
                    planned[0]["section"] = "muc0000"
                plan = {"corpus": "CP024", "work": work, "member": member, "sources": sources,
                        "genre": genre, "sections": planned}
                if plan_path.exists() and read_json(plan_path) != plan:
                    raise ValueError("Kế hoạch hoặc nguồn đã thay đổi. Lưu trữ an toàn toàn bộ kế hoạch, draft và review cũ trước khi tạo lại.")
            print(work, "kế hoạch:", plan["sections"])
            chosen = [s for s in plan["sections"] if section_number is None or s["section"] == f"muc{section_number:04d}"]
            if not chosen:
                raise ValueError(f"Không có mục {section_number} trong {work}.")
            if mode == "nhap":
                if not confirmed:
                    raise ValueError("Xem trước và xác nhận ranh giới trước khi gọi CLC.")
                write_protected({plan_path: json_bytes(plan)})
            for item in chosen:
                section, ranges = item["section"], item["ranges"]
                label = f"{work}_{section}"
                _, work_id, units, _, fingerprint = load_work(paths.root, "CP024", work, member, plan["genre"], {}, section, ranges,
                                                         data_root=paths.data_root, output_root=paths.output_root)
                if mode == "nguon":
                    for kind in ("han", "viet"):
                        text = row[f"{kind}_path"].read_bytes().decode("utf-8-sig")
                        spans = content_line_spans(text)
                        print(kind, "dòng:", len(spans))
                        matches = [(i, text[a:b]) for i, (a, b) in enumerate(spans, 1) if keyword.casefold() in text[a:b].casefold()]
                        for i, line in matches[:20]: print(f"{i:4} {line}")
                    print(f"{label} — đơn vị đã tách (chưa dóng hàng):")
                    for kind, title in (("han", "Hán"), ("nghia", "Dịch nghĩa")):
                        print(f"{title}: {len(units[kind])} đơn vị")
                        for unit in units[kind]:
                            print(f"  {unit['id']} | {unit['text']}")
                    results[label] = {"units": units, "ranges": ranges}
                    continue
                audit = alignment_audit_dir(output, member, work, section)
                draft_path, review_path = audit / "draft.json", audit / "review.json"
                if mode == "nhap" and review_path.exists() and read_json(review_path).get("approved") is True:
                    raise ValueError(f"{label} đã duyệt; lưu trữ bản cũ an toàn trước khi tạo lại.")
                if mode == "nhap" and draft_path.exists():
                    old = read_json(draft_path)
                    if old.get("fingerprint") != fingerprint:
                        raise ValueError("Dấu vân tay thay đổi; lưu trữ draft/review cũ trước khi tạo lại.")
                    if old.get("links", {}).get("nghia") and old.get("meaning_backend") == method.upper():
                        print("Dùng lại bản nháp đã có; lưu trữ bản cũ an toàn nếu cần tạo lại.")
                        if section_previews:
                            export_draft_preview(audit, label, old, units, work_id, fingerprint)
                        print("Thống kê:", quality(old))
                        from .notebook_helpers import show_alignment
                        show_alignment(old)
                        results[label] = old
                        continue
                result = run_alignment(paths.root, "CP024", work, member=member, genre=plan["genre"], section=section,
                                       ranges=ranges, export=mode == "xuat", data_root=paths.data_root,
                                       output_root=paths.output_root, meaning_method=method)
                if mode == "nhap" and not result["links"]["nghia"]:
                    raise RuntimeError(f"{label}: {method.upper()} không tạo liên kết: {result['status'].get(method.upper())}")
                if mode == "nhap":
                    if section_previews:
                        export_draft_preview(audit, label, result, units, work_id, fingerprint)
                    print("Thống kê:", quality(result))
                from .notebook_helpers import show_alignment
                show_alignment(result)
                results[label] = result
        except (OSError, ValueError, RuntimeError) as exc:
            failures[number] = str(exc)
            print("Lỗi:", exc)
            if not continue_on_error:
                raise
    return {"inventory": inventory, "results": results, "errors": failures}


def run_cp024_by_work(project, *, member="TV04", mode="nguon", batch=False, file_number=5,
                      file_numbers=(), data_root=None, output_root=None, method="clc", **options):
    """Keep CLC batches in the audit cache and publish one set of files per work."""
    paths = resolve_paths(user_root=project, data_root=data_root, output_root=output_root)
    if method not in {"clc", "dp"}:
        raise ValueError("PHUONG_PHAP phải là clc hoặc dp.")
    selection = dict(member=member, data_root=paths.data_root, output_root=paths.output_root)
    if mode == "nguon":
        return run_cp024(project, mode=mode, batch=batch, file_number=file_number,
                         file_numbers=file_numbers, method=method, **selection, **options)
    if mode not in {"nhap", "xuat"}:
        raise ValueError("CHE_DO phải là nguon, nhap hoặc xuat.")
    if options.get("section_number") is not None or options.get("whole_files", ()):
        raise ValueError("Đầu ra theo bài cần SO_MUC = None và DONG_TOAN_FILE = set().")
    if batch and not file_numbers:
        inventory, errors = discover_sources(paths.data_root / "CP024" / "03_text_sach")
        if errors:
            raise ValueError("; ".join(errors))
        file_numbers = [entry["file_id"] for entry in inventory]
    numbers = list(file_numbers) if batch else [file_number]
    if not numbers or any(type(n) is not int or n < 0 for n in numbers) or len(set(numbers)) != len(numbers):
        raise ValueError("Danh sách số file không hợp lệ.")
    output = clean_book_root(paths.root, "CPO_24", member, output_root=paths.output_root)
    cache_root = paths.output_root
    legacy = cache_root / member
    if (legacy / member / "CP024" / "05_quan_ly").is_dir():
        cache_root = legacy
    if method == "dp":
        cache_root = paths.output_root / ".cp024_dp"
        output = output / "dp"
    cache = clean_book_root(paths.root, "CP024", member, output_root=cache_root)
    results, errors = {}, {}
    for number in sorted(numbers):
        work = f"bai{number:04d}"
        audit = alignment_audit_dir(output, member, work)
        try:
            if mode == "nhap":
                batch_options = {**options, "continue_on_error": False, "section_previews": False, "method": method}
                run_cp024(project, mode=mode, file_number=number, member=member,
                          data_root=paths.data_root, output_root=cache_root, **batch_options)
                plan = read_json(alignment_audit_dir(cache, member, work) / "alignment_plan.json")
                documents = {}
                for item in plan["sections"]:
                    section = item["section"]
                    folder = alignment_audit_dir(cache, member, work, section)
                    for path in sorted(folder.glob("*.json")):
                        documents.setdefault(path.name, {})[section] = read_json(path)
                drafts = documents["draft.json"]
                reviews = documents["review_template.json"]
            else:
                plan = read_json(audit / "alignment_plan.json")
                drafts = read_json(audit / "draft.json")
                reviews = read_json(audit / "review.json")
            expected = {item["section"] for item in plan["sections"]}
            if set(drafts) != expected or set(reviews) != expected:
                raise ValueError("JSON phải chứa đủ các mục trong kế hoạch.")
            rows, unaligned = [], []
            for item in plan["sections"]:
                section = item["section"]
                _, identity, units, _, fingerprint = load_work(
                    paths.root, "CP024", work, member, plan["genre"], {}, section,
                    item["ranges"], data_root=paths.data_root, output_root=paths.output_root)
                draft, review = drafts[section], reviews[section]
                verify_identity(draft, identity, fingerprint)
                verify_identity(review, identity, fingerprint)
                links = draft["links"] if mode == "nhap" else review["links"]
                linked_rows = make_rows(units, links)
                if not linked_rows:
                    raise ValueError(f"{section} chưa có liên kết hợp lệ.")
                rows.extend(row["cells"] for row in linked_rows)
                missing = unmatched_ids(units, links)
                if mode == "xuat":
                    skipped = review.get("skipped", {})
                    if review.get("approved") is not True or set(skipped) != {uid for ids in missing.values() for uid in ids} or any(
                        not isinstance(reason, str) or not reason.strip() for reason in skipped.values()
                    ):
                        raise ValueError(f"{section} cần được duyệt và ghi đủ lý do skipped.")
                else:
                    for column, kind in enumerate(("han", "am", "nghia", "tho")):
                        for unit in units[kind]:
                            if unit["id"] in missing[kind]:
                                row = [""] * len(HEADERS)
                                row[column] = unit["text"]
                                unaligned.append(row)
            rows.extend(unaligned)
            folder = output / "04_dong_hang" / work
            stem = f"CPO_24_{work}" + ("_ban_nhap" if mode == "nhap" else "_parallel")
            if mode == "nhap":
                stream = io.StringIO(newline="")
                writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
                writer.writerow(HEADERS)
                writer.writerows(rows)
                tsv = stream.getvalue().encode("utf-8-sig")
            else:
                tsv = "".join("\t".join(row) + "\n" for row in rows).encode("utf-8")
            files = {
                folder / f"{stem}.tsv": tsv,
                folder / f"{stem}.xlsx": xlsx_bytes("DONG_HANG", HEADERS, rows),
            }
            write_protected(files)
            if mode == "nhap":
                for name, document in {"alignment_plan.json": plan, **documents}.items():
                    if name != "review.json":
                        write_json(audit / name, document)
                review_path = audit / "review.json"
                initial_reviews = {**reviews, **documents.get("review.json", {})}
                if not review_path.exists():
                    write_protected({review_path: json_bytes(initial_reviews)})
            results[work] = list(files)
            print(f"{work}: {len(rows)} hàng", *files, sep="\n")
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            errors[number] = str(exc)
            print(f"{work}: {exc}")
            if not options.get("continue_on_error"):
                raise
    return {"results": results, "errors": errors}
