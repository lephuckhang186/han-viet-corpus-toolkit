"""Sao lưu nguyên bản, ghi nguyên tử và kiểm tra dấu vân tay file."""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_bytes(path: Path, content: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".dang_ghi_", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def immutable_bytes(path: Path, content: bytes):
    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError(f"File đã có nội dung khác: {path}. Chọn phiên bản mới.")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)


def write_json(path: Path, value):
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def read_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def backup(source: Path, destination: Path) -> str:
    digest = sha256(source)
    if destination.exists():
        if sha256(destination) != digest:
            raise FileExistsError(f"Bản sao nguồn khác bản gốc: {destination}; không ghi đè.")
        return digest
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(prefix=".sao_luu_", dir=destination.parent)
    os.close(handle)
    try:
        shutil.copyfile(source, tmp)
        if sha256(Path(tmp)) != digest:
            raise OSError("Dấu kiểm bản sao không khớp nguồn.")
        os.replace(tmp, destination)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return digest


@contextmanager
def workspace_lock(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    path = root / ".dang_chay.lock"
    try:
        handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError(f"Một tool khác đang ghi thư mục này. Nếu đã đóng mọi tool, kiểm tra rồi xóa {path}.") from None
    try:
        os.write(handle, str(os.getpid()).encode("ascii"))
        os.close(handle)
        yield
    finally:
        path.unlink(missing_ok=True)
