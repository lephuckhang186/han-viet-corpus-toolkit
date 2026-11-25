"""Cross-platform path, runtime environment, and compute device resolution."""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
import re
from typing import Any


ROOT_MARKERS = ("ten_file.py", "pyproject.toml")


def detect_runtime(explicit: str = "auto") -> str:
    """Detect whether running in kaggle, colab, or local environment."""
    if explicit and explicit != "auto":
        if explicit not in {"local", "kaggle", "colab"}:
            raise ValueError(f"Unsupported runtime environment: {explicit!r}")
        return explicit
    env_override = os.environ.get("HANVIET_ENV", "").strip().lower()
    if env_override and env_override != "auto":
        if env_override in {"local", "kaggle", "colab"}:
            return env_override
    if Path("/kaggle/working").is_dir() or os.environ.get("KAGGLE_KERNEL_RUN_TYPE"):
        return "kaggle"
    try:
        if importlib.util.find_spec("google.colab") is not None:
            return "colab"
    except (ImportError, ValueError):
        pass
    return "local"


def resolve_device(explicit: str = "auto") -> str:
    """Resolve compute device with safe CPU fallback when CUDA/torch is unavailable."""
    chosen = (os.environ.get("HANVIET_DEVICE") or explicit or "auto").strip()
    if chosen != "auto":
        return chosen
    try:
        if importlib.util.find_spec("torch") is not None:
            import torch  # noqa: PLC0415

            if torch.cuda.is_available():
                return "gpu:0"
    except Exception:
        pass
    return "cpu"


def _find_repo_root(start: Path) -> Path | None:
    resolved = start.expanduser().resolve()
    for candidate in (resolved, *resolved.parents):
        if any((candidate / marker).is_file() for marker in ROOT_MARKERS):
            return candidate
    return None


def resolve_project_root(
    user_root: str | Path | None = None,
    config_root: str | Path | None = None,
    start_dir: str | Path | None = None,
) -> Path:
    """Resolve project root via priority:
    1. Explicit user-provided argument
    2. HANVIET_PROJECT_ROOT environment variable
    3. Configuration file value (project.root)
    4. Auto-discovery from start_dir / cwd / package location using repo markers.
    """
    if user_root:
        return Path(user_root).expanduser().resolve()
    env_root = os.environ.get("HANVIET_PROJECT_ROOT", "").strip()
    if env_root:
        return Path(env_root).expanduser().resolve()
    if config_root:
        return Path(config_root).expanduser().resolve()
    for candidate in (
        Path(start_dir) if start_dir else Path.cwd(),
        Path(__file__).resolve().parents[3],
    ):
        found = _find_repo_root(candidate)
        if found is not None:
            return found
    raise FileNotFoundError(
        "Could not resolve repository root containing ten_file.py or pyproject.toml. "
        "Provide user_root or set HANVIET_PROJECT_ROOT."
    )


def resolve_subpath(
    value: str | Path | None,
    root: Path,
    default_relative: str,
    env_var: str | None = None,
) -> Path:
    """Resolve a configurable path cleanly handling relative, absolute, spaces, and UTF-8 names."""
    raw: str | Path | None = value
    if raw is None and env_var:
        env_val = os.environ.get(env_var, "").strip()
        if env_val:
            raw = env_val
    if raw is None:
        raw = default_relative
    p = Path(raw).expanduser()
    return p.resolve() if p.is_absolute() else (root / p).resolve()


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    data_root: Path
    output_root: Path
    resources_root: Path
    dict_root: Path
    configs_root: Path
    prompts_root: Path
    schemas_root: Path
    cache_root: Path

    def member_output_root(self, member: str | int) -> Path:
        label = f"TV{member:02d}" if isinstance(member, int) else str(member)
        if not re.fullmatch(r"TV\d{2}", label):
            raise ValueError(f"Invalid member code: {member!r}")
        return self.output_root / label

    def book_output_root(self, topic: str, book_code: str, member: str | int) -> Path:
        return self.member_output_root(member) / f"{topic}_{book_code}"


def resolve_paths(
    user_root: str | Path | None = None,
    config: dict[str, Any] | None = None,
    *,
    data_root: str | Path | None = None,
    output_root: str | Path | None = None,
    resources_root: str | Path | None = None,
    cache_root: str | Path | None = None,
) -> ProjectPaths:
    """Resolve all project directories using user args -> env vars -> config -> defaults."""
    project_cfg = (config or {}).get("project", {}) if config else {}
    root = resolve_project_root(user_root=user_root, config_root=project_cfg.get("root"))
    runtime = detect_runtime((config or {}).get("runtime", {}).get("environment", "auto"))

    default_cache = (
        "/kaggle/temp/hanviet_cache"
        if runtime == "kaggle"
        else "/content/hanviet_cache"
        if runtime == "colab"
        else ".cache/hanviet"
    )
    resolved_resources = resolve_subpath(
        resources_root if resources_root is not None else project_cfg.get("resources_root"),
        root,
        "resources",
        "HANVIET_RESOURCES_ROOT",
    )
    dict_cfg = project_cfg.get("dict_root")
    resolved_dict = resolve_subpath(dict_cfg, root, "dict")
    if not resolved_dict.is_dir() and (resolved_resources / "dictionaries").is_dir():
        resolved_dict = resolved_resources / "dictionaries"

    return ProjectPaths(
        root=root,
        data_root=resolve_subpath(
            data_root if data_root is not None else project_cfg.get("data_root"),
            root,
            "data",
            "HANVIET_DATA_ROOT",
        ),
        output_root=resolve_subpath(
            output_root if output_root is not None else project_cfg.get("output_root"),
            root,
            "san_pham",
            "HANVIET_OUTPUT_ROOT",
        ),
        resources_root=resolved_resources,
        dict_root=resolved_dict,
        configs_root=root / "configs",
        prompts_root=root / "prompts",
        schemas_root=root / "schemas",
        cache_root=resolve_subpath(
            cache_root if cache_root is not None else project_cfg.get("cache_root"),
            root,
            default_cache,
            "HANVIET_CACHE_DIR",
        ),
    )
