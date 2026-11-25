"""YAML config loading, secret-safe credential lookup, and stage dependency checks."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

from .paths import resolve_paths, resolve_project_root


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML configuration dictionary safely."""
    import yaml  # noqa: PLC0415

    content = Path(path).read_text(encoding="utf-8")
    loaded = yaml.safe_load(content)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError(f"YAML configuration must be a mapping: {path}")
    return loaded


def load_project_config(
    project_root: str | Path | None = None,
    config_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load configs/project.yaml if present, falling back to safe defaults."""
    root = resolve_project_root(user_root=project_root)
    target = Path(config_path) if config_path else (root / "configs" / "project.yaml")
    if target.is_file():
        return load_yaml(target)
    return {
        "project": {"root": None, "data_root": "data", "output_root": "san_pham", "resources_root": "resources"},
        "runtime": {"environment": "auto", "device": "auto", "encoding": "utf-8"},
    }


def load_method_config(name: str, project_root: str | Path | None = None) -> dict[str, Any]:
    """Load configs/methods/<name>.yaml."""
    paths = resolve_paths(user_root=project_root)
    target = paths.configs_root / "methods" / f"{name}.yaml"
    return load_yaml(target) if target.is_file() else {}


def get_credential(
    env_var: str,
    *,
    project_root: str | Path | None = None,
    env_files: tuple[str, ...] = (".env", ".env.clc_ocr"),
) -> str | None:
    """Resolve an API key from process env vars or local .env files (never logged)."""
    val = os.environ.get(env_var, "").strip()
    if val:
        return val
    try:
        root = resolve_project_root(user_root=project_root)
    except FileNotFoundError:
        return None
    for rel in env_files:
        candidate = root / rel
        if not candidate.is_file():
            continue
        for line in candidate.read_text(encoding="utf-8-sig").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            key, sep, raw_val = stripped.partition("=")
            if sep and key.strip() == env_var:
                cleaned = raw_val.strip().strip('"').strip("'")
                if cleaned:
                    return cleaned
    return None


STAGE_PACKAGES: dict[str, tuple[str, ...]] = {
    "base": ("yaml", "PIL", "pypdfium2", "pandas", "requests", "xlsxwriter"),
    "source_preparation": ("PIL", "pypdfium2"),
    "cleaning": ("yaml", "pandas"),
    "segmentation": ("yaml",),
    "alignment": ("yaml", "requests", "xlsxwriter"),
    "alignment_embeddings": ("huggingface_hub", "sentence_transformers", "numpy"),
    "ocr_han": ("PIL", "requests", "paddleocr", "transformers", "torch"),
    "ocr_viet": ("PIL", "pytesseract", "vietocr", "einops", "torch"),
    "llm": ("requests", "jsonschema"),
}


def find_tesseract_binary(explicit_cmd: str | None = None) -> str | None:
    """Locate Tesseract binary from explicit arg, env TESSERACT_CMD, or PATH."""
    candidate = explicit_cmd or os.environ.get("TESSERACT_CMD", "").strip()
    if candidate:
        p = Path(candidate)
        return str(p) if p.is_file() else shutil.which(candidate)
    return shutil.which("tesseract")


def check_tesseract(explicit_cmd: str | None = None, lang: str = "vie") -> dict[str, Any]:
    """Verify Tesseract binary availability and required traineddata language pack."""
    binary = find_tesseract_binary(explicit_cmd)
    if not binary:
        return {
            "ok": False,
            "binary": None,
            "has_lang": False,
            "message": (
                "Tesseract binary not found. Install Tesseract OCR and ensure 'tesseract' is on PATH "
                "or set TESSERACT_CMD. For Vietnamese, install the 'vie' traineddata pack."
            ),
        }
    try:
        proc = subprocess.run([binary, "--list-langs"], capture_output=True, text=True, check=False, timeout=15)
        langs = {line.strip() for line in (proc.stdout + "\n" + proc.stderr).splitlines() if line.strip()}
        has_lang = lang in langs
        msg = "OK" if has_lang else f"Tesseract found at {binary}, but language pack '{lang}' is missing."
        return {"ok": has_lang, "binary": binary, "has_lang": has_lang, "langs": sorted(langs), "message": msg}
    except OSError as exc:
        return {"ok": False, "binary": binary, "has_lang": False, "message": f"Failed running Tesseract: {exc}"}


def check_dependencies(stage: str, *, require_tesseract: bool = False) -> dict[str, Any]:
    """Inspect stage dependencies without importing heavy GPU packages or downloading models."""
    packages = STAGE_PACKAGES.get(stage, STAGE_PACKAGES["base"])
    missing = [pkg for pkg in packages if importlib.util.find_spec(pkg) is None]
    report: dict[str, Any] = {"stage": stage, "missing_packages": missing, "ok": not missing}
    if require_tesseract or stage == "ocr_viet":
        tess = check_tesseract()
        report["tesseract"] = tess
        if not tess["ok"]:
            report["ok"] = False
    if not report["ok"]:
        hints = []
        if missing:
            hints.append(f"Missing Python packages for stage '{stage}': {', '.join(missing)}.")
        if report.get("tesseract") and not report["tesseract"]["ok"]:
            hints.append(report["tesseract"]["message"])
        report["message"] = " ".join(hints)
    else:
        report["message"] = f"Dependencies for stage '{stage}' are ready."
    return report
