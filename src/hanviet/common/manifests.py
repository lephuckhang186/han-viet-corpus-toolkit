"""Per-stage manifest, configuration snapshot, fingerprint, review status, and error logging."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io import bytes_hash, json_bytes, read_json, write_json


def stage_manifest_payload(
    *,
    stage: str,
    version: str,
    input_manifest: list[dict[str, Any]] | dict[str, Any],
    output_manifest: list[dict[str, Any]] | dict[str, Any],
    config_snapshot: dict[str, Any],
    review_status: str,
    statistics: dict[str, Any] | None = None,
    error_log: list[dict[str, Any]] | None = None,
    input_fingerprint: str | None = None,
    output_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Create a standardized per-stage manifest record without cross-stage orchestration coupling."""
    in_fp = input_fingerprint or bytes_hash(json_bytes(input_manifest))
    out_fp = output_fingerprint or bytes_hash(json_bytes(output_manifest))
    return {
        "schema": "hanviet.stage_manifest.v1",
        "stage": stage,
        "version": version,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_fingerprint": in_fp,
        "output_fingerprint": out_fp,
        "review_status": review_status,
        "config_snapshot": config_snapshot,
        "input_manifest": input_manifest,
        "output_manifest": output_manifest,
        "statistics": statistics or {},
        "error_log": error_log or [],
    }


def write_stage_manifest(path: Path, payload: dict[str, Any]) -> Path:
    """Persist stage manifest JSON atomically."""
    write_json(path, payload)
    return Path(path)


def read_stage_manifest(path: Path) -> dict[str, Any]:
    """Read an existing stage manifest JSON."""
    return read_json(path)
