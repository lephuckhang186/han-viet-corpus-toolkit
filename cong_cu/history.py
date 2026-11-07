"""Ghi nhận thay đổi để hoàn tác; giữ bản trước và sau của từng file bị sửa."""
from pathlib import Path
from uuid import uuid4
import copy
import gzip
import hashlib
import json
import re

from .storage import atomic_bytes, read_json, write_json


def pending_path(root: Path) -> Path:
    return root / "05_quan_ly" / "lich_su" / "dang_ghi.json"


def _read_meta(folder: Path):
    path = folder / "thay_doi.json.gz"
    if path.exists():
        return json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))
    return read_json(folder / "thay_doi.json", {})


def _write_meta(folder: Path, meta: dict):
    data = json.dumps(meta, ensure_ascii=False).encode("utf-8")
    atomic_bytes(folder / "thay_doi.json.gz", gzip.compress(data, compresslevel=3, mtime=0))


def _target(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or "ban_goc" in path.parts:
        raise ValueError("Thao tác chỉ áp dụng cho sản phẩm của tool, không áp dụng cho bản gốc.")
    return path


def _digest(data: bytes | None):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def _stored(folder: Path, name: str) -> Path:
    path = (folder / name).resolve()
    if not path.is_relative_to(folder.resolve()):
        raise ValueError("Đường dẫn bản lưu hoàn tác không hợp lệ.")
    return path


def _apply(root: Path, folder: Path, meta: dict, side: str):
    for item in meta["files"]:
        path = _target(root, item["path"])
        stored = item[side]
        if stored is None:
            path.unlink(missing_ok=True)
        else:
            atomic_bytes(path, _stored(folder, stored).read_bytes())
    write_json(root / "05_quan_ly" / "vung_cat.json", meta[f"{side}_manifest"])


def _check_states(root: Path, folder: Path, meta: dict, *, exact_after: bool):
    for item in meta["files"]:
        path = _target(root, item["path"])
        current = path.read_bytes() if path.exists() else None
        accepted = [item["after_hash"]] if exact_after else [item["before_hash"], item["after_hash"]]
        if _digest(current) not in accepted:
            raise FileExistsError(f"File đã được sửa ngoài tool, giữ nguyên: {path}")
        for side in ("before", "after"):
            if item[side] is not None and _digest(_stored(folder, item[side]).read_bytes()) != item[f"{side}_hash"]:
                raise OSError(f"Bản lưu hoàn tác không còn nguyên vẹn: {folder}")


def recover(root: Path):
    """Nếu lần ghi trước bị ngắt, quay về trạng thái trước; không đè sửa tay."""
    pointer = pending_path(root)
    if not pointer.exists():
        return
    token = read_json(pointer, {}).get("id")
    if not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{32}", token):
        raise ValueError("Mã thao tác đang ghi không hợp lệ.")
    folder = pointer.parent / token
    meta = _read_meta(folder)
    if meta.get("status") in ("pending", "undo_pending"):
        _check_states(root, folder, meta, exact_after=False)
        _apply(root, folder, meta, "before")
        meta["status"] = "recovered"
        _write_meta(folder, meta)
    elif meta.get("status") not in ("applied", "undone", "rolled_back", "recovered"):
        raise ValueError("Thiếu bản ghi để phục hồi thao tác đang ghi.")
    pointer.unlink(missing_ok=True)


def commit(root: Path, before: dict, after: dict, changes: dict[str, bytes | None], action: str):
    token = uuid4().hex
    folder = root / "05_quan_ly" / "lich_su" / token
    folder.mkdir(parents=True, exist_ok=False)
    next_manifest = copy.deepcopy(after)
    next_manifest["history_tip"] = token
    meta = {"action": action, "status": "pending", "before_manifest": before,
            "after_manifest": next_manifest, "files": []}
    for index, (relative, content) in enumerate(changes.items()):
        path = _target(root, relative)
        old = path.read_bytes() if path.exists() else None
        item = {"path": relative, "before": None, "after": None,
                "before_hash": _digest(old), "after_hash": _digest(content)}
        for side, data in (("before", old), ("after", content)):
            if data is not None:
                name = f"{index:04d}_{side}.bin"
                atomic_bytes(folder / name, data)
                item[side] = name
        meta["files"].append(item)
    _write_meta(folder, meta)  # Journal phải tồn tại trước khi thay đổi sản phẩm.
    write_json(pending_path(root), {"id": token})
    try:
        _apply(root, folder, meta, "after")
    except Exception:
        _apply(root, folder, meta, "before")
        meta["status"] = "rolled_back"
        _write_meta(folder, meta)
        pending_path(root).unlink(missing_ok=True)
        raise
    meta["status"] = "applied"
    _write_meta(folder, meta)
    pending_path(root).unlink(missing_ok=True)
    return next_manifest


def undo(root: Path, current: dict):
    token = current.get("history_tip")
    if not token:
        raise ValueError("Chưa có thao tác mới để hoàn tác. Với vùng cũ, chọn vùng rồi bấm Bỏ vùng.")
    if not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{32}", token):
        raise ValueError("Mã lịch sử hoàn tác không hợp lệ.")
    folder = root / "05_quan_ly" / "lich_su" / token
    meta = _read_meta(folder)
    if meta.get("status") != "applied" or current != meta.get("after_manifest"):
        raise ValueError("Trạng thái đã thay đổi; không thể hoàn tác an toàn thao tác này.")
    _check_states(root, folder, meta, exact_after=True)
    meta["status"] = "undo_pending"
    _write_meta(folder, meta)
    write_json(pending_path(root), {"id": token})
    _apply(root, folder, meta, "before")
    meta["status"] = "undone"
    _write_meta(folder, meta)
    pending_path(root).unlink(missing_ok=True)
    return meta["action"]
