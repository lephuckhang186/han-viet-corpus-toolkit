"""Reusable cleaning stage functions extracted from clean_text.ipynb (preserving protected behavior)."""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
import io
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any
import unicodedata
from zipfile import ZipFile

from hanviet.common.io import bytes_hash
from .han_cleaner import clean_han
from .viet_cleaner import clean_viet, word_spans


DEFAULT_BOOK_FOLDERS = {"CPO_09": "BacSu", "CPO_11": "ThiDinh", "CPO_12": "LyTran"}
TEXT_FOLDERS = {
    "han": Path("han"),
    "dich_am": Path("viet") / "dich_am",
    "dich_nghia": Path("viet") / "dich_nghia",
    "dich_tho": Path("viet") / "dich_tho",
}


def sha256_bytes(data: bytes) -> str:
    return bytes_hash(data, "sha256")


def natural_key(text: str):
    return [int(s) if s.isdigit() else s.casefold() for s in re.split(r"(\d+)", text)]


def safe_component(name: str) -> str:
    if name in {"", ".", ".."} or any(c in name for c in '/\\:*?"<>|\r\n\t'):
        raise ValueError(f"Tên đầu ra không an toàn: {name!r}")
    return name


def describe_source(
    name: str,
    *,
    book_folders: dict[str, str] | None = None,
    selected_codes: set[str] | None = None,
    selected_kinds: set[str] | None = None,
    member_number: int = 4,
    input_granularity: str = "parts",
) -> dict[str, Any] | None:
    book_folders = book_folders or DEFAULT_BOOK_FOLDERS
    selected_codes = selected_codes or set(book_folders)
    selected_kinds = selected_kinds or set(TEXT_FOLDERS)
    parts = PurePosixPath(name.replace("\\", "/")).parts
    if not name.lower().endswith(".txt") or "05_quan_ly" in parts:
        return None
    stage = next((p for p in ("02_ocr_tho", "01_nguon") if p in parts), None)
    if stage is None:
        return None
    pos = parts.index(stage)
    code = next((code for code, folder in book_folders.items() if folder in parts[:pos]), None)
    tail = parts[pos + 1:]
    if code not in selected_codes or not tail:
        return None
    members = {int(m.group(1)) for p in parts if (m := re.search(r"(?:^|_)TV(\d+)(?:_|$)", p))}
    if members != {member_number}:
        return None
    if tail[0] == "han":
        kind = "han"
    elif len(tail) > 1 and tail[0] == "viet":
        kind = tail[1]
    else:
        return None
    if kind not in selected_kinds:
        return None
    if stage == "01_nguon" and ((code, kind) != ("CPO_09", "dich_nghia") or len(tail) != 3):
        return None
    filename = parts[-1]
    merged = filename.endswith("_ocr_tho.txt")
    if stage == "02_ocr_tho" and merged != (input_granularity == "merged"):
        return None
    stem = parts[-2] if stage == "02_ocr_tho" else Path(filename).stem
    return dict(code=code, kind=kind, work=stem, stage=stage)


def read_sources(
    path: Path | str,
    *,
    book_folders: dict[str, str] | None = None,
    selected_codes: set[str] | None = None,
    selected_kinds: set[str] | None = None,
    member_number: int = 4,
    input_granularity: str = "parts",
) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Chưa có đầu vào: {path}. Đặt INPUT_PATH đúng thư mục/ZIP OCR.")
    if path.is_dir():
        entries = [(p.relative_to(path).as_posix(), p) for p in path.rglob("*.txt")]
        get_bytes = lambda item: item.read_bytes()
        archive = None
    elif path.suffix.lower() == ".zip":
        archive = ZipFile(path)
        entries = [(p.filename, p) for p in archive.infolist() if not p.is_dir()]
        get_bytes = archive.read
    else:
        raise ValueError("INPUT_PATH phải là thư mục hoặc ZIP.")
    sources, identities = [], set()
    try:
        for name, item in sorted(entries, key=lambda pair: natural_key(pair[0])):
            info = describe_source(
                name,
                book_folders=book_folders,
                selected_codes=selected_codes,
                selected_kinds=selected_kinds,
                member_number=member_number,
                input_granularity=input_granularity,
            )
            if info is None:
                continue
            identity = (info["code"], info["kind"], info["work"], PurePosixPath(name).name)
            if identity in identities:
                raise ValueError(f"Nguồn trùng nhiều lượt chạy: {name}. Chọn một thư mục OCR.")
            identities.add(identity)
            raw = get_bytes(item)
            sources.append(dict(info, relative_path=name, text=raw.decode("utf-8-sig"), source_sha256=sha256_bytes(raw)))
    finally:
        if archive is not None:
            archive.close()
    if not sources:
        raise ValueError("Không tìm thấy TXT đúng cấu trúc. Kiểm tra INPUT_PATH và INPUT_GRANULARITY.")
    return sources


def attach_native_vietnamese_pages(source: dict[str, Any], root: Path) -> None:
    text_path = PurePosixPath(source["relative_path"])
    book = text_path.parents[3]
    index = root / book / "05_quan_ly" / "nguon_tho_viet.json"
    if not index.is_file():
        return
    relative = text_path.relative_to(book).as_posix()
    exports = json.loads(index.read_text(encoding="utf-8"))["exports"]
    pages = next((entry["pages"] for entry in exports if entry["file"] == relative), [])
    segments = source["text"].split("\f")
    if len(segments) == len(pages) and all(
        sha256_bytes(segment.encode("utf-8")) == page["selected_sha256_utf8"]
        for segment, page in zip(segments, pages)
    ):
        source["review_pages"] = [dict(pdf_page=page["pdf_page"]) for page in pages]


def attach_review_pages(sources: list[dict[str, Any]], root: Path | str) -> None:
    root = Path(root)
    manifest = root / "05_quan_ly" / "ghep_theo_tac_pham.json"
    entries = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else []
    by_work = {(r["work"], r["sha256"]): r["source_files"] for r in entries if r.get("status") == "merged"}
    for source in sources:
        if source["stage"] == "01_nguon":
            attach_native_vietnamese_pages(source, root)
            continue
        text_path = PurePosixPath(source["relative_path"])
        segments = source["text"].split("\f")
        names = by_work.get((source["work"], source["source_sha256"]))
        if not text_path.name.endswith("_ocr_tho.txt") and len(segments) == 1:
            names = [text_path.with_suffix(".png").name]
        if not names or len(names) != len(segments):
            continue
        source["review_pages"] = []
        book, _, *version_folder = text_path.parent.parts
        for segment_text, source_name in zip(segments, names):
            image_name = PurePosixPath(source_name).name
            part = root / text_path.parent / Path(image_name).with_suffix(".txt")
            image = root / book / "01_nguon" / Path(*version_folder) / image_name
            page_match = re.search(r"_pdfp(\d+)\.png$", image_name)
            metadata = part.with_suffix(".meta.json")
            valid_image = image if image.is_file() else None
            polygons = {}
            if metadata.is_file() and part.is_file() and valid_image:
                meta = json.loads(metadata.read_text(encoding="utf-8"))
                part_bytes = part.read_bytes()
                if (
                    sha256_bytes(part_bytes) == meta["output_hashes"]["txt"]
                    and part_bytes.decode("utf-8-sig") == segment_text
                    and sha256_bytes(image.read_bytes()) == meta["identity"]["source_sha256"]
                ):
                    reading_map = meta["review"].get("reading_map", [])
                    if len(segment_text.split("\n")) == len(reading_map):
                        polygons = {row["txt_line"]: row["polygon"] for row in reading_map}
            source["review_pages"].append(
                dict(
                    pdf_page=int(page_match[1]) if page_match else None,
                    source_image=valid_image.relative_to(root).as_posix() if valid_image else "",
                    polygons=polygons,
                )
            )


def build_records(
    sources: list[dict[str, Any]],
    vocabulary: set[str],
    *,
    known_non_content_lines: dict[tuple[str, str], set[str]] | None = None,
    punctuation_replacements: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    from .viet_cleaner import suffix_digit_suggestion

    known_non_content = known_non_content_lines or {}
    records: list[dict[str, Any]] = []
    for source in sources:
        pages = source["text"].replace("\r\n", "\n").replace("\r", "\n").split("\f")
        kind = source["kind"]
        native_pdf = source["stage"] == "01_nguon"
        normalized = [
            [
                clean_han(line, punctuation_replacements=punctuation_replacements)
                if kind == "han"
                else clean_viet(line, kind, native_pdf=native_pdf, punctuation_replacements=punctuation_replacements)
                for line in page.split("\n")
            ]
            for page in pages
        ]
        counts = Counter(text for page in normalized for text, _, _ in page if text)
        for page_no, page in enumerate(normalized, 1):
            lines = pages[page_no - 1].split("\n")
            page_maps = source.get("review_pages", [])
            location = page_maps[page_no - 1] if page_no <= len(page_maps) else {}
            last = max((i for i, (text, _, _) in enumerate(page, 1) if text), default=0)
            for line_no, (text, rules, flags) in enumerate(page, 1):
                flags = list(flags)
                if text and counts[text] > 1:
                    flags.append("repeated_line")
                if text and text in known_non_content.get((source["code"], kind), set()):
                    flags.append("configured_non_content_line")
                if page_no < len(pages) and line_no == last:
                    flags.append("page_boundary_check")
                oov = set()
                if kind == "dich_am" and vocabulary:
                    oov = {
                        token.casefold()
                        for _, _, token in word_spans(text.replace("[MASK]", " "))
                        if all(unicodedata.category(c)[0] in "LM" for c in token)
                        and token.casefold() not in vocabulary
                    }
                row_id = sha256_bytes(
                    json.dumps([source["relative_path"], source["source_sha256"], page_no, line_no], ensure_ascii=False).encode()
                )[:24]
                records.append(
                    dict(
                        row_id=row_id,
                        relative_path=source["relative_path"],
                        source_sha256=source["source_sha256"],
                        code=source["code"],
                        kind=kind,
                        work=source["work"],
                        page=page_no,
                        line=line_no,
                        raw=lines[line_no - 1],
                        clean=text,
                        pdf_page=location.get("pdf_page") or "",
                        source_image=location.get("source_image", ""),
                        polygon=location.get("polygons", {}).get(line_no),
                        automatic_rules=";".join(rules),
                        reasons=";".join(flags),
                        suggested=suffix_digit_suggestion(text) if kind != "han" else text,
                        context_before=lines[line_no - 2] if line_no > 1 else "",
                        context_after=lines[line_no] if line_no < len(lines) else "",
                        oov_tokens=" | ".join(sorted(oov)),
                    )
                )
    return records


def csv_bytes(rows: list[dict[str, Any]], fields: list[str]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def write_once(path: Path | str, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == data:
            return
        raise FileExistsError(f"Đã có file khác nội dung, không ghi đè: {path}")
    with path.open("xb") as stream:
        stream.write(data)


def review_csv_rows(path: Path | str, records: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not Path(path).is_file():
        raise FileNotFoundError(f"Chưa có bảng duyệt: {path}. Chạy cell preview_review trước.")
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected = {r["row_id"]: r for r in records}
    if len(rows) != len(expected) or {r.get("row_id") for r in rows} != set(expected):
        raise ValueError("Bảng duyệt thiếu/trùng/thừa dòng hoặc nguồn thay đổi.")
    for row in rows:
        original = expected[row["row_id"]]
        for key in ("source_sha256", "relative_path", "clean", "page", "line"):
            if str(row.get(key, "")) != str(original[key]):
                raise ValueError(f"Bảng duyệt không khớp nguồn/cấu hình: {row['row_id']} / {key}")
    return rows


def validate_review_action(action: str, replacement: str, allowed: set[str]) -> None:
    if action not in allowed:
        raise ValueError(f"Action không hợp lệ: {action}")
    if any(c in replacement for c in "\r\n\f\t"):
        raise ValueError("replacement phải là một dòng, không chứa TAB hay ngắt trang.")
    if action == "replace" and not replacement.strip():
        raise ValueError("Dùng delete thay cho replacement rỗng.")


def read_decisions(path: Path | str, records: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    decisions: dict[str, dict[str, str]] = {}
    for row in review_csv_rows(path, records):
        action = row.get("action", "").strip().casefold()
        replacement = row.get("replacement", "")
        validate_review_action(action, replacement, {"", "keep", "replace", "delete", "join_next"})
        decisions[row["row_id"]] = dict(action=action, replacement=replacement, note=row.get("note", ""))
    return decisions


def apply_decisions(
    records: list[dict[str, Any]],
    decisions: dict[str, dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    output, audit = [], []
    for record in records:
        decision = decisions.get(record["row_id"], {})
        action = decision.get("action", "")
        text = decision.get("replacement", "") if action == "replace" else record["clean"]
        deleted = action == "delete"
        output.append(dict(record, text=text, deleted=deleted, join_next=action == "join_next"))
        trace = dict(
            row_id=record["row_id"],
            source=record["relative_path"],
            source_sha256=record["source_sha256"],
            page=record["page"],
            pdf_page=record.get("pdf_page"),
            line=record["line"],
        )
        if record["raw"] != record["clean"]:
            audit.append(dict(trace, before=record["raw"], after=record["clean"], action="automatic", rules=record["automatic_rules"]))
        if action:
            audit.append(dict(trace, before=record["clean"], after=None if deleted else text, action=action, note=decision.get("note", "")))
    return output, audit


def assemble_works(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], str]:
    groups = defaultdict(list)
    for row in rows:
        groups[(row["code"], row["kind"], row["work"])].append(row)
    result = {}
    for key, group in groups.items():
        chunks = []
        pending = False
        previous_location = None
        has_text_on_part = False
        for row in group:
            location = (row["relative_path"], row["page"])
            if location != previous_location:
                if previous_location is not None and not pending:
                    chunks.append("\f")
                has_text_on_part = False
                previous_location = location
            if row["deleted"] or not row["text"]:
                continue
            if pending:
                chunks.append("" if key[1] == "han" else " ")
            elif has_text_on_part:
                chunks.append("\n")
            chunks.append(row["text"])
            pending = row["join_next"]
            has_text_on_part = True
        if pending:
            raise ValueError(f"join_next ở cuối tác phẩm không có dòng tiếp: {key}")
        result[key] = "".join(chunks)
    return result


def clean_version_folder(topic_code: str, code: str, kind: str) -> Path:
    if not re.fullmatch(r"CPO_\d{2}", code):
        raise ValueError(f"Mã sách không hợp lệ: {code}")
    return Path(f"{topic_code}_{code}") / "03_text_sach" / TEXT_FOLDERS[kind]


def make_export_files(
    works: dict[tuple[str, str, str], str],
    rows: list[dict[str, Any]],
    audit: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    *,
    topic_code: str,
    run_name: str,
    input_granularity: str = "parts",
    unresolved_count: int = 0,
    punctuation_replacements: dict[str, str] | None = None,
) -> dict[Path, bytes]:
    files: dict[Path, bytes] = {}
    manifest = []
    book_texts = defaultdict(list)
    for (code, kind, stem), text in sorted(works.items(), key=lambda kv: natural_key("/".join(kv[0]))):
        stem = safe_component(stem)
        relative = clean_version_folder(topic_code, code, kind) / (stem + ".txt")
        files[relative] = text.encode("utf-8")
        if input_granularity == "merged":
            book_texts[(code, kind)].append((stem, text))
        source_rows = [r for r in rows if (r["code"], r["kind"], r["work"]) == (code, kind, stem)]
        manifest.append(
            dict(
                code=code,
                kind=kind,
                work=stem,
                file=relative.as_posix(),
                sha256=sha256_bytes(files[relative]),
                source_rows=[
                    dict(
                        row_id=r["row_id"],
                        source=r["relative_path"],
                        source_sha256=r["source_sha256"],
                        page=r["page"],
                        line=r["line"],
                        deleted=r["deleted"],
                        join_next=r["join_next"],
                    )
                    for r in source_rows
                ],
            )
        )
    for (code, kind), parts in book_texts.items():
        filename = "han.txt" if kind == "han" else f"viet_{kind}.txt"
        files[clean_version_folder(topic_code, code, kind) / filename] = "\f".join(text for _, text in parts).encode("utf-8")
    text_outputs = [dict(file=path.as_posix(), sha256=sha256_bytes(data)) for path, data in files.items()]
    management = Path("05_quan_ly") / run_name
    encode_json = lambda data: (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    files[management / "work_manifest.json"] = encode_json(manifest)
    files[management / "changes.jsonl"] = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in audit).encode("utf-8")
    files[management / "summary.json"] = encode_json(
        dict(
            stage="step_5_reviewed_draft_not_alignment_or_quota_certification",
            source_files=len(sources),
            works=len(works),
            changed_or_reviewed_lines=len(audit),
            input_granularity=input_granularity,
            unresolved_lines=unresolved_count,
            punctuation_replacements=punctuation_replacements or {},
            text_outputs=text_outputs,
            sources=[dict(path=s["relative_path"], sha256=s["source_sha256"]) for s in sources],
        )
    )
    return files
