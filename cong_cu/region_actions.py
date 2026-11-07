"""Tra cứu, thay/bỏ vùng và xác nhận tiến độ; không đụng bản PDF nguồn."""
from datetime import datetime, timezone
from pathlib import Path
import copy
import hashlib

from ten_file import CAC_BAN, ten_tac_pham, ten_vung
from .models import Box, validate_assignment
from .storage import read_json, workspace_lock
from . import history, pdf_ops, text_ops


def region_id(record):
    return record.get("id", record["fingerprint"])


class RegionActions:
    def __init__(self, workspace):
        self.workspace = workspace

    def list(self, *, work=None, version=None, source=None, page=None):
        records = self.workspace.manifest()["records"]
        return [r for r in records if (work is None or r["work"] == work)
                and (version is None or r["version"] == version)
                and (source is None or r["source_key"] == source)
                and (page is None or r.get("page") == page)]

    def find(self, token):
        for record in self.list():
            if region_id(record) == token:
                return record
        raise ValueError("Vùng không còn tồn tại. Cập nhật danh sách rồi chọn lại.")

    def overlaps(self, source, page, work, kind, version, box, excluding=None):
        result = []
        for record in self.list(source=source, page=page, work=work, version=version):
            if record["kind"] != kind or region_id(record) == excluding or "box" not in record:
                continue
            other = Box(*record["box"])
            if box.as_list() == other.as_list():
                continue  # Trùng hoàn toàn đã được bộ lưu nhận diện.
            width = max(0, min(box.x1, other.x1) - max(box.x0, other.x0))
            height = max(0, min(box.y1, other.y1) - max(box.y0, other.y0))
            intersection = width * height
            area = (box.x1 - box.x0) * (box.y1 - box.y0)
            other_area = (other.x1 - other.x0) * (other.y1 - other.y0)
            ratio = intersection / (area + other_area - intersection)
            if ratio >= .8:
                result.append(record)
        return result

    def replace_pdf(self, token, page, box, note="", allow_outside=False):
        old = self.find(token)
        if old["mode"] == "text":
            raise ValueError("Đây là vùng TXT; dùng cửa sổ chọn chữ để sửa.")
        w = self.workspace
        source = w.book.source(old["source_key"])
        validate_assignment(w.book, old["work"], source, page, allow_outside)
        raw = pdf_ops.extract_text(source.path, page, box) if old["mode"] == "pdf_text" else None
        png = pdf_ops.crop_png(source.path, page, box, old["dpi"])
        update = {"page": page, "box": box.as_list(), "note": note,
                  "outside_assignment": not source.contains(page)}
        return self._change(token, update, png=png, raw_text=raw, source=source)

    def replace_text(self, token, char_start, char_end, note=""):
        old = self.find(token)
        if old["mode"] != "text":
            raise ValueError("Vùng này lấy từ PDF, không phải TXT.")
        path = Path(old["source_path"])
        raw, selection = text_ops.select_characters(path, char_start, char_end)
        if not raw.strip():
            raise ValueError("Vùng TXT chỉ có khoảng trắng.")
        from .models import Source
        source = Source(old["source_key"], path, (), "chung", "TXT đã được chọn trước đó.")
        return self._change(token, {"selection": selection, "note": note}, raw_text=raw, source=source)

    def remove(self, token):
        return self._change(token, None)

    def _rebuild_text(self, manifest, old, changes, replacement_text):
        w = self.workspace
        parts = w._current_parts(manifest, old["work"], old["kind"], old["version"])
        stem = ten_tac_pham(w.book.code, old["work"], old["kind"], old["version"])
        merged = w.variant_folder(old["kind"]) / f"{stem}_trich_xuat_tho.txt"
        relative = merged.relative_to(w.root).as_posix()
        if parts and old["mode"] != "pdf_image":
            texts = []
            for part in parts:
                if region_id(part) in replacement_text:
                    texts.append(replacement_text[region_id(part)])
                else:
                    texts.append((w.root / part["text_file"]).read_text(encoding="utf-8"))
            changes[relative] = text_ops.join_parts(texts).encode("utf-8")
            manifest["artifacts"][relative] = hashlib.sha256(changes[relative]).hexdigest()
        elif relative in manifest["artifacts"]:
            changes[relative] = None
            manifest["artifacts"].pop(relative)
        for part in parts:
            part["work_outputs"] = [p for p in part["files"] if p.endswith(".png")]
            if old["mode"] != "pdf_image":
                part["work_outputs"].append(relative)

    def _change(self, token, update, *, png=None, raw_text=None, source=None):
        w = self.workspace
        with workspace_lock(w.root):
            history.recover(w.root)
            before = w.manifest()
            manifest = copy.deepcopy(before)
            old = next((r for r in manifest["records"] if region_id(r) == token), None)
            if old is None:
                raise ValueError("Vùng đã được sửa hoặc bỏ ở cửa sổ khác; chọn lại vùng.")
            for relative in old["files"]:
                if not (w.root / relative).is_file():
                    raise FileNotFoundError(f"Thiếu file vùng đã lưu: {relative}")
            w._check_generated(before, [w.root / p for p in old["files"]])
            changes = {relative: None for relative in old["files"]}
            for relative in old["files"]:
                manifest["artifacts"].pop(relative, None)
            replacement = None
            replacement_text = {}
            if update is not None:
                sources = read_json(w.sources_path, {})
                archived = w._archive_source(source, sources)
                replacement = copy.deepcopy(old)
                replacement.update(update)
                replacement["id"] = token
                replacement["source_sha256"] = archived["sha256"]
                replacement["edited_at"] = datetime.now(timezone.utc).isoformat()
                replacement["fingerprint"] = w.region_fingerprint(replacement)
                if any(region_id(r) != token and r["fingerprint"] == replacement["fingerprint"] for r in manifest["records"]):
                    raise ValueError("Vùng thay thế trùng hoàn toàn một vùng khác đã lưu.")
                stem = ten_tac_pham(w.book.code, old["work"], old["kind"], old["version"])
                piece = ten_vung(old["sequence"], replacement.get("page"))
                replacement["files"] = []
                if png is not None:
                    relative = (w.variant_folder(old["kind"]) / stem / f"{piece}.png").relative_to(w.root).as_posix()
                    changes[relative] = png
                    replacement["files"].append(relative)
                if raw_text is not None:
                    relative = (w.manage / "text_tho" / stem / f"{piece}.txt").relative_to(w.root).as_posix()
                    changes[relative] = raw_text.encode("utf-8")
                    replacement["files"].append(relative)
                    replacement["text_file"] = relative
                    replacement_text[token] = raw_text
                for relative in replacement["files"]:
                    manifest["artifacts"][relative] = hashlib.sha256(changes[relative]).hexdigest()
            position = manifest["records"].index(old)
            if replacement is None:
                manifest["records"].pop(position)
            else:
                manifest["records"][position] = replacement
            self._rebuild_text(manifest, old, changes, replacement_text)
            manifest["reviewed"] = [r for r in manifest.get("reviewed", [])
                                    if not w._same_variant(r, old["work"], old["kind"], old["version"])]
            w._commit(before, manifest, changes, "Thay vùng" if update is not None else "Bỏ vùng")
            return replacement or old

    def mark_reviewed(self, work, kind, version, complete=True):
        w = self.workspace
        w._validate_variant(work, kind, version)
        with workspace_lock(w.root):
            history.recover(w.root)
            before = w.manifest()
            manifest = copy.deepcopy(before)
            if not w._current_parts(manifest, work, kind, version):
                raise ValueError("Chưa có vùng nào của bản văn này để xác nhận đã kiểm tra đủ.")
            reviewed = [r for r in manifest.get("reviewed", []) if not w._same_variant(r, work, kind, version)]
            if complete:
                reviewed.append({"work": work, "kind": kind, "version": version,
                                 "checked_at": datetime.now(timezone.utc).isoformat()})
            manifest["reviewed"] = reviewed
            w._commit(before, manifest, {}, "Xác nhận đủ bản văn" if complete else "Bỏ xác nhận đủ")
