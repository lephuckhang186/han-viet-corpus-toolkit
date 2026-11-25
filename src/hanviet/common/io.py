"""Atomic file operations, SHA-256 checksums, protected writes, and workspace locking."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any


def sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of a file using 1 MiB streaming reads."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bytes_hash(data: bytes, algorithm: str = "sha256") -> str:
    """Compute hex digest for an in-memory bytes buffer."""
    return hashlib.new(algorithm, data).hexdigest()


def json_bytes(data: Any) -> bytes:
    """Serialize data to pretty UTF-8 JSON bytes with trailing newline."""
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def atomic_bytes(path: Path, content: bytes) -> None:
    """Atomically write bytes via temporary file + os.replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".dang_ghi_", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def immutable_bytes(path: Path, content: bytes) -> None:
    """Write bytes only if file does not exist or has identical byte content."""
    path = Path(path)
    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError(f"File đã có nội dung khác: {path}. Chọn phiên bản mới.")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)


def write_protected(files: dict[Path, bytes]) -> None:
    """Verify no destination conflicts before creating any file in the batch."""
    for path, data in files.items():
        p = Path(path)
        if p.exists() and p.read_bytes() != data:
            raise FileExistsError(f"Đã có bản xuất khác nội dung: {p}")
    for path, data in files.items():
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            with p.open("xb") as stream:
                stream.write(data)


def write_json(path: Path, value: Any) -> None:
    """Atomically write JSON with UTF-8 encoding."""
    atomic_bytes(path, json_bytes(value))


_MISSING = object()


def read_json(path: Path, default: Any = _MISSING) -> Any:
    """Read UTF-8 JSON (with optional BOM tolerance)."""
    path = Path(path)
    if not path.exists():
        if default is not _MISSING:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def backup(source: Path, destination: Path) -> str:
    """Copy source to destination safely and verify matching SHA-256."""
    source = Path(source)
    destination = Path(destination)
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
    """Acquire an exclusive lock file under workspace root."""
    root = Path(root)
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
