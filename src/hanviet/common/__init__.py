"""Shared cross-platform utilities: paths, configuration, atomic I/O, stage manifests, and LLM client."""

from .io import (
    atomic_bytes,
    backup,
    bytes_hash,
    immutable_bytes,
    json_bytes,
    read_json,
    sha256,
    workspace_lock,
    write_json,
    write_protected,
)
from .paths import ProjectPaths, detect_runtime, resolve_device, resolve_paths, resolve_project_root

__all__ = [
    "ProjectPaths",
    "atomic_bytes",
    "backup",
    "bytes_hash",
    "detect_runtime",
    "immutable_bytes",
    "json_bytes",
    "read_json",
    "resolve_device",
    "resolve_paths",
    "resolve_project_root",
    "sha256",
    "workspace_lock",
    "write_json",
    "write_protected",
]
