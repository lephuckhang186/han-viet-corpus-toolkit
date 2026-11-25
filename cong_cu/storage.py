"""Backward-compatible shim for hanviet.source_preparation.storage."""
from hanviet.source_preparation.storage import (
    atomic_bytes,
    backup,
    immutable_bytes,
    read_json,
    sha256,
    workspace_lock,
    write_json,
)

__all__ = [
    "atomic_bytes",
    "backup",
    "immutable_bytes",
    "read_json",
    "sha256",
    "workspace_lock",
    "write_json",
]
