"""Tổ chức sản phẩm theo tác phẩm, lưu provenance và gom các vùng đã chọn."""
from datetime import datetime, timezone
import copy
from pathlib import Path
import hashlib
import json

from ten_file import CAC_BAN, MA_DE_TAI, OUTPUT_ROOT, THANH_VIEN, ten_tac_pham, ten_vung
from .models import Book, Box, Source, validate_assignment, validate_work
from . import history, pdf_ops, text_ops
from .region_actions import RegionActions
from .storage import backup, immutable_bytes, read_json, sha256, workspace_lock, write_json


class Workspace:
    def __init__(self, book: Book, output_root: Path | None = None):
        self.book = book
        self.root = (output_root or OUTPUT_ROOT) / f"{MA_DE_TAI}_{book.code}"
        self.manage = self.root / "05_quan_ly"
        self.manifest_path = self.manage / "vung_cat.json"
        self.sources_path = self.manage / "nguon.json"
        self._verified_sources = {}
        self.regions = RegionActions(self)

    def manifest(self) -> dict:
        return read_json(self.manifest_path, {
            "schema": 1, "book": self.book.code, "member": THANH_VIEN,
            "topic": MA_DE_TAI, "status": "draft_regions_not_aligned",
            "records": [], "artifacts": {}, "absent": [],
        })

    def prepare(self) -> dict:
        """Sao lưu đầy đủ nguồn, kiểm tra hash; không OCR/cắt hàng loạt."""
        with workspace_lock(self.root):
            history.recover(self.root)
            for _, side in CAC_BAN.values():
                (self.root / "01_nguon" / side).mkdir(parents=True, exist_ok=True)
            for side in ("han", "viet"):
                (self.root / "02_ocr_tho" / side).mkdir(parents=True, exist_ok=True)
            for name in ("03_text_sach", "04_dong_hang", "05_quan_ly"):
                (self.root / name).mkdir(parents=True, exist_ok=True)
            sources = read_json(self.sources_path, {})
            for source in self.book.sources:
                self._archive_source(source, sources)
            write_json(self.sources_path, sources)
            if not self.manifest_path.exists():
                write_json(self.manifest_path, self.manifest())
            immutable_bytes(self.root / "03_text_sach" / "CHUA_THUC_HIEN.txt",
                            "Bước 3 chưa tạo han.txt/viet.txt sạch. Không dùng file trống làm kết quả.\n".encode())
            return sources

    def _archive_source(self, source: Source, sources: dict) -> dict:
        if not source.path.is_file():
            raise FileNotFoundError(f"Không thấy nguồn: {source.path}; sửa tên trong ten_file.py.")
        target = self.root / "01_nguon" / source.archive_side / "ban_goc" / source.path.name
        signature = self._source_signature(source.path, target)
        cached = self._verified_sources.get(source.key)
        if cached and cached[0] == signature and sources.get(source.key, {}).get("sha256") == cached[1]:
            return sources[source.key]
        if source.key in sources and sha256(source.path) != sources[source.key]["sha256"]:
            raise ValueError("Nguồn đã thay đổi so với manifest; giữ bản cũ và kiểm tra lại nguồn.")
        digest = backup(source.path, target)
        if source.key in sources and sources[source.key]["sha256"] != digest:
            raise ValueError("Nguồn đã thay đổi so với manifest. Dùng nguồn/phiên bản mới, không trộn nguồn.")
        entry = {"path": str(source.path.resolve()), "backup": target.relative_to(self.root).as_posix(),
                 "sha256": digest, "ranges": source.ranges, "note": source.note}
        sources[source.key] = entry
        self._verified_sources[source.key] = (self._source_signature(source.path, target), digest)
        return entry

    @staticmethod
    def _source_signature(*paths):
        result = []
        for path in paths:
            if not path.exists():
                result.append(None)
            else:
                stat = path.stat()
                result.append((str(path.resolve()), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns))
        return tuple(result)

    def _commit(self, before: dict, after: dict, changes: dict, action: str):
        generated = [self.root / relative for relative in changes
                     if relative != self.sources_path.relative_to(self.root).as_posix()]
        self._check_generated(before, generated)
        return history.commit(self.root, before, after, changes, action)

    def undo_last(self):
        with workspace_lock(self.root):
            history.recover(self.root)
            return history.undo(self.root, self.manifest())

    def read_session(self):
        try:
            state = read_json(self.manage / "phien_lam_viec.json", {})
            return state if isinstance(state, dict) else {}
        except (OSError, ValueError):
            return {}  # Cài đặt giao diện hỏng không ngăn mở nguồn và sản phẩm.

    def save_session(self, state: dict):
        write_json(self.manage / "phien_lam_viec.json", state)

    def _validate_variant(self, work: str, kind: str, version: int):
        validate_work(work)
        if kind not in CAC_BAN:
            raise ValueError(f"Loại bản văn phải là một trong {list(CAC_BAN)}.")
        if not 1 <= version <= 9999:
            raise ValueError("Phiên bản cần từ 1 đến 9999.")

    def variant_folder(self, kind: str) -> Path:
        return self.root / "01_nguon" / CAC_BAN[kind][1]

    def _same_variant(self, record: dict, work: str, kind: str, version: int):
        return (record["work"], record["kind"], record["version"]) == (work, kind, version)

    @staticmethod
    def region_fingerprint(record):
        ignored = {"note", "unreviewed", "outside_assignment", "id", "fingerprint", "sequence",
                   "saved_at", "edited_at", "files", "text_file", "work_outputs"}
        identity = {k: v for k, v in record.items() if k not in ignored}
        return hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def _current_parts(self, manifest: dict, work: str, kind: str, version: int) -> list[dict]:
        return sorted((r for r in manifest["records"] if self._same_variant(r, work, kind, version)),
                      key=lambda item: item["sequence"])

    def _check_generated(self, manifest: dict, paths):
        for path in paths:
            relative = path.relative_to(self.root).as_posix()
            if path.exists() and manifest["artifacts"].get(relative) != sha256(path):
                raise FileExistsError(f"Sản phẩm đã bị sửa ngoài tool: {path}. Chọn v02 để giữ bản sửa.")

    def save_pdf_region(self, source_key: str, page: int, box: Box, work: str, kind: str,
                        version: int = 1, dpi: int = 300, extract_text: bool = False,
                        note: str = "", allow_outside: bool = False) -> dict:
        self._validate_variant(work, kind, version)
        source = self.book.source(source_key)
        validate_assignment(self.book, work, source, page, allow_outside)
        if not self.sources_path.exists():
            self.prepare()
        # Compute text first: a scan must not leave a misleading empty TXT/crop.
        raw_text = pdf_ops.extract_text(source.path, page, box) if extract_text else None
        png = pdf_ops.crop_png(source.path, page, box, dpi)
        record = {"work": work, "kind": kind, "version": version, "source_key": source_key,
                  "source_path": str(source.path.resolve()), "page": page, "box": box.as_list(),
                  "mode": "pdf_text" if extract_text else "pdf_image", "dpi": dpi,
                  "note": note, "outside_assignment": not source.contains(page),
                  "unreviewed": True}
        return self._save(record, source, png=png, raw_text=raw_text)

    def save_text_region(self, path: Path, work: str, kind: str, version: int = 1,
                         line_start: int | None = None, line_end: int | None = None,
                         char_start: int | None = None, char_end: int | None = None,
                         note: str = "") -> dict:
        self._validate_variant(work, kind, version)
        if self.book.work_range:
            import re
            match = re.fullmatch(r"bai(\d+)", work)
            if not match or not self.book.work_range[0] <= int(match[1]) <= self.book.work_range[1]:
                raise ValueError("Mã bài TXT ngoài phạm vi TV2 của sách này.")
        if line_start is not None and line_end is not None:
            raw, selection = text_ops.select_lines(path, line_start, line_end)
        elif char_start is not None and char_end is not None:
            raw, selection = text_ops.select_characters(path, char_start, char_end)
        else:
            raise ValueError("Cần khoảng dòng hoặc ký tự của file TXT.")
        if not raw.strip():
            raise ValueError("Vùng TXT chỉ có khoảng trắng.")
        if not self.sources_path.exists():
            self.prepare()
        key = "txt_" + sha256(path)[:12]
        source = Source(key, path, (), "chung", "TXT do người dùng chọn, không xác nhận đã làm sạch.")
        record = {"work": work, "kind": kind, "version": version, "source_key": key,
                  "source_path": str(path.resolve()), "page": None, "selection": selection,
                  "mode": "text", "note": note, "unreviewed": True}
        return self._save(record, source, raw_text=raw)

    def _save(self, record: dict, source: Source, png: bytes | None = None, raw_text: str | None = None):
        with workspace_lock(self.root):
            history.recover(self.root)
            manifest = self.manifest()
            before = copy.deepcopy(manifest)
            sources = read_json(self.sources_path, {})
            archived = self._archive_source(source, sources)
            record["source_sha256"] = archived["sha256"]
            fingerprint = self.region_fingerprint(record)
            for existing in manifest["records"]:
                if existing["fingerprint"] == fingerprint:
                    # Check the existing files, rather than trusting the manifest alone.
                    self._check_generated(manifest, [self.root / p for p in existing["files"]])
                    if not all((self.root / p).exists() for p in existing["files"]):
                        raise FileNotFoundError("File vùng đã lưu bị thiếu; chạy --check trước khi tiếp tục.")
                    return {**existing, "skipped": True}
            parts = self._current_parts(manifest, record["work"], record["kind"], record["version"])
            if any(a["work"] == record["work"] and a["kind"] == record["kind"] and a["version"] == record["version"]
                   for a in manifest["absent"]):
                raise ValueError("Bản văn đã đánh dấu không có. Chọn phiên bản mới hoặc sửa ghi nhận trước.")
            if parts and parts[0]["mode"] != record["mode"]:
                raise ValueError("Không trộn chế độ ảnh/PDF-text/TXT trong cùng bản văn và phiên bản. Dùng v02.")
            record["sequence"] = max((p["sequence"] for p in parts), default=0) + 1
            record["fingerprint"] = fingerprint
            record["id"] = fingerprint
            record["saved_at"] = datetime.now(timezone.utc).isoformat()
            stem = ten_tac_pham(self.book.code, record["work"], record["kind"], record["version"])
            folder = self.variant_folder(record["kind"])
            piece_stem = ten_vung(record["sequence"], record["page"])
            image_path = folder / stem / f"{piece_stem}.png"
            text_path = self.manage / "text_tho" / stem / f"{piece_stem}.txt"
            record["files"] = []
            if png is not None:
                record["files"].append(image_path.relative_to(self.root).as_posix())
            if raw_text is not None:
                record["text_file"] = text_path.relative_to(self.root).as_posix()
                record["files"].append(record["text_file"])
            merged_text_path = folder / f"{stem}_trich_xuat_tho.txt"
            outputs = {}
            if raw_text is not None:
                previous = [(self.root / p["text_file"]).read_text(encoding="utf-8") for p in parts]
                outputs[merged_text_path] = text_ops.join_parts(previous + [raw_text]).encode("utf-8")
            changes = {path.relative_to(self.root).as_posix(): data for path, data in outputs.items()}
            if png is not None:
                changes[image_path.relative_to(self.root).as_posix()] = png
            if raw_text is not None:
                changes[text_path.relative_to(self.root).as_posix()] = raw_text.encode("utf-8")
            for relative, data in changes.items():
                manifest["artifacts"][relative] = hashlib.sha256(data).hexdigest()
            record["work_outputs"] = []
            if png is not None:
                record["work_outputs"].append(image_path.relative_to(self.root).as_posix())
            record["work_outputs"].extend(p.relative_to(self.root).as_posix() for p in outputs)
            manifest["records"].append(record)
            manifest["reviewed"] = [entry for entry in manifest.get("reviewed", [])
                                    if not self._same_variant(entry, record["work"], record["kind"], record["version"])]
            changes[self.sources_path.relative_to(self.root).as_posix()] = (json.dumps(sources, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            self._commit(before, manifest, changes, "Lưu vùng")
            return record

    def mark_absent(self, work: str, kind: str, version: int, note: str):
        self._validate_variant(work, kind, version)
        if not note.strip():
            raise ValueError("Ghi lý do/nguồn đã kiểm tra khi đánh dấu không có bản văn.")
        if not self.sources_path.exists():
            self.prepare()
        with workspace_lock(self.root):
            history.recover(self.root)
            manifest = self.manifest()
            before = copy.deepcopy(manifest)
            if self._current_parts(manifest, work, kind, version):
                raise ValueError("Đã có vùng của bản văn này, không thể đánh dấu không có.")
            entry = {"work": work, "kind": kind, "version": version, "note": note.strip(),
                     "status": "not_present_user_confirmed"}
            manifest["absent"] = [a for a in manifest["absent"] if not self._same_variant(a, work, kind, version)] + [entry]
            self._commit(before, manifest, {}, "Ghi nhận không có bản văn")

    def summary(self, work: str, version: int = 1, *, manifest: dict | None = None) -> dict:
        manifest = self.manifest() if manifest is None else manifest
        result = {}
        for kind in CAC_BAN:
            parts = self._current_parts(manifest, work, kind, version)
            absent = any(self._same_variant(a, work, kind, version) for a in manifest["absent"])
            reviewed = any(self._same_variant(a, work, kind, version) for a in manifest.get("reviewed", []))
            status = ("complete" if reviewed else "draft") if parts else ("not_present" if absent else "not_reviewed")
            result[kind] = {"regions": len(parts), "status": status}
        return result

    def check(self) -> dict:
        if not self.manifest_path.exists() or not self.sources_path.exists():
            return {"ok": False, "problems": ["Chưa chuẩn bị nguồn; chạy --prepare."], "regions": 0}
        manifest = self.manifest()
        problems = []
        for relative, digest in manifest["artifacts"].items():
            path = self.root / relative
            if not path.is_file() or sha256(path) != digest:
                problems.append(relative)
        for source in read_json(self.sources_path, {}).values():
            for path in (Path(source["path"]), self.root / source["backup"]):
                if not path.is_file() or sha256(path) != source["sha256"]:
                    problems.append(str(path))
        return {"ok": not problems, "problems": problems, "regions": len(manifest["records"]),
                "note": "Chỉ kiểm tra file/hash; chưa xác nhận nghĩa, ranh giới hoặc dóng hàng."}
